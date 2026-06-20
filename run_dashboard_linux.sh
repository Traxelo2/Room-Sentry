#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d venv ]; then echo "venv not found. Run ./install_linux.sh first."; exit 1; fi
. venv/bin/activate
python dashboard_server.py --open
