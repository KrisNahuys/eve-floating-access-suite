#!/usr/bin/env python3
"""
EYES — continuous PC camera for Architect01 house.

  eyes start [index] [interval_sec]   background watch (default cam 0, every 5s)
  eyes once [index]                   single frame
  eyes status                         last frame + running?
  eyes stop                           request stop
  eyes latest                         print path to latest.jpg

Keeps:
  media/stage/eyes/latest.jpg     always current
  media/stage/eyes/frames/        rolling history (auto-prune)
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parent
EYES_DIR = ROOT / "media" / "stage" / "eyes"
FRAMES = EYES_DIR / "frames"
LATEST = EYES_DIR / "latest.jpg"
STATE = CONTROL / "eyes_state.json"
STOP_FLAG = CONTROL / "eyes_stop.flag"
PID_FILE = CONTROL / "eyes.pid"

# disk hygiene
MAX_FRAMES = 120
DEFAULT_INTERVAL = 5.0
DEFAULT_INDEX = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def save_state(d: dict) -> None:
    d["ts"] = utc_now()
    STATE.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def prune_frames() -> None:
    if not FRAMES.exists():
        return
    files = sorted(FRAMES.glob("eye_*.jpg"), key=lambda p: p.stat().st_mtime)
    while len(files) > MAX_FRAMES:
        old = files.pop(0)
        try:
            old.unlink()
        except OSError:
            pass


def grab(index: int = 0) -> Path | None:
    try:
        import cv2
    except ImportError as e:
        print("opencv missing:", e)
        return None

    EYES_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"cannot open camera index {index}")
        return None

    frame = None
    for _ in range(6):
        ret, frame = cap.read()
        if not ret:
            frame = None
    cap.release()
    if frame is None:
        print("no frame")
        return None

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = FRAMES / f"eye_{stamp}_uvc{index}.jpg"
    import cv2 as _cv2

    _cv2.imwrite(str(path), frame)
    _cv2.imwrite(str(LATEST), frame)
    prune_frames()
    prev = load_state()
    save_state(
        {
            "event": "grab",
            "index": index,
            "latest": str(LATEST),
            "frame": str(path),
            "bytes": path.stat().st_size,
            "running": bool(prev.get("running")),
            "interval": prev.get("interval"),
            "pid": prev.get("pid"),
        }
    )
    print(f"eye: {path}")
    print(f"latest: {LATEST}")
    return path


def run_loop(index: int, interval: float) -> int:
    try:
        import cv2
    except ImportError as e:
        print("opencv missing:", e)
        return 1

    if STOP_FLAG.exists():
        try:
            STOP_FLAG.unlink()
        except OSError:
            pass

    EYES_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    print(f"EYES ON · index={index} interval={interval}s · pid={os.getpid()}")
    print(f"latest → {LATEST}")
    n = 0
    fails = 0
    while True:
        if STOP_FLAG.exists():
            print("stop flag — eyes off")
            break
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            fails += 1
            save_state(
                {
                    "event": "error",
                    "error": "open_failed",
                    "fails": fails,
                    "running": True,
                    "index": index,
                    "interval": interval,
                }
            )
            print(f"open fail #{fails}")
            time.sleep(interval)
            continue
        frame = None
        for _ in range(4):
            ret, frame = cap.read()
            if not ret:
                frame = None
        cap.release()
        if frame is None:
            fails += 1
            print(f"frame fail #{fails}")
            time.sleep(interval)
            continue
        fails = 0
        n += 1
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = FRAMES / f"eye_{stamp}_uvc{index}.jpg"
        cv2.imwrite(str(path), frame)
        cv2.imwrite(str(LATEST), frame)
        if n % 5 == 0:
            prune_frames()
        save_state(
            {
                "event": "tick",
                "n": n,
                "index": index,
                "interval": interval,
                "latest": str(LATEST),
                "frame": str(path),
                "bytes": path.stat().st_size,
                "running": True,
                "pid": os.getpid(),
            }
        )
        if n == 1 or n % 12 == 0:
            print(f"eyes tick n={n} {path.name} {path.stat().st_size}b")
        # sleep in slices so stop is responsive
        end = time.time() + interval
        while time.time() < end:
            if STOP_FLAG.exists():
                break
            time.sleep(0.25)

    save_state({"event": "stopped", "n": n, "running": False, "latest": str(LATEST)})
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except OSError:
        pass
    print("EYES OFF")
    return 0


def start_background(index: int, interval: float) -> int:
    # if already running, report
    st = load_state()
    if st.get("running") and PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip())
            # Windows: check process
            import subprocess

            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if str(pid) in (r.stdout or ""):
                print(f"already running pid={pid}")
                print(f"latest: {LATEST}")
                return 0
        except Exception:
            pass

    if STOP_FLAG.exists():
        try:
            STOP_FLAG.unlink()
        except OSError:
            pass

    py = sys.executable
    script = Path(__file__).resolve()
    # detached-ish on Windows
    CREATE_NO_WINDOW = 0x08000000
    import subprocess

    args = [py, str(script), "run", str(index), str(interval)]
    try:
        proc = subprocess.Popen(
            args,
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,  # type: ignore[attr-defined]
        )
    except Exception:
        proc = subprocess.Popen(
            args,
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    time.sleep(1.2)
    # force one immediate grab so latest exists even if loop slow
    grab(index)
    save_state(
        {
            "event": "start",
            "running": True,
            "index": index,
            "interval": interval,
            "launcher_pid": proc.pid,
            "latest": str(LATEST),
        }
    )
    print(f"EYES STARTED · launcher_pid={proc.pid} index={index} every {interval}s")
    print(f"latest: {LATEST}")
    print("stop:  python eyes.py stop")
    return 0


def stop() -> int:
    STOP_FLAG.write_text(utc_now(), encoding="utf-8")
    st = load_state()
    st["running"] = False
    st["event"] = "stop_requested"
    save_state(st)
    print("stop requested")
    return 0


def status() -> int:
    st = load_state()
    print(json.dumps(st, indent=2))
    if LATEST.exists():
        print(f"latest_exists: {LATEST} ({LATEST.stat().st_size} bytes)")
        print(f"latest_mtime: {datetime.fromtimestamp(LATEST.stat().st_mtime)}")
    else:
        print("latest_exists: no")
    if PID_FILE.exists():
        print(f"pid_file: {PID_FILE.read_text(encoding='utf-8').strip()}")
    return 0


def main(argv: list[str]) -> int:
    cmd = (argv[0] if argv else "status").lower()
    if cmd in ("once", "snap", "grab"):
        idx = int(argv[1]) if len(argv) > 1 else DEFAULT_INDEX
        return 0 if grab(idx) else 1
    if cmd == "run":
        # foreground loop (used by start)
        idx = int(argv[1]) if len(argv) > 1 else DEFAULT_INDEX
        interval = float(argv[2]) if len(argv) > 2 else DEFAULT_INTERVAL
        return run_loop(idx, interval)
    if cmd == "start":
        idx = int(argv[1]) if len(argv) > 1 else DEFAULT_INDEX
        interval = float(argv[2]) if len(argv) > 2 else DEFAULT_INTERVAL
        return start_background(idx, interval)
    if cmd == "stop":
        return stop()
    if cmd in ("status", "show"):
        return status()
    if cmd == "latest":
        print(LATEST if LATEST.exists() else "missing")
        return 0 if LATEST.exists() else 1
    print("usage: eyes.py start|stop|status|once|latest|run [index] [interval]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
