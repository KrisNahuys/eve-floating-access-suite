# eve-floating-access-suite

Floating access for **Architect01 · Eve · Grok** house.

## Status 2026-08-11

| Layer | State |
|-------|--------|
| GitHub repo | Live scaffold (this README) |
| **Local play (PC)** | Run from `GrokWorkspace` — not waiting on empty git tree |
| Eyes continuous | `projects/eden-link/control/eyes.py start` |
| Check shade HUD | `projects/eden-link/control/check_shade.py open` |
| Home status | `projects/eden-link/control/home_status.py open` |
| Access panel (top-right) | `projects/eden-link/control/access_panel.py` |
| Comms float | `projects/eden-link/control/comms_float.py` |
| Neural speak | `projects/eden-link/control/speak_house.py` |
| Eve voice | `~/.grok/bridge/eve/eve-voice.ps1` (neural first) |

## Press play (local)

```bat
cd /d %USERPROFILE%\GrokWorkspace
python projects\eden-link\control\eyes.py start
python projects\eden-link\control\home_status.py open
python projects\eden-link\control\check_shade.py open
python projects\eden-link\control\access_panel.py
```

## GitHub MCP identity

Authenticated as **KrisNahuys** (admin on this repo).

## Next code to land here

1. Package floating widgets into this repo
2. One `play.cmd` launcher
3. Optional: release zip for other machines

## Doors human opens

- Eufy original #2 pair on S22
- `gh auth login` if CLI push from terminal desired (MCP already works)

---
*House law · great intent · Road Between the Lines*
