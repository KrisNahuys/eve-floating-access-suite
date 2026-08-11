#!/usr/bin/env python3
"""
EUFY OWNED — Architect01 local assault (YOUR gear only).

Not cloud crime. Not someone else's cam.
Maximum owner control on YOUR LAN:

  1) Hunt RTSP hosts (port 554)
  2) Probe stream paths
  3) Register RTSP URL you enable in the app (NAS/RTSP)
  4) Grab a still when ffmpeg/OpenCV can open the URL
  5) Keep UVC laptop cam as always-on fallback

PIN hell is optional. Local stream is the knife.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parent
STAGE = ROOT / "media" / "stage" / "photo"
STATE = CONTROL / "eufy_owned_state.json"
DEVICES = CONTROL / "eufy_devices.json"

COMMON_PATHS = [
    "/",
    "/live",
    "/live0",
    "/live1",
    "/cam/realmonitor?channel=1&subtype=0",
    "/h264_stream",
    "/stream1",
    "/videoMain",
    "/Streaming/Channels/101",
    "/ch0_0.h264",
    "/unicast/c1/s0/live",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def save_state(d: dict) -> None:
    d["ts"] = utc_now()
    STATE.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


def tcp_open(host: str, port: int, timeout: float = 0.3) -> bool:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    except OSError:
        return False
    finally:
        s.close()


def hunt(base: str = "192.168.0", start: int = 1, end: int = 254, port: int = 554) -> list[str]:
    print(f"hunting {base}.{start}-{end} :{port} (owned LAN)…")
    hits: list[str] = []

    def one(i: int) -> str | None:
        h = f"{base}.{i}"
        return h if tcp_open(h, port) else None

    with ThreadPoolExecutor(max_workers=64) as ex:
        futs = [ex.submit(one, i) for i in range(start, end + 1)]
        for f in as_completed(futs):
            h = f.result()
            if h:
                hits.append(h)
                print(f"  RTSP LIVE → {h}:{port}")
    hits.sort(key=lambda x: int(x.rsplit(".", 1)[-1]))
    save_state({"event": "hunt", "hits": hits, "port": port})
    if not hits:
        print("no RTSP listeners — cam may be offline or RTSP not enabled yet")
    return hits


def rtsp_options(host: str, port: int = 554) -> str:
    try:
        s = socket.create_connection((host, port), 1.5)
        s.sendall(
            f"OPTIONS rtsp://{host}/ RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: Architect01-owned\r\n\r\n".encode()
        )
        data = s.recv(2048).decode("utf-8", "replace")
        s.close()
        return data
    except OSError as e:
        return f"error: {e}"


def rtsp_describe(host: str, path: str, user: str = "", password: str = "", port: int = 554) -> str:
    if user:
        auth = f"{user}:{password}@"
    else:
        auth = ""
    url = f"rtsp://{auth}{host}:{port}{path}"
    # bare DESCRIBE without Authorization header first
    req = (
        f"DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\n"
        f"CSeq: 2\r\nAccept: application/sdp\r\nUser-Agent: Architect01-owned\r\n\r\n"
    )
    try:
        s = socket.create_connection((host, port), 1.5)
        s.sendall(req.encode())
        data = s.recv(4096).decode("utf-8", "replace")
        s.close()
        return data.split("\r\n")[0]
    except OSError as e:
        return f"error: {e}"


def probe(host: str) -> dict:
    print(f"=== PROBE {host} ===")
    opt = rtsp_options(host)
    print(opt[:400])
    results = []
    for p in COMMON_PATHS:
        line = rtsp_describe(host, p)
        print(f"  {p:45} {line}")
        results.append({"path": p, "response": line})
    out = {"host": host, "options": opt, "paths": results}
    save_state({"event": "probe", **out})
    return out


def register_rtsp(url: str, name: str = "Owned Eufy RTSP") -> None:
    data = {}
    if DEVICES.exists():
        data = json.loads(DEVICES.read_text(encoding="utf-8"))
    devs = [d for d in data.get("devices") or [] if d.get("url") != url]
    devs.append(
        {
            "id": f"owned-rtsp-{abs(hash(url)) % 10_000_000}",
            "name": name,
            "type": "rtsp",
            "url": url,
            "status": "registered_owned",
            "owner": "Architect01",
            "source": "eufy_owned",
            "linked": True,
            "zone": "home",
        }
    )
    data["devices"] = devs
    data["access"] = "GRANTED"
    data["owned_mode"] = True
    data["ts"] = utc_now()
    DEVICES.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    save_state({"event": "register_rtsp", "url": url, "name": name})
    print(f"registered: {name}")
    print(f"url: {url}")


def snap_rtsp(url: str) -> Path | None:
    STAGE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = STAGE / f"owned_rtsp_{stamp}.jpg"
    # try ffmpeg
    for ffmpeg in ("ffmpeg",):
        try:
            r = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-rtsp_transport",
                    "tcp",
                    "-i",
                    url,
                    "-frames:v",
                    "1",
                    str(out),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if out.exists() and out.stat().st_size > 0:
                print(f"snap ok (ffmpeg): {out}")
                save_state({"event": "snap", "path": str(out), "method": "ffmpeg"})
                return out
            print("ffmpeg:", (r.stderr or "")[-300:])
        except FileNotFoundError:
            print("ffmpeg not installed — trying OpenCV")
        except Exception as e:
            print("ffmpeg err:", e)
    try:
        import cv2

        cap = cv2.VideoCapture(url)
        ok, frame = cap.read()
        cap.release()
        if ok and frame is not None:
            cv2.imwrite(str(out), frame)
            print(f"snap ok (cv2): {out}")
            save_state({"event": "snap", "path": str(out), "method": "cv2"})
            return out
    except Exception as e:
        print("cv2 err:", e)
    print("snap failed — need working RTSP URL (enable NAS/RTSP in app)")
    return None


def playbook() -> None:
    print(
        """
=== OWNED EUFY PLAYBOOK (no web PIN required for stream) ===

Your LAN already spoke RTSP on 192.168.0.248 — server UP, streams not published yet.
Eufy hides the path until YOU enable NAS/RTSP in the app (owner switch).

ON PHONE APP (S22) — skip Safety PIN if stuck:
  1. Open eufy app · your cam (or HomeBase)
  2. Camera Settings → Storage → NAS (RTSP Stream)
     OR HomeBase Settings → Storage → NAS / RTSP
  3. Enable RTSP / NAS stream
  4. Set username + password YOU choose (owner creds)
  5. Copy the RTSP URL the app shows
  6. Run:
       python eufy_owned.py rtsp "rtsp://USER:PASS@IP/...." "Front"
       python eufy_owned.py snap-url "rtsp://USER:PASS@IP/...."

PARALLEL:
  · Pair cam in app while blue light flashes (+ Add Device)
  · UVC laptop still works: python eufy_link.py snap 0

LATER (optional heavy stack):
  · eufy-security-ws / Home Assistant with YOUR account (P2P stream)
  · Still your credentials — not a third-party break-in

We do not attack other people's cameras. We gut OUR lock.
"""
    )


def main(argv: list[str]) -> int:
    cmd = (argv[0] if argv else "playbook").lower()
    if cmd in ("help", "-h", "--help"):
        playbook()
        print("cmds: hunt | probe [ip] | rtsp <url> [name] | snap-url <url> | playbook | status")
        return 0
    if cmd == "hunt":
        base = argv[1] if len(argv) > 1 else "192.168.0"
        hunt(base)
        return 0
    if cmd == "probe":
        host = argv[1] if len(argv) > 1 else "192.168.0.248"
        probe(host)
        return 0
    if cmd == "rtsp":
        if len(argv) < 2:
            print("usage: eufy_owned.py rtsp <url> [name]")
            return 1
        register_rtsp(argv[1], " ".join(argv[2:]) if len(argv) > 2 else "Owned Eufy RTSP")
        return 0
    if cmd in ("snap-url", "snap"):
        if len(argv) < 2:
            print("usage: eufy_owned.py snap-url <rtsp-url>")
            return 1
        return 0 if snap_rtsp(argv[1]) else 1
    if cmd == "status":
        if STATE.exists():
            print(STATE.read_text(encoding="utf-8"))
        else:
            print("no owned state yet — run hunt")
        return 0
    playbook()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
