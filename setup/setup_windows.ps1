# Windows helper to create venv and install requirements
Write-Host "LIBRO Windows bootstrap script"

if (-not (Test-Path -Path .\.venv)) {
    python -m venv .venv
}

.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
if (Test-Path requirements-pinned.txt) {
    pip install -r requirements-pinned.txt
} elseif (Test-Path requirements.txt) {
    pip install -r requirements.txt
} else {
    Write-Host "No requirements file found. Skipping pip install."
}

New-Item -ItemType Directory -Force -Path csv_files, logs | Out-Null
if (-not (Test-Path logs\server.log)) { New-Item logs\server.log -ItemType File | Out-Null }
Write-Host "Done. Run .\.venv\Scripts\python.exe Server.py to start the server."