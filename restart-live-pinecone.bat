@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\local-server.ps1" -Action restart -Mode live -Backend pinecone
set "result=%errorlevel%"
if /i not "%~1"=="--no-pause" pause
exit /b %result%
