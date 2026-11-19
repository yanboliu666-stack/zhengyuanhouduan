"""微型信号机状态跟踪（driver）单元测试：STATUS → ControllerState 映射。

依赖 zhengyuan 的 traffic_control（本测试动态加入其路径）。
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (
    _ROOT,
    os.path.normpath(os.path.join(_ROOT, "..", "zhengyuan")),
    os.path.normpath(os.path.join(_ROOT, "..", "zhengyuan", "src")),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from host.driver import MiniSignalDriver, _controller_mode  # noqa: E402
from host.gd32_link import LinkMode, PhaseMapping  # noqa: E402
from host.protocol import Mode, Stage, StatusFrame  # noqa: E402
from traffic_control.models import ControllerMode  # noqa: E402


def status(mode, stage, link_lost=False, fault=False, phase=2, elapsed_ms=0):
    return StatusFrame(
        active_phase=phase,
        stage=stage,
        mode=mode,
        link_lost=link_lost,
        fault=fault,
        phase_elapsed_ms=elapsed_ms,
        seq=1,
    )


def mapping():
    return PhaseMapping(
        controller_address=0x01,
        phases={"P_N": 1, "P_E": 2, "P_S": 3, "P_W": 4},
        special={"all_red": 0x00, "flash": 0xFE, "off": 0xFF},
    )


def test_green_normal():
    assert _controller_mode(status(Mode.NORMAL, Stage.GREEN), LinkMode.REMOTE) is ControllerMode.NORMAL


def test_yellow_clearance():
    assert _controller_mode(status(Mode.NORMAL, Stage.YELLOW), LinkMode.REMOTE) is ControllerMode.CLEARANCE


def test_all_red_stage():
    assert _controller_mode(status(Mode.NORMAL, Stage.ALL_RED), LinkMode.REMOTE) is ControllerMode.ALL_RED


def test_flash_is_fault():
    assert _controller_mode(status(Mode.NORMAL, Stage.FLASH), LinkMode.REMOTE) is ControllerMode.FAULT


def test_local_is_manual_override():
    assert _controller_mode(status(Mode.LOCAL, Stage.GREEN), LinkMode.REMOTE) is ControllerMode.MANUAL_OVERRIDE


def test_failsafe_is_fault():
    assert _controller_mode(status(Mode.FAILSAFE, Stage.FLASH, link_lost=True), LinkMode.REMOTE) is ControllerMode.FAULT


def test_startup_is_all_red():
    assert _controller_mode(status(Mode.STARTUP, Stage.FLASH), LinkMode.REMOTE) is ControllerMode.ALL_RED


def test_link_fault_wins():
    assert _controller_mode(status(Mode.NORMAL, Stage.GREEN), LinkMode.FAULT) is ControllerMode.FAULT


def test_internal_fault_wins():
    assert _controller_mode(status(Mode.NORMAL, Stage.GREEN, fault=True), LinkMode.REMOTE) is ControllerMode.FAULT


def test_driver_state_from_status():
    d = MiniSignalDriver(mapping())
    d.update(status(Mode.NORMAL, Stage.GREEN, phase=2, elapsed_ms=5000), LinkMode.REMOTE, now=100.0)
    state = d.state(now=100.0)
    assert state.mode is ControllerMode.NORMAL
    assert state.current_phase_id == "P_E"
    assert state.phase_started_at == 100.0 - 5.0  # now - 5000ms


def test_driver_phase_started_at_does_not_drift_between_polls():
    """回归：两次轮询之间 phase_started_at 必须保持稳定，不能随 now 后移。"""
    d = MiniSignalDriver(mapping())
    d.update(status(Mode.NORMAL, Stage.GREEN, phase=2, elapsed_ms=5000), LinkMode.REMOTE, now=100.0)
    assert d.state(now=100.0).phase_started_at == 95.0
    # 轮询间隙 now 前进，但 phase_started_at 不变（否则决策层把绿灯时长算成冻结）。
    assert d.state(now=101.0).phase_started_at == 95.0
    assert d.state(now=105.0).phase_started_at == 95.0


def test_driver_phase_started_at_stable_across_polls_in_same_green():
    """回归：同一绿灯内多次轮询，phase_started_at 必须完全不变（浮点相等）。

    决策层用「phase_started_at 是否变化」判断相位是否重启；若这里每次轮询都抖动
    几毫秒，会被误判为重启、反复清零无车计时，导致一直不切灯（几十秒空放）。
    """
    d = MiniSignalDriver(mapping())
    # 第一次进入绿灯：elapsed=5000ms
    d.update(status(Mode.NORMAL, Stage.GREEN, phase=2, elapsed_ms=5000), LinkMode.REMOTE, now=100.0)
    first = d.state(now=100.0).phase_started_at
    # 同一绿灯继续（elapsed 增长），phase_started_at 必须逐位相等
    d.update(status(Mode.NORMAL, Stage.GREEN, phase=2, elapsed_ms=6000), LinkMode.REMOTE, now=101.0)
    assert d.state(now=101.0).phase_started_at == first
    d.update(status(Mode.NORMAL, Stage.GREEN, phase=2, elapsed_ms=7000), LinkMode.REMOTE, now=102.0)
    assert d.state(now=102.0).phase_started_at == first


def test_driver_phase_started_at_updates_on_new_green():
    """进入新绿灯（或清空后重回绿灯）时，phase_started_at 才更新。"""
    d = MiniSignalDriver(mapping())
    d.update(status(Mode.NORMAL, Stage.GREEN, phase=1, elapsed_ms=12000), LinkMode.REMOTE, now=100.0)
    p_n = d.state(now=100.0).phase_started_at  # 100 - 12 = 88
    # 清空（黄灯/全红）期间不更新绿灯起点
    d.update(status(Mode.NORMAL, Stage.YELLOW, phase=1, elapsed_ms=1000), LinkMode.REMOTE, now=112.0)
    d.update(status(Mode.NORMAL, Stage.ALL_RED, phase=1, elapsed_ms=500), LinkMode.REMOTE, now=115.0)
    assert d.state(now=115.0).phase_started_at == p_n
    # 新绿灯 P_E
    d.update(status(Mode.NORMAL, Stage.GREEN, phase=2, elapsed_ms=25), LinkMode.REMOTE, now=116.0)
    assert d.state(now=116.0).phase_started_at == 116.0 - 0.025
    assert d.state(now=116.0).current_phase_id == "P_E"


def test_driver_no_status_is_all_red():
    d = MiniSignalDriver(mapping())
    state = d.state(now=10.0)
    assert state.mode is ControllerMode.ALL_RED
    assert state.current_phase_id is None


def test_driver_all_red_hold_has_no_phase():
    d = MiniSignalDriver(mapping())
    d.update(status(Mode.NORMAL, Stage.ALL_RED, phase=0x00), LinkMode.REMOTE, now=10.0)
    state = d.state(now=10.0)
    assert state.mode is ControllerMode.ALL_RED
    assert state.current_phase_id is None
