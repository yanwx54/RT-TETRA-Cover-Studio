from __future__ import annotations

import os
import tempfile
from pathlib import Path


cache_dir = Path(tempfile.gettempdir()) / "RT-TETRA-Cover-Studio" / "matplotlib"
cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
