# MyACE Import Bootstrap Script (Windows PowerShell)
#
# Usage:
#   $env:MYACE_SERVER = "https://myace.macjuu.com"
#   irm https://raw.githubusercontent.com/niels-emmer/myace/main/scripts/bootstrap-import.ps1 | iex
#   # or if you've cloned the repo:
#   .\scripts\bootstrap-import.ps1
#
# This script:
#   1. Detects your platform and downloads a pre-built binary if available
#   2. Falls back to venv+pip if no binary exists for your platform
#   3. Guides you through creating an API token and logging in
#   4. Starts the local companion server for web UI imports
#
# Environment variables:
#   MYACE_SERVER  — MyACE server URL (required)
#
# This script is idempotent — safe to re-run.

$ErrorActionPreference = "Stop"

$MYACE_DIR = "${env:USERPROFILE}\.myace"
$BIN_DIR = "${MYACE_DIR}\bin"
$VENV_DIR = "${MYACE_DIR}\venv"
$MYACE_SERVER = $env:MYACE_SERVER
$GH_RELEASE = "https://github.com/niels-emmer/myace/releases/latest/download"

function Write-Info  { Write-Host "✓ $($args -join ' ')" -ForegroundColor Green }
function Write-Warn  { Write-Host "! $($args -join ' ')" -ForegroundColor Yellow }
function Write-Error { Write-Host "✗ $($args -join ' ')" -ForegroundColor Red }
function Write-Step  { Write-Host "`n=== $($args -join ' ') ===" -ForegroundColor Cyan }

# ─── Step 1: Check MyACE server URL ────────────────────────────
Write-Step "MyACE Server"

if (-not $MYACE_SERVER) {
    Write-Error "MYACE_SERVER is not set."
    Write-Host ""
    Write-Host "  This script needs your MyACE server URL. Set it before running:"
    Write-Host ""
    Write-Host "    `$env:MYACE_SERVER = 'https://myace.macjuu.com'"
    Write-Host "    irm https://raw.githubusercontent.com/niels-emmer/myace/main/scripts/bootstrap-import.ps1 | iex"
    Write-Host ""
    exit 1
}

Write-Info "Using server: $MYACE_SERVER"

# ─── Step 2: Detect platform and try binary download ───────────
Write-Step "Downloading myace binary"

if (-not (Test-Path $BIN_DIR)) {
    New-Item -ItemType Directory -Path $BIN_DIR -Force | Out-Null
}

$binaryName = $null
$myaceBin = "${BIN_DIR}\myace.exe"

# Detect architecture
$arch = if ([Environment]::Is64BitOperatingSystem) { "x86_64" } else { "x86" }

if ($arch -eq "x86_64") {
    $binaryName = "myace-windows-x86_64.exe"
} else {
    Write-Warn "Unsupported Windows architecture: $arch"
}

$binaryDownloaded = $false

if ($binaryName) {
    $downloadUrl = "${GH_RELEASE}/${binaryName}"
    $checksumUrl = "${GH_RELEASE}/${binaryName}.sha256"
    Write-Info "Downloading ${binaryName}..."
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $myaceBin -ErrorAction Stop

        # Verify checksum
        try {
            $checksumContent = Invoke-WebRequest -Uri $checksumUrl -ErrorAction Stop
            $checksumLines = $checksumContent -split "`n"
            $expectedHash = $null
            foreach ($line in $checksumLines) {
                if ($line -match '^([a-f0-9]+)\s+\*?myace-windows') {
                    $expectedHash = $matches[1]
                    break
                }
            }
            if ($expectedHash) {
                $actualHash = (Get-FileHash -Path $myaceBin -Algorithm SHA256).Hash.ToLower()
                if ($expectedHash -ne $actualHash) {
                    Write-Error "Checksum mismatch! Downloaded binary may be tampered with."
                    Remove-Item -Path $myaceBin -Force
                    Write-Warn "Falling back to pip install."
                } else {
                    Write-Info "Binary downloaded and verified: $myaceBin"
                    $binaryDownloaded = $true
                }
            } else {
                Write-Warn "Checksum file found but no entry for ${binaryName} — skipping verification."
                $binaryDownloaded = $true
            }
        } catch {
            Write-Warn "No checksum file found — skipping verification."
            $binaryDownloaded = $true
        }
    } catch {
        Write-Warn "Binary download failed (no release yet?). Falling back to pip install."
    }
} else {
    Write-Warn "No pre-built binary for this platform. Falling back to pip install."
}

# ─── Step 3: Fall back to venv+pip if binary not available ─────
if (-not $binaryDownloaded) {
    Write-Step "Setting up Python virtual environment"

    # Check Python 3.12+
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

    if (-not (Test-Path $MYACE_DIR)) {
        New-Item -ItemType Directory -Path $MYACE_DIR -Force | Out-Null
    }

    if (Test-Path $VENV_DIR) {
        Write-Warn "Virtual environment already exists at $VENV_DIR"
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

    Write-Info "Upgrading pip..."
    python -m pip install --quiet --upgrade pip

    Write-Info "Installing myace-cli[serve] from GitHub..."
    try {
        python -m pip install --quiet "myace-cli[serve] @ git+https://github.com/niels-emmer/myace.git#subdirectory=cli"
        if ($LASTEXITCODE -eq 0) {
            Write-Info "myace-cli installed successfully"
            $myaceBin = "myace"
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
}

# ─── Step 4: Verify installation ───────────────────────────────
Write-Step "Verifying installation"

if ($binaryDownloaded) {
    # Binary was downloaded — add to PATH for this session
    $env:Path = "${BIN_DIR};${env:Path}"
    $helpText = & $myaceBin --help 2>&1 | Select-Object -First 1
    Write-Info "myace CLI is ready: $helpText"
} else {
    try {
        $helpText = & myace --help 2>&1 | Select-Object -First 1
        Write-Info "myace CLI is ready: $helpText"
    } catch {
        Write-Warn "myace command not found in PATH after install"
        Write-Warn "You may need to activate the venv manually:"
        Write-Host "    $activateScript"
    }
}

# ─── Step 5: Guide user ────────────────────────────────────────
Write-Step "Setup Complete — Next Steps"

Write-Host ""
Write-Host "  To connect to your MyACE server:"
Write-Host ""
Write-Host "    1. Open the MyACE web UI and create an API token:"
Write-Host "       $MYACE_SERVER/settings"
Write-Host ""
Write-Host "    2. Log in (you'll be prompted for the server URL and token):"
Write-Host "       $myaceBin login"
Write-Host ""
Write-Host "    3. Start the local companion server:"
Write-Host "       $myaceBin serve"
Write-Host ""
Write-Host "    4. Go to the Import page in your browser and scan your machine."
Write-Host ""

if ($binaryDownloaded) {
    Write-Host "  Binary install:"
    Write-Host ""
    Write-Host "    myace.exe is at $myaceBin"
    Write-Host "    Add it to your PATH:  `$env:Path = '${BIN_DIR};' + `$env:Path"
    Write-Host ""
} else {
    Write-Host "  Quick reference:"
    Write-Host ""
    Write-Host "    Activate venv later:  $activateScript"
    Write-Host ""
}

Write-Info "Bootstrap complete"
