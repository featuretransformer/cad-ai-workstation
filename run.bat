@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   Starting AI-Native CAD-CAM Workstation Stack...
echo ===================================================

if exist backend\.venv\Scripts\python.exe (
    set "PYTHON_EXE=backend\.venv\Scripts\python.exe"
) else if exist .venv\Scripts\python.exe (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" run.py %*
pause
