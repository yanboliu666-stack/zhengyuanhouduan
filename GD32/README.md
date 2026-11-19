# GD32 —— 本地临时控制接口层（影子运行）

把「智能交通信号控制」的逻辑决策层接到一块 **GD32E230C8T6** 驱动的**微型四向红绿灯**
上，用于**影子运行**：让 zhengyuan 决策层的相位建议，在缩小的实物模型上被安全执行
与观察，而不是直接控制真实信号机。

## 架构与分工

```
视觉感知层(YOLO) ──感知JSON──▶ zhengyuan 逻辑层(DecisionLayer) ──相位软请求──▶ GD32 微型红绿灯
                                                                      ▲
                                             状态回读(执行反馈) ─────────┘
```

| 部分 | 目录 | 负责方 | 状态 |
|---|---|---|---|
| 宿主机控制接口层（软请求 + 执行反馈） | [`host/`](host/) | 我方 | ✅ 已实现 + 单测通过 |
| 影子运行配置 / 相位映射 | [`configs/`](configs/) [`host/phase_mapping.yaml`](host/phase_mapping.yaml) | 我方 | ✅ |
| 合成感知源（无摄像头演示用） | [`scripts/simulate_perception.py`](scripts/simulate_perception.py) | 我方 | ✅ |
| **固件开发规格书（逻辑要求 + 接口协议）** | [`docs/gd32-firmware-spec.md`](docs/gd32-firmware-spec.md) | 我方（供同事） | ✅ |
| **原理图与接线** | [`docs/schematic.md`](docs/schematic.md) | 我方（供同事） | ✅ |
| GD32 固件（C / SPL） | [`firmware/`](firmware/) | **同事** | ⏳ 待开发 |

> **边界**：宿主机**只发相位指示（软请求），绝不直接下发灯色或配时**。最小绿/最大绿/
> 黄灯/全红/失联全红由 GD32 固件本地裁决，并回读状态形成执行反馈——与 zhengyuan
> `interface/hikvision` 的软请求边界一致。

## 关键文档

- **给固件同事**：先读 [`docs/gd32-firmware-spec.md`](docs/gd32-firmware-spec.md)
  （逻辑 + 协议）和 [`docs/schematic.md`](docs/schematic.md)（原理图/接线）。
- **串口协议字节级契约**：[`host/protocol.py`](host/protocol.py)（与规格书一一对应，
  是联调抓包基准）。

## 宿主机接口层（我方）快速开始

前置：zhengyuan 已 `uv sync`（依赖 pyyaml / pyserial / pytest）。

```bash
cd /home/ubuntu/GD32
export ZHENGYUAN_ROOT=/home/ubuntu/zhengyuan

# 1) 单元测试（协议 + 链路，不依赖真机）
/home/ubuntu/zhengyuan/.venv/bin/python -m pytest tests/ -q

# 2) 终端 A：合成感知源（替代视觉感知层，常驻、场景循环）
/home/ubuntu/zhengyuan/.venv/bin/python scripts/simulate_perception.py \
    --out /tmp/gd32-traffic/perception.json

# 3) 终端 B：全链路主循环（configs/shadow.yaml 已默认 serial + /dev/ttyACM0）
/home/ubuntu/zhengyuan/.venv/bin/python main.py --config configs/shadow.yaml

# 4) 终端 C（可选）：感知层输出可视化看板
/home/ubuntu/zhengyuan/.venv/bin/python scripts/perception_dashboard.py \
    --path /tmp/gd32-traffic/perception.json --port 8090
#     然后浏览器打开 http://127.0.0.1:8090
```

`configs/shadow.yaml` 里 `decision_config` 指向 zhengyuan 的
`../zhengyuan/configs/default.yaml`（决策层算法/权重都在那里，你调参就改它），
本文件只用 `signal_phases` 覆盖「相位配时」（min=12/max=80/yellow=3/all_red=1，
与固件一致）。这样**改决策权重不需要再动接口层**。离线冒烟可临时把
`link.transport.type` 改成 `null`。

## 目录结构

```
GD32/
├── main.py                       # 入口 bootstrap（加 sys.path 后调 host.main）
├── host/                         # 宿主机控制接口层（我方）
│   ├── protocol.py               #   串口帧协议 / CRC16 / 字节填充（字节级契约）
│   ├── transports.py             #   SerialTransport / NullTransport
│   ├── gd32_link.py              #   软请求 + 心跳 + 状态回读
│   ├── driver.py                 #   STATUS → ControllerState（执行反馈）
│   ├── perception.py             #   感知 JSON 读取
│   ├── main.py                   #   主循环：感知→决策→GD32
│   └── phase_mapping.yaml        #   phase_id ↔ 相位号
├── configs/
│   └── shadow.yaml               # 影子运行配置（串口/感知/配时覆盖/心跳）
├── scripts/
│   ├── simulate_perception.py     # 合成感知源（演示，场景循环）
│   └── perception_dashboard.py    # 感知层输出可视化看板（演示）
├── tests/                        # 单元测试（41 个，全绿）
├── docs/
│   ├── gd32-firmware-spec.md     # 固件开发规格书（同事）
│   └── schematic.md              # 原理图与接线（同事）
└── firmware/                     # 固件（同事），见其 README
```

## 依赖关系（复用的 zhengyuan 组件）

- `traffic_control.decision_layer.DecisionLayer` —— 逻辑层门面（`tick()` 输出 `PhaseDecision`）。
- `traffic_control.perception` —— 感知 JSON 校验与归一化（`normalize_detections` 等）。
- `traffic_control.models` —— `ControllerState` / `ControllerMode`（执行反馈用）。
- 感知 JSON 格式沿用 zhengyuan `docs/perception-interface.md` §8（原子写、≥2Hz、空场景心跳）。
