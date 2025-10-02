"""Utilities for ensuring the project root is importable."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ROOT_STR = str(_ROOT)

if _ROOT_STR not in sys.path:
    sys.path.insert(0, _ROOT_STR)

__all__ = ("_ROOT", "_ROOT_STR")
