"""感知输入读取：把视觉感知层写入的 JSON 快照转成决策层输入。

文件格式与 zhengyuan ``docs/perception-interface.md`` §8 完全一致（复用
``traffic_control.perception`` 的规范 ID 校验）。文件缺失 / 损坏 / 非 JSON 时
不抛异常，而是返回空输入：决策层把「无数据」与「没车」区分开，会走降级
（FAILSAFE）并告警——感知断流 ≠ 没车。
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from traffic_control.models import VehicleObservation
from traffic_control.perception import (
    DownstreamReport,
    RawDetection,
    downstream_occupancy,
    normalize_detections,
)


def read_perception(
    path: Path, now: float
) -> tuple[tuple[VehicleObservation, ...], dict[str, float | None]]:
    """读取一帧感知 JSON，转换为决策层输入。

    返回 ``(observations, downstream_occupancy_dict)``。读不到 / 损坏时返回
    ``((), {})``（空输入，触发决策层降级）。
    """
    try:
        import json

        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, ImportError):
        return (), {}

    frame_at = float(raw.get("observed_at", now))

    detections = raw.get("detections", [])
    observations: Sequence[VehicleObservation] = normalize_detections(
        RawDetection(
            track_id=int(d["track_id"]),
            lane_id=str(d["lane_id"]),
            observed_at=float(d.get("observed_at", frame_at)),
            speed_mps=(
                float(d["speed_mps"]) if d.get("speed_mps") is not None else None
            ),
            confidence=(
                float(d["confidence"]) if d.get("confidence") is not None else None
            ),
        )
        for d in detections
    )

    reports = raw.get("downstream", [])
    downstream = downstream_occupancy(
        DownstreamReport(
            lane_id=str(r["lane_id"]),
            occupancy=(
                float(r["occupancy"]) if r.get("occupancy") is not None else None
            ),
            observed_at=float(r.get("observed_at", frame_at)),
        )
        for r in reports
    )

    return tuple(observations), downstream
