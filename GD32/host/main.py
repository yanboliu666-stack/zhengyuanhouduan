"""影子运行主循环（宿主机）：视觉感知 → 决策层 → GD32 微型红绿灯。

这是把 zhengyuan 逻辑层（DecisionLayer）与 GD32 微型信号机串起来的板子主程序，
语义对齐 zhengyuan 的 ``main.py``，但控制接口换成 GD32 串口（软请求 + 状态回读）：

    感知 JSON 文件 ──读──> DecisionLayer.tick() ──> G32Link.request_phase() ──> GD32
                                    ▲                                        │
                                    └────────── 状态回读 G32Link.poll() ───────┘

边界说明（务必理解，不要破坏）：
  * 软请求：只发「相位指示」，绝不直接下发灯色或配时。最小绿 / 最大绿 / 黄灯 /
    全红 / 失联全红由 GD32 固件本地裁决，固件可拒绝或推迟切换。
  * 执行反馈：决策层不乐观地假设灯已切换，而是等 GD32 回读状态确认当前相位。
  * 遇问题回退并告警：感知断流 → 决策层 FAILSAFE → 请求黄闪（交 GD32 本地兜底）；
    感知恢复 → 重新接管 + 复位；链路丢失 → 心跳判故障 → 告警；收到 SIGINT/SIGTERM
    → 摘除 + 关闭 + 优雅退出。

用法（GD32 目录）::

    python main.py --config configs/shadow.yaml                 # 接串口跑（无限循环）
    python main.py --config configs/shadow.yaml --max-ticks 5   # 离线冒烟（NullTransport）
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from host.driver import MiniSignalDriver
from host.gd32_link import G32Link, Heartbeat, LinkMode, PhaseMapping
from host.perception import read_perception
from host.protocol import Special
from host.transports import NullTransport, SerialTransport, Transport

log = logging.getLogger("gd32.main")


# --------------------------------------------------------------------------- #
# 路径引导：让本进程能找到 GD32/host 与 zhengyuan 的 traffic_control / interface
# --------------------------------------------------------------------------- #
def _ensure_paths() -> None:
    here = Path(__file__).resolve().parent          # GD32/host
    gd32_root = here.parent                          # GD32/
    for p in (str(gd32_root), str(here.parent)):
        if p not in sys.path:
            sys.path.insert(0, p)
    # zhengyuan 根目录（env 覆盖，默认 GD32 的兄弟目录 ../zhengyuan）。
    zhengyuan = Path(
        __import__("os").environ.get("ZHENGYUAN_ROOT", gd32_root.parent / "zhengyuan")
    )
    for p in (str(zhengyuan), str(zhengyuan / "src")):
        if p not in sys.path:
            sys.path.insert(0, p)


_ensure_paths()

from traffic_control.config_loader import load_config  # noqa: E402
from traffic_control.decision_layer import DecisionLayer  # noqa: E402
from traffic_control.degradation import DegradationMode  # noqa: E402
from traffic_control.models import ControllerState  # noqa: E402
from traffic_control.perception import CANONICAL_LANE_IDS  # noqa: E402
from traffic_control.phasing import phase_groups  # noqa: E402
from traffic_control.structured_log import (  # noqa: E402
    BlackBox,
    JsonlFileSink,
    LoggingPipeline,
    MqttCloudSink,
    NullCloudSink,
    compute_config_hash,
)
from traffic_control.telemetry import AlarmEvent, AlarmType  # noqa: E402


# --------------------------------------------------------------------------- #
# 构建传输 / 链路
# --------------------------------------------------------------------------- #
def build_transport(cfg: Mapping[str, Any]) -> Transport:
    t = cfg["type"]
    if t is None or t == "null":
        return NullTransport()
    if t == "serial":
        s = cfg.get("serial", {})
        return SerialTransport(
            port=s.get("port", "/dev/ttyUSB0"),
            baudrate=int(s.get("baudrate", 115200)),
        )
    raise ValueError(f"unsupported transport type: {t!r}")


def build_link(cfg: Mapping[str, Any], gd32_root: Path) -> G32Link:
    mapping = PhaseMapping.from_yaml(gd32_root / cfg["phase_mapping"])
    hb = cfg.get("heartbeat", {})
    return G32Link(
        transport=build_transport(cfg["transport"]),
        mapping=mapping,
        heartbeat=Heartbeat(
            interval_s=float(hb.get("interval_s", 1.0)),
            timeout_s=float(hb.get("timeout_s", 0.5)),
            max_missed=int(hb.get("max_missed", 3)),
        ),
    )


# --------------------------------------------------------------------------- #
# 结构化日志 / 云端上报（复用 zhengyuan structured_log，契约见 logging-data-contract.md）
# --------------------------------------------------------------------------- #
_cloud_log = logging.getLogger("gd32.cloud")


class LoggingMqttCloudSink(MqttCloudSink):
    """带连接状态日志的 MQTT 云端上报（不改 zhengyuan 代码，只加日志）。"""

    def _on_connect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        super()._on_connect(client, userdata, flags, reason_code, properties)
        _cloud_log.info("cloud connected")

    def _on_disconnect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        super()._on_disconnect(client, userdata, flags, reason_code, properties)
        _cloud_log.warning("cloud disconnected")


def build_cloud_sink(cfg: Mapping[str, Any], junction_id: str) -> Any:
    """按 shadow.yaml 的 cloud 段构建云端上报（mqtt / null）。"""
    cloud = cfg.get("cloud") or {}
    if not cloud or cloud.get("type") != "mqtt":
        return NullCloudSink()
    _cloud_log.info(
        "cloud uploading enabled -> mqtt://%s:%s (topic=%s/%s)",
        cloud["host"], cloud.get("port", 1883),
        cloud.get("topic_prefix", "traffic-control"), junction_id,
    )
    return LoggingMqttCloudSink(
        junction_id,
        host=str(cloud["host"]),
        port=int(cloud.get("port", 1883)),
        username=cloud.get("username"),
        password=cloud.get("password"),
        tls=bool(cloud.get("tls", False)),
        qos=int(cloud.get("qos", 1)),
        topic_prefix=str(cloud.get("topic_prefix", "traffic-control")),
        keepalive_s=int(cloud.get("keepalive_s", 60)),
        client_id=cloud.get("client_id"),
    )


class FilteredLoggingPipeline(LoggingPipeline):
    """过滤良性告警：信号机处于清空/启动/故障（非 NORMAL）时的静默不是真故障。

    决策层在这些阶段正确闭嘴，但每 tick 会发一条 ``no_feasible_phase``
    (reason=controller_not_normal/unknown_current_phase)，会刷屏云端。
    这里把它们静默掉（真正的 no_feasible_successor 等仍照常上报）。
    """

    _BENIGN_REASONS = frozenset(
        {"controller_not_normal", "unknown_current_phase", "invalid_phase_start_time"}
    )

    def report_alarm(self, event: AlarmEvent) -> None:
        if (
            event.alarm_type == AlarmType.NO_FEASIBLE_PHASE
            and (event.detail or {}).get("reason") in self._BENIGN_REASONS
        ):
            return  # 良性静默，不上云
        super().report_alarm(event)


def build_logging(
    cfg: Mapping[str, Any], junction_id: str, config_hash: str, cloud_sink: Any
) -> LoggingPipeline:
    """本地 JSONL 落盘 + 黑匣子 + 可选云端上报。"""
    log_cfg = cfg.get("logging") or {}
    directory = str(log_cfg.get("directory", "/tmp/gd32-traffic/logs"))
    file_sink = JsonlFileSink(
        directory,
        retention_days=int(log_cfg.get("retention_days", 7)),
    )
    black_box = BlackBox(max_ticks=int(log_cfg.get("black_box_ticks", 120)))
    return FilteredLoggingPipeline(
        junction_id=junction_id,
        boot_id=uuid.uuid4().hex,
        config_hash=config_hash,
        file_sink=file_sink,
        cloud_sink=cloud_sink,
        black_box=black_box,
        crash_dump_path=Path(directory) / "tick.crash",
    )


def build_traffic_state(
    junction_id: str, now: float, state: ControllerState, result: Any
) -> dict[str, Any]:
    """构造「交通状态」快照，供云端看板渲染（替代本地 8090 看板）。

    8 个规范车道全部显式给出（无车补 0），云端无需知道规范 ID 即可渲染。
    """
    lanes = {}
    for lane_id in sorted(CANONICAL_LANE_IDS):
        ls = result.lane_states.get(lane_id)
        lanes[lane_id] = {
            "vehicle_count": ls.vehicle_count if ls is not None else 0,
            "oldest_wait_s": ls.oldest_wait_s if ls is not None else 0.0,
            "downstream_blocked": ls.downstream_blocked if ls is not None else False,
        }
    phases = {
        pid: {
            "vehicle_count": d.vehicle_count,
            "oldest_wait_s": d.oldest_wait_s,
        }
        for pid, d in result.demands.items()
    }
    return {
        "junction_id": junction_id,
        "ts_wall": now,
        "current_phase_id": state.current_phase_id,
        "degradation": result.degradation.value,
        "lanes": lanes,
        "phases": phases,
    }


def build_timings(
    layer: DecisionLayer, mapping: PhaseMapping
) -> list[tuple[float, float, float, float]]:
    """按固件相位编号 1..4 排序，取出决策层各相位的配时（配时对齐）。"""
    phases = layer.runtime.phases
    ordered = sorted(mapping.phases.items(), key=lambda kv: kv[1])
    timings: list[tuple[float, float, float, float]] = []
    for phase_id, _ in ordered:
        phase = phases[phase_id]
        timings.append(
            (phase.min_green_s, phase.max_green_s, phase.yellow_s, phase.all_red_s)
        )
    return timings


def apply_phase_timing(
    config: Mapping[str, Any], timing_map: Mapping[str, Mapping[str, float]]
) -> dict[str, Any]:
    """把影子运行所需的相位配时覆盖进决策层配置的 ``signal.phases``。

    只覆盖配时（min/max/yellow/all_red）；``movement_ids`` 从决策层布局派生，
    其余一切（评分权重 / 优先级 / 阈值 / 行人 / 降级等）**全部沿用决策层配置**。
    这样用户以后调决策权重、改算法参数，只需改 decision_config 那份 YAML，
    无需再动本接口层。
    """
    layout = config["signal"]["layout"]
    groups = phase_groups(layout["mode"], layout.get("main_road_direction"))
    phases: list[dict[str, Any]] = []
    for group in groups:
        timing = timing_map.get(group.phase_id)
        if timing is None:
            raise ValueError(
                f"shadow.yaml 的 signal_phases 缺少相位 {group.phase_id!r}；"
                f"布局派生相位为 {sorted(g.phase_id for g in groups)}"
            )
        phases.append(
            {
                "phase_id": group.phase_id,
                "movement_ids": sorted(group.movement_ids),
                "min_green_s": float(timing["min_green_s"]),
                "max_green_s": float(timing["max_green_s"]),
                "yellow_s": float(timing["yellow_s"]),
                "all_red_s": float(timing.get("all_red_s", 0.0)),
            }
        )
    merged = dict(config)
    merged["signal"] = {**config["signal"], "phases": phases}
    return merged


def load_shadow_decision_config(
    cfg: Mapping[str, Any],
    gd32_root: Path,
    decision_config_override: str | None = None,
) -> dict[str, Any]:
    """加载决策层配置，并叠加影子运行的相位配时覆盖。"""
    path = decision_config_override or cfg["decision_config"]
    config = load_config(gd32_root / path)
    timing = cfg.get("signal_phases")
    if timing:
        config = apply_phase_timing(config, timing)
    return config


# --------------------------------------------------------------------------- #
# 指挥中心接管 / 摘除（占位：命令文件，跨进程方式待定）
# --------------------------------------------------------------------------- #
def check_control_room(
    layer: DecisionLayer, link: G32Link, cmd_path: Path | None, now: float
) -> None:
    if cmd_path is None:
        return
    try:
        cmd = json.loads(cmd_path.read_text(encoding="utf-8")).get("command")
    except (OSError, ValueError, json.JSONDecodeError):
        return
    if cmd == "takeover" and not layer.manual_override:
        layer.takeover(now)
        link.request_takeover()
        log.warning("control room takeover")
    elif cmd == "release" and layer.manual_override:
        layer.release(now)
        link.reset()
        log.info("control room release")


# --------------------------------------------------------------------------- #
# 主循环
# --------------------------------------------------------------------------- #
def run_loop(
    layer: DecisionLayer,
    link: G32Link,
    driver: MiniSignalDriver,
    pipeline: LoggingPipeline,
    cloud_sink: Any,
    junction_id: str,
    perception_path: Path,
    signal_state_path: Path,
    tick_period_s: float,
    heartbeat_interval_s: float,
    initial_phase: str,
    cmd_path: Path | None,
    max_ticks: int | None,
) -> None:
    ticks = 0
    last_poll = 0.0
    fault_active = False
    initial_requested = False
    last_status_key: tuple | None = None

    while True:
        now = time.time()

        check_control_room(layer, link, cmd_path, now)

        observations, downstream = read_perception(perception_path, now)
        state: ControllerState = driver.state(now)
        result = layer.tick(now, state, observations, downstream)
        # 每 tick 全量落盘；相位/降级/模式变化等事件由管线触发上云。
        pipeline.on_tick(state, result)
        # 周期性上传感知/交通状态（供云端看板，替代本地 8090 看板）。
        if cloud_sink is not None:
            cloud_sink.publish_event(
                "traffic_state", build_traffic_state(junction_id, now, state, result)
            )

        # 启动序列结束后需要从某个相位起步；决策层不提议「第一个相位」。
        # FAILSAFE（感知断流）时不请求首绿，改走下方黄闪兜底。
        if result.startup is None:
            if (
                state.current_phase_id is None
                and result.degradation is not DegradationMode.FAILSAFE
            ):
                if not initial_requested:
                    link.request_phase(initial_phase, reason="initial_green")
                    initial_requested = True
                    log.info("request initial green -> %s", initial_phase)
            else:
                _apply_decision(link, state, result.decision, now)

        # 故障检测：感知断流 → 请求黄闪（固件黄闪 2×超时后会自动切本地固定配时）。
        # 恢复：直接判读感知文件新鲜度。固件切本地固定配时后，决策层会被静默
        # （mode=LOCAL → MANUAL_OVERRIDE），此时 result.degradation 恒为 NORMAL，
        # 不能再拿它判断「感知是否恢复」。
        if result.degradation is DegradationMode.FAILSAFE:
            if not fault_active:
                link.request_special(Special.FLASH, reason="failsafe")
                fault_active = True
                log.error("FAILSAFE: perception dead — flash yellow")
        elif fault_active and perception_is_fresh(
            perception_path, now, layer.parameters.observation_timeout_s
        ):
            link.request_takeover()
            link.reset()
            fault_active = False
            log.warning("perception recovered — re-takeover and reset GD32")

        # 心跳 / 状态轮询（执行反馈的来源）。
        if now - last_poll >= heartbeat_interval_s:
            last_poll = now
            status = link.poll()
            driver.update(status, link.mode, time.time())
            if status is not None:
                # 把当前绿灯相位写入共享文件，供闭环合成感知源读取（绿灯方向驶离）。
                write_signal_state(signal_state_path, status, link.mapping, time.time())
                # 诊断日志：固件灯态变化时打印，用于核对固件计时是否与决策层一致。
                key = (status.active_phase, status.stage)
                if key != last_status_key:
                    last_status_key = key
                    log.info(
                        "GD32 -> phase=%s stage=%s elapsed_ms=%d",
                        status.active_phase, status.stage, status.phase_elapsed_ms,
                    )
            if link.mode is LinkMode.FAULT:
                if status is not None:
                    # 链路恢复：重新接管 + 复位，让 GD32 重跑启动序列（规格书 §6.4）。
                    link.request_takeover()
                    link.reset()
                    log.warning("link recovered — re-takeover and reset GD32")
                else:
                    log.error("link fault — GD32 unreachable (misses=%d)", link.heartbeat.misses)
                    pipeline.publish_event(
                        "heartbeat_fault",
                        {
                            "ts_wall": now,
                            "link_mode": link.mode.value,
                            "consecutive_misses": link.heartbeat.misses,
                        },
                    )

        ticks += 1
        if max_ticks is not None and ticks >= max_ticks:
            break
        time.sleep(max(0.0, tick_period_s - (time.time() - now)))


def _apply_decision(
    link: G32Link, state: ControllerState, decision: Any, now: float
) -> None:
    """把决策层的 PhaseDecision 下发给 GD32（软请求，仅在切换时发）。"""
    proposed = decision.selected_phase_id
    all_red_required = "all_red_required" in decision.constraints_applied

    if not decision.feasible and all_red_required:
        link.request_phase(None, reason=decision.reason, all_red_required=True)
        return

    if decision.feasible and proposed is not None and proposed != state.current_phase_id:
        link.request_phase(
            proposed, reason=decision.reason, all_red_required=all_red_required
        )
        log.info(
            "request switch -> %s (reason=%s, green=%.1fs)",
            proposed, decision.reason, now - state.phase_started_at,
        )


# --------------------------------------------------------------------------- #
# 信号状态共享（闭环合成感知源读取：绿灯方向车辆驶离）
# --------------------------------------------------------------------------- #
_STAGE_NAMES = {0: "green", 1: "yellow", 2: "all_red", 3: "flash", 4: "off"}


def write_signal_state(
    path: Path, status: Any, mapping: PhaseMapping, now: float
) -> None:
    """把 GD32 回读的当前相位/阶段写入共享 JSON，供感知源闭环使用。"""
    phase_id = mapping.phase_id(status.active_phase) if 1 <= status.active_phase <= 4 else None
    data = {
        "phase_id": phase_id,
        "stage": _STAGE_NAMES.get(status.stage, "unknown"),
        "updated_at": now,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def perception_is_fresh(path: Path, now: float, timeout_s: float) -> bool:
    """直接判读感知文件的 ``observed_at`` 是否新鲜（不依赖决策层）。

    用于故障恢复：固件切本地固定配时后决策层被静默，无法再用 ``result.degradation``
    判断感知是否恢复，因此这里直接读文件时间戳。
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return (now - float(raw.get("observed_at", 0.0))) <= timeout_s
    except (OSError, ValueError, json.JSONDecodeError):
        return False


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GD32 影子运行控制接口层")
    p.add_argument("--config", default="configs/shadow.yaml", help="影子运行配置 YAML")
    p.add_argument("--decision-config", default=None, help="覆盖 shadow.yaml 里的 decision_config")
    p.add_argument("--max-ticks", type=int, default=None, help="跑 N 个 tick 后停止（离线冒烟用）")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    gd32_root = Path(__file__).resolve().parent.parent
    cfg = yaml.safe_load((gd32_root / args.config).read_text(encoding="utf-8"))

    config = load_shadow_decision_config(cfg, gd32_root, args.decision_config)
    junction_id = str(cfg.get("junction_id", "mini_1"))
    cloud_sink = build_cloud_sink(cfg, junction_id)
    pipeline = build_logging(cfg, junction_id, compute_config_hash(config), cloud_sink)
    layer = DecisionLayer(config, sink=pipeline)
    link = build_link(cfg["link"], gd32_root)
    driver = MiniSignalDriver(link.mapping)

    link.open()
    log.info("transport opened (%s)", cfg["link"]["transport"]["type"])

    # 请求远程控制权并复位固件状态机，使双方启动序列（5s 黄闪 + 10s 全红）对齐。
    link.request_takeover()
    link.reset()
    link.configure_timing(build_timings(layer, link.mapping))

    initial_phase = cfg.get("initial_phase") or next(iter(layer.runtime.phases))

    def stop(signum: int, _frame: object) -> None:
        log.info("signal %s received — shutting down", signum)
        raise KeyboardInterrupt

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, stop)
        except (ValueError, OSError):
            pass

    cmd_path = cfg.get("control_room", {}).get("command_path")
    signal_state_path = Path(
        cfg.get("signal_state_path", "/tmp/gd32-traffic/signal_state.json")
    )
    try:
        run_loop(
            layer=layer,
            link=link,
            driver=driver,
            pipeline=pipeline,
            cloud_sink=cloud_sink,
            junction_id=junction_id,
            perception_path=Path(cfg["perception"]["input_path"]),
            signal_state_path=signal_state_path,
            tick_period_s=float(cfg["tick_period_s"]),
            heartbeat_interval_s=float(cfg["link"]["heartbeat"].get("interval_s", 1.0)),
            initial_phase=initial_phase,
            cmd_path=Path(cmd_path) if cmd_path else None,
            max_ticks=args.max_ticks,
        )
    except KeyboardInterrupt:
        pass
    finally:
        log.info("detaching from GD32 signal controller")
        try:
            link.request_detach()
        finally:
            link.close()
            pipeline.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
