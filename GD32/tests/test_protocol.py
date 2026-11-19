"""串口协议单元测试：CRC16 / 字节填充 / 帧编解码 / 语义化载荷。"""
from __future__ import annotations

import pytest

from host.protocol import (
    ADDR_CTRL,
    ADDR_HOST,
    Command,
    ProtocolError,
    ResultAck,
    StatusFrame,
    crc16,
    decode_frame,
    encode_config_timing,
    encode_frame,
    stuff,
    unstuff,
)


def test_crc16_known_vector():
    # CRC-16/CCITT-FALSE 的经典校验值："123456789" -> 0x29B1
    assert crc16(b"123456789") == 0x29B1


def test_crc16_empty():
    assert crc16(b"") == 0xFFFF


def test_stuff_roundtrip():
    for raw in (b"", b"\x7e", b"\x7d", b"\x7e\x7d\x01\x02", b"abc\x7d\x7e"):
        assert unstuff(stuff(raw)) == raw


def test_stuff_never_contains_flag():
    raw = bytes(range(256))
    assert b"\x7e" not in stuff(raw)


def test_unstuff_rejects_bad_escape():
    with pytest.raises(ProtocolError):
        unstuff(b"\x7d\x00")  # 非法转义对


def test_unstuff_rejects_dangling_escape():
    with pytest.raises(ProtocolError):
        unstuff(b"\x7d")


def test_encode_decode_roundtrip():
    payload = b"\x01\x02\x03\x04"
    raw = encode_frame(ADDR_CTRL, Command.PHASE_REQUEST, payload)
    frame = decode_frame(raw)
    assert frame.addr == ADDR_CTRL
    assert frame.cmd == Command.PHASE_REQUEST
    assert frame.payload == payload


def test_encode_frame_delimiters():
    raw = encode_frame(ADDR_CTRL, Command.STATUS_QUERY)
    assert raw[0] == 0x7E
    assert raw[-1] == 0x7E
    # 帧体内不得出现裸 FLAG。
    assert 0x7E not in raw[1:-1]


def test_payload_with_flag_and_esc_is_escaped():
    # 载荷故意包含 0x7E / 0x7D，验证转义 + CRC 依然正确。
    raw = encode_frame(ADDR_CTRL, Command.SPECIAL, b"\x7e\x7d\x00")
    frame = decode_frame(raw)
    assert frame.payload == b"\x7e\x7d\x00"


def test_decode_rejects_crc_corruption():
    raw = bytearray(encode_frame(ADDR_CTRL, Command.STATUS_QUERY))
    raw[-2] ^= 0xFF  # 破坏 CRC 最后一个字节
    with pytest.raises(ProtocolError):
        decode_frame(bytes(raw))


def test_decode_rejects_bad_length():
    raw = bytearray(encode_frame(ADDR_CTRL, Command.STATUS_QUERY, b"\x01\x02"))
    # 修改 LEN 字段（第 3 个字节，即 raw[2]）
    raw[2] = 0x09
    with pytest.raises(ProtocolError):
        decode_frame(bytes(raw))


def test_decode_rejects_missing_flag():
    with pytest.raises(ProtocolError):
        decode_frame(b"\x00\x01\x02\x03\x04")


def test_status_frame_roundtrip():
    status = StatusFrame(
        active_phase=2,
        stage=0,
        mode=0,
        link_lost=False,
        fault=False,
        phase_elapsed_ms=123456,
        seq=7,
    )
    frame = decode_frame(encode_frame(ADDR_CTRL, Command.STATUS, status_bytes(status)))
    parsed = StatusFrame.from_payload(frame.payload)
    assert parsed == status


def test_result_ack_roundtrip():
    frame = decode_frame(encode_frame(ADDR_CTRL, Command.CONFIG_ACK, b"\x00"))
    assert ResultAck.from_payload(frame.payload).result == 0


def test_config_timing_encoding():
    payload = encode_config_timing([(12.0, 30.0, 3.0, 1.0)] * 4)
    assert len(payload) == 32
    # 第一个相位 min_green = 12.0s -> 120 分秒，小端 uint16。
    assert payload[0:2] == (120).to_bytes(2, "little")
    # yellow = 3.0s -> 30 分秒（第 3 个 uint16，偏移 4）。
    assert payload[4:6] == (30).to_bytes(2, "little")


def test_config_timing_requires_four_phases():
    with pytest.raises(ValueError):
        encode_config_timing([(12.0, 30.0, 3.0, 1.0)])


def status_bytes(status: StatusFrame) -> bytes:
    return (
        bytes((status.active_phase, status.stage, status.mode,
               int(status.link_lost), int(status.fault)))
        + status.phase_elapsed_ms.to_bytes(4, "little")
        + bytes((status.seq,))
    )
