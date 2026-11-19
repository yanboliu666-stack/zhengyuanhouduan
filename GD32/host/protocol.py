"""影子运行串口协议（宿主机 ↔ GD32E230 微型信号机）。

本模块是与固件 ``firmware/app/protocol.h`` 一一对应的 Python 实现，是控制接口层
与微型红绿灯之间唯一的字节级契约。协议采用二进制帧 + CRC16-CCITT + 字节填充，
风格对齐 zhengyuan 的 ``interface/hikvision/protocol.py``（HDLC FLAG/转义思路），
但为本地微型模型做了简化，不依赖任何国标字节细节。

帧结构::

    0x7E | ADDR | CMD | LEN | PAYLOAD(LEN) | CRC16(LE) | 0x7E
            └────────── 字节填充(0x7D 转义) ──────────┘

    * CRC16 覆盖 ADDR..PAYLOAD（未填充字节），多项式 0x1021，初值 0xFFFF。
    * 转义：0x7E -> 0x7D 0x5E；0x7D -> 0x7D 0x5D。

详见 ``docs/shadow-run-protocol.md``（权威），改协议时两处同步修改。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

# --------------------------------------------------------------------------- #
# 字节级常量
# --------------------------------------------------------------------------- #
FLAG = 0x7E
ESC = 0x7D
ESC_XOR = 0x20

ADDR_HOST = 0x00
ADDR_CTRL = 0x01

CRC_POLY = 0x1021
CRC_INIT = 0xFFFF


class Command(IntEnum):
    """帧命令字。宿主机→GD32 取低 7 位；GD32→宿主机在命令字上置 0x80。"""

    PHASE_REQUEST = 0x01
    STATUS_QUERY = 0x02
    TAKEOVER = 0x03
    DETACH = 0x04
    SPECIAL = 0x05
    CONFIG_TIMING = 0x06
    RESET = 0x07

    # 响应帧命令字
    PHASE_ACK = 0x81
    STATUS = 0x82
    TAKEOVER_ACK = 0x83
    DETACH_ACK = 0x84
    SPECIAL_ACK = 0x85
    CONFIG_ACK = 0x86
    RESET_ACK = 0x87


class Result(IntEnum):
    OK = 0x00
    DEFERRED = 0x01   # 最小绿未到，已挂起请求
    REJECTED = 0x02   # 未知相位 / 非法参数
    ERROR = 0xFF


class Special(IntEnum):
    ALL_RED = 0x00
    FLASH = 0xFE
    OFF = 0xFF


class Stage(IntEnum):
    GREEN = 0x00
    YELLOW = 0x01
    ALL_RED = 0x02
    FLASH = 0x03
    OFF = 0x04


class Mode(IntEnum):
    """STATUS 帧的**运行模式**（区别于 stage 的灯色阶段）。

    清空（黄灯/全红）不是运行模式，而是由 ``stage`` 表达；本枚举只表示
    信号机处于哪种控制模式。
    """

    NORMAL = 0x00    # 远程自适应（宿主机已接管，正常决策）
    LOCAL = 0x01     # 本地固定配时（宿主机未接管 / 已摘除）
    FAILSAFE = 0x02  # 失联黄闪兜底（link_timeout 内未收到有效帧）
    FAULT = 0x03     # 内部故障
    STARTUP = 0x04   # 启动序列中（5s 黄闪 + 10s 全红）


# 相位编号（与 phase_mapping.yaml 及固件一致）。0x00 = 无/全红，1..4 = P_N..P_W。
PHASE_NONE = 0x00

# STATUS 帧固定载荷长度：active_phase(1) + stage(1) + mode(1) + link_lost(1)
# + fault(1) + phase_elapsed_ms(4, LE) + seq(1) = 10 字节。
STATUS_PAYLOAD_LEN = 10


class ProtocolError(Exception):
    """帧编解码失败（FLAG 缺失 / 转义非法 / CRC 不匹配 / 长度非法）。"""


# --------------------------------------------------------------------------- #
# CRC / 字节填充
# --------------------------------------------------------------------------- #
def crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE：poly 0x1021，init 0xFFFF，不反转、不异或输出。"""
    crc = CRC_INIT
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ CRC_POLY) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def stuff(data: bytes) -> bytes:
    """对 ADDR..CRC 区域做 0x7D 字节转义，保证帧内不含裸 FLAG。"""
    out = bytearray()
    for b in data:
        if b == FLAG:
            out += bytes((ESC, FLAG ^ ESC_XOR))
        elif b == ESC:
            out += bytes((ESC, ESC ^ ESC_XOR))
        else:
            out.append(b)
    return bytes(out)


def unstuff(data: bytes) -> bytes:
    """还原字节转义；遇到非法转义序列抛 ProtocolError。"""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b == ESC:
            if i + 1 >= n:
                raise ProtocolError("dangling escape byte")
            nxt = data[i + 1]
            if nxt not in (FLAG ^ ESC_XOR, ESC ^ ESC_XOR):
                raise ProtocolError(f"invalid escape sequence 0x7D 0x{nxt:02X}")
            out.append(nxt ^ ESC_XOR)
            i += 2
        elif b == FLAG:
            raise ProtocolError("raw FLAG inside frame body")
        else:
            out.append(b)
            i += 1
    return bytes(out)


# --------------------------------------------------------------------------- #
# 帧编解码
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Frame:
    addr: int
    cmd: int
    payload: bytes = b""

    def is_response(self) -> bool:
        return bool(self.cmd & 0x80)


def encode_frame(addr: int, cmd: int, payload: bytes = b"") -> bytes:
    """编码一帧：FLAG + stuffed(ADDR|CMD|LEN|PAYLOAD|CRC16) + FLAG。"""
    if not 0 <= addr <= 0xFF:
        raise ValueError("addr out of range")
    if not 0 <= cmd <= 0xFF:
        raise ValueError("cmd out of range")
    if not 0 <= len(payload) <= 0xFF:
        raise ValueError("payload too long (>255 bytes)")
    header = bytes((addr, cmd, len(payload)))
    crc = crc16(header + payload)
    body = header + payload + crc.to_bytes(2, "little")
    return bytes((FLAG,)) + stuff(body) + bytes((FLAG,))


def decode_frame(raw: bytes) -> Frame:
    """解码一帧：校验 FLAG、转义、长度与 CRC，返回 Frame。"""
    if len(raw) < 6:
        raise ProtocolError("frame too short")
    if raw[0] != FLAG or raw[-1] != FLAG:
        raise ProtocolError("missing FLAG delimiter")
    body = unstuff(raw[1:-1])
    if len(body) < 5:  # ADDR + CMD + LEN + CRC16(2)
        raise ProtocolError("frame body too short")
    addr, cmd, length = body[0], body[1], body[2]
    if length != len(body) - 5:
        raise ProtocolError(
            f"length mismatch: header={length}, actual={len(body) - 5}"
        )
    payload = body[3 : 3 + length]
    crc_field = body[-2:]
    crc_got = crc16(body[:-2])
    crc_expect = int.from_bytes(crc_field, "little")
    if crc_got != crc_expect:
        raise ProtocolError(
            f"CRC mismatch: got 0x{crc_got:04X}, expected 0x{crc_expect:04X}"
        )
    return Frame(addr=addr, cmd=cmd, payload=payload)


# --------------------------------------------------------------------------- #
# 语义化载荷
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PhaseRequest:
    phase: int
    all_red_required: bool = False

    def to_payload(self) -> bytes:
        flags = 0x01 if self.all_red_required else 0x00
        return bytes((self.phase & 0xFF, flags))


@dataclass(frozen=True)
class StatusFrame:
    """GD32 回读的运行状态（执行反馈闭环的依据）。"""

    active_phase: int
    stage: int
    mode: int
    link_lost: bool
    fault: bool
    phase_elapsed_ms: int
    seq: int

    @classmethod
    def from_payload(cls, payload: bytes) -> "StatusFrame":
        if len(payload) != STATUS_PAYLOAD_LEN:
            raise ProtocolError(
                f"STATUS payload must be {STATUS_PAYLOAD_LEN} bytes, "
                f"got {len(payload)}"
            )
        return cls(
            active_phase=payload[0],
            stage=payload[1],
            mode=payload[2],
            link_lost=bool(payload[3]),
            fault=bool(payload[4]),
            phase_elapsed_ms=int.from_bytes(payload[5:9], "little"),
            seq=payload[9],
        )


@dataclass(frozen=True)
class PhaseAck:
    phase: int
    result: int

    @classmethod
    def from_payload(cls, payload: bytes) -> "PhaseAck":
        if len(payload) != 2:
            raise ProtocolError(f"PHASE_ACK payload must be 2 bytes, got {len(payload)}")
        return cls(phase=payload[0], result=payload[1])


@dataclass(frozen=True)
class ResultAck:
    result: int

    @classmethod
    def from_payload(cls, payload: bytes) -> "ResultAck":
        if len(payload) != 1:
            raise ProtocolError(f"ACK payload must be 1 byte, got {len(payload)}")
        return cls(result=payload[0])


def encode_config_timing(
    timings: list[tuple[float, float, float, float]],
) -> bytes:
    """把 4 个相位的 (min_green, max_green, yellow, all_red)（秒）编码为
    CONFIG_TIMING 载荷：每相位 4 个 uint16 分秒值（0.1 s），共 32 字节。

    ``timings`` 长度必须为 4（对应 phase 1..4），顺序与 phase_mapping.yaml 一致。
    """
    if len(timings) != 4:
        raise ValueError("exactly 4 phase timings are required")
    payload = bytearray()
    for min_g, max_g, yellow, all_red in timings:
        for value in (min_g, max_g, yellow, all_red):
            ds = int(round(value * 10.0))
            if not 0 <= ds <= 0xFFFF:
                raise ValueError(f"timing {value}s out of representable range")
            payload += ds.to_bytes(2, "little")
    return bytes(payload)
