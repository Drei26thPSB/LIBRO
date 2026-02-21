#!/usr/bin/env bash
set -euo pipefail

echo "Running remote bootstrap (remote_install.sh)"

PROJECT_DIR=$(pwd)

if [ ! -f setup/setup_rpi.sh ]; then
  echo "Expected to find setup/setup_rpi.sh in project root. Aborting." >&2
  exit 2
fi

echo "Delegating to setup/setup_rpi.sh (may require sudo on the Pi)"
bash setup/setup_rpi.sh "$@"

echo "remote_install.sh finished"
