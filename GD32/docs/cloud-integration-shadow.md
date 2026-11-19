# 影子运行 · 临时云端接入开发文档（给云端同事）

> 版本：临时接入版。数据契约**完全复用** [`logging-data-contract.md`](../zhengyuan/docs/logging-data-contract.md)，
> 你已按该契约开发完的**基座无需改动**。本文只告诉你「影子运行这个临时实例」与生产的几个差异点 + 你要给我哪些参数。

---

## 1. 一句话结论

影子运行（GD32 微型红绿灯）临时接入云端，**只上传「事件」，不上传逐 tick 全量快照**（与生产契约一致）。
云端基座收到的是和产线**同 schema、同 topic 结构**的 MQTT 消息，唯一变化是 `junction_id` 换成临时值。

## 2. 临时实例参数（请按此配置你的消费侧）

| 项 | 影子运行值 | 说明 |
|---|---|---|
| `junction_id` | **`mini_1`** | 区别于生产 `panan_1`，用这个做主题/去重维度 |
| topic 前缀 | `traffic-control` | 与生产一致 |
| 采样率 | 2 Hz | 与生产一致 |
| 相位集合 | `P_N` / `P_E` / `P_S` / `P_W`（模式 A，四向） | 4 相位，每向直行+左转合并 |
| 上传内容 | 仅**事件**（见 §4） | 逐 tick 快照只落本地、不上云 |
| 原始逐车检测 | 不上传 | 与契约一致 |

## 3. MQTT 连接参数（需要你提供给我）

请回填下面几项，我在宿主侧配置：

```yaml
cloud:
  type: mqtt
  host: <mqtt broker 地址>        # 待你提供
  port: 1883                      # 或 8883(TLS)
  username: <临时账号>            # 待你提供（可空）
  password: <临时密码>            # 待你提供（可空）
  tls: false                      # 是否 TLS
  qos: 1
  topic_prefix: traffic-control
  keepalive_s: 60
```

> 我可以先用 `host` 填一个临时 broker 地址、账号留空来冒烟；你给到正式地址后改一行即可。

## 4. 会上传哪些事件（复用契约 §4）

| event_type | 触发 | 关键字段 |
|---|---|---|
| `decision_change` | 相位切换 | `from_phase` / `to_phase` / `reason` |
| `degradation_change` | 降级模式变化 | `from_mode` / `to_mode`（normal/partial/failsafe） |
| `mode_change` | 控制器模式变化 | `from_mode` / `to_mode`（normal/clearance/all_red/fault/manual_override） |
| `feedback_failure` | 执行反馈失败 | `current_phase_id` / `requested_phase_id` |
| `alarm` | 决策层告警 | `alarm_type` / `level` / `detail` |
| `heartbeat_fault` | 信号机心跳超时 | `detail` |
| **`traffic_state`** | **周期性（2 Hz，每 tick）** | **感知/交通状态，供云端看板渲染（§4.1）** |

**MQTT topic（不变）：**

```
traffic-control/mini_1/event/{event_type}     # 事件，QoS1，retain=false
traffic-control/mini_1/alarm                  # 告警，QoS1，retain=false
```

幂等：每个事件含 `tick_id`，后台按 `(junction_id, event_type, tick_id)` 去重（同契约 §5）。

### 4.1 `traffic_state` 事件（云端可视化看板，替代本地 8090）

本次临时新增的**周期事件**，用于云端渲染「各方向车辆排队」看板（对应原先
`http://127.0.0.1:8090` 的功能）。频率 **2 Hz**（每 tick 一条），payload：

```json
{
  "junction_id": "mini_1",
  "ts_wall": 1731081600.0,
  "current_phase_id": "P_E",
  "degradation": "normal",
  "lanes": {
    "north_through": {"vehicle_count": 2, "oldest_wait_s": 8.0, "downstream_blocked": false},
    "north_left":    {"vehicle_count": 0, "oldest_wait_s": 0.0, "downstream_blocked": false},
    "east_through":  {"vehicle_count": 3, "oldest_wait_s": 5.0, "downstream_blocked": false},
    "east_left":     {"vehicle_count": 1, "oldest_wait_s": 3.0, "downstream_blocked": false},
    "south_through": {"vehicle_count": 0, "oldest_wait_s": 0.0, "downstream_blocked": false},
    "south_left":    {"vehicle_count": 0, "oldest_wait_s": 0.0, "downstream_blocked": false},
    "west_through":  {"vehicle_count": 4, "oldest_wait_s": 9.0, "downstream_blocked": true},
    "west_left":     {"vehicle_count": 0, "oldest_wait_s": 0.0, "downstream_blocked": false}
  },
  "phases": {
    "P_N": {"vehicle_count": 2, "oldest_wait_s": 8.0},
    "P_E": {"vehicle_count": 4, "oldest_wait_s": 5.0},
    "P_S": {"vehicle_count": 0, "oldest_wait_s": 0.0},
    "P_W": {"vehicle_count": 4, "oldest_wait_s": 9.0}
  }
}
```

- **8 个规范车道全部显式给出**（无车补 `0`），云端无需知道规范 ID 列表即可直接渲染。
- 车道规范 ID：`{north,east,south,west}_{through,left}`。
- `current_phase_id` = 信号机当前实际相位（GD32 回读）；`degradation` = 决策层降级模式。
- 云端看板据此渲染：每向「直行/左转」车辆数、当前绿灯相位、降级状态、数据新鲜度（`ts_wall`）。

## 5. 影子运行唯一的一处语义差异（重要，请知悉）

- `state.controller` 来自 **GD32 实际回读的 STATUS**（真实当前相位 + 相位起点），**不是**生产的「乐观模型」。
  因此 `mode` 里会出现真实的 `clearance` / `all_red`（黄灯/全红清空阶段），比生产更准。
- `action.selected_phase_id` 仍是**决策层提议**（软请求），`state.controller.current_phase_id` 是**信号机实际相位**——两者在切换间隙会不同，属正常。

## 6. 本地侧（影子运行主机）会做什么（我方实现，仅说明）

- 复用 `LoggingPipeline` + `MqttCloudSink`，与生产同一套代码路径。
- 每 tick 生成快照 → 本地 JSONL 落盘（临时目录，可配）；**变化时**推事件上云。
- 云端 broker 不可达时：本地出站队列 + 指数退避重连，不影响控制回路（尽力而为）。

## 7. 前置条件：固件升级（黄闪 → 本地固定配时）

> 这一节给**硬件同事**。云端看板要正确展示「故障降级」状态，依赖固件先完成下面的升级。

### 7.1 配时变更

| 项 | 新值 |
|---|---|
| 全红清空 all_red | **0.5s**（原 1s） |
| 最大绿 max_green | **80s** |
| 最小绿 min_green | 12s（不变） |
| 黄灯 yellow | 3s（不变） |

### 7.2 故障降级流程（核心改动）

```
感知/决策层断流 ──超时──> 黄闪 ──(6s 未恢复)──> 本地固定配时（20s/相位轮转）
```

- 黄闪触发：① 宿主发 `SPECIAL flash`（感知断流）；② 固件看门狗 3s 无帧（决策层/链路失联）。
- 升级：黄闪持续 `2 × 3s = 6s` 仍未恢复 → 固件自动切 `LOCAL` 本地固定配时。

### 7.3 固件改动（`User/config.h` + `User/mini_signal.c`，共 3 处）

`config.h`：
```c
#define CFG_DEFAULT_ALL_RED_MS   (500UL)    /* 全红清空 0.5s（原 1000） */
#define CFG_LOCAL_GREEN_MS       (20000UL)  /* 本地固定绿灯 20s（原 45000） */
#define CFG_FLASH_ESCALATE_MS    (2UL * CFG_LINK_TIMEOUT_MS)  /* 黄闪 6s 后切本地 */
```

`mini_signal.c` 的 `SIG_FAILSAFE_FLASH` 分支：
```c
case SIG_FAILSAFE_FLASH:
    flash_tick();
    if (s_stage_ms >= CFG_FLASH_ESCALATE_MS) {
        s_mode = MODE_LOCAL;
        s_link_lost = 0;
        s_active_phase = 1;
        s_target_phase = 0; s_pending_phase = 0;
        enter_green();
    }
    break;
```

> 详见 [`gd32-firmware-flash-checklist.md`](gd32-firmware-flash-checklist.md)（含烧录后自检清单）。

### 7.4 云端会看到什么（事件时序，供看板展示故障态）

感知断流时，云端按顺序收到：

| 时刻 | 事件 | 字段 |
|---|---|---|
| ~6s | `degradation_change` | `from=normal → to=failsafe` |
| ~6s | `mode_change` | `from=normal → to=fault`（黄闪） |
| ~12s | `mode_change` | `from=fault → to=manual_override`（本地固定配时） |
| 恢复 | `mode_change` + `degradation_change` | 回到 normal |

> 注：`mode` 的取值映射见 §5；「本地固定配时」在 ControllerMode 里映射为 `manual_override`（信号机本地自主运行、决策层静默）。云端看板可据此把 `fault` 渲染为「黄闪」、`manual_override` 渲染为「本地固定配时」。

## 8. 验收判据

- [ ] 影子运行跑起来后，云端能订阅到 `traffic-control/mini_1/event/decision_change`，且相位切换时收到。
- [ ] 云端能收到 `traffic-control/mini_1/event/traffic_state`（2 Hz，8 车道车辆数）。
- [ ] 降级（感知断流 → 黄闪/本地固定配时）时能收到 §7.4 的事件时序。
- [ ] 后台按 `(mini_1, event_type, tick_id)` 去重正常，无重复事件。

---

### 已定配置（已就绪）

- MQTT broker：`192.168.0.112:1883`，账号 `admin` / `publicpassword`，无 TLS。
- topic 前缀：`traffic-control`，`junction_id=mini_1`。
