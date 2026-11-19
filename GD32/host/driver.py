"""微型信号机状态跟踪：把 GD32 回读的 STATUS 帧翻译成决策层要的
``ControllerState``，形成「执行反馈」闭环。

决策层（``DecisionLayer.tick`` / ``FeedbackMonitor``）不直接相信自己的建议，
而是相信信号机**实际**回到的相位。本驱动从 ``G32Link.poll()`` 回读的状态里
重建真实相位与相位起点，交给决策层比对确认。
"""
from __future__ import annotations

from traffic_control.models import ControllerMode, ControllerState

from host.gd32_link import LinkMode, PhaseMapping
from host.protocol import Mode, PHASE_NONE, Special, Stage, StatusFrame


def _controller_mode(status: StatusFrame, link_mode: LinkMode) -> ControllerMode:
    """STATUS 帧 → ControllerMode（决策层认可的控制器状态枚举）。"""
    if link_mode is LinkMode.FAULT or status.fault:
        return ControllerMode.FAULT
    if status.link_lost or status.mode == Mode.FAILSAFE:
        # 失联黄闪 = 降级兜底，视为故障，决策层不再提案。
        return ControllerMode.FAULT
    if status.mode == Mode.FAULT:
        return ControllerMode.FAULT
    if status.mode == Mode.LOCAL:
        # 固件本地固定配时（未接管）：决策层闭嘴（与 zhengyuan takeover 语义一致）。
        return ControllerMode.MANUAL_OVERRIDE
    if status.mode == Mode.STARTUP:
        # 启动序列中（5s 黄闪 + 10s 全红），视同全红，决策层不提案。
        return ControllerMode.ALL_RED
    # Mode.NORMAL：按灯色阶段细分清空状态。
    stage = status.stage
    if stage == Stage.GREEN:
        return ControllerMode.NORMAL
    if stage == Stage.YELLOW:
        return ControllerMode.CLEARANCE
    if stage == Stage.ALL_RED:
        return ControllerMode.ALL_RED
    # FLASH / OFF / 未知阶段：一律视为故障，停止提案。
    return ControllerMode.FAULT


class MiniSignalDriver:
    """维护 GD32 微型信号机的真实相位状态。"""

    def __init__(self, mapping: PhaseMapping):
        self._mapping = mapping
        self._status: StatusFrame | None = None
        self._link_mode: LinkMode = LinkMode.LOCAL
        self._phase_started_at: float = 0.0
        self._last_stage: int | None = None

    def update(
        self,
        status: StatusFrame | None,
        link_mode: LinkMode,
        now: float | None = None,
    ) -> None:
        """固化「当前绿灯相位」的绝对起点。

        只在**刚进入绿灯阶段**（stage 由非 green 变为 green）时算一次
        ``now - phase_elapsed_ms/1000``，绿灯期间保持不变。这样决策层拿到的
        ``phase_started_at`` 是稳定的浮点数，不会被其内部「相位起点是否变化」的
        精确相等判断误判为相位重启（否则会把无车计时反复清零，导致不切灯）。
        """
        self._status = status
        self._link_mode = link_mode
        if status is not None and now is not None:
            if status.stage == Stage.GREEN and self._last_stage != Stage.GREEN:
                self._phase_started_at = now - status.phase_elapsed_ms / 1000.0
            self._last_stage = status.stage
        elif now is not None:
            self._phase_started_at = now

    def state(self, now: float) -> ControllerState:
        """构造决策层要的控制器状态。

        尚未收到任何 STATUS（刚开机）时返回 ALL_RED / 无相位，避免把
        「未知」当成「某相位绿灯中」。
        """
        if self._status is None:
            return ControllerState(
                mode=ControllerMode.ALL_RED,
                current_phase_id=None,
                phase_started_at=now,
            )
        return ControllerState(
            mode=_controller_mode(self._status, self._link_mode),
            current_phase_id=self._phase_id(self._status.active_phase),
            phase_started_at=self._phase_started_at,
        )

    def _phase_id(self, phase_number: int) -> str | None:
        if phase_number == PHASE_NONE:
            return None
        if phase_number in (Special.FLASH, Special.OFF):
            return None
        return self._mapping.phase_id(phase_number)
