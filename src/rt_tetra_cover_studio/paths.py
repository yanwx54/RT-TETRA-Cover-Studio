from __future__ import annotations

import sys
from pathlib import Path


def project_dir() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root is not None:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    return project_dir().joinpath(*parts)
