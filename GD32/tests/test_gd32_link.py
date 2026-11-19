"""GD32 控制链路单元测试：软请求编码 / 状态回读 / 心跳故障判定。"""
from __future__ import annotations

from pathlib import Path

from host.gd32_link import G32Link, LinkMode, PhaseMapping
from host.protocol import (
    ADDR_CTRL,
    Command,
    StatusFrame,
    decode_frame,
    encode_frame,
)
from host.transports import NullTransport


def make_mapping() -> PhaseMapping:
    return PhaseMapping(
        controller_address=0x01,
        phases={"P_N": 1, "P_E": 2, "P_S": 3, "P_W": 4},
        special={"all_red": 0x00, "flash": 0xFE, "off": 0xFF},
    )


def make_link(replies=None) -> tuple[G32Link, NullTransport]:
    transport = NullTransport(replies=replies)
    link = G32Link(transport=transport, mapping=make_mapping())
    link.open()
    return link, transport


def status_bytes(status: StatusFrame) -> bytes:
    return encode_frame(
        ADDR_CTRL,
        Command.STATUS,
        (
            bytes((status.active_phase, status.stage, status.mode,
                   int(status.link_lost), int(status.fault)))
            + status.phase_elapsed_ms.to_bytes(4, "little")
            + bytes((status.seq,))
        ),
    )


def sample_status(phase=2, stage=0, mode=0, elapsed_ms=0, seq=1) -> bytes:
    return status_bytes(
        StatusFrame(
            active_phase=phase,
            stage=stage,
            mode=mode,
            link_lost=False,
            fault=False,
            phase_elapsed_ms=elapsed_ms,
            seq=seq,
        )
    )


def test_request_phase_encodes_correct_frame():
    link, transport = make_link()
    link.request_phase("P_E", reason="p0_wait_preempt")
    assert len(transport.sent) == 1
    frame = decode_frame(transport.sent[0])
    assert frame.cmd == Command.PHASE_REQUEST
    assert frame.payload == bytes((2, 0x00))  # phase=2, flags=0


def test_request_phase_all_red_maps_to_special():
    link, transport = make_link()
    link.request_phase(None, reason="failsafe", all_red_required=True)
    frame = decode_frame(transport.sent[0])
    assert frame.cmd == Command.SPECIAL
    assert frame.payload == bytes((0x00,))  # all_red


def test_request_phase_unknown_id_raises():
    link, _ = make_link()
    try:
        link.request_phase("P_UNKNOWN")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError for unknown phase id")


def test_request_phase_none_noop():
    link, transport = make_link()
    link.request_phase(None)
    assert transport.sent == []  # 决策层未选中相位，不发指示


def test_poll_parses_status_and_resets_heartbeat():
    link, transport = make_link(replies=[sample_status(phase=3, elapsed_ms=5000, seq=9)])
    status = link.poll()
    assert status is not None
    assert status.active_phase == 3
    assert status.phase_elapsed_ms == 5000
    assert link.mode is not LinkMode.FAULT


def test_poll_drains_acks_until_status():
    # 串口里混着 ACK：poll 应排空 ACK，直到读到 STATUS 为止。
    ack = encode_frame(ADDR_CTRL, Command.PHASE_ACK, bytes((2, 0x00)))
    status_frame = sample_status(phase=4, elapsed_ms=1000, seq=3)
    link, transport = make_link(replies=[ack, status_frame])
    got = link.poll()
    assert got is not None
    assert got.active_phase == 4
    assert transport.replies == []  # ACK 与 STATUS 都被消费


def test_poll_ignores_bad_frames_and_keeps_draining():
    bad = b"\x7e\x00\x00\x00\x00\x7e"  # 缺 CRC / 长度非法，解不出
    status_frame = sample_status(phase=1, seq=5)
    link, transport = make_link(replies=[bad, status_frame])
    got = link.poll()
    assert got is not None
    assert got.active_phase == 1


def test_poll_no_reply_marks_fault_after_threshold():
    link, transport = make_link(replies=[])  # 永远无响应
    for _ in range(3):
        link.poll()
    assert link.mode is LinkMode.FAULT


def test_takeover_and_detach():
    link, transport = make_link()
    link.request_takeover()
    assert link.mode is LinkMode.REMOTE
    link.request_detach()
    assert link.mode is LinkMode.LOCAL


def test_configure_timing_encodes_32_byte_payload():
    link, transport = make_link()
    link.configure_timing([(12.0, 30.0, 3.0, 1.0)] * 4)
    frame = decode_frame(transport.sent[0])
    assert frame.cmd == Command.CONFIG_TIMING
    assert len(frame.payload) == 32


def test_reset_sends_reset_command():
    link, transport = make_link()
    link.reset()
    assert decode_frame(transport.sent[0]).cmd == Command.RESET


def test_mapping_loads_from_yaml(tmp_path: Path):
    yaml_path = tmp_path / "mapping.yaml"
    yaml_path.write_text(
        "phases:\n  P_N: 1\n  P_E: 2\n  P_S: 3\n  P_W: 4\n"
        "special:\n  all_red: 0x00\n  flash: 0xFE\n  off: 0xFF\n"
        "controller_address: 0x01\n",
        encoding="utf-8",
    )
    mapping = PhaseMapping.from_yaml(yaml_path)
    assert mapping.phase_number("P_W") == 4
    assert mapping.phase_id(2) == "P_E"
    assert mapping.special["flash"] == 0xFE
