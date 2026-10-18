@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\local-server.ps1" -Action stop
set "result=%errorlevel%"
if /i not "%~1"=="--no-pause" pause
exit /b %result%
