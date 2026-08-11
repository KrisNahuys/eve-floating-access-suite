@echo off
cd /d "%~dp0"
echo === PRESS PLAY - Eve Floating Access Suite ===
start "eyes" python control\eyes.py start
timeout /t 1 /nobreak >nul
start "home" python control\home_status.py open
start "shade" python control\check_shade.py open
start "access" python control\access_panel.py
start "comms" python control\comms_float.py
echo Launched.
pause
