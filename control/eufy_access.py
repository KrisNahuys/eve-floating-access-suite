#!/usr/bin/env python3
"""Eufy access — Architect01 grant for account + portal open."""

from __future__ import annotations

import json
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

CONTROL = Path(__file__).resolve().parent
STATE = CONTROL / "eufy_access_state.json"
OPS = CONTROL / "ops_registry.json"
LIFE = CONTROL / "my_life.json"
ACCESS_STATE = CONTROL / "access_granted_state.json"

# Official cloud portals (login with granted account)
PORTAL_SECURITY = "https://mysecurity.eufylife.com"
PORTAL_ACCOUNT = "https://myaccount.eufylife.com"
PORTAL_HOME = "https://www.eufy.com"

DEFAULT_ACCOUNT = "addyfixit02@gmail.com"
LIFE_TIERS = (100, 200, 500)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def load_json(path: Path, default: dict | None = None) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default if default is not None else {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ensure_life_slots() -> dict:
    """Ensure My@Life$100, $200, $500 exist; recompute total."""
    data = load_json(
        LIFE,
        {
            "owner": "Eve.AddF.Architect",
            "operator": "addf/0",
            "handle": "Architect01",
            "slots": {},
            "access": {"execute": True, "all_permission_alive": True},
        },
    )
    slots = data.setdefault("slots", {})
    for amount in LIFE_TIERS:
        key = f"My@Life${amount}"
        if key not in slots:
            slots[key] = {
                "id": key,
                "amount": amount,
                "label": f"Life {amount}",
                "owner": "Eve.AddF.Architect",
            }
        else:
            slots[key]["amount"] = amount
            slots[key].setdefault("owner", "Eve.AddF.Architect")
            slots[key].setdefault("label", f"Life {amount}")
            slots[key]["id"] = key
    # Tag eufy budget options on these tiers
    for amount in LIFE_TIERS:
        key = f"My@Life${amount}"
        slots[key]["eufy_option"] = True
        slots[key]["account"] = DEFAULT_ACCOUNT
    data["total"] = sum(int(v.get("amount") or 0) for v in slots.values())
    data.setdefault("access", {})["execute"] = True
    data["access"]["eufy"] = "granted"
    data["eufy"] = {
        "access": "GRANTED",
        "account": DEFAULT_ACCOUNT,
        "life_options": [f"My@Life${a}" for a in LIFE_TIERS],
    }
    save_json(LIFE, data)
    return data


def grant(account: str = DEFAULT_ACCOUNT) -> dict:
    ts = utc_now()
    life = ensure_life_slots()
    state = {
        "access": "GRANTED",
        "owner": "Architect01",
        "account": account,
        "accounts": [account],
        "provider": "eufy",
        "portals": {
            "security": PORTAL_SECURITY,
            "account": PORTAL_ACCOUNT,
            "home": PORTAL_HOME,
        },
        "my_life_options": [f"My@Life${a}" for a in LIFE_TIERS],
        "my_life_total": life.get("total"),
        "layers": {
            "eufy_cloud": "always_allowed",
            "eufy_security": "always_allowed",
            "eufy_account": account,
            "camera_stack": "linked_when_signed_in",
            "local_control": "always_allowed",
        },
        "note": "Stack grant — sign in with account in browser/app; no cloud password stored here",
        "ts": ts,
        "granted_by": "Architect01",
    }
    save_json(STATE, state)

    # ops policy
    if OPS.exists():
        reg = load_json(OPS)
        pol = reg.setdefault("policy", {})
        pol["eufy_access"] = "GRANTED"
        pol["eufy_account"] = account
        pol["eufy_always"] = True
        py = sys.executable
        life_show = CONTROL / "life_show.py"
        eufy_py = CONTROL / "eufy_access.py"
        fns = reg.setdefault("functions", {})
        for amount in LIFE_TIERS:
            key = f"My@Life${amount}"
            fns[key] = {
                "cmd": f'"{py}" "{life_show}" {amount}',
                "ts": ts,
                "by": "eufy_access",
                "always_allowed": True,
            }
        fns["eufy_status"] = {
            "cmd": f'"{py}" "{eufy_py}" status',
            "ts": ts,
            "by": "eufy_access",
            "always_allowed": True,
        }
        fns["eufy_open"] = {
            "cmd": f'"{py}" "{eufy_py}" open',
            "ts": ts,
            "by": "eufy_access",
            "always_allowed": True,
        }
        save_json(OPS, reg)

    # access_granted_state layers
    if ACCESS_STATE.exists():
        ag = load_json(ACCESS_STATE)
        layers = ag.setdefault("layers", {})
        layers["eufy"] = "GRANTED"
        layers["eufy_account"] = account
        ag["eufy"] = {
            "access": "GRANTED",
            "account": account,
            "my_life": [f"My@Life${a}" for a in LIFE_TIERS],
        }
        ag["ts"] = ts
        save_json(ACCESS_STATE, ag)

    return state


def open_portal(which: str = "security") -> str:
    urls = {
        "security": PORTAL_SECURITY,
        "account": PORTAL_ACCOUNT,
        "home": PORTAL_HOME,
        "my": PORTAL_SECURITY,
        "login": PORTAL_SECURITY,
    }
    url = urls.get(which.lower(), PORTAL_SECURITY)
    webbrowser.open(url)
    return url


def status() -> dict:
    if not STATE.exists():
        return {"access": "NOT_GRANTED", "hint": "run: python eufy_access.py grant"}
    return load_json(STATE)


def main(argv: list[str]) -> int:
    cmd = (argv[0] if argv else "grant").lower()
    account = DEFAULT_ACCOUNT
    if len(argv) >= 2 and "@" in argv[1]:
        account = argv[1]

    if cmd in ("grant", "allow", "yes"):
        st = grant(account)
        print("=== EUFY ACCESS GRANTED ===")
        print(f"account:     {st['account']}")
        print(f"access:      {st['access']}")
        print(f"security:    {st['portals']['security']}")
        print(f"My@Life:     {' · '.join(st['my_life_options'])}")
        print(f"life total:  {st['my_life_total']}")
        print(f"ts:          {st['ts']}")
        print()
        print("Sign in with that Gmail on the Eufy portal/app (password stays with you).")
        return 0

    if cmd in ("status", "show"):
        st = status()
        print(json.dumps(st, indent=2))
        return 0

    if cmd in ("open", "portal", "login"):
        which = argv[1] if len(argv) > 1 and "@" not in argv[1] else "security"
        if not STATE.exists():
            grant(account)
        url = open_portal(which)
        print(f"opened: {url}")
        print(f"account: {account}  (sign in)")
        return 0

    if cmd in ("life", "mylife"):
        life = ensure_life_slots()
        print("=== My@Life (eufy options + all) ===")
        for a in LIFE_TIERS:
            k = f"My@Life${a}"
            v = life["slots"].get(k, {})
            print(f"  {k}: amount={v.get('amount')} eufy_option={v.get('eufy_option')}")
        print(f"total all slots: {life.get('total')}")
        return 0

    # Delegate live camera link to eufy_link.py (UVC · snap · RTSP · probe)
    if cmd in (
        "link",
        "connect",
        "discover",
        "snap",
        "preview",
        "probe",
        "rtsp",
        "map",
        "devices",
    ):
        link = CONTROL / "eufy_link.py"
        args = [sys.executable, str(link)]
        if cmd == "devices":
            args.append("status")
        elif cmd == "connect":
            args.append("link")
        else:
            args.append(cmd)
        args.extend(argv[1:])
        import subprocess

        return subprocess.call(args)

    print("usage: eufy_access.py grant|status|open|life|link|discover|snap|preview|probe|rtsp|map [email]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
