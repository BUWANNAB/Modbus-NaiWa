# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all


modbus_datas, modbus_binaries, modbus_hiddenimports = collect_all("pymodbus")

a = Analysis(
    ["run_app.py"],
    pathex=["src"],
    binaries=modbus_binaries,
    datas=[("assets", "assets"), *modbus_datas],
    hiddenimports=["serial", *modbus_hiddenimports],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

filtered_binaries = [
    # These are OS API-set contracts or unrelated ICU builds found on the
    # builder's PATH; do not shadow Windows' own API-set/ICU implementations.
    binary
    for binary in a.binaries
    if not str(binary[0]).replace("\\", "/").rsplit("/", 1)[-1].lower().startswith(("api-ms-", "ext-ms-"))
    and not str(binary[0]).replace("\\", "/").rsplit("/", 1)[-1].lower().startswith("icu")
]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    filtered_binaries,
    a.datas,
    [],
    name="NaiWaModbus",
    icon="assets/mascot/app_icon.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
