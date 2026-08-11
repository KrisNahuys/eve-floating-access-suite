# eve-floating-access-suite

Floating / always-on-top **access suite** for the Architect01 · Eve · Grok house.

## Press play

```bat
cd eve-floating-access-suite
pip install -r requirements.txt
PLAY.cmd
```

Or piece by piece:

```bat
python control\eyes.py start
python control\home_status.py open
python control\check_shade.py open
python control\access_panel.py
python control\comms_float.py
python control\speak_house.py "House online"
```

## What you get

| Module | Role |
|--------|------|
| `eyes.py` | Continuous PC camera → `media/stage/eyes/latest.jpg` |
| `check_shade.py` | On-screen reference HUD |
| `home_status.py` | One-glance HTML/MD status |
| `access_panel.py` | Top-right floating access panel |
| `comms_float.py` | Floating status chrome (generic; no PII defaults) |
| `speak_house.py` | Neural TTS (edge-tts AU Natasha) |
| `eufy_link.py` / `eufy_owned.py` / `eufy_access.py` | Own-gear Eufy/UVC/RTSP tools |
| `PLAY.cmd` | One-click launcher |

## Requirements

- Windows 10/11
- Python 3.10+
- `pip install -r requirements.txt` (opencv, numpy, edge-tts)
- Optional: FFmpeg on PATH for video/RTSP snaps

## Privacy

This public pack **does not** ship vault secrets, bank data, or private family locations.
Those stay in local Shadow Wolf / GrokWorkspace only.

## License / house

Local free-run · great intent · Road Between the Lines.
