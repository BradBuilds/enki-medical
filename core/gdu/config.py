"""
GDU Configuration

Single source of truth for GDU-related paths and settings.
"""

import os
from pathlib import Path

# Active set registry path (relative to project root). Point ENKI_ACTIVE_SET at your own
# active set to admit your own libraries without editing the shipped one.
ACTIVE_SET_PATH = Path(os.environ.get("ENKI_ACTIVE_SET", "active_set_v3.json"))
