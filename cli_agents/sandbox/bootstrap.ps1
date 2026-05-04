# cli_agents/sandbox/bootstrap.ps1
# Runs at Windows Sandbox login via LogonCommand in the .wsb file.
# Installs Python + cli_agents from HostShare, then starts the bridge.

$share  = "C:\HostShare"
$logDir = "C:\SandboxLogs"
$log    = "$logDir\bootstrap.log"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $log -Value $line
}

Log "=== Bootstrap start ==="

# ── 1. Python ─────────────────────────────────────────────────────────────────
$pyExe = "$share\python-installer.exe"
$hasPy = $null -ne (Get-Command python -ErrorAction SilentlyContinue)

if (-not $hasPy) {
    if (Test-Path $pyExe) {
        Log "Installing Python from $pyExe ..."
        Start-Process -FilePath $pyExe `
            -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" `
            -Wait
        # Refresh PATH so python is visible in this session
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("PATH","User")
        Log "Python installed"
    } else {
        Log "WARNING: python-installer.exe not found in share — skipping"
    }
} else {
    Log "Python already present"
}

# ── 2. pip-upgrade (quiet) ────────────────────────────────────────────────────
python -m pip install --upgrade pip --quiet
Log "pip up to date"

# ── 3. Install cli_agents ─────────────────────────────────────────────────────
$pkgDir = "$share\cli_agents_dist"
if (Test-Path $pkgDir) {
    Log "Installing cli_agents from $pkgDir ..."
    python -m pip install --quiet $pkgDir
    Log "cli_agents installed"
} else {
    Log "WARNING: cli_agents_dist not found — bridge will fail to import"
}

# ── 4. Copy .env ──────────────────────────────────────────────────────────────
$envSrc = "$share\.env"
$envDst = "C:\SandboxEnv\.env"
if (Test-Path $envSrc) {
    New-Item -ItemType Directory -Force -Path "C:\SandboxEnv" | Out-Null
    Copy-Item $envSrc $envDst -Force
    $env:ENV_FILE = $envDst
    Log "Copied .env → $envDst"
} else {
    Log "WARNING: no .env in share — agent will rely on system env vars"
}

# ── 5. Launch the bridge ──────────────────────────────────────────────────────
$bridge = "$share\cli_agents\sandbox\bridge_sandbox.py"
if (-not (Test-Path $bridge)) {
    Log "ERROR: bridge_sandbox.py not found at $bridge"
    exit 1
}

Log "Starting SandboxCLIBridge ..."
python $bridge