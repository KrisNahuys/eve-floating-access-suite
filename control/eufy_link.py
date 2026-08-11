#!/usr/bin/env python3
"""
Eufy / local camera link — Architect01 owned gear.

Paths we use (all *your* hardware / *your* account):
  1) UVC / DirectShow  — any USB or integrated camera Windows exposes
  2) Eufy cloud portal — sign-in as addyfixit02@gmail.com (password never stored)
  3) RTSP / HTTP URL   — if you enable local stream on HomeBase / cam (you paste URL)

No cloud password stored. No third-party accounts. Local free-run.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parent
DEVICES = CONTROL / "eufy_devices.json"
STATE = CONTROL / "eufy_link_state.json"
STAGE = ROOT / "media" / "stage" / "photo"
PORTAL = "https://mysecurity.eufylife.com"
ACCOUNT = "addyfixit02@gmail.com"

# Common local camera ports (owned LAN probe — connect only, no exploit)
PROBE_PORTS = (554, 8554, 80, 443, 8000, 8080, 8899)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def load_devices() -> dict:
    if DEVICES.exists():
        return json.loads(DEVICES.read_text(encoding="utf-8"))
    return {
        "access": "GRANTED",
        "account": ACCOUNT,
        "portal": PORTAL,
        "devices": [],
    }


def save_devices(data: dict) -> None:
    data["ts"] = utc_now()
    DEVICES.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def save_state(payload: dict) -> None:
    payload["ts"] = utc_now()
    STATE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def discover_uvc(max_index: int = 6) -> list[dict]:
    """List UVC/DirectShow capture devices via OpenCV."""
    try:
        import cv2
    except ImportError as e:
        print("opencv missing:", e)
        return []

    found: list[dict] = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            continue
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        ret, frame = cap.read()
        ok = bool(ret and frame is not None)
        cap.release()
        if not ok:
            continue
        # Heuristic names — Windows rarely gives OpenCV a friendly name by index
        label = "Integrated Camera" if i == 0 else f"UVC index {i}"
        if i == 1 and h >= 720:
            label = "UVC / secondary (720p+)"
        found.append(
            {
                "id": f"uvc-{i}",
                "name": label,
                "type": "uvc",
                "backend": "dshow",
                "index": i,
                "width": w,
                "height": h,
                "status": "live",
                "owner": "Architect01",
                "media_stage": "media/stage/photo",
                "zone": "pc_local",
            }
        )
    return found


def register_uvc(devices: list[dict] | None = None) -> dict:
    data = load_devices()
    uvc = devices if devices is not None else discover_uvc()
    # Keep non-uvc entries (cloud slots / manual RTSP)
    kept = [d for d in data.get("devices") or [] if d.get("type") not in ("uvc", "camera") or d.get("source") == "manual"]
    # Prefer replacing placeholder TBD slots + old uvc
    kept = [d for d in kept if not str(d.get("id", "")).startswith("slot-") and d.get("status") != "pending_sign_in"]
    for d in uvc:
        d["source"] = "local_discover"
        d["linked"] = True
        kept.append(d)
    # Ensure cloud placeholders remain if no Eufy cloud devices yet
    if not any(d.get("type") == "eufy_cloud" for d in kept):
        kept.append(
            {
                "id": "eufy-cloud-pending",
                "name": "Eufy Security (cloud — sign in)",
                "type": "eufy_cloud",
                "zone": "home",
                "status": "pending_sign_in",
                "account": ACCOUNT,
                "portal": PORTAL,
                "note": "Pair cams in Eufy app, then run: eufy_link.py map",
            }
        )
    data["devices"] = kept
    data["access"] = "GRANTED"
    data["account"] = ACCOUNT
    data["portal"] = PORTAL
    data["local_uvc_count"] = len(uvc)
    data["link"] = "live" if uvc else "no_uvc"
    data["note"] = (
        "UVC devices are local Windows cameras. Wireless Eufy cams need app/cloud "
        "or RTSP URL you enable — paste with: eufy_link.py rtsp <url> <name>"
    )
    save_devices(data)
    save_state({"event": "register_uvc", "count": len(uvc), "devices": uvc})
    return data


def snap(index: int = 0, tag: str = "eufy") -> Path | None:
    try:
        import cv2
    except ImportError as e:
        print("opencv missing:", e)
        return None

    STAGE.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"cannot open camera index {index}")
        return None
    # warm-up frames (auto-exposure)
    frame = None
    for _ in range(8):
        ret, frame = cap.read()
        if not ret:
            frame = None
    cap.release()
    if frame is None:
        print("no frame")
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = STAGE / f"{tag}_uvc{index}_{stamp}.jpg"
    ok = cv2.imwrite(str(out), frame)
    if not ok or not out.exists():
        print("write failed")
        return None
    save_state(
        {
            "event": "snap",
            "index": index,
            "path": str(out),
            "bytes": out.stat().st_size,
        }
    )
    print(f"snap ok: {out}")
    print(f"bytes:   {out.stat().st_size}")
    return out


def open_portal() -> str:
    webbrowser.open(PORTAL)
    save_state({"event": "portal_open", "url": PORTAL, "account": ACCOUNT})
    print(f"opened:  {PORTAL}")
    print(f"account: {ACCOUNT}  (sign in — password stays with you)")
    return PORTAL


def add_rtsp(url: str, name: str = "Eufy RTSP") -> dict:
    data = load_devices()
    dev = {
        "id": f"rtsp-{abs(hash(url)) % 10_000_000}",
        "name": name,
        "type": "rtsp",
        "url": url,
        "status": "registered",
        "source": "manual",
        "owner": "Architect01",
        "media_stage": "media/stage/photo",
        "zone": "home",
        "linked": True,
    }
    devices = [d for d in data.get("devices") or [] if d.get("url") != url]
    devices.append(dev)
    data["devices"] = devices
    save_devices(data)
    save_state({"event": "rtsp_add", "url": url, "name": name})
    print(f"registered RTSP: {name}")
    print(f"url: {url}")
    return data


def probe_host(host: str, ports: tuple[int, ...] = PROBE_PORTS, timeout: float = 0.35) -> list[int]:
    open_ports: list[int] = []
    for port in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            if s.connect_ex((host, port)) == 0:
                open_ports.append(port)
        except OSError:
            pass
        finally:
            s.close()
    return open_ports


def probe_lan(base: str = "192.168.0", start: int = 1, end: int = 40) -> list[dict]:
    """Light connect-scan on own LAN for hosts with camera-ish ports open."""
    hits: list[dict] = []
    print(f"probing {base}.{start}-{end} ports {PROBE_PORTS} (owned LAN, connect only)…")
    for i in range(start, end + 1):
        host = f"{base}.{i}"
        ports = probe_host(host)
        if ports:
            hits.append({"host": host, "ports": ports})
            print(f"  {host} open={ports}")
    save_state({"event": "lan_probe", "base": base, "hits": hits})
    if not hits:
        print("no camera-ish ports in range (HomeBase offline, different subnet, or RTSP disabled)")
    return hits


def status() -> dict:
    data = load_devices()
    uvc = discover_uvc()
    out = {
        "access": data.get("access"),
        "account": data.get("account"),
        "portal": data.get("portal"),
        "registered_devices": data.get("devices"),
        "uvc_live_now": uvc,
        "stage": str(STAGE),
        "state_file": str(STATE),
    }
    print(json.dumps(out, indent=2))
    return out


def preview(index: int = 0, seconds: float = 3.0) -> int:
    """Prove link: try GUI window; if headless OpenCV, burst-snap frames instead."""
    try:
        import cv2
        import time
    except ImportError as e:
        print("opencv missing:", e)
        return 1
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"cannot open index {index}")
        return 1

    # Prefer GUI when highgui is built; many pip wheels are headless.
    gui_ok = True
    win = f"Architect01 cam link · uvc-{index}"
    try:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    except cv2.error:
        gui_ok = False

    t0 = time.time()
    frames = 0
    last = None
    STAGE.mkdir(parents=True, exist_ok=True)
    burst_dir = STAGE / f"preview_uvc{index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if not gui_ok:
        burst_dir.mkdir(parents=True, exist_ok=True)

    while time.time() - t0 < seconds:
        ret, frame = cap.read()
        if not ret:
            break
        frames += 1
        last = frame
        if gui_ok:
            cv2.putText(
                frame,
                f"OWNED LINK uvc-{index}  {frames}",
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 120),
                2,
            )
            try:
                cv2.imshow(win, frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
            except cv2.error:
                gui_ok = False
                burst_dir.mkdir(parents=True, exist_ok=True)
        elif frames % 5 == 0:
            cv2.imwrite(str(burst_dir / f"f{frames:04d}.jpg"), frame)

    cap.release()
    if gui_ok:
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass
    # Always leave a final still
    if last is not None:
        still = STAGE / f"preview_still_uvc{index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(str(still), last)
        print(f"still:   {still}")
    if not gui_ok:
        print(f"preview: headless burst → {burst_dir} (pip opencv has no GUI)")
    print(f"preview done frames={frames} index={index} gui={gui_ok}")
    save_state({"event": "preview", "index": index, "frames": frames, "gui": gui_ok})
    return 0 if frames else 1


def print_help() -> None:
    print(
        """usage: eufy_link.py <cmd>

  status              registry + live UVC
  discover | list     scan UVC indexes
  register | link     write UVC devices into eufy_devices.json
  snap [index]        capture frame → media/stage/photo
  preview [index] [s] live window (default 3s)
  open | portal       Eufy Security web (sign-in yourself)
  rtsp <url> [name]   register your local RTSP URL
  probe [base]        light LAN port probe (default 192.168.0)
  map                 re-register + status (after app sign-in)

Your gear. Password never stored here.
"""
    )


def main(argv: list[str]) -> int:
    cmd = (argv[0] if argv else "status").lower()

    if cmd in ("help", "-h", "--help"):
        print_help()
        return 0

    if cmd in ("status", "show"):
        status()
        return 0

    if cmd in ("discover", "list", "ls"):
        uvc = discover_uvc()
        print(f"=== UVC LIVE ({len(uvc)}) ===")
        for d in uvc:
            print(f"  [{d['index']}] {d['id']:8} {d['name']:28} {d['width']}x{d['height']}")
        if not uvc:
            print("  (none — plug USB cam or enable integrated camera)")
        save_state({"event": "discover", "uvc": uvc})
        return 0

    if cmd in ("register", "link", "connect"):
        data = register_uvc()
        print("=== LINKED ===")
        print(f"uvc count: {data.get('local_uvc_count')}")
        for d in data.get("devices") or []:
            print(f"  {d.get('id'):20} {d.get('type'):12} {d.get('name')} [{d.get('status')}]")
        print(f"registry: {DEVICES}")
        return 0

    if cmd in ("snap", "shot", "capture"):
        idx = int(argv[1]) if len(argv) > 1 else 0
        path = snap(idx)
        return 0 if path else 1

    if cmd in ("preview", "live", "view"):
        idx = int(argv[1]) if len(argv) > 1 else 0
        secs = float(argv[2]) if len(argv) > 2 else 3.0
        return preview(idx, secs)

    if cmd in ("open", "portal", "login", "app"):
        open_portal()
        return 0

    if cmd == "rtsp":
        if len(argv) < 2:
            print("usage: eufy_link.py rtsp <url> [name]")
            return 1
        url = argv[1]
        name = " ".join(argv[2:]) if len(argv) > 2 else "Eufy RTSP"
        add_rtsp(url, name)
        return 0

    if cmd in ("probe", "scan", "lan"):
        base = argv[1] if len(argv) > 1 else "192.168.0"
        probe_lan(base)
        return 0

    if cmd == "map":
        register_uvc()
        open_portal()
        status()
        print()
        print("After Eufy app shows your cams: note model/name and we fill cloud slots.")
        print("If HomeBase RTSP is on: eufy_link.py rtsp rtsp://USER:PASS@IP/live0")
        return 0

    print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
