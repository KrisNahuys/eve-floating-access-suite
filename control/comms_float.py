#!/usr/bin/env python3
"""Floating status box — generic house chrome (no personal PII in defaults)."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
import tkinter as tk

CONTROL = Path(__file__).resolve().parent
STATE = CONTROL / "comms_float_state.json"

def load_bits() -> dict:
    bits = {
        "title": "House · Comms",
        "line1": "Architect01 · Eve · Grok",
        "line2": "Clear eyes · shield · sword-as-peace",
        "line3": "Road Between the Lines",
        "rule": "Great intent · no dark feed",
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    if STATE.exists():
        try:
            bits.update(json.loads(STATE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return bits

def main() -> int:
    bits = load_bits()
    root = tk.Tk()
    root.title(bits.get("title", "Comms"))
    root.attributes("-topmost", True)
    root.configure(bg="#0d1117")
    root.geometry("320x220+40+80")
    for key in ("line1", "line2", "line3", "rule", "ts"):
        tk.Label(root, text=bits.get(key, ""), fg="#e6edf3", bg="#0d1117",
                 font=("Segoe UI", 10), wraplength=280, justify="left").pack(anchor="w", padx=12, pady=4)
    root.mainloop()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
