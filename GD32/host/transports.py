"""传输层：串口（USB 转 TTL / UART）与空实现（离线冒烟 / 测试）。

与 zhengyuan 的 ``interface/hikvision/transports.py`` 对齐：串口懒加载
pyserial，未接串口的环境也能 import；``NullTransport`` 支持回放脚本，供测试。
"""
from __future__ import annotations

import abc
from typing import Optional


class Transport(abc.ABC):
    """字节流传输抽象。"""

    @abc.abstractmethod
    def open(self) -> None: ...

    @abc.abstractmethod
    def close(self) -> None: ...

    @abc.abstractmethod
    def send(self, data: bytes) -> None: ...

    @abc.abstractmethod
    def receive(self, timeout: float) -> Optional[bytes]: ...

    @property
    @abc.abstractmethod
    def is_open(self) -> bool: ...


class SerialTransport(Transport):
    """UART 串口传输（GD32E230 的 USART0 ↔ USB 转 TTL 模块）。

    默认 115200 8N1（固件端保持一致，见 ``firmware/app/config.h``）。
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser = None

    def open(self) -> None:
        import serial  # 懒加载：未接串口的环境也能 import 本模块

        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout,
        )

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def send(self, data: bytes) -> None:
        if self._ser is None:
            raise RuntimeError("serial transport not open")
        self._ser.write(data)

    def receive(self, timeout: float) -> Optional[bytes]:
        """读一帧：以首 FLAG 开始、到下一个 FLAG 结束（字节填充区不含 FLAG）。

        空闲填充 0x7E / 前导噪声可能导致 read_until 错位；本协议无空闲填充，
        且微型模型链路噪声极低，此简单实现已够用。若现场出现错帧，参考
        zhengyuan ``transports.SerialTransport`` 的 TODO 改为缓冲状态机切帧。
        """
        if self._ser is None:
            raise RuntimeError("serial transport not open")
        self._ser.timeout = timeout
        first = self._ser.read_until(bytes((0x7E,)))
        if not first.endswith(b"\x7e"):
            return None
        rest = self._ser.read_until(bytes((0x7E,)))
        if not rest.endswith(b"\x7e"):
            return None
        return first + rest

    @property
    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open


class NullTransport(Transport):
    """空传输：不回传任何数据，用于离线冒烟 / 单元测试。

    测试可把 ``replies`` 设为脚本化响应队列，``receive`` 按顺序弹出；
    也可读取 ``sent`` 检查宿主机实际发出的字节流。
    """

    def __init__(self, replies: Optional[list[bytes]] = None):
        self._open = False
        self.sent: list[bytes] = []
        self.replies: list[bytes] = list(replies) if replies else []

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def send(self, data: bytes) -> None:
        self.sent.append(data)

    def receive(self, timeout: float) -> Optional[bytes]:
        if self.replies:
            return self.replies.pop(0)
        return None

    @property
    def is_open(self) -> bool:
        return self._open
