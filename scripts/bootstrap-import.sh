#!/usr/bin/env bash
# MyACE Import Bootstrap Script
#
# Usage:
#   export MYACE_SERVER=https://myace.macjuu.com
#   curl -fsSL https://raw.githubusercontent.com/niels-emmer/myace/main/scripts/bootstrap-import.sh | bash
#   # or if you've cloned the repo:
#   ./scripts/bootstrap-import.sh
#
# This script:
#   1. Detects your platform and downloads a pre-built binary if available
#   2. Falls back to venv+pip if no binary exists for your platform
#   3. Guides you through creating an API token and logging in
#   4. Starts the local companion server for web UI imports
#
# Environment variables:
#   MYACE_SERVER  — MyACE server URL (required)
#   MYACE_DIR     — Data directory (default: ~/.myace)
#
# This script is idempotent — safe to re-run.

set -euo pipefail

MYACE_DIR="${MYACE_DIR:-${HOME}/.myace}"
BIN_DIR="${MYACE_DIR}/bin"
VENV_DIR="${MYACE_DIR}/venv"
MYACE_SERVER="${MYACE_SERVER:-}"
SCRIPT_URL="https://raw.githubusercontent.com/niels-emmer/myace/main/scripts/bootstrap-import.sh"
GH_RELEASE="https://github.com/niels-emmer/myace/releases/latest/download"

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

# ─── Step 1: Check MyACE server URL ────────────────────────────
header "MyACE Server"

if [ -z "$MYACE_SERVER" ]; then
    error "MYACE_SERVER is not set."
    echo ""
    echo "  This script needs your MyACE server URL. Set it before running:"
    echo ""
    echo "    export MYACE_SERVER=https://myace.macjuu.com"
    echo "    curl -fsSL ${SCRIPT_URL} | bash"
    echo ""
    echo "  Or as a one-liner:"
    echo "    export MYACE_SERVER=https://myace.macjuu.com; curl -fsSL ${SCRIPT_URL} | bash"
    exit 1
fi

info "Using server: ${MYACE_SERVER}"

# ─── Step 2: Detect platform and try binary download ───────────
header "Downloading myace binary"

mkdir -p "$BIN_DIR"

OS="$(uname -s)"
ARCH="$(uname -m)"
BINARY_NAME=""
MYACE_BIN="${BIN_DIR}/myace"

case "${OS}" in
    Linux)
        case "${ARCH}" in
            x86_64|amd64) BINARY_NAME="myace-linux-x86_64" ;;
            *) warn "Unsupported Linux architecture: ${ARCH}" ;;
        esac
        ;;
    Darwin)
        case "${ARCH}" in
            x86_64)  BINARY_NAME="myace-macos-x86_64" ;;
            arm64)   BINARY_NAME="myace-macos-arm64" ;;
            *)       warn "Unsupported macOS architecture: ${ARCH}" ;;
        esac
        ;;
    *)
        warn "Unsupported OS: ${OS}" ;;
esac

BINARY_DOWNLOADED=false

if [ -n "$BINARY_NAME" ]; then
    DOWNLOAD_URL="${GH_RELEASE}/${BINARY_NAME}"
    info "Downloading ${BINARY_NAME}..."
    if curl -fsSL "$DOWNLOAD_URL" -o "$MYACE_BIN" 2>/dev/null; then
        chmod +x "$MYACE_BIN"
        info "Binary downloaded to ${MYACE_BIN}"
        BINARY_DOWNLOADED=true
    else
        warn "Binary download failed (no release yet?). Falling back to pip install."
    fi
else
    warn "No pre-built binary for ${OS}/${ARCH}. Falling back to pip install."
fi

# ─── Step 3: Fall back to venv+pip if binary not available ─────
if [ "$BINARY_DOWNLOADED" = false ]; then
    header "Setting up Python virtual environment"

    # Check Python 3.12+
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

    PY_VERSION=$("$PYTHON" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
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

    if [ -d "$VENV_DIR" ]; then
        warn "Virtual environment already exists at ${VENV_DIR}"
    else
        info "Creating virtual environment at ${VENV_DIR}..."
        "$PYTHON" -m venv "$VENV_DIR"
    fi

    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"

    info "Upgrading pip..."
    python -m pip install --quiet --upgrade pip

    info "Installing myace-cli[serve] from GitHub..."
    if python -m pip install --quiet "myace-cli[serve] @ git+https://github.com/niels-emmer/myace.git#subdirectory=cli"; then
        info "myace-cli installed successfully"
        MYACE_BIN="myace"
    else
        error "Failed to install myace-cli"
        echo ""
        echo "  Check that git is installed and you have internet access."
        echo "  If you're behind a proxy, set HTTP_PROXY/HTTPS_PROXY."
        exit 1
    fi
fi

# ─── Step 4: Verify installation ───────────────────────────────
header "Verifying installation"

if [ "$BINARY_DOWNLOADED" = true ]; then
    # Binary was downloaded — add to PATH for this session
    export PATH="${BIN_DIR}:${PATH}"
    info "myace CLI is ready: $("${MYACE_BIN}" --help 2>&1 | head -1)"
else
    if command -v myace &>/dev/null; then
        info "myace CLI is ready: $(myace --help 2>&1 | head -1)"
    else
        warn "myace command not found in PATH after install"
        warn "You may need to activate the venv manually:"
        echo "    source ${VENV_DIR}/bin/activate"
    fi
fi

# ─── Step 5: Guide user ────────────────────────────────────────
header "Setup Complete — Next Steps"

echo ""
echo "  ${BOLD}To connect to your MyACE server:${NC}"
echo ""
echo "    1. Open the MyACE web UI and create an API token:"
echo "       ${MYACE_SERVER}/settings"
echo ""
echo "    2. Log in (you'll be prompted for the server URL and token):"
echo "       ${MYACE_BIN} login"
echo ""
echo "    3. Start the local companion server:"
echo "       ${MYACE_BIN} serve"
echo ""
echo "    4. Go to the Import page in your browser and scan your machine."
echo ""

if [ "$BINARY_DOWNLOADED" = true ]; then
    echo "  ${BOLD}Binary install:${NC}"
    echo ""
    echo "    ${MYACE_BIN} is at ${MYACE_BIN}"
    echo "    Add it to your PATH:  export PATH=\"${BIN_DIR}:\$PATH\""
    echo "    Or symlink it:        sudo ln -sf ${MYACE_BIN} /usr/local/bin/myace"
    echo ""
else
    echo "  ${BOLD}Quick reference:${NC}"
    echo ""
    echo "    Activate venv later:  source ${VENV_DIR}/bin/activate"
    echo ""
fi

echo "  ${BOLD}Re-run this script:${NC}"
echo "    export MYACE_SERVER=${MYACE_SERVER}; curl -fsSL ${SCRIPT_URL} | bash"
echo ""

info "Bootstrap complete"
