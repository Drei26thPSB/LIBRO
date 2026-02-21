#!/usr/bin/env bash
set -euo pipefail

echo "LIBRO Raspberry Pi bootstrap script"

echo "1/6: Updating package lists (requires sudo)"
sudo apt update

echo "2/6: Installing system packages"
sudo apt install -y python3 python3-venv python3-pip python3-tk libjpeg-dev zlib1g-dev beep

echo "3/6: Creating virtual environment"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip

if [ -f requirements-pinned.txt ]; then
  echo "4/6: Installing Python dependencies from requirements-pinned.txt"
  pip install -r requirements-pinned.txt
elif [ -f requirements.txt ]; then
  echo "4/6: Installing Python dependencies from requirements.txt"
  pip install -r requirements.txt
else
  echo "No requirements file found. Skipping pip install."
fi

echo "5/6: Ensuring data folders exist"
mkdir -p csv_files logs
touch logs/server.log

echo "6/6: Done."

echo "Next steps:"
echo " - Start server: ./.venv/bin/python Server.py"
echo " - (Optional) To run on startup, run this script with --install-service to install a systemd service."

if [ "${1-}" = "--install-service" ]; then
  echo "Installing systemd service..."
  SERVICE_PATH=/etc/systemd/system/libro.service
  # Copy example unit which uses %h specifier for the user's home directory
  sudo cp deploy/libro.service.example "$SERVICE_PATH"
  sudo systemctl daemon-reload
  sudo systemctl enable libro
  sudo systemctl start libro
  echo "Service enabled and started."
fi
