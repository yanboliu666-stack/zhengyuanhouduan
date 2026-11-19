# 断流降级为「本地固定配时」· 固件修改建议

> 面向对象：负责 GD32 固件的同事。
> 目标：把「感知断流」的降级行为，从当前的**黄闪**改为**本地固定配时方案**，让路口在感知故障期间仍按固定周期正常运行。
> 配套协议仍以 [`host/protocol.py`](../host/protocol.py) 与 [`docs/gd32-firmware-spec.md`](gd32-firmware-spec.md) 为准。

---

## 1. 现状（为什么现在是全红/黄闪）

当前链路在「视觉感知层停发数据」时：

```
感知停发 → 宿主机决策层判 FAILSAFE → 宿主机发 SPECIAL flash(0xFE) → 固件进 FAILSAFE_FLASH（四向黄闪）
```

于是路口停在黄闪，不再放行。这对真实路口是**过激**的：感知断流只是「眼睛瞎了」，信号机本身是好的，应当改跑本地固定配时。

## 2. 目标行为

| 故障类型 | 触发 | 期望灯态 |
|---|---|---|
| **感知断流**（宿主还活着，但没有感知数据） | 宿主决策层 FAILSAFE → 宿主发 `DETACH(0x04)` | 固件进入 **LOCAL 本地固定配时**，四向按固定方案轮流放行 |
| **通信断链**（宿主失联，串口无有效帧） | 固件看门狗 3s 超时 | 仍走 **黄闪**（保持不变，这是真故障） |
| 感知恢复 | 宿主发 `TAKEOVER(0x03)` | 固件回到 REMOTE 自适应 |

## 3. 改动总览

| 侧 | 改动 |
|---|---|
| **固件（你）** | 把「本地固定配时方案」参数化 + 合理默认值（§4） |
| 主机（接口层，我方） | FAILSAFE 时发 `DETACH` 而非 `FLASH`（§5） |

> 好消息：固件**已经**具备「`DETACH` → LOCAL 固定轮转」的骨架。本次主要是把「本地配时方案」做成**可配置、参数合理**，并确认边界行为，改动量不大。

---

## 4. 固件侧改动建议

### 4.1 本地固定配时方案参数化（必做）

现状（`User/config.h`）：

```c
#define CFG_LOCAL_GREEN_MS  (45000UL)   /* LOCAL 固定绿灯 45s，单一硬编码 */
```

`User/mini_signal.c` 的 `mini_signal_tick()` GREEN 阶段 LOCAL 分支：

```c
if (s_mode == MODE_LOCAL) {
    if (s_stage_ms >= CFG_LOCAL_GREEN_MS) {   // ← 45s 硬编码
        s_target_phase = next;
        enter_yellow();
    }
}
```

**建议**：改成**每相位可配置的固定绿灯表**，默认 20s（比 45s 更适合“保障正常运行”的观感，值可另定）：

1. `config.h` 新增默认值：

```c
/* 本地固定配时方案：每相位固定绿灯（ms），下标 0..3 = N/E/S/W */
#define CFG_LOCAL_GREEN_MS_DEFAULT   (20000UL)   /* 默认 20s，可按“方案”调整 */
```

2. `mini_signal.c` 增加本地配时表并初始化：

```c
static uint32_t s_local_green_ms[4];   /* 本地固定配时：每相位绿灯 ms */

void mini_signal_init(void) {
    ...
    for (i = 0; i < 4; i++) {
        s_local_green_ms[i] = CFG_LOCAL_GREEN_MS_DEFAULT;
    }
    ...
}
```

3. LOCAL 分支改读该表：

```c
if (s_mode == MODE_LOCAL) {
    if (s_stage_ms >= s_local_green_ms[s_active_phase - 1]) {
        s_target_phase = next;
        enter_yellow();
    }
}
```

> 清空（黄灯 3s + 全红 1s）继续沿用各相位已有的 `yellow` / `all_red`，无需单独定义。

### 4.2 新增「本地配时」下发命令（可选，推荐）

若希望宿主机能动态下发本地配时方案（而不是写死默认值），扩展协议加一个命令：

- **`CMD_CONFIG_LOCAL = 0x08`**（主机 → GD32），载荷 **8 字节 = 4 × uint16 分秒(LE)**，顺序 **N/E/S/W**，表示各相位本地固定绿灯时长。
- 固件收到后写 `s_local_green_ms[]`，回 **`0x88 CONFIG_LOCAL_ACK`**（1 字节结果码：`0x00` OK / `0x02` 长度非法）。

`User/protocol.h` 命令字枚举处加：

```c
CMD_CONFIG_LOCAL = 0x08,
```

`User/mini_signal.c` 的 `mini_signal_handle_command()` 加分支：

```c
case CMD_CONFIG_LOCAL:
    if (len == 8) {
        for (p = 0; p < 4; p++) {
            s_local_green_ms[p] = ((uint32_t)(payload[p*2] | (payload[p*2+1] << 8))) * 100UL;
        }
        result = RESULT_OK;
    } else {
        result = RESULT_REJECTED;
    }
    ack[0] = result;
    protocol_send_frame(PROTO_ADDR_HOST, CMD_CONFIG_LOCAL | CMD_ACK_MASK, ack, 1);
    break;
```

> 主机侧对应的 Python 编码/下发逻辑我方会同步加，保证两边字节一致。

### 4.3 边界行为确认（多数已满足，核对即可）

- `DETACH` 分支现状：`s_mode = MODE_LOCAL; s_pending_phase = 0;` —— ✅ 已满足，保留。
- 清空（YELLOW/ALL_RED）中途收到 DETACH：清空走完后进入 LOCAL 固定轮转 —— ✅ 现状已满足。
- `send_status()` 在 LOCAL 时上报 `mode = 1`（LOCAL）—— ✅ 现状已满足，宿主机据此知道「已切本地」。
- 失联看门狗**只在 REMOTE 生效**（`s_mode == MODE_REMOTE && ...`）—— ✅ 现状已满足：LOCAL 模式下不黄闪，正好符合「本地固定配时保障运行」语义，**不要改**。

---

## 5. 主机侧配套改动（接口层，我方负责，此处仅说明契约）

`host/main.py` 的 FAILSAFE 分支：

- 现在：`link.request_special(Special.FLASH)`（黄闪）。
- 改为：`link.request_detach()`（交权 → 固件进入 LOCAL 固定配时）。

恢复：感知恢复后 `link.request_takeover()`（回 REMOTE 自适应）。

**与固件的交互契约**（固件无需感知主机内部实现，只需保证下面两条成立）：

1. 收到 `DETACH(0x04)` → 进入 LOCAL，开始按固定方案轮转，并在 STATUS 上报 `mode=1`。
2. 收到 `TAKEOVER(0x03)` → 回到 REMOTE，接受相位软请求。

---

## 6. 验收标准（烧录后自测）

- [ ] 感知停发 → 约 3s 内固件进入 LOCAL，四向按固定配时轮流放行（**不再黄闪/全红**）。
- [ ] 固定周期 = 每相位 20s 绿 + 3s 黄 + 1s 全红（或按配置值）。
- [ ] 感知恢复 → 固件回到 REMOTE 自适应。
- [ ] 拔掉串口（通信断链）→ 仍黄闪（保持不变）。
- [ ] STATUS 在 LOCAL 期间 `mode=1`，切回 REMOTE 后 `mode=0`。

---

## 7. 关键结论（一句话）

> **感知断流 = 交权给本地固定配时（DETACH → LOCAL）；通信断链 = 黄闪（看门狗）。**
> 固件已有的 `DETACH→LOCAL` 骨架直接复用，本次只需把「本地固定绿灯」从硬编码 45s 改为可配置（默认 20s），其余边界已满足。
