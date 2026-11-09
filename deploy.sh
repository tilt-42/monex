#!/usr/bin/env bash
# Publishes the committed code to GitHub, then updates and restarts the bot on the Pi.
set -euo pipefail

if [ -n "$(git status --porcelain)" ]; then
  echo "You have uncommitted changes. Commit them first." >&2
  exit 1
fi

git push origin main
ssh -t raspi@raspi 'cd ~/projects/monex && git pull --ff-only && .venv/bin/pip install --quiet -r requirements.txt && sudo systemctl restart monex && sleep 5 && systemctl status monex --no-pager -n 5'
