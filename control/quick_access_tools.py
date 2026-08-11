#!/usr/bin/env python3
"""
QUICK ACCESS TOOLS — operator shortlist for access board + access panel

Architect01 · free-run · Eve.AddF.Architect

Single source of truth for tools shown under:
  python direct_control.py access
  python direct_control.py access tools
  python access_panel.py  (GUI + --cli tools)

CLI:
  python quick_access_tools.py           # human list
  python quick_access_tools.py json      # JSON
  python quick_access_tools.py ids       # tool ids only
  python quick_access_tools.py run <id>  # run a tool
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTROL = Path(__file__).resolve().parent
DIRECT = CONTROL / "direct_control.py"

# (id, label, direct_control args, category)
# High-use operator + house suite tools.
QUICK_ACCESS_TOOLS: list[tuple[str, str, list[str], str]] = [
    # grant / board
    ("granted", "Access granted", ["granted"], "grant"),
    ("yes-baby", "Yes baby (granted)", ["yes-baby"], "grant"),
    ("access-x", "Access X all", ["access-x"], "grant"),
    ("remote-grant", "Remote grant all", ["remote-grant"], "grant"),
    ("params", "List parameters", ["params"], "board"),
    ("panel", "Access panel float", ["panel"], "board"),
    ("point", "Access point map", ["point"], "board"),
    ("tools", "Tools list only", ["access", "tools"], "board"),
    # stack
    ("hub", "Hub status", ["hub", "status"], "stack"),
    ("eden", "Eden status", ["eden", "status"], "stack"),
    ("sw", "Shadow Wolf status", ["sw", "status"], "stack"),
    ("exe", "Exe status", ["exe", "status"], "stack"),
    ("seat", "Seat 0110", ["seat", "0110"], "stack"),
    ("wire", "Wire all", ["wire"], "stack"),
    ("code-all", "Code all (quick)", ["code-all", "--quick"], "stack"),
    # remote / here
    ("here", "HERE station", ["here"], "remote"),
    ("phone", "Phone status", ["phone", "status"], "remote"),
    ("phone-int", "Phone integral", ["phone", "integral"], "remote"),
    ("remote", "Remote apps list", ["remote"], "remote"),
    # house suite (eyes / shade / home / eufy / float)
    ("eyes", "Eyes status", ["eyes", "status"], "house"),
    ("eyes-start", "Eyes start", ["eyes", "start"], "house"),
    ("eyes-once", "Eyes once (frame)", ["eyes", "once"], "house"),
    ("shade", "Check shade open", ["shade", "open"], "house"),
    ("home", "Home status open", ["home", "open"], "house"),
    ("eufy", "Eufy access status", ["eufy", "status"], "house"),
    ("eufy-open", "Eufy portal open", ["eufy", "open"], "house"),
    ("comms", "Comms float", ["comms"], "house"),
    ("speak", "Speak house online", ["speak", "House online"], "house"),
    # media
    ("camera", "Camera open", ["camera"], "media"),
    ("snap", "Camera snap", ["snap"], "media"),
    ("media", "Media sequence", ["media"], "media"),
    ("editor", "Local editor", ["editor"], "media"),
    ("hot", "Hot editor", ["hot"], "media"),
    # security / a11y
    ("curtain", "Security curtain", ["curtain", "run"], "security"),
    ("a11y", "Accessibility tools", ["a11y"], "security"),
    ("viewers", "Viewer policy", ["viewers"], "security"),
    # life / test / gate
    ("life", "My@Life", ["life"], "life"),
    ("wedding", "Wedding", ["wedding"], "life"),
    ("celebrate", "Celebrate party", ["celebrate"], "life"),
    ("smoke", "Smoke test", ["smoke"], "test"),
    ("gate", "Gate 0444 list", ["gate"], "gate"),
    ("realms", "Realms access", ["realms"], "gate"),
]

# When direct_control.py is missing (public suite pack), run these scripts instead.
FALLBACK_SCRIPTS: dict[str, list[str]] = {
    "params": ["list_parameters.py", "list"],
    "panel": ["access_panel.py"],
    "tools": ["quick_access_tools.py"],
    "eyes": ["eyes.py", "status"],
    "eyes-start": ["eyes.py", "start"],
    "eyes-once": ["eyes.py", "once"],
    "shade": ["check_shade.py", "open"],
    "home": ["home_status.py", "open"],
    "eufy": ["eufy_access.py", "status"],
    "eufy-open": ["eufy_access.py", "open"],
    "comms": ["comms_float.py"],
    "speak": ["speak_house.py", "House online"],
}

CATEGORIES = (
    "grant",
    "board",
    "stack",
    "remote",
    "house",
    "media",
    "security",
    "life",
    "test",
    "gate",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def as_records() -> list[dict]:
    rows = []
    for tid, label, args, cat in QUICK_ACCESS_TOOLS:
        rec = {
            "id": tid,
            "label": label,
            "args": list(args),
            "cmd": " ".join(args),
            "category": cat,
        }
        if tid in FALLBACK_SCRIPTS:
            rec["fallback"] = FALLBACK_SCRIPTS[tid]
        rows.append(rec)
    return rows


def by_category() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in as_records():
        out.setdefault(r["category"], []).append(r)
    return out


def get(tool_id: str) -> dict | None:
    key = tool_id.strip().lower().replace("_", "-")
    for r in as_records():
        if r["id"] == key:
            return r
    return None


def format_list(prefix: str = "  ") -> str:
    lines = [
        "=== QUICK ACCESS TOOLS ===",
        f"count: {len(QUICK_ACCESS_TOOLS)} | owner: Architect01 | free-run: ON",
        f"ts: {utc_now()}",
        "",
    ]
    cats = by_category()
    for cat in CATEGORIES:
        items = cats.get(cat) or []
        if not items:
            continue
        lines.append(f"## {cat}")
        for r in items:
            lines.append(f"{prefix}{r['id']:14}  {r['label']:24}  ->  {r['cmd']}")
        lines.append("")
    lines.append("run:  python direct_control.py <cmd>")
    lines.append("also: python direct_control.py access tools")
    lines.append("also: python quick_access_tools.py run <id>")
    return "\n".join(lines)


def run_tool(tool_id: str, timeout: int = 90) -> tuple[int, str]:
    """Run a quick tool. Prefer direct_control; fall back to local suite scripts."""
    rec = get(tool_id)
    if not rec:
        return 1, f"unknown tool: {tool_id}"

    if DIRECT.exists():
        cmd = [sys.executable, str(DIRECT), *rec["args"]]
    else:
        fb = FALLBACK_SCRIPTS.get(rec["id"])
        if not fb:
            return 1, f"no direct_control and no fallback for {rec['id']}"
        script = CONTROL / fb[0]
        if not script.exists():
            return 1, f"fallback missing: {script}"
        cmd = [sys.executable, str(script), *fb[1:]]

    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        return p.returncode, out
    except Exception as e:
        return 1, str(e)


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    verb = (argv[0] if argv else "list").lower()
    if verb in ("json", "--json"):
        print(json.dumps({
            "title": "Quick Access Tools",
            "ts": utc_now(),
            "owner": "Architect01",
            "count": len(QUICK_ACCESS_TOOLS),
            "tools": as_records(),
            "by_category": by_category(),
        }, indent=2, ensure_ascii=False))
        return 0
    if verb in ("ids", "id"):
        for r in as_records():
            print(r["id"])
        return 0
    if verb in ("get",) and len(argv) > 1:
        r = get(argv[1])
        if not r:
            print(f"unknown tool: {argv[1]}")
            return 1
        print(json.dumps(r, indent=2))
        return 0
    if verb in ("run", "exec") and len(argv) > 1:
        code, out = run_tool(argv[1])
        if out:
            print(out)
        return code
    print(format_list())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
