# GD32 固件修改清单（烧录前必读，一次性交底）

> 面向：硬件同事。改完重新编译 → 烧录进 GD32E230C8T6 开发板。
> 对应工程：`GD32E230C8T6/`（Keil MDK）。要改的文件就两个：
> `User/config.h`、`User/mini_signal.c`。协议/灯驱动/主循环都不用动。

---

## 0. 本次要做的三件事

| # | 内容 | 文件 |
|---|---|---|
| 1 | 全红清空改为 **0.5s**（原 1s） | `config.h` |
| 2 | 本地固定配时绿灯改为 **20s**（原 45s，推荐，可调） | `config.h` |
| 3 | 故障黄闪持续 **6s** 未恢复 → 自动切**本地固定配时** | `mini_signal.c` |

> 最大绿 80s、最小绿 12s、黄灯 3s 已在当前固件里是对的，不用改。

---

## 1. `User/config.h` 修改

在「配时默认值」一段（当前大概在第 61~71 行）：

**① 全红清空 1s → 0.5s**

```c
#define CFG_DEFAULT_ALL_RED_MS      (500UL)     /* 清空全红 0.5 s */
```

（原来是 `(1000UL)`，把 `1000` 改成 `500` 即可。）

**② 本地固定配时 45s → 20s（推荐，可按现场调）**

```c
#define CFG_LOCAL_GREEN_MS          (20000UL)   /* LOCAL 固定绿灯 20.0 s */
```

（原来是 `(45000UL)`。）

**③ 在 `CFG_LINK_TIMEOUT_MS` 下面新增一行**（黄闪升级阈值 = 2 个超时周期）：

```c
#define CFG_LINK_TIMEOUT_MS         (3000UL)    /* 失联阈值 3.0 s（已有，别动） */
#define CFG_FLASH_ESCALATE_MS       (2UL * CFG_LINK_TIMEOUT_MS)  /* 黄闪 6s 后切本地 */
```

---

## 2. `User/mini_signal.c` 修改（黄闪升级逻辑，核心）

找到 `mini_signal_tick()` 里的 `SIG_FAILSAFE_FLASH` 分支，当前大致是：

```c
case SIG_FAILSAFE_FLASH:
    flash_tick();
    break;
```

改成：

```c
case SIG_FAILSAFE_FLASH:
    flash_tick();
    if (s_stage_ms >= CFG_FLASH_ESCALATE_MS) {
        /* 黄闪 2×超时(6s)仍未恢复 → 自动降级为本地固定配时，保证路口正常轮转 */
        s_mode = MODE_LOCAL;          /* 本地固定配时 */
        s_link_lost = 0;
        s_active_phase = 1;           /* 从 N 相起步 */
        s_target_phase = 0;
        s_pending_phase = 0;
        enter_green();                /* s_stage_ms 归零，进入绿灯固定轮转 */
    }
    break;
```

> 说明：
> - `s_stage_ms` 在进入黄闪时已经被清零（`enter_failsafe_flash()` 和 `handle_special(flash)` 里都有 `s_stage_ms = 0`），所以 `s_stage_ms >= 6s` 就是「黄闪已持续 6s」，判断可靠。
> - 这个分支同时覆盖两种故障：① 宿主发 `SPECIAL flash`（感知断流）；② 固件看门狗自进黄闪（决策层/链路失联）。两种最终都走同一升级逻辑。

---

## 3. 完整故障流程（改完后应是这样）

```
感知断流 ──> 宿主发 SPECIAL flash ─┐
                                   ├──> 固件黄闪 ──(6s 未恢复)──> 本地固定配时(20s/相位轮转)
决策层/链路失联 ──> 固件看门狗3s ──┘
                                            ▲
   感知恢复 → 宿主发 TAKEOVER + RESET ───────┘（退出黄闪/本地，回自适应）
```

配时（宿主启动会经 CONFIG_TIMING 下发，两边一致）：
**最小绿 12s / 最大绿 80s / 黄灯 3s / 全红 0.5s**。

---

## 4. 烧录后自检清单（拿串口助手/看板对着验）

- [ ] 上电：5s 黄闪 → 10s 全红 → 绿灯 N 相（不变）。
- [ ] 正常相位切换：黄灯 3s → **全红 0.5s** → 下个绿灯（全红明显变短）。
- [ ] 关掉合成感知（或按看板「注入故障」）：约 6s 后进黄闪；**再等 6s 自动变成四向固定轮转（20s/相位）**，不再停在黄闪。
- [ ] 恢复感知：灯组重新回到自适应切换。
- [ ] 拔掉串口：3s 进黄闪 → 6s 后自动转本地固定配时（同上）。

---

## 5. 关键结论（一句话）

> 配时：全红 0.5s、最大绿 80s；故障：**黄闪 6s → 本地固定配时**，而不是永久黄闪。
> 改动只有 3 处：`config.h` 两行数值 + 一个宏，`mini_signal.c` 一段 8 行。
