#!/usr/bin/env python3
"""
Root entrypoint proxy for Rclone Cloud Manager CLI.
Routes command-line execution directly to src/main.py.
"""

import sys
from pathlib import Path

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.main import main

if __name__ == "__main__":
    main()
