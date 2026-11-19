"""GD32 微型信号机控制链路：决策层相位 → 相位映射 → 协议 → 传输 → 心跳/接管。

这是「本地临时控制接口层」的核心：把 zhengyuan 逻辑层输出的 ``PhaseDecision``
（软请求，只提相位建议）翻译成串口帧下发给 GD32 微型信号机，并通过状态回读
闭环执行反馈。**只发相位指示，绝不直接下发灯色**——灯色与配时由 GD32 固件本地
裁决（最小绿/黄灯/全红/失联全红），这与 zhengyuan ``interface/hikvision`` 的
软请求边界一致。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping, Optional

import yaml

from host.protocol import (
    Command,
    Frame,
    PhaseAck,
    Result,
    ResultAck,
    Special,
    StatusFrame,
    decode_frame,
    encode_config_timing,
    encode_frame,
)
from host.transports import Transport


class LinkMode(str, Enum):
    LOCAL = "local"    # GD32 本地自动运行
    REMOTE = "remote"  # 上位机远程控制（已接管）
    FAULT = "fault"    # 链路故障（应回退本地并报警）


@dataclass
class Heartbeat:
    """周期状态查询充当心跳，连续无响应判定断线。"""

    interval_s: float = 1.0
    timeout_s: float = 0.5
    max_missed: int = 3
    _missed: int = field(default=0, init=False, repr=False)

    def record(self, responded: bool) -> None:
        self._missed = 0 if responded else self._missed + 1

    @property
    def link_lost(self) -> bool:
        return self._missed >= self.max_missed

    @property
    def misses(self) -> int:
        return self._missed

    def reset(self) -> None:
        self._missed = 0


@dataclass(frozen=True)
class PhaseMapping:
    """决策层 phase_id ↔ 固件相位编号 / 特殊态的映射（来自 YAML）。"""

    controller_address: int
    phases: Mapping[str, int]
    special: Mapping[str, int]

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PhaseMapping":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(
            controller_address=int(data.get("controller_address", 0x01)),
            phases={str(k): int(v) for k, v in data["phases"].items()},
            special={str(k): int(v) for k, v in (data.get("special") or {}).items() if v is not None},
        )

    def phase_number(self, phase_id: str) -> int:
        if phase_id not in self.phases:
            raise KeyError(f"no GD32 phase mapped for decision phase {phase_id!r}")
        return self.phases[phase_id]

    def phase_id(self, phase_number: int) -> str | None:
        for pid, num in self.phases.items():
            if num == phase_number:
                return pid
        return None


@dataclass
class G32Link:
    """宿主机 ↔ GD32E230 微型信号机的控制接口。"""

    transport: Transport
    mapping: PhaseMapping
    heartbeat: Heartbeat = field(default_factory=Heartbeat)
    _mode: LinkMode = field(default=LinkMode.LOCAL, init=False, repr=False)
    _requested_phase: int | None = field(default=None, init=False, repr=False)
    _last_status: StatusFrame | None = field(default=None, init=False, repr=False)
    _last_rx: bytes | None = field(default=None, init=False, repr=False)
    _last_rx_cmd: int | None = field(default=None, init=False, repr=False)

    # ------------------------------------------------------------------ 生命周期
    def open(self) -> None:
        self.transport.open()

    def close(self) -> None:
        self.transport.close()

    # ------------------------------------------------------------------ 相位指示
    def request_phase(
        self,
        phase_id: str | None,
        reason: str = "",
        all_red_required: bool = False,
    ) -> None:
        """把决策层 phase_id 映射成固件相位编号并下发软请求。"""
        if phase_id is None:
            if all_red_required:
                return self.request_special(Special.ALL_RED, reason=reason)
            return  # 决策层未选中相位，不发指示
        phase_number = self.mapping.phase_number(phase_id)
        payload = bytes((phase_number, 0x01 if all_red_required else 0x00))
        self._requested_phase = phase_number
        self._send(Command.PHASE_REQUEST, payload)

    def request_special(self, special: Special, reason: str = "") -> None:
        self._requested_phase = None
        self._send(Command.SPECIAL, bytes((int(special),)))

    def configure_timing(self, timings: list[tuple[float, float, float, float]]) -> None:
        """把决策层各相位的 (min_green, max_green, yellow, all_red)（秒）下发，
        使固件本地最小绿/最大绿/清空时序与决策层一致（配时对齐）。
        """
        self._send(Command.CONFIG_TIMING, encode_config_timing(timings))

    def reset(self) -> None:
        """复位固件信号机状态机，使其重跑 5s 黄闪 + 10s 全红启动序列。"""
        self._send(Command.RESET)

    # ------------------------------------------------------------------ 心跳/状态
    def poll(self) -> StatusFrame | None:
        """状态查询（心跳）。排空串口缓冲直至收到 STATUS，返回解析结果。

        GD32 对每个命令都会回 ACK，串口里会混着 PHASE_ACK / CONFIG_ACK 等帧；
        这里循环读取直到 STATUS（或超时），ACK 只记录、不作为状态返回，
        避免状态回读错位与心跳误判。
        """
        self._send(Command.STATUS_QUERY)
        deadline = time.monotonic() + self.heartbeat.timeout_s
        status: StatusFrame | None = None
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            raw = self.transport.receive(min(0.2, remaining))
            if raw is None:
                break
            self._last_rx = raw
            try:
                frame = decode_frame(raw)
            except Exception:
                continue  # 坏帧/半帧：丢弃，继续排空
            if frame.cmd == Command.STATUS:
                status = StatusFrame.from_payload(frame.payload)
                self._last_status = status
                break
            self._last_rx_cmd = frame.cmd  # ACK 等：记录命令字，继续排空
        self.heartbeat.record(status is not None)
        if self.heartbeat.link_lost:
            self._mode = LinkMode.FAULT
        return status

    # ------------------------------------------------------------------ 接管/摘除
    def request_takeover(self) -> None:
        self._send(Command.TAKEOVER)
        self._mode = LinkMode.REMOTE

    def request_detach(self) -> None:
        self._send(Command.DETACH)
        self._mode = LinkMode.LOCAL

    # ------------------------------------------------------------------ 属性
    @property
    def mode(self) -> LinkMode:
        return self._mode

    @property
    def last_requested_phase(self) -> int | None:
        return self._requested_phase

    @property
    def last_status(self) -> StatusFrame | None:
        return self._last_status

    @property
    def last_rx(self) -> bytes | None:
        return self._last_rx

    # ------------------------------------------------------------------ 内部
    def _send(self, cmd: Command, payload: bytes = b"") -> None:
        frame = encode_frame(self.mapping.controller_address, int(cmd), payload)
        self.transport.send(frame)
