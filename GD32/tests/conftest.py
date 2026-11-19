"""pytest 路径引导：把 GD32 根目录加入 sys.path，使 ``host`` 可导入。

协议/链路测试不依赖 zhengyuan（它们只依赖 host.* 与 stdlib + pyyaml）。
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
