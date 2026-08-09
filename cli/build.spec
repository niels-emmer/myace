# -*- mode: python ; fill-column: 100 -*-
#
# PyInstaller build spec for myace CLI.
#
# Build with:
#   pyinstaller cli/build.spec --clean
#
# Produces a single-file executable at dist/myace (or dist/myace.exe on Windows).

import os
import platform

import PyInstaller.utils.hooks as hooks

block_cipher = None

# The spec file is executed from the cli/ directory (where the spec lives).
SPEC_DIR = "."

# ── Collect metadata for Rich and Typer ──────────────────────────
# These packages need their metadata bundled so features like
# Rich's markup and Typer's help text work correctly.
datas = []
for pkg in ("rich", "typer", "click"):
    try:
        datas += hooks.copy_metadata(pkg)
    except Exception:
        pass

a = Analysis(
    ["myace_cli/main.py"],
    pathex=[SPEC_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # ── Lazy-loaded by local_server.py ──────────────────────
        # PyInstaller's static analysis can't see imports inside
        # function bodies, so we list them explicitly.
        "fastapi",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "starlette",
        "starlette.applications",
        "starlette.middleware",
        "starlette.middleware.base",
        "starlette.responses",
        "starlette.requests",
        "starlette.routing",
        # ── Typer shell completion ──────────────────────────────
        "shellingham",
        # ── Pydantic v2 ─────────────────────────────────────────
        "pydantic",
        "pydantic.dataclasses",
        "pydantic.fields",
        "pydantic.type_adapter",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Things we definitely don't need — saves ~10 MB.
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "PIL",
        "cv2",
        "cryptography",
        "zmq",
        "jupyter",
        "notebook",
        "ipython",
        "bokeh",
        "dask",
        "distributed",
        "tornado",
        "sphinx",
        "setuptools",
        "pip",
        "wheel",
        # Test frameworks
        "pytest",
        "_pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="myace",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # ── Windows only ────────────────────────────────────────────
    icon=None,
    version=None,
)
