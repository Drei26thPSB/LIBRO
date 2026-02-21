#!/usr/bin/env bash
set -euo pipefail

usage(){
  cat <<EOF
Usage: $0 user@host[:port] [remote_dir] [--install-service]

Examples:
  $0 pi@raspberrypi             # copy to ~/LIBRO and run setup
  $0 pi@raspberrypi /home/pi/LIBRO --install-service

This script transfers the current project to the remote Pi (excluding .venv when possible)
and runs the Pi-side installer `setup/setup_rpi.sh`.
EOF
}

if [ "$#" -lt 1 ]; then
  usage
  exit 1
fi

REMOTE="$1"
REMOTE_DIR="${2:-~/LIBRO}"
INSTALL_SERVICE_FLAG=""
if [ "${3:-}" = "--install-service" ]; then
  INSTALL_SERVICE_FLAG="--install-service"
fi

echo "Transferring project to ${REMOTE}:${REMOTE_DIR}"

# Prefer rsync if available for efficient transfers and easy excludes
if command -v rsync >/dev/null 2>&1; then
  rsync -av --delete --exclude='.venv' ./ "$REMOTE:$REMOTE_DIR"
else
  # Fallback: stream a tarball over ssh excluding .venv
  tar --exclude='.venv' -czf - . | ssh "$REMOTE" "mkdir -p $REMOTE_DIR && tar xzf - -C $REMOTE_DIR"
fi

echo "Running remote installer"
ssh "$REMOTE" "bash -lc 'cd $REMOTE_DIR && bash setup/setup_rpi.sh ${INSTALL_SERVICE_FLAG}'"

echo "Done. Web UI should be at http://<pi-ip>:5000 after install."
