"""Entry point pro blackboard-backup-viewer.

Spuštění:
    python launcher.py            # použije ./config.toml
    python launcher.py path.toml  # vlastní cesta k configu
"""
from __future__ import annotations

import sys

from bb_viewer.server import main

if __name__ == "__main__":
    sys.exit(main())
