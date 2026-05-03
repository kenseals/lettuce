from __future__ import annotations

import os
from pathlib import Path

DEFAULT_WORKSPACE = Path.cwd()
LETTUCE_HOME = Path(os.environ.get("LETTUCE_HOME", str(DEFAULT_WORKSPACE / ".lettuce"))).expanduser().resolve()
