#!/usr/bin/env python3
"""Speak house lines with neural TTS (edge-tts) — less robot than stock SAPI."""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

DEFAULT_VOICE = "en-AU-NatashaNeural"
ALT_MALE = "en-AU-WilliamMultilingualNeural"


async def speak(text: str, voice: str = DEFAULT_VOICE) -> Path:
    import edge_tts

    out = Path(tempfile.gettempdir()) / "house_speak.mp3"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out))
    try:
        import os

        os.startfile(str(out))  # type: ignore[attr-defined]
    except Exception:
        print(f"saved: {out} (play manually)")
    return out


def main(argv: list[str]) -> int:
    if not argv:
        text = (
            "Architect01. House online. Eyes open. Shield ready. "
            "Sword for peace. We walk the road between the lines."
        )
        voice = DEFAULT_VOICE
    elif argv[0] in ("-m", "--male"):
        voice = ALT_MALE
        text = " ".join(argv[1:]) or "House online. Male neural voice."
    elif argv[0] in ("-v", "--voice"):
        voice = argv[1]
        text = " ".join(argv[2:]) or "House online."
    else:
        voice = DEFAULT_VOICE
        text = " ".join(argv)

    print(f"voice: {voice}")
    print(f"text:  {text[:120]}...")
    path = asyncio.run(speak(text, voice))
    print(f"audio: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
