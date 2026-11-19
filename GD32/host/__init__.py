"""GD32 本地临时控制接口层（宿主机侧）。

连接视觉感知层（感知 JSON）→ zhengyuan 逻辑层（DecisionLayer）→ GD32 微型
红绿灯（串口软请求 + 状态回读）。宿主机在 RK3588 或任意 Linux/PC 上运行，
通过 USB 转 TTL 连接 GD32E230 的 USART0。
"""
