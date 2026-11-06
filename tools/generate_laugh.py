"""Generate a small, original, offline laugh-like WAV prompt for the app."""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path


def main() -> None:
    sample_rate = 22050
    duration = 0.98
    total = int(sample_rate * duration)
    pulses = (0.04, 0.26, 0.49, 0.72)
    pulse_duration = 0.19
    rng = random.Random(34)
    samples: list[int] = []

    for index in range(total):
        t = index / sample_rate
        signal = 0.0
        for pulse_index, start in enumerate(pulses):
            local = t - start
            if 0 <= local < pulse_duration:
                progress = local / pulse_duration
                envelope = min(1.0, progress * 15) * max(0.0, (1.0 - progress) ** 0.55)
                fundamental = 250 + 85 * math.sin(progress * math.pi) - pulse_index * 5
                phase = 2 * math.pi * fundamental * local
                voiced = (
                    math.sin(phase)
                    + 0.54 * math.sin(phase * 2.02 + 0.2)
                    + 0.28 * math.sin(phase * 3.05 + 0.7)
                    + 0.13 * math.sin(phase * 4.1 + 1.4)
                ) / 1.95
                rasp = (rng.random() * 2 - 1) * 0.055
                signal += envelope * (0.78 * voiced + rasp)
        fade = min(1.0, (duration - t) * 20)
        sample = int(max(-1.0, min(1.0, signal * fade)) * 32767 * 0.58)
        samples.append(sample)

    output = Path(__file__).resolve().parents[1] / "assets" / "naiwa_laugh.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(b"".join(struct.pack("<h", value) for value in samples))
    print(f"Generated {output} ({len(samples) / sample_rate:.2f}s)")


if __name__ == "__main__":
    main()
