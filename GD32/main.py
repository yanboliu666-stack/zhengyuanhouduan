#!/usr/bin/env python3
"""GD32 影子运行入口（bootstrap）。

在 GD32 目录下运行：:

    python main.py --config configs/shadow.yaml
    python main.py --config configs/shadow.yaml --max-ticks 5

它把 GD32/ 与 zhengyuan 的源码路径加进 sys.path，再调用 ``host.main``。
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from host.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
