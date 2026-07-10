@echo off
cd /d %~dp0\..
python -m streamlit run app/dashboard/main.py
pause
