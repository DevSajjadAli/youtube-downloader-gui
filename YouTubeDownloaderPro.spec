# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for YouTube Downloader Pro
# Run:  pyinstaller YouTubeDownloaderPro.spec

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── Collect data files from packages that need runtime resources ──────────────
datas = []
datas += collect_data_files('customtkinter')
datas += collect_data_files('darkdetect')

# ── Add our own assets folder ─────────────────────────────────────────────────
datas += [
    ('assets', 'assets'),
]

# ── Hidden imports that PyInstaller misses ────────────────────────────────────
hiddenimports = []
hiddenimports += collect_submodules('customtkinter')
hiddenimports += collect_submodules('PIL')
hiddenimports += collect_submodules('yt_dlp')
hiddenimports += [
    'yt_dlp',
    'yt_dlp.extractor',
    'yt_dlp.postprocessor',
    'yt_dlp.utils',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageTk',
    'customtkinter',
    'darkdetect',
    'packaging',
    'imageio_ffmpeg',
    'win32com.client',
    'winsound',
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas', 'jupyter'],
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
    name='YouTubeDownloaderPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                     # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\icon.ico',           # App icon baked into EXE
    version_file=None,
    uac_admin=False,
    uac_uiaccess=False,
)
