#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${1:-}"

if [ ! -f README.md ] || [ ! -f room_sentry.py ]; then
  echo "Run this from the RoomSentry repo root."
  exit 1
fi

git init
if ! git branch --show-current >/dev/null 2>&1; then
  git checkout -b main
else
  git branch -M main
fi

git add .
git commit -m "Initial open-source RoomSentry release" || true

if [ -n "$REPO_URL" ]; then
  git remote remove origin >/dev/null 2>&1 || true
  git remote add origin "$REPO_URL"
  git push -u origin main
else
  echo "Local git repo is ready. To push:"
  echo "git remote add origin https://github.com/YOUR_USERNAME/roomsentry.git"
  echo "git push -u origin main"
fi
