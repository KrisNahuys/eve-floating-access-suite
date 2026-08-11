#!/usr/bin/env python3
"""
ACCESS PANEL — top-right floating · always on top · load all parameters
              + quick access tools list (run from panel)

Architect01 · free-run · Eve.AddF.Architect

  python access_panel.py              # open panel (loads all params + tools)
  python access_panel.py --refresh    # re-export incorporate list then open
  python access_panel.py --cli        # print params only (no GUI)
  python access_panel.py --cli tools  # print quick access tools list
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

CONTROL = Path(__file__).resolve().parent
# Full house: .../GrokWorkspace/projects/eden-link/control
# Portable suite pack: .../eve-floating-access-suite/control
_EDEN_CAND = CONTROL.parent
_WS_CAND = CONTROL.parents[2] if len(CONTROL.parents) >= 3 else _EDEN_CAND
if (_WS_CAND / "continuity").exists():
    WS = _WS_CAND
    EDEN = _EDEN_CAND
else:
    # public floating suite root = parent of control/
    WS = _EDEN_CAND
    EDEN = _EDEN_CAND
DIRECT = CONTROL / "direct_control.py"
LOGGER = WS / "continuity" / "tools" / "stack_logger.py"
STATE = CONTROL / "access_panel_state.json"
LIST_MOD = CONTROL / "list_parameters.py"

# import gather + quick tools from siblings
sys.path.insert(0, str(CONTROL))
try:
    from list_parameters import gather, incorporate  # type: ignore
except Exception:
    gather = None  # type: ignore
    incorporate = None  # type: ignore
try:
    from quick_access_tools import as_records, format_list, by_category, run_tool  # type: ignore
except Exception:
    as_records = None  # type: ignore
    format_list = None  # type: ignore
    by_category = None  # type: ignore
    run_tool = None  # type: ignore


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

    # quick access tools shortlist → parameters + panel payload
    tools = as_records() if as_records is not None else []
    add("tools", "quick_access_count", len(tools), "quick_access_tools")
    add("tools", "quick_access_ids", [t["id"] for t in tools], "quick_access_tools")
    if by_category is not None:
        cats = by_category()
        add("tools", "quick_access_categories", list(cats.keys()), "quick_access_tools")

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
        "quick_access_tools": tools,
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

    # top-right geometry (taller for tools list)
    w, h = 460, 720
    margin = 16
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = max(margin, sw - w - margin)
    y = margin + 8
    # keep below typical taskbar if screen is short
    if y + h > sh - 40:
        h = max(420, sh - y - 48)
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
        text="top-right · floating · tools",
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

    # --- quick access tools list (selectable + Run) ---
    tools_frame = tk.Frame(main, bg="#0b1020")
    tools_frame.pack(fill="x", padx=8, pady=(0, 4))
    tk.Label(
        tools_frame,
        text="QUICK ACCESS TOOLS",
        fg="#f5a524",
        bg="#0b1020",
        font=("Segoe UI", 9, "bold"),
        anchor="w",
    ).pack(fill="x")

    tools_row = tk.Frame(tools_frame, bg="#0b1020")
    tools_row.pack(fill="x", pady=(2, 0))
    tools_list = tk.Listbox(
        tools_row,
        height=7,
        bg="#141b2d",
        fg="#eef2ff",
        selectbackground="#2f3f5e",
        selectforeground="#fff",
        font=("Consolas", 8),
        relief="flat",
        highlightthickness=0,
        activestyle="none",
        exportselection=False,
    )
    tools_scroll = tk.Scrollbar(tools_row, orient="vertical", command=tools_list.yview)
    tools_list.configure(yscrollcommand=tools_scroll.set)
    tools_list.pack(side="left", fill="both", expand=True)
    tools_scroll.pack(side="right", fill="y")

    tool_btns = tk.Frame(tools_frame, bg="#0b1020")
    tool_btns.pack(fill="x", pady=(4, 2))

    # keep id order matching listbox lines
    tool_records: list[dict] = []

    def fill_tools(d: dict | None = None) -> None:
        nonlocal tool_records
        tool_records = list((d or {}).get("quick_access_tools") or [])
        if not tool_records and as_records is not None:
            tool_records = as_records()
        tools_list.delete(0, "end")
        for t in tool_records:
            tools_list.insert("end", f"{t['id']:12}  {t['label']}")

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
        tools = d.get("quick_access_tools") or []
        out.insert("end", f"quick tools: {len(tools)}\n")
        if d.get("written"):
            out.insert("end", f"wrote: {len(d['written'])} file(s)\n")
        out.insert("end", "\n")
        # tools first so operator sees them without scrolling past every param group
        if tools:
            out.insert("end", "## quick_access_tools\n")
            for t in tools:
                out.insert("end", f"  {t['id']:12}  {t['label']:24}  ->  {t['cmd']}\n")
            out.insert("end", "\n")
        for g in d.get("groups") or []:
            out.insert("end", f"## {g}\n")
            for p in d.get("by_group", {}).get(g, []):
                out.insert("end", f"  {p['key']:26} = {fmt_val(p['value'])}\n")
            out.insert("end", "\n")
        out.configure(state="disabled")
        meta.config(text=f"n={d.get('count', 0)} · tools={len(tools)}")
        fill_tools(d)
        set_status(f"All parameters + tools · {d.get('count', 0)} · {d.get('ts', '')}")

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

    def do_show_tools() -> None:
        """Jump text pane to tools section / re-list tools."""
        if format_list is not None:
            text = format_list()
        else:
            text = "quick_access_tools unavailable"
        out.configure(state="normal")
        out.insert("end", "\n--- quick access tools ---\n" + text + "\n")
        out.configure(state="disabled")
        out.see("end")
        set_status(f"Tools listed · {len(tool_records)}")

    def do_run_selected_tool(_event=None) -> None:
        sel = tools_list.curselection()
        if not sel:
            set_status("Select a tool first")
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(tool_records):
            set_status("Invalid tool selection")
            return
        t = tool_records[idx]
        args = list(t.get("args") or [])
        label = t.get("label") or t.get("id")
        tid = t.get("id") or ""
        set_status(f"Running {label}…")

        def work() -> None:
            if run_tool is not None and tid:
                code, text = run_tool(tid)
                text = text or f"(exit {code})"
            else:
                text = run_direct(args)

            def done() -> None:
                out.configure(state="normal")
                out.insert("end", f"\n--- tool: {tid} ({' '.join(args)}) ---\n")
                out.insert("end", (text[-1800:] if len(text) > 1800 else text) + "\n")
                out.configure(state="disabled")
                out.see("end")
                set_status(f"Done · {label}")
                log_stack(f"run tool {tid}")

            root.after(0, done)

        threading.Thread(target=work, daemon=True).start()
    tools_list.bind("<Double-Button-1>", do_run_selected_tool)
    tools_list.bind("<Return>", do_run_selected_tool)

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
        ("Tools", do_show_tools, "#f5a524"),
        ("Smoke", do_smoke, "#8b7cff"),
        ("Close", root.destroy, "#ff6b7a"),
    ):
        b = tk.Button(btns, text=text, command=cmd, **style)
        b.configure(fg=accent)
        b.pack(side="left", padx=3)

    for text, cmd, accent in (
        ("Run tool", do_run_selected_tool, "#3dd68c"),
        ("List tools", do_show_tools, "#6ea8ff"),
    ):
        b = tk.Button(tool_btns, text=text, command=cmd, **style)
        b.configure(fg=accent)
        b.pack(side="left", padx=3)

    render(data)
    root.mainloop()
    log_stack("close")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv and argv[0] in ("--cli", "cli", "list"):
        rest = argv[1:]
        if rest and rest[0] in ("tools", "tool", "quick"):
            if format_list is not None:
                print(format_list())
            else:
                print("quick_access_tools unavailable")
            return 0
        data = load_all_parameters(do_write="--write" in argv or "write" in argv)
        print(f"=== ACCESS PANEL (cli) count={data['count']} ===")
        tools = data.get("quick_access_tools") or []
        if tools:
            print(f"\n## quick_access_tools ({len(tools)})")
            for t in tools:
                print(f"  {t['id']:14}  {t['label']:24}  ->  {t['cmd']}")
        for g in data["groups"]:
            print(f"\n## {g}")
            for p in data["by_group"][g]:
                print(f"  {p['key']:28} = {fmt_val(p['value'])}")
        if data.get("written"):
            print("\nwrote:")
            for p in data["written"]:
                print(f"  {p}")
        return 0
    if argv and argv[0] in ("tools", "tool", "quick"):
        if format_list is not None:
            print(format_list())
        else:
            print("quick_access_tools unavailable")
        return 0
    if argv and argv[0] in ("--refresh", "refresh"):
        # force write then open
        load_all_parameters(do_write=True)
    return open_panel()


if __name__ == "__main__":
    raise SystemExit(main())
