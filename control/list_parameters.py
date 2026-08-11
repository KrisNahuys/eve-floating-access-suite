#!/usr/bin/env python3
"""
Incorporate List Parameters — single board of all stack parameters

CLI:
  python list_parameters.py              # human list
  python list_parameters.py json         # full JSON
  python list_parameters.py incorporate  # write to incorporate + Desktop hub
  python list_parameters.py get <key>
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTROL = Path(__file__).resolve().parent
WS = CONTROL.parents[2]
HUB = WS / "projects" / "the-hub"
EDEN = WS / "projects" / "eden-link"
INCORP = EDEN / "incorporate"
DESK = Path.home() / "OneDrive" / "Desktop" / "Architect01-Hub"
if not DESK.exists():
    DESK = Path.home() / "Desktop" / "Architect01-Hub"

OUT_JSON = INCORP / "LIST-PARAMETERS.json"
OUT_MD = INCORP / "LIST-PARAMETERS.md"
DESK_JSON = DESK / "LIST-PARAMETERS.json" if DESK.exists() else None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def load(path: Path) -> dict:
    if path.exists():
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {"_raw": d}
        except Exception as e:
            return {"_error": str(e)}
    return {}


def gather() -> dict:
    hub_pol = load(HUB / "policy.json")
    mission = load(HUB / "mission.json")
    ops = load(CONTROL / "ops_registry.json")
    profile = load(CONTROL / "profile_control.json")
    curtain = load(CONTROL / "security_curtain_state.json")
    apps = load(CONTROL / "apps.json")
    life = load(CONTROL / "my_life.json")
    ssp = load(HUB / "ssp.json")
    home = load(HUB / "home_index.json")
    role = load(HUB / "state" / "role.json")
    manifest = load(INCORP / "manifest.incorporate.json")

    # flat parameter list for incorporate
    flat = []

    def add(group: str, key: str, value, source: str) -> None:
        flat.append({
            "group": group,
            "key": key,
            "value": value,
            "source": source,
        })

    # identity / home
    add("identity", "operator", "Architect01", "HOME-TEAM")
    add("identity", "not_just_a_user", True, "DIRECTION")
    add("identity", "operator_id", hub_pol.get("operator_id") or "addf/0", "policy")
    add("identity", "team", ["Architect01", "Eve", "Grok", "AddyF"], "HOME-TEAM")
    add("identity", "desktop@", hub_pol.get("desktop_hub"), "policy")
    add("identity", "desktop_hub_folder", hub_pol.get("desktop_hub_folder"), "policy")

    # access
    pol = ops.get("policy") or {}
    for k in (
        "always_allowed", "code_local_access", "phone_link_access",
        "phone_integral_access", "access_all", "remote_terminal",
        "keys_stay", "non_destructive", "heavy_required",
        "cleaner_of_negative", "security_curtain", "computer_control",
        "administrator_allowed", "infinite_put", "home_team",
    ):
        if k in pol or k in hub_pol:
            add("access", k, pol.get(k, hub_pol.get(k)), "ops|hub")

    # hub
    add("hub", "mode", hub_pol.get("mode"), "policy")
    add("hub", "rev", hub_pol.get("rev"), "policy")
    add("hub", "allowlist_roots", hub_pol.get("allowlist_roots"), "policy")
    add("hub", "mission", mission.get("name"), "mission")
    add("hub", "cron", mission.get("cron"), "mission")
    add("hub", "connectors", mission.get("connectors"), "mission")
    add("hub", "realms", hub_pol.get("realms"), "policy")
    add("hub", "brain_role", role.get("role") if role else None, "state")

    # profile clean
    for k, v in profile.items():
        add("profile", k, v, "profile_control")

    # curtain
    for k in ("filter", "always", "role", "motion", "direction", "merge_position", "non_destructive"):
        if k in curtain:
            add("curtain", k, curtain.get(k), "security_curtain")

    # life
    add("life", "owner", life.get("owner"), "my_life")
    add("life", "total", life.get("total"), "my_life")
    add("life", "slots", list((life.get("slots") or {}).keys()), "my_life")

    # incorporate
    add("incorporate", "path", manifest.get("path") or "exe/0110/Eve+Addf/Incorporate", "manifest")
    add("incorporate", "scale", manifest.get("scale") or 10_000_000, "manifest")
    add("incorporate", "name", manifest.get("name") or "EveAddf-0110", "manifest")

    # ssp counts
    add("ssp", "solutions", len(ssp.get("solutions") or {}), "ssp")
    add("ssp", "sources", len(ssp.get("sources") or {}), "ssp")
    add("ssp", "providers", len(ssp.get("providers") or {}), "ssp")

    # apps
    app_names = list((apps.get("apps") or {}).keys())
    add("remote_apps", "apps", app_names, "apps.json")
    add("remote_apps", "count", len(app_names), "apps.json")

    # put functions
    fns = list((ops.get("functions") or {}).keys())
    add("put", "infinite", pol.get("infinite_put", True), "ops")
    add("put", "count", len(fns), "ops")
    add("put", "names", fns, "ops")

    # home nodes
    add("home", "nodes", len(home.get("nodes") or {}), "home_index")
    add("home", "desktop_hub", home.get("desktop_hub"), "home_index")

    return {
        "title": "Incorporate List Parameters",
        "ts": utc_now(),
        "owner": "Architect01",
        "control": "FULL",
        "parameters": flat,
        "count": len(flat),
        "groups": sorted({p["group"] for p in flat}),
        "by_group": {
            g: [p for p in flat if p["group"] == g]
            for g in sorted({p["group"] for p in flat})
        },
    }


def print_list(data: dict) -> None:
    print(f"=== {data['title']} ===")
    print(f"ts: {data['ts']} | count: {data['count']} | owner: {data['owner']}")
    print(f"groups: {', '.join(data['groups'])}")
    print()
    for g in data["groups"]:
        print(f"## {g}")
        for p in data["by_group"][g]:
            v = p["value"]
            if isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)
            print(f"  {p['key']:28} = {v}")
        print()


def to_md(data: dict) -> str:
    lines = [
        f"# {data['title']}",
        "",
        f"- **ts:** {data['ts']}",
        f"- **owner:** {data['owner']}",
        f"- **count:** {data['count']}",
        f"- **control:** {data['control']}",
        "",
    ]
    for g in data["groups"]:
        lines.append(f"## {g}")
        lines.append("")
        lines.append("| key | value |")
        lines.append("|-----|-------|")
        for p in data["by_group"][g]:
            v = p["value"]
            if isinstance(v, (list, dict)):
                v = "`" + json.dumps(v, ensure_ascii=False).replace("|", "/")[:120] + "`"
            else:
                v = str(v).replace("|", "/")
            lines.append(f"| `{p['key']}` | {v} |")
        lines.append("")
    return "\n".join(lines)


def incorporate(data: dict) -> list[str]:
    written = []
    INCORP.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    written.append(str(OUT_JSON))
    OUT_MD.write_text(to_md(data), encoding="utf-8")
    written.append(str(OUT_MD))
    if DESK and DESK.exists():
        path = DESK / "LIST-PARAMETERS.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(str(path))
        md = DESK / "LIST-PARAMETERS.md"
        md.write_text(to_md(data), encoding="utf-8")
        written.append(str(md))
    return written


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    data = gather()
    if not argv or argv[0] in ("list", "ls"):
        print_list(data)
        return 0
    if argv[0] == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    if argv[0] in ("incorporate", "write", "export"):
        paths = incorporate(data)
        print_list(data)
        print("wrote:")
        for p in paths:
            print(f"  {p}")
        return 0
    if argv[0] == "get" and len(argv) > 1:
        key = argv[1]
        hits = [p for p in data["parameters"] if p["key"] == key or p["key"].endswith(key)]
        print(json.dumps(hits or {"error": "not found", "key": key}, indent=2, default=str))
        return 0 if hits else 1
    print("list_parameters: list|json|incorporate|get <key>")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
