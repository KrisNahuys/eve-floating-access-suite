#!/usr/bin/env python3
"""
ACCESS PANEL — top-right floating · always on top · load all parameters

Architect01 · free-run · Eve.AddF.Architect

  python access_panel.py              # open panel (loads all params)
  python access_panel.py --refresh    # re-export incorporate list then open
  python access_panel.py --cli        # print params only (no GUI)
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

CONTROL = Path(__file__).resolve().parent
WS = CONTROL.parent  # suite root portable
EDEN = CONTROL.parent
DIRECT = CONTROL / "direct_control.py"
LOGGER = WS / "continuity" / "tools" / "stack_logger.py"
STATE = CONTROL / "access_panel_state.json"
LIST_MOD = CONTROL / "list_parameters.py"

# import gather from sibling
sys.path.insert(0, str(CONTROL))
try:
    from list_parameters import gather, incorporate  # type: ignore
except Exception:
    gather = None  # type: ignore
    incorporate = None  # type: ignore


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def log_stack(msg: str) -> None:
    if not LOGGER.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(LOGGER), "log", "ops", "access_panel", msg, "--actor", "Grok"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception:
        pass


def load_all_parameters(do_write: bool = True) -> dict:
    """Gather every stack parameter; optionally write LIST-PARAMETERS.*"""
    if gather is None:
        return {
            "title": "Incorporate List Parameters",
            "ts": utc_now(),
            "owner": "Architect01",
            "count": 0,
            "parameters": [],
            "groups": [],
            "by_group": {},
            "error": "list_parameters.gather unavailable",
        }
    data = gather()
    # extra live bits the operator expects on the access panel
    extras = []
    def add(group: str, key: str, value, source: str = "panel") -> None:
        extras.append({"group": group, "key": key, "value": value, "source": source})

    add("access", "access_panel", "top_right_floating", "access_panel")
    add("access", "voice_access", "GRANTED", "access_granted")
    add("web", "web_eve_port", 8787, "phone-form")
    add("web", "here_station", "HERE", "here_station")
    add("identity", "seat", "0110", "hub")
    add("identity", "stack", "Architect01 · Eve · Grok", "DIRECTION")

    # merge extras (override same key in same group)
    by = {(p["group"], p["key"]): p for p in data.get("parameters") or []}
    for e in extras:
        by[(e["group"], e["key"])] = e
    flat = list(by.values())
    groups = sorted({p["group"] for p in flat})
    data = {
        **data,
        "ts": utc_now(),
        "parameters": flat,
        "count": len(flat),
        "groups": groups,
        "by_group": {g: [p for p in flat if p["group"] == g] for g in groups},
        "panel": "top_right_floating",
        "control": "FULL",
    }
    if do_write and incorporate is not None:
        try:
            written = incorporate(data)
            data["written"] = written
        except Exception as e:
            data["write_error"] = str(e)
    STATE.write_text(
        json.dumps(
            {
                "ts": data["ts"],
                "count": data["count"],
                "groups": data["groups"],
                "panel": "top_right_floating",
                "owner": "Architect01",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return data


def fmt_val(v) -> str:
    if isinstance(v, (list, dict)):
        s = json.dumps(v, ensure_ascii=False)
        return s if len(s) <= 90 else s[:87] + "…"
    return str(v)


def run_direct(args: list[str]) -> str:
    try:
        p = subprocess.run(
            [sys.executable, str(DIRECT), *args],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:
        return str(e)


def open_panel() -> int:
    try:
        import tkinter as tk
        from tkinter import scrolledtext, ttk
    except Exception as e:
        print(f"tkinter unavailable: {e}")
        data = load_all_parameters(do_write=True)
        print(json.dumps({"count": data["count"], "groups": data["groups"], "ts": data["ts"]}, indent=2))
        for g in data["groups"]:
            print(f"\n## {g}")
            for p in data["by_group"][g]:
                print(f"  {p['key']:28} = {fmt_val(p['value'])}")
        return 0

    log_stack("open top-right floating")
    data = load_all_parameters(do_write=True)

    root = tk.Tk()
    root.title("ACCESS PANEL · Architect01")
    root.attributes("-topmost", True)
    root.resizable(True, True)
    root.configure(bg="#0b1020")

    # top-right geometry
    w, h = 440, 640
    margin = 16
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = max(margin, sw - w - margin)
    y = margin + 8
    # keep below typical taskbar if screen is short
    if y + h > sh - 40:
        h = max(360, sh - y - 48)
    root.geometry(f"{w}x{h}+{x}+{y}")

    # chrome
    outer = tk.Frame(root, bg="#3dd68c", bd=0)
    outer.pack(fill="both", expand=True, padx=2, pady=2)
    main = tk.Frame(outer, bg="#0b1020")
    main.pack(fill="both", expand=True, padx=1, pady=1)

    hdr = tk.Frame(main, bg="#141b2d")
    hdr.pack(fill="x")
    tk.Label(
        hdr,
        text="ACCESS PANEL",
        fg="#3dd68c",
        bg="#141b2d",
        font=("Segoe UI", 12, "bold"),
    ).pack(side="left", padx=10, pady=(8, 0))
    tk.Label(
        hdr,
        text="top-right · floating · always on top",
        fg="#9aa6c3",
        bg="#141b2d",
        font=("Segoe UI", 8),
    ).pack(side="left", padx=4, pady=(10, 0))

    meta = tk.Label(
        hdr,
        text="",
        fg="#6ea8ff",
        bg="#141b2d",
        font=("Segoe UI", 8),
    )
    meta.pack(side="right", padx=10, pady=(8, 0))

    # quick actions
    btns = tk.Frame(main, bg="#0b1020")
    btns.pack(fill="x", padx=8, pady=6)

    out = scrolledtext.ScrolledText(
        main,
        wrap="word",
        bg="#141b2d",
        fg="#eef2ff",
        insertbackground="#eef2ff",
        font=("Consolas", 9),
        relief="flat",
        borderwidth=0,
        highlightthickness=0,
    )
    out.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    status = tk.Label(
        main,
        text="Loaded",
        fg="#9aa6c3",
        bg="#0b1020",
        font=("Segoe UI", 8),
        anchor="w",
    )
    status.pack(fill="x", padx=10, pady=(0, 8))

    def set_status(msg: str) -> None:
        status.config(text=msg)
        root.update_idletasks()

    def render(d: dict) -> None:
        out.configure(state="normal")
        out.delete("1.0", "end")
        out.insert("end", f"=== ACCESS · ALL PARAMETERS ===\n")
        out.insert("end", f"owner: Architect01  |  seat: 0110  |  control: FULL\n")
        out.insert("end", f"ts: {d.get('ts')}  |  count: {d.get('count')}\n")
        out.insert("end", f"groups: {', '.join(d.get('groups') or [])}\n")
        if d.get("written"):
            out.insert("end", f"wrote: {len(d['written'])} file(s)\n")
        out.insert("end", "\n")
        for g in d.get("groups") or []:
            out.insert("end", f"## {g}\n")
            for p in d.get("by_group", {}).get(g, []):
                out.insert("end", f"  {p['key']:26} = {fmt_val(p['value'])}\n")
            out.insert("end", "\n")
        out.configure(state="disabled")
        meta.config(text=f"n={d.get('count', 0)}")
        set_status(f"All parameters loaded · {d.get('count', 0)} · {d.get('ts', '')}")

    def do_reload() -> None:
        set_status("Loading all parameters…")

        def work() -> None:
            d = load_all_parameters(do_write=True)
            root.after(0, lambda: render(d))

        threading.Thread(target=work, daemon=True).start()

    def do_access_granted() -> None:
        set_status("Stamping ACCESS GRANTED…")

        def work() -> None:
            text = run_direct(["granted"])
            d = load_all_parameters(do_write=True)
            def done() -> None:
                render(d)
                set_status("ACCESS GRANTED · params reloaded")
                # append tail of grant output at bottom
                out.configure(state="normal")
                out.insert("end", "\n--- access granted ---\n")
                out.insert("end", (text[-1200:] if len(text) > 1200 else text) + "\n")
                out.configure(state="disabled")
                out.see("end")
            root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def do_web_eve() -> None:
        set_status("Loading web Eve on HERE…")
        here = CONTROL / "here_station.py"

        def work() -> None:
            try:
                p = subprocess.run(
                    [sys.executable, str(here), "web-eve"],
                    capture_output=True,
                    text=True,
                    timeout=25,
                    check=False,
                )
                msg = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
                tail = "\n".join(msg[-8:]) if msg else "web-eve done"
            except Exception as e:
                tail = str(e)

            def done() -> None:
                set_status("Web Eve · HERE")
                out.configure(state="normal")
                out.insert("end", "\n--- web eve ---\n" + tail + "\n")
                out.configure(state="disabled")
                out.see("end")

            root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def do_smoke() -> None:
        set_status("Smoke…")

        def work() -> None:
            text = run_direct(["smoke"])

            def done() -> None:
                out.configure(state="normal")
                out.insert("end", "\n--- smoke ---\n" + (text[-1500:] if len(text) > 1500 else text) + "\n")
                out.configure(state="disabled")
                out.see("end")
                set_status("Smoke done")

            root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    style = {
        "bg": "#243049",
        "fg": "#eef2ff",
        "activebackground": "#2f3f5e",
        "activeforeground": "#fff",
        "relief": "flat",
        "padx": 8,
        "pady": 4,
        "font": ("Segoe UI", 8, "bold"),
    }
    for text, cmd, accent in (
        ("Reload all", do_reload, "#3dd68c"),
        ("Access granted", do_access_granted, "#6ea8ff"),
        ("Web Eve", do_web_eve, "#f5a524"),
        ("Smoke", do_smoke, "#8b7cff"),
        ("Close", root.destroy, "#ff6b7a"),
    ):
        b = tk.Button(btns, text=text, command=cmd, **style)
        b.configure(fg=accent)
        b.pack(side="left", padx=3)

    render(data)
    root.mainloop()
    log_stack("close")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv and argv[0] in ("--cli", "cli", "list"):
        data = load_all_parameters(do_write="--write" in argv or "write" in argv)
        print(f"=== ACCESS PANEL (cli) count={data['count']} ===")
        for g in data["groups"]:
            print(f"\n## {g}")
            for p in data["by_group"][g]:
                print(f"  {p['key']:28} = {fmt_val(p['value'])}")
        if data.get("written"):
            print("\nwrote:")
            for p in data["written"]:
                print(f"  {p}")
        return 0
    if argv and argv[0] in ("--refresh", "refresh"):
        # force write then open
        load_all_parameters(do_write=True)
    return open_panel()


if __name__ == "__main__":
    raise SystemExit(main())
