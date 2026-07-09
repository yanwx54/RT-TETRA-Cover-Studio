# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


PROJECT_DIR = Path(SPECPATH).parent

datas = [
    (str(PROJECT_DIR / "config"), "config"),
    (str(PROJECT_DIR / "examples"), "examples"),
]

hiddenimports = collect_submodules("matplotlib.backends")

a = Analysis(
    [str(PROJECT_DIR / "scripts" / "run_gui.py")],
    pathex=[str(PROJECT_DIR / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(PROJECT_DIR / "packaging" / "hooks" / "rt_tetra_runtime.py")],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RT-TETRA-Cover-Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="RT-TETRA-Cover-Studio",
)
