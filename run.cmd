@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create the Python environment first. See README.md.
  exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn papertrail.server:app --host 127.0.0.1 --port 8000
