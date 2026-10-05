#!/bin/bash
# ---------------------------------------------------------------
# Chatbot Quality Analyzer - launcher (macOS / Linux)
#
# macOS: double-click this file in Finder.
# Linux: run `bash start.command` in a terminal.
#
# First run creates a virtual environment and installs the
# dependencies (a few minutes). Later runs start immediately.
# Stop the panel with Ctrl+C in this window.
# ---------------------------------------------------------------

# Work from the script's folder (dashboard.py uses relative paths)
cd "$(dirname "$0")" || exit 1

PORT=8501

bekle_ve_cik() {
    echo ""
    read -n 1 -s -r -p "Press any key to close..."
    exit "${1:-1}"
}

tarayici_ac() {
    if command -v open >/dev/null 2>&1; then open "$1"
    elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1
    fi
}

echo "=============================================="
echo "  Chatbot Quality Analyzer"
echo "=============================================="
echo ""

# --- 1) Virtual environment (first run only) -----------------
if [ ! -x ".venv/bin/streamlit" ]; then
    PY=""
    for aday in python3.13 python3.12 python3.11 python3; do
        if command -v "$aday" >/dev/null 2>&1 &&
           "$aday" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
            PY="$aday"
            break
        fi
    done
    if [ -z "$PY" ]; then
        echo "ERROR: Python 3.11 or newer is required."
        echo "Download it from https://www.python.org/downloads/ and run this again."
        bekle_ve_cik 1
    fi

    echo "First run: setting up the environment with $("$PY" --version)."
    echo "This takes a few minutes and happens only once."
    echo ""
    "$PY" -m venv .venv || { echo "ERROR: could not create .venv"; bekle_ve_cik 1; }
    ./.venv/bin/pip install --upgrade pip >/dev/null
    ./.venv/bin/pip install -r requirements.txt || {
        echo ""
        echo "ERROR: dependency installation failed (see the messages above)."
        echo "Delete the .venv folder and run this again to retry."
        bekle_ve_cik 1
    }
    echo ""
fi

# --- 2) Find a free port -------------------------------------
#
# With --server.port given explicitly, Streamlit does NOT pick another
# port when it is busy; it exits with "Port is not available".
SON_PORT=$((PORT + 15))
if command -v lsof >/dev/null 2>&1; then
    while lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; do
        # Is THIS panel already running there? Then just open it.
        if lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null \
             | xargs -I{} ps -p {} -o command= 2>/dev/null \
             | grep -q "dashboard.py"; then
            echo "The panel is already running: http://localhost:$PORT"
            tarayici_ac "http://localhost:$PORT"
            exit 0
        fi
        PORT=$((PORT + 1))
        if [ $PORT -gt $SON_PORT ]; then
            echo "ERROR: no free port between 8501 and $SON_PORT."
            bekle_ve_cik 1
        fi
    done
fi

# --- 3) Run --------------------------------------------------
export PYTHONIOENCODING=utf-8

echo "Starting the panel on http://localhost:$PORT ..."
echo "Your browser will open shortly. Stop with Ctrl+C."
echo ""

./.venv/bin/streamlit run dashboard.py --server.port $PORT

echo ""
echo "The panel has stopped."
bekle_ve_cik 0
