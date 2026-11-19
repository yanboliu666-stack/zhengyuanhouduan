# 故障降级流程升级 · 固件修改建议（黄闪 → 本地固定配时）

> 面向对象：负责 GD32 固件的同事。
> 变更目标：故障（感知断流 / 决策层失联）时不再是「停在黄闪」，而是
> **黄闪 2 个超时周期后自动切「本地固定配时」**，保证路口长期正常运行。
> 配时同时调整：**全红清空 0.5s、最大绿 80s**。

---

## 1. 目标故障流程（三级）

```
                    ┌─ 感知断流（宿主决策层 FAILSAFE）─> 宿主发 SPECIAL flash(0xFE)
  无输出 超时 ──────┤
                    └─ 决策层/链路失联（固件看门狗 3s 无有效帧）─> 固件自进黄闪
                                    │
                                    ▼
                           【黄闪 FAILSAFE_FLASH】
                                    │ 持续 2 × 3s = 6s 仍未恢复
                                    ▼
                       【本地固定配时 LOCAL】（四向按固定方案轮流放行）
                                    │ 宿主恢复 → TAKEOVER + RESET
                                    ▼
                          【REMOTE 自适应】（恢复正常）
```

- **感知断流**（宿主还活着）：宿主决策层 FAILSAFE → 宿主发 `SPECIAL flash` → 固件黄闪。
- **决策层/链路失联**（宿主死/断）：固件看门狗（REMOTE 下 3s 无有效帧）→ 固件自进黄闪。
- 两种触发最终都进同一「黄闪」态，之后按同一套升级逻辑走。

## 2. 配时变更（已由宿主 CONFIG_TIMING 下发，固件无需改常量）

| 项 | 新值 | 说明 |
|---|---|---|
| 全红清空 all_red | **0.5 s** | 相位切换的清空全红（黄灯→全红→绿灯） |
| 最大绿 max_green | **80 s** | 已改 |
| 最小绿 min_green | 12 s | 不变 |
| 黄灯 yellow | 3 s | 不变 |

> 这些值宿主启动时会用 `CONFIG_TIMING` 下发（`all_red=5` 分秒 → 固件 `×100=500ms`）。
> 固件 `config.h` 里的默认值可同步改成 0.5s 以防 CONFIG_TIMING 丢失，但非必须。

## 3. 固件改动（升级逻辑，必做）

`User/mini_signal.c` 的 `mini_signal_tick()` 中，`SIG_FAILSAFE_FLASH` 分支目前只做
`flash_tick()`。改为：**黄闪持续满 2 个超时周期后，自动切 LOCAL 本地固定配时**。

`User/config.h` 加常量：

```c
/* 黄闪升级：持续 2 × 失联阈值(3s) = 6s 仍未恢复 → 自动切本地固定配时 */
#define CFG_FLASH_ESCALATE_MS   (2UL * CFG_LINK_TIMEOUT_MS)
```

`User/mini_signal.c` 的 `SIG_FAILSAFE_FLASH` 分支：

```c
case SIG_FAILSAFE_FLASH:
    flash_tick();
    if (s_stage_ms >= CFG_FLASH_ESCALATE_MS) {
        /* 黄闪超时：降级为本地固定配时，保证路口正常轮转 */
        s_mode = MODE_LOCAL;          /* 本地固定配时 */
        s_link_lost = 0;
        s_active_phase = 1;           /* 从 N 相起步 */
        s_target_phase = 0;
        s_pending_phase = 0;
        enter_green();                /* s_stage_ms=0，进入绿灯固定轮转 */
    }
    break;
```

> `s_stage_ms` 在进入黄闪时已归零（`enter_failsafe_flash` / `handle_special` 都会 `s_stage_ms=0`），
> 因此 `s_stage_ms >= 6s` 即「黄闪已持续 6s」，判断可靠。

## 4. 本地固定配时方案（沿用 LOCAL，建议一起确认）

- 本地固定绿灯目前 `CFG_LOCAL_GREEN_MS = 45000`（45s/相位）。若想更「正常运行」，
  可改为 20s 或做成可配置表（见 [`gd32-firmware-local-plan-change.md`](gd32-firmware-local-plan-change.md) §4）。
- 升级到 LOCAL 后，`send_status()` 会自动上报 `mode=1`（LOCAL），宿主据此知道「已切本地」。

## 5. 宿主侧配套（已由我方完成，仅说明契约）

- 感知断流 FAILSAFE → 宿主发 `SPECIAL flash(0xFE)` → 固件黄闪。
- 感知恢复 → 宿主发 `TAKEOVER(0x03)` + `RESET(0x07)` → 固件退出黄闪/本地，回 REMOTE。
- 固件只需保证：收到 `SPECIAL flash` → 黄闪；黄闪 6s → LOCAL；收到 `TAKEOVER+RESET` → 回 REMOTE。

## 6. 验收标准

- [ ] 感知停发 → 约 6s（决策层 FAILSAFE）后固件进黄闪。
- [ ] 黄闪持续 **6s** 仍未恢复 → 固件自动切 LOCAL，四向按固定配时轮流放行。
- [ ] 切换清空：黄灯 3s → **全红 0.5s** → 绿灯（全红从 1s 变 0.5s 后肉眼可辨）。
- [ ] 感知恢复 → 宿主 TAKEOVER+RESET → 固件回 REMOTE 自适应。
- [ ] 拔串口（决策层/链路失联）→ 3s 黄闪 → 6s 后 LOCAL（同样走升级逻辑）。
