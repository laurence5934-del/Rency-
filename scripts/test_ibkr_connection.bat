@echo off
cd /d %~dp0\..
python tests\test_ibkr_connection.py
pause
