#!/usr/bin/env bash
set -euo pipefail
export DISPLAY=:0
export XAUTHORITY=/home/librarysys/.Xauthority
export LIBRO_BOOT_DIRECT_START=1
export PYTHONUNBUFFERED=1
cd "/home/librarysys/LIBRO"

# Wait for X to be ready before launching Tk.
for _ in $(seq 1 40); do
  if xset q >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

# Prevent screen blank/sleep in kiosk mode.
xset s off >/dev/null 2>&1 || true
xset -dpms >/dev/null 2>&1 || true
xset s noblank >/dev/null 2>&1 || true

exec "/home/librarysys/LIBRO/.venv/bin/python" "/home/librarysys/LIBRO/Attendance.py"
