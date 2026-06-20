#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
./run_dashboard_linux.sh &
sleep 2
./run_linux.sh
