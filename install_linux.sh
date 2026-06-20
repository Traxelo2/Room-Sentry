#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python migrate_config.py
mkdir -p snapshots logs events clips runtime
echo "Install complete. Run ./run_all_linux.sh or ./run_linux.sh"
