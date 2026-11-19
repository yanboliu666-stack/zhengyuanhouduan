# 影子运行 · 部署说明（更换边缘计算机）

> 本包只含「影子运行宿主接口层」（GD32/）。zhengyuan 逻辑决策层请从 GitHub 部署；
> GD32 固件已烧录，无需打包。

## 1. 目录关系（务必保持兄弟目录）

```
<工作目录>/
├── zhengyuan/          # 从 GitHub clone 的逻辑决策层（你部署）
└── GD32/               # 本包解压出来的接口层
```

`GD32/host/main.py` 默认按 `../zhengyuan` 找逻辑层（可用环境变量 `ZHENGYUAN_ROOT` 覆盖）。

## 2. 部署步骤

```bash
# ① clone 逻辑层并装依赖
git clone <你的 zhengyuan 仓库地址> zhengyuan
cd zhengyuan && uv sync

# ② 解压本包到 zhengyuan 的兄弟目录
cd ..
tar xzf gd32-shadow-run.tar.gz     # 得到 GD32/
```

## 3. 按需改配置（`GD32/configs/shadow.yaml`）

| 项 | 默认值 | 新机器可能要改 |
|---|---|---|
| `link.serial.port` | `/dev/ttyACM0` | 看 `ls /dev/tty*` 实际串口 |
| `decision_config` | `../zhengyuan/configs/default.yaml` | 一般不用改 |
| `cloud.host` | `192.168.0.112` | 若云端服务器 IP 变了就改 |
| `cloud.username/password` | `admin/publicpassword` | 一般不用改 |
| `perception.input_path` | `/tmp/gd32-traffic/perception.json` | 一般不用改 |

## 4. 串口权限（一次）

```bash
sudo chmod a+rw /dev/ttyACM0        # 或 usermod -aG dialout $USER 后重登录
```

## 5. 启动（两个终端）

```bash
# 终端 A：合成感知源
cd GD32
/home/<user>/zhengyuan/.venv/bin/python scripts/simulate_perception.py \
    --out /tmp/gd32-traffic/perception.json \
    --signal-state /tmp/gd32-traffic/signal_state.json \
    --fault-flag /tmp/gd32-traffic/fault.flag

# 终端 B：主循环
cd GD32
/home/<user>/zhengyuan/.venv/bin/python main.py --config configs/shadow.yaml
```

> venv python 路径按你 `uv sync` 后的实际位置；也可用 `uv run python main.py`（在 zhengyuan 目录下 `uv run` 会自动带上依赖）。

## 6. 自检

```bash
cd GD32
/home/<user>/zhengyuan/.venv/bin/python -m pytest tests/ -q   # 期望 43 passed
```

启动后终端 B 应看到 `cloud connected`；云端订阅 `traffic-control/mini_1/#` 能收到 `traffic_state` 等事件。

## 7. 文档索引（给同事）

- 云端接入 + 固件升级交底：`docs/cloud-integration-shadow.md`
- 固件烧录清单：`docs/gd32-firmware-flash-checklist.md`
- 串口协议 / 固件规格：`docs/gd32-firmware-spec.md`
