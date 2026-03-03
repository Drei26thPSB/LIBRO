#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/home/librarysys/LIBRO}"
APP_USER="${2:-librarysys}"
SERVICE_NAME="${3:-libro-kiosk.service}"
PYTHON_BIN="$APP_DIR/.venv/bin/python"
ATTENDANCE_PY="$APP_DIR/Attendance.py"
WRAPPER="$APP_DIR/setup/start_attendance_kiosk.sh"
UNIT_PATH="/etc/systemd/system/$SERVICE_NAME"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing Python venv binary: $PYTHON_BIN"
  echo "Run setup/setup_rpi.sh first."
  exit 1
fi

if [ ! -f "$ATTENDANCE_PY" ]; then
  echo "Missing file: $ATTENDANCE_PY"
  exit 1
fi

mkdir -p "$APP_DIR/setup"

cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export DISPLAY=:0
export XAUTHORITY=/home/$APP_USER/.Xauthority
export LIBRO_BOOT_DIRECT_START=1
export PYTHONUNBUFFERED=1
cd "$APP_DIR"

# Wait for X to be ready before launching Tk.
for _ in \$(seq 1 40); do
  if xset q >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

# Prevent screen blank/sleep in kiosk mode.
xset s off >/dev/null 2>&1 || true
xset -dpms >/dev/null 2>&1 || true
xset s noblank >/dev/null 2>&1 || true

exec "$PYTHON_BIN" "$ATTENDANCE_PY"
EOF
chmod +x "$WRAPPER"

sudo tee "$UNIT_PATH" >/dev/null <<EOF
[Unit]
Description=LIBRO Attendance Kiosk
After=graphical.target network-online.target
Wants=graphical.target network-online.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$APP_USER/.Xauthority
Environment=LIBRO_BOOT_DIRECT_START=1
ExecStart=$WRAPPER
Restart=always
RestartSec=2
StandardOutput=append:$APP_DIR/logs/kiosk_stdout.log
StandardError=append:$APP_DIR/logs/kiosk_stderr.log

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Installed and started $SERVICE_NAME"
echo "Check logs with:"
echo "  journalctl -u $SERVICE_NAME -f"
