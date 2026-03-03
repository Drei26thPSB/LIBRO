param(
  [Parameter(Mandatory=$true)][string]$remote,
  [string]$remoteDir = "~/LIBRO",
  [switch]$InstallService
)

Write-Host "Warning: this PowerShell helper uses scp/ssh from OpenSSH. It will COPY the project directory as-is." -ForegroundColor Yellow
Write-Host "If you have a local .venv, remove or exclude it before running this script to avoid copying large files." -ForegroundColor Yellow

$installArg = ""
if ($InstallService) { $installArg = "--install-service" }

# Ensure ssh/scp commands exist
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
  Write-Error "scp not found. Install OpenSSH client or use the POSIX script tools/transfer_install.sh from WSL/macOS."; exit 1
}

# Create remote dir and copy
ssh $remote "mkdir -p $remoteDir"
scp -r * $remote:`$remoteDir

Write-Host "Running remote installer..."
ssh $remote "bash -lc 'cd $remoteDir && bash setup/setup_rpi.sh $installArg'"

Write-Host "Done. Web UI should be at http://<pi-ip>:5000 after install." -ForegroundColor Green
