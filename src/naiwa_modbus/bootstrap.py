from __future__ import annotations

import os
import sys
from pathlib import Path

_DLL_DIRECTORY_HANDLES = []


def configure_frozen_windows_runtime() -> None:
    """Prioritize the Qt DLLs shipped with the frozen Windows application."""
    if not sys.platform.startswith("win") or not getattr(sys, "frozen", False):
        return

    bundle_root = Path(sys._MEIPASS)
    qt_dir = bundle_root / "PySide6"
    shiboken_dir = bundle_root / "shiboken6"
    dll_dirs = [path for path in (qt_dir, shiboken_dir) if path.is_dir()]
    path_dirs = [*dll_dirs, bundle_root]

    # Keep the DLL directory handles alive for the entire process. This puts
    # the bundled Qt build ahead of unrelated Qt DLLs installed elsewhere.
    # Do not register the bundle root: PyInstaller may collect third-party DLLs
    # there from the build machine's PATH, including an ICU build that is
    # incompatible with Qt's imports.
    if hasattr(os, "add_dll_directory"):
        _DLL_DIRECTORY_HANDLES.extend(os.add_dll_directory(str(path)) for path in dll_dirs)
        sys._naiwa_dll_directory_handles = _DLL_DIRECTORY_HANDLES

    inherited_path = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join([*(str(path) for path in path_dirs), inherited_path])
    os.environ["QT_PLUGIN_PATH"] = str(qt_dir / "plugins")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qt_dir / "plugins" / "platforms")
