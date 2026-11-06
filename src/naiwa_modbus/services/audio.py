from __future__ import annotations

import os
import sys
import time
from pathlib import Path

try:
    import winsound
except ImportError:  # pragma: no cover - Windows is the packaged target.
    winsound = None


def resource_path(relative: str) -> Path:
    """Resolve a bundled asset in source and PyInstaller one-file builds."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    return root / relative


class LaughPlayer:
    def __init__(self) -> None:
        self.enabled = True
        self.custom_path: str | None = None
        self._last_played = 0.0
        self.minimum_gap = 1.8

    def play(self, *, force: bool = False) -> None:
        if not self.enabled or winsound is None:
            return
        now = time.monotonic()
        if not force and now - self._last_played < self.minimum_gap:
            return
        path = Path(self.custom_path) if self.custom_path else resource_path("assets/naiwa_laugh.wav")
        if not path.is_file():
            return
        try:
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            self._last_played = now
        except (RuntimeError, OSError):
            pass

    def stop(self) -> None:
        if winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except (RuntimeError, OSError):
                pass
