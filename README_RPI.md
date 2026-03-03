Raspberry Pi deployment notes

Overview
- This project runs a Flask-based CSV manager and an optional Tkinter-based attendance UI (Attendance.py).

Preparation on Raspberry Pi (Raspbian / Raspberry Pi OS)
1. Update & install prerequisites:
   sudo apt update && sudo apt install -y python3 python3-venv python3-pip python3-tk libjpeg-dev zlib1g-dev

2. Copy project to the Pi (do not copy the `.venv` directory):
   scp -r LIBRO pi@raspberrypi:/home/pi/

3. On the Pi, create and activate a venv:
   cd ~/LIBRO
   python3 -m venv .venv
   source .venv/bin/activate

4. Install Python dependencies:
   pip install -r requirements.txt

Running the server
- Start the Flask app:
  ./.venv/bin/python Server.py
- For production use, run under a WSGI server (gunicorn/uwsgi) or configure as a systemd service (see `deploy/libro.service.example`).

Attendance UI
- `Attendance.py` uses `tkinter` and requires a graphical desktop environment. Run it on the Pi desktop.
- Sound: On Linux, the helper will use the `beep` utility if installed; otherwise a fallback ASCII bell is used.

Notes
- The application stores attendance CSVs in the `csv_files` folder (added for portability).
- Don't copy a Windows `.venv` to the Pi — create a new venv on the device.
- When transferring, copy all files and folders from the project except the `.venv` directory. The `setup/setup_rpi.sh` script will create a clean `.venv` on the Pi and install pinned dependencies from `requirements-pinned.txt`.

Setup script
- To bootstrap a fresh Raspberry Pi after copying the project, run:
  - `chmod +x setup/setup_rpi.sh`
  - `./setup/setup_rpi.sh` (or `./setup/setup_rpi.sh --install-service` to enable a systemd service)

Kiosk startup for Attendance.py (fullscreen on boot)
- For your path/user (`/home/librarysys/LIBRO`, user `librarysys`):
  - `cd /home/librarysys/LIBRO`
  - `chmod +x setup/install_kiosk_service.sh`
  - `./setup/install_kiosk_service.sh /home/librarysys/LIBRO librarysys`
- This installs `libro-kiosk.service` that:
  - waits for GUI (`DISPLAY=:0`)
  - disables screen blanking
  - launches `Attendance.py`
  - restarts automatically on crash
  - writes logs to:
    - `logs/kiosk_stdout.log`
    - `logs/kiosk_stderr.log`
- Debug commands:
  - `systemctl status libro-kiosk.service`
  - `journalctl -u libro-kiosk.service -f`

Contact
- If you want, I can add an automated setup script to bootstrap a fresh Pi.
