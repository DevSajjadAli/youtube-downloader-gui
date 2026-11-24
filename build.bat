@echo off
:: YouTube Downloader Pro — Build Script
:: Builds a single-file .exe using PyInstaller
:: Usage: Double-click build.bat  OR  run from command prompt

cd /d "%~dp0"
title YouTube Downloader Pro — Build

echo.
echo =========================================================
echo   YouTube Downloader Pro — Build Tool
echo =========================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)
echo [OK] Python found.

:: Ensure PyInstaller is available
python -m pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    python -m pip install pyinstaller --quiet
)
echo [OK] PyInstaller ready.

:: Ensure assets/icons exist
if not exist "assets\icon.ico" (
    echo [INFO] Generating icons...
    python assets\generate_icons.py
)
echo [OK] Assets ready.

:: Clean previous build
if exist "dist\YouTubeDownloaderPro.exe" del /f /q "dist\YouTubeDownloaderPro.exe"

echo.
echo [BUILD] Compiling — please wait (this takes 1-3 minutes)...
python -m pyinstaller YouTubeDownloaderPro.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check output above for details.
    pause
    exit /b 1
)

echo.
if exist "dist\YouTubeDownloaderPro.exe" (
    echo =========================================================
    echo   BUILD SUCCESSFUL!
    echo =========================================================
    echo.
    echo   Output: dist\YouTubeDownloaderPro.exe
    for %%F in ("dist\YouTubeDownloaderPro.exe") do echo   Size:   %%~zF bytes
    echo.
    echo   You can now distribute dist\YouTubeDownloaderPro.exe
    echo   Users just double-click to run — no Python needed!
    echo.
    explorer dist
) else (
    echo [ERROR] EXE not found after build.
)

pause
