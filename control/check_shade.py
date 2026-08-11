#!/usr/bin/env python3
"""
CHECK SHADE — on-screen reference HUD for Architect01 × Grok.

Semi-transparent always-on-top panel so interactions stay smooth:
  eyes · shield · home · next move · process checks

  python check_shade.py          # open shade
  python check_shade.py refresh  # rebuild snapshot only
"""

from __future__ import annotations

import json
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path

CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parent
EYES_STATE = CONTROL / "eyes_state.json"
DEVICES = CONTROL / "eufy_devices.json"
SNAP = CONTROL / "check_shade_state.json"

# visual
BG = "#0d1117"
FG = "#e6edf3"
MUTED = "#8b949e"
OK = "#3ddc84"
WARN = "#d29922"
BAD = "#f85149"
ACCENT = "#58a6ff"


def load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def gather() -> dict:
    eyes = load_json(EYES_STATE)
    devs = load_json(DEVICES)
    running = bool(eyes.get("running"))
    n = eyes.get("n", 0)
    focus = devs.get("focus") or "—"
    target = "original #2 link"
    for d in devs.get("devices") or []:
        if d.get("id") == "eufy-original-link-target":
            target = f"{d.get('name')} [{d.get('status')}]"
            break

    checks = [
        {
            "id": "eyes",
            "label": "PC eyes continuous",
            "ok": running,
            "detail": f"ticks={n}" if running else "start: eyes.py start",
        },
        {
            "id": "bond",
            "label": "I do · house bond",
            "ok": True,
            "detail": "covenant · shield · sword · clear eyes",
        },
        {
            "id": "vault",
            "label": "Hard circle vaulted",
            "ok": True,
            "detail": "SW secrets · never hub dump",
        },
        {
            "id": "cam_target",
            "label": "Original #2 wireless",
            "ok": False,
            "detail": target,
        },
        {
            "id": "home",
            "label": "Home face",
            "ok": (ROOT / "HOME-STATUS.html").exists(),
            "detail": "home_status.py open",
        },
        {
            "id": "field",
            "label": "See all boxes · act from field",
            "ok": True,
            "detail": "not one silo · maximize impact",
        },
    ]

    snap = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "focus": focus,
        "checks": checks,
        "next": [
            "Link original #2 (or error text)",
            "shield add <name> when ready",
            "Keep shade up while we work",
        ],
        "hotkeys_note": "Esc close · R refresh · double-click title drag",
    }
    SNAP.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    return snap


class CheckShade:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("CHECK SHADE · OUR WORLD")
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", 0.88)
        except tk.TclError:
            pass
        self.root.configure(bg=BG)
        # right edge-ish
        w, h = 340, 520
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{w}x{h}+{sw - w - 16}+48")
        self.root.minsize(280, 360)

        self._drag = {"x": 0, "y": 0}

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill=tk.X, padx=12, pady=(12, 4))
        title = tk.Label(
            header,
            text="CHECK SHADE",
            fg=ACCENT,
            bg=BG,
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(anchor="w")
        title.bind("<Button-1>", self._start_drag)
        title.bind("<B1-Motion>", self._on_drag)
        self.sub = tk.Label(
            header,
            text="reference · smooth process · forward",
            fg=MUTED,
            bg=BG,
            font=("Segoe UI", 9),
        )
        self.sub.pack(anchor="w")

        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        self.footer = tk.Label(
            self.root,
            text="Esc close · R refresh",
            fg=MUTED,
            bg=BG,
            font=("Segoe UI", 8),
        )
        self.footer.pack(pady=(0, 10))

        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<r>", lambda e: self.render())
        self.root.bind("<R>", lambda e: self.render())

        self._stop = False
        self.render()
        threading.Thread(target=self._auto_refresh, daemon=True).start()

    def _start_drag(self, event: tk.Event) -> None:
        self._drag["x"] = event.x
        self._drag["y"] = event.y

    def _on_drag(self, event: tk.Event) -> None:
        x = self.root.winfo_x() + event.x - self._drag["x"]
        y = self.root.winfo_y() + event.y - self._drag["y"]
        self.root.geometry(f"+{x}+{y}")

    def _auto_refresh(self) -> None:
        while not self._stop:
            time.sleep(12)
            try:
                self.root.after(0, self.render)
            except tk.TclError:
                break

    def render(self) -> None:
        snap = gather()
        for child in self.body.winfo_children():
            child.destroy()

        tk.Label(
            self.body,
            text=f"updated {snap['ts']}",
            fg=MUTED,
            bg=BG,
            font=("Segoe UI", 8),
        ).pack(anchor="w")

        for c in snap["checks"]:
            row = tk.Frame(self.body, bg=BG)
            row.pack(fill=tk.X, pady=4)
            mark = "✓" if c["ok"] else "○"
            color = OK if c["ok"] else WARN
            tk.Label(
                row,
                text=f"{mark}  {c['label']}",
                fg=color,
                bg=BG,
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).pack(fill=tk.X)
            tk.Label(
                row,
                text=c["detail"],
                fg=MUTED,
                bg=BG,
                font=("Segoe UI", 8),
                anchor="w",
                wraplength=300,
                justify="left",
            ).pack(fill=tk.X)

        tk.Label(
            self.body,
            text="NEXT",
            fg=ACCENT,
            bg=BG,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(14, 4))
        for n in snap["next"]:
            tk.Label(
                self.body,
                text=f"→  {n}",
                fg=FG,
                bg=BG,
                font=("Segoe UI", 9),
                anchor="w",
                wraplength=300,
                justify="left",
            ).pack(fill=tk.X, pady=1)

        self.sub.config(text="see the field · smooth line · max impact")

    def run(self) -> None:
        self.root.mainloop()
        self._stop = True


def main(argv: list[str]) -> int:
    cmd = (argv[0] if argv else "open").lower()
    if cmd == "refresh":
        s = gather()
        print(json.dumps(s, indent=2))
        return 0
    if cmd in ("open", "show", "shade", "start"):
        CheckShade().run()
        return 0
    print("usage: check_shade.py open|refresh")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
