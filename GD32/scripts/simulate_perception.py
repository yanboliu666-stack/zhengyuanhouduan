#!/usr/bin/env python3
"""闭环合成感知源（演示用）：模拟视觉感知层，按 ≥2 Hz 写感知 JSON 快照。

与旧版（固定时间表、开环）不同，本版是**闭环**：
  - 读取主循环写出的 ``signal_state.json``（当前绿灯相位）；
  - 绿灯方向：车辆以一定速率「驶离」（队列减少）；
  - 红灯方向：车辆随机「到达」（队列增加）；
  - 存在 ``fault.flag`` 时：**停止输出**（感知断流），模拟感知层故障，
    用于观察主循环/决策层进入 FAILSAFE 黄闪兜底与恢复。

用法::

    python scripts/simulate_perception.py \
        --out /tmp/gd32-traffic/perception.json \
        --signal-state /tmp/gd32-traffic/signal_state.json \
        --fault-flag /tmp/gd32-traffic/fault.flag

帧格式与 zhengyuan ``docs/perception-interface.md`` §8 完全一致；原子写。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from collections import deque
from pathlib import Path

# 方向 -> (直行/左转) -> 规范 lane_id
LANE_OF = {
    ("N", "through"): "north_through",
    ("N", "left"): "north_left",
    ("E", "through"): "east_through",
    ("E", "left"): "east_left",
    ("S", "through"): "south_through",
    ("S", "left"): "south_left",
    ("W", "through"): "west_through",
    ("W", "left"): "west_left",
}
# 决策层相位 -> 方向
PHASE_DIR = {"P_N": "N", "P_E": "E", "P_S": "S", "P_W": "W"}
DIRS = ("N", "E", "S", "W")


def read_signal_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"phase_id": None, "stage": None}


def green_direction(signal: dict) -> str | None:
    if signal.get("stage") == "green" and signal.get("phase_id") in PHASE_DIR:
        return PHASE_DIR[signal["phase_id"]]
    return None


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser(description="闭环合成感知源（影子运行演示）")
    ap.add_argument("--out", default="/tmp/gd32-traffic/perception.json")
    ap.add_argument("--signal-state", default="/tmp/gd32-traffic/signal_state.json")
    ap.add_argument("--fault-flag", default="/tmp/gd32-traffic/fault.flag")
    ap.add_argument("--rate", type=float, default=2.0, help="写帧频率 Hz（≥2）")
    ap.add_argument("--drain-rate", type=float, default=1.0, help="绿灯方向驶离速率（辆/秒）")
    ap.add_argument("--arrival-prob", type=float, default=0.07,
                    help="每个红灯方向每 tick 的来车概率（≈0.14 辆/秒/向）")
    ap.add_argument("--max-queue", type=int, default=15, help="单方向最大排队长度（防无限增长）")
    args = ap.parse_args()

    out = Path(args.out)
    sig_path = Path(args.signal_state)
    flag_path = Path(args.fault_flag)
    period = 1.0 / max(args.rate, 0.1)

    # 每方向车辆队列：(track_id, lane)，lane ∈ {through, left}
    cars: dict[str, deque] = {d: deque() for d in DIRS}
    next_id = 100

    def add_car(d: str, lane: str) -> None:
        nonlocal next_id
        cars[d].append((next_id, lane))
        next_id += 1

    def init_dir(d: str, n: int) -> None:
        """给方向 d 预置 n 辆车（约 75% 直行 / 25% 左转）。"""
        for _ in range(n):
            add_car(d, "through" if random.random() < 0.75 else "left")

    # 初始队列：4 向合计约 20 辆，随机分布（每向 2~8 辆，约 75% 直行 / 25% 左转）
    for d in DIRS:
        init_dir(d, random.randint(2, 8))

    drain_acc = 0.0
    was_fault = False

    print(
        f"closed-loop perception: {out} @{args.rate}Hz | "
        f"drain={args.drain_rate}/s | signal_state={sig_path} | "
        f"fault_flag={flag_path} (Ctrl+C to stop)",
        flush=True,
    )
    try:
        while True:
            wall = time.time()

            # 故障注入：感知层停止输出（断流），直到标志被清除
            if flag_path.exists():
                if not was_fault:
                    print("⚠ 故障注入：感知层停止输出（断流）", flush=True)
                    was_fault = True
                time.sleep(period)
                continue
            if was_fault:
                print("✅ 感知恢复：继续输出", flush=True)
                was_fault = False

            sig = read_signal_state(sig_path)
            g = green_direction(sig)

            # 绿灯方向驶离
            if g is not None:
                drain_acc += period * args.drain_rate
                while drain_acc >= 1.0 and cars[g]:
                    cars[g].popleft()
                    drain_acc -= 1.0
                if not cars[g]:
                    drain_acc = 0.0

            # 红灯方向随机来车（绿灯方向不放车；单方向封顶防无限增长）
            for d in DIRS:
                if d == g:
                    continue
                if len(cars[d]) < args.max_queue and random.random() < args.arrival_prob:
                    add_car(d, "through" if random.random() < 0.75 else "left")

            # 组装帧
            detections = [
                {
                    "track_id": tid,
                    "lane_id": LANE_OF[(d, lane)],
                    "observed_at": wall,
                    "speed_mps": 0.2,
                    "confidence": 0.95,
                }
                for d in DIRS
                for (tid, lane) in cars[d]
            ]
            atomic_write(out, {"observed_at": wall, "detections": detections, "downstream": []})
            time.sleep(max(0.0, period - (time.time() - wall)))
    except KeyboardInterrupt:
        pass
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
