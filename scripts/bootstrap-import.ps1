# MyACE Import Bootstrap Script (Windows PowerShell)
#
# Usage:
#   irm https://raw.githubusercontent.com/niels-emmer/myace/main/scripts/bootstrap-import.ps1 | iex
#   # or if you've cloned the repo:
#   .\scripts\bootstrap-import.ps1
#
# This script:
#   1. Checks for Python 3.12+
#   2. Creates a virtual environment at ~\.myace\venv\
#   3. Installs myace-cli[serve] from GitHub
#   4. Guides you through creating an API token and logging in
#   5. Starts the local companion server for web UI imports
#
# Environment variables:
#   MYACE_SERVER  — MyACE server URL (default: http://localhost:8000)
#
# Prerequisites:
#   - Python 3.12 or later (with pip)
#   - Git for Windows (for pip's git+https installs)
#
# This script is idempotent — safe to re-run.

$ErrorActionPreference = "Stop"

$MYACE_DIR = "${env:USERPROFILE}\.myace"
$VENV_DIR = "${MYACE_DIR}\venv"
$MYACE_SERVER = if ($env:MYACE_SERVER) { $env:MYACE_SERVER } else { "http://localhost:8000" }

function Write-Info  { Write-Host "✓ $($args -join ' ')" -ForegroundColor Green }
function Write-Warn  { Write-Host "! $($args -join ' ')" -ForegroundColor Yellow }
function Write-Error { Write-Host "✗ $($args -join ' ')" -ForegroundColor Red }
function Write-Step  { Write-Host "`n=== $($args -join ' ') ===" -ForegroundColor Cyan }

# ─── Step 1: Check Python 3.12+ ───────────────────────────────
Write-Step "Checking Python"

$python = $null
foreach ($cmd in @("python3", "python")) {
    try {
        $python = (Get-Command $cmd -ErrorAction Stop).Source
        break
    } catch {
        continue
    }
}

if (-not $python) {
    Write-Error "Python 3 not found."
    Write-Host ""
    Write-Host "  Install Python 3.12+ from:"
    Write-Host "    https://www.python.org/downloads/"
    Write-Host ""
    Write-Host "  Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

$pyVersion = & $python --version 2>&1
Write-Info "Found $pyVersion at $python"

# Parse version
if ($pyVersion -match '(\d+)\.(\d+)') {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 12)) {
        Write-Error "Python 3.12+ required (found $major.$minor)"
        Write-Host ""
        Write-Host "  Upgrade Python from: https://www.python.org/downloads/"
        exit 1
    }
} else {
    Write-Error "Could not parse Python version"
    exit 1
}

# ─── Step 2: Create virtual environment ────────────────────────
Write-Step "Setting up virtual environment"

if (-not (Test-Path $MYACE_DIR)) {
    New-Item -ItemType Directory -Path $MYACE_DIR -Force | Out-Null
}

if (Test-Path $VENV_DIR) {
    Write-Warn "Virtual environment already exists at $VENV_DIR"
    Write-Warn "Activating existing environment..."
} else {
    Write-Info "Creating virtual environment at $VENV_DIR..."
    & $python -m venv $VENV_DIR
}

# Activate the virtual environment
$activateScript = "${VENV_DIR}\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    . $activateScript
} else {
    Write-Error "Virtual environment activation script not found at $activateScript"
    exit 1
}

# ─── Step 3: Install myace-cli ─────────────────────────────────
Write-Step "Installing myace-cli"

Write-Info "Upgrading pip..."
python -m pip install --quiet --upgrade pip

Write-Info "Installing myace-cli[serve] from GitHub..."
try {
    python -m pip install --quiet "git+https://github.com/niels-emmer/myace.git#subdirectory=cli[serve]"
    if ($LASTEXITCODE -eq 0) {
        Write-Info "myace-cli installed successfully"
    } else {
        throw "pip install failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Error "Failed to install myace-cli: $_"
    Write-Host ""
    Write-Host "  Check that Git for Windows is installed and you have internet access."
    Write-Host "  https://git-scm.com/download/win"
    exit 1
}

# ─── Step 4: Verify installation ───────────────────────────────
Write-Step "Verifying installation"

try {
    $helpText = & myace --help 2>&1 | Select-Object -First 1
    Write-Info "myace CLI is ready: $helpText"
} catch {
    Write-Warn "myace command not found in PATH after install"
    Write-Warn "You may need to activate the venv manually:"
    Write-Host "    $activateScript"
}

# ─── Step 5: Guide user ────────────────────────────────────────
Write-Step "Setup Complete — Next Steps"

Write-Host ""
Write-Host "  Option A: Import via web UI (recommended for first use)"
Write-Host ""
Write-Host "    1. Open the MyACE web UI and create an API token:"
Write-Host "       $MYACE_SERVER/settings"
Write-Host ""
Write-Host "    2. Activate the environment and start the companion server:"
Write-Host "       $activateScript"
Write-Host "       myace login --server $MYACE_SERVER --token <your-token>"
Write-Host "       myace serve"
Write-Host ""
Write-Host "    3. Go to the Import page in your browser and scan your machine."
Write-Host ""
Write-Host "  Option B: One-shot CLI import"
Write-Host ""
Write-Host "    $activateScript"
Write-Host "    myace login --server $MYACE_SERVER --token <your-token>"
Write-Host "    myace import --path ~\.config\opencode --name my-config --push"
Write-Host ""
Write-Host "  Quick reference:"
Write-Host ""
Write-Host "    Activate venv later:  $activateScript"
Write-Host ""

Write-Info "Bootstrap complete"
