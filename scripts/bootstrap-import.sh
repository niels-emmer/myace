#!/usr/bin/env bash
# MyACE Import Bootstrap Script
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/niels-emmer/myace/main/scripts/bootstrap-import.sh | bash
#   # or if you've cloned the repo:
#   ./scripts/bootstrap-import.sh
#
# This script:
#   1. Checks for Python 3.12+
#   2. Creates a virtual environment at ~/.myace/venv/
#   3. Installs myace-cli[serve] from GitHub
#   4. Guides you through creating an API token and logging in
#   5. Starts the local companion server for web UI imports
#
# Environment variables:
#   MYACE_SERVER  — MyACE server URL (default: http://localhost:8000)
#   MYACE_DIR     — Data directory (default: ~/.myace)
#
# Prerequisites:
#   - Python 3.12 or later
#   - pip (usually included with Python)
#   - git (for pip's git+https installs)
#
# This script is idempotent — safe to re-run.

set -euo pipefail

MYACE_DIR="${MYACE_DIR:-${HOME}/.myace}"
VENV_DIR="${MYACE_DIR}/venv"
MYACE_SERVER="${MYACE_SERVER:-http://localhost:8000}"
SCRIPT_URL="https://raw.githubusercontent.com/niels-emmer/myace/main/scripts/bootstrap-import.sh"

# ─── Color helpers ─────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()  { printf "${GREEN}✓${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}!${NC} %s\n" "$*"; }
error() { printf "${RED}✗${NC} %s\n" "$*"; }
header(){ printf "\n${CYAN}=== %s ===${NC}\n" "$*"; }

# ─── Step 1: Check Python 3.12+ ───────────────────────────────
header "Checking Python"

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON=$(command -v "$cmd")
        break
    fi
done

if [ -z "$PYTHON" ]; then
    error "Python 3 not found."
    echo ""
    echo "  Install Python 3.12+ from:"
    echo "    https://www.python.org/downloads/"
    echo ""
    echo "  Or on macOS with Homebrew:"
    echo "    brew install python@3.12"
    echo ""
    echo "  On Ubuntu/Debian:"
    echo "    sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi

PY_VERSION=$("$PYTHON" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]; }; then
    error "Python 3.12+ required (found $PY_VERSION)"
    echo ""
    echo "  Upgrade Python to 3.12 or later:"
    echo "    https://www.python.org/downloads/"
    exit 1
fi

info "Found Python ${PY_VERSION} at ${PYTHON}"

# ─── Step 2: Create virtual environment ────────────────────────
header "Setting up virtual environment"

mkdir -p "$MYACE_DIR"

if [ -d "$VENV_DIR" ]; then
    warn "Virtual environment already exists at ${VENV_DIR}"
    warn "Activating existing environment..."
else
    info "Creating virtual environment at ${VENV_DIR}..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

# ─── Step 3: Install myace-cli ─────────────────────────────────
header "Installing myace-cli"

info "Upgrading pip..."
"$PYTHON" -m pip install --quiet --upgrade pip

info "Installing myace-cli[serve] from GitHub..."
if pip install --quiet "git+https://github.com/niels-emmer/myace.git#subdirectory=cli[serve]"; then
    info "myace-cli installed successfully"
else
    error "Failed to install myace-cli"
    echo ""
    echo "  Check that git is installed and you have internet access."
    echo "  If you're behind a proxy, set HTTP_PROXY/HTTPS_PROXY."
    exit 1
fi

# ─── Step 4: Verify installation ───────────────────────────────
header "Verifying installation"

if command -v myace &>/dev/null; then
    info "myace CLI is ready: $(myace --help 2>&1 | head -1)"
else
    warn "myace command not found in PATH after install"
    warn "You may need to activate the venv manually:"
    echo "    source ${VENV_DIR}/bin/activate"
fi

# ─── Step 5: Guide user ────────────────────────────────────────
header "Setup Complete — Next Steps"

echo ""
echo "  ${BOLD}Option A: Import via web UI (recommended for first use)${NC}"
echo ""
echo "    1. Open the MyACE web UI and create an API token:"
echo "       ${MYACE_SERVER}/settings"
echo ""
echo "    2. Activate the environment and start the companion server:"
echo "       source ${VENV_DIR}/bin/activate"
echo "       myace login --server ${MYACE_SERVER} --token <your-token>"
echo "       myace serve"
echo ""
echo "    3. Go to the Import page in your browser and scan your machine."
echo ""
echo "  ${BOLD}Option B: One-shot CLI import${NC}"
echo ""
echo "    source ${VENV_DIR}/bin/activate"
echo "    myace login --server ${MYACE_SERVER} --token <your-token>"
echo "    myace import --path ~/.config/opencode --name my-config --push"
echo ""
echo "  ${BOLD}Quick reference:${NC}"
echo ""
echo "    Activate venv later:  source ${VENV_DIR}/bin/activate"
echo "    Re-run this script:   curl -fsSL ${SCRIPT_URL} | bash"
echo ""

info "Bootstrap complete"
