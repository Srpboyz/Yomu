# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['asyncio', 'dataclasses', 'difflib', 'filecmp', 'psutil', 'pydoc', 'pywintypes', 'sqlite3', 'tzdata', 'uuid', 'zoneinfo', 'bs4']
hiddenimports += collect_submodules('dateparser')
hiddenimports += collect_submodules('PyQt6')

a = Analysis(
    ['yomu/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('resources', 'resources'), ('_sources', '_sources')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['_sources'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='yomu-reader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='.',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='yomu-linux',
)
