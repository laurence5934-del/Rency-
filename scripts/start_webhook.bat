@echo off
cd /d %~dp0\..
python -m uvicorn app.api.webhook_server:app --reload --port 8000
pause
