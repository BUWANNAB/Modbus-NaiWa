from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from naiwa_modbus.bootstrap import configure_frozen_windows_runtime

configure_frozen_windows_runtime()

from naiwa_modbus.main import main


if __name__ == "__main__":
    raise SystemExit(main())
