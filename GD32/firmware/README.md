# firmware/ —— GD32 固件（同事负责）

本目录由**负责固件的同事**自行实现。开发前请先完整阅读以下两份文档（**权威依据**）：

1. **固件开发规格书**：[`../docs/gd32-firmware-spec.md`](../docs/gd32-firmware-spec.md)
   —— 逻辑要求 + 串口协议（字节级）+ 状态机 + 配时 + 失联看门狗 + 验收标准。
2. **原理图与接线**：[`../docs/schematic.md`](../docs/schematic.md)
   —— 引脚分配表 + LED 接线 + BOM + 串口/供电/SWD 接线。

## 硬性约定（联调前必须一致）

- 相位号固定 `1=N 2=E 3=S 4=W`，灯序固定 `红/黄/绿`。
- 串口 **115200 8N1**，PA9=TX / PA10=RX。
- 帧协议、CRC16（poly `0x1021`，init `0xFFFF`）、字节填充，**必须**与
  [`../host/protocol.py`](../host/protocol.py) 逐字节一致。
- STATUS 载荷固定 10 字节、CONFIG_TIMING 固定 32 字节（分秒 `uint16` 小端）。

## 参考实现（可选）

宿主机侧已有完整、可运行的参考实现（`../host/`），含 CRC16 与帧编解码的单元测试，
可直接作为固件对照与联调抓包基线：

```bash
cd ../  &&  /home/ubuntu/zhengyuan/.venv/bin/python -m pytest tests/ -q
```

## 建议工程结构

```
firmware/
├── Makefile                 # arm-none-eabi-gcc 构建（引用 GD32E23x_Firmware_Library）
├── app/
│   ├── main.c               # 时钟/SysTick/USART/GPIO 初始化 + 主循环
│   ├── protocol.c/.h        # 帧编解码（CRC16 + 字节填充 + 切帧状态机）
│   ├── mini_signal.c/.h     # 信号机状态机（规格书 §5）
│   ├── lamp_driver.c/.h     # 灯色矩阵 → GPIO（规格书 §5.2）
│   └── config.h             # 引脚/配时/失联阈值（规格书 §3 / §5.7）
└── gd32e230c8t6.ld          # 链接脚本（64KB Flash @0x08000000, 8KB SRAM @0x20000000）
```

> GD32E23x 标准外设库（SPL）请从 GigaDevice 官网获取 `GD32E23x_Firmware_Library`，
> 其自带的 `startup_gd32e230.s` 与 `system_gd32e230.c` 直接使用即可。
