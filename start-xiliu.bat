@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\xiliu.exe" (
  echo Please run uv sync --dev first.
  pause
  exit /b 1
)
if not exist "web\dist\index.html" (
  call npm.cmd --prefix web ci
  if errorlevel 1 exit /b 1
  call npm.cmd --prefix web run build
  if errorlevel 1 exit /b 1
)
".venv\Scripts\xiliu.exe" web --open
