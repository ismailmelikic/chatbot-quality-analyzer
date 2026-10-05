@echo off
rem ---------------------------------------------------------------
rem Chatbot Quality Analyzer - launcher (Windows)
rem
rem Double-click this file. First run creates a virtual environment
rem and installs the dependencies (a few minutes). Later runs start
rem immediately. Stop the panel with Ctrl+C in this window.
rem ---------------------------------------------------------------
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo ==============================================
echo   Chatbot Quality Analyzer
echo ==============================================
echo.

if exist ".venv\Scripts\streamlit.exe" goto calistir

set "PY="
where py >nul 2>nul && py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo ERROR: Python 3.11 or newer is required.
    echo Download it from https://www.python.org/downloads/
    echo During installation, tick "Add python.exe to PATH". Then run this again.
    pause
    exit /b 1
)

echo First run: setting up the environment. This takes a few minutes
echo and happens only once.
echo.
%PY% -m venv .venv || goto hata
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto hata
echo.

:calistir
echo Starting the panel. Your browser will open shortly.
echo Stop with Ctrl+C.
echo.
".venv\Scripts\streamlit.exe" run dashboard.py
echo.
echo The panel has stopped.
pause
exit /b 0

:hata
echo.
echo ERROR: setup failed (see the messages above).
echo Delete the .venv folder and run this again to retry.
pause
exit /b 1
