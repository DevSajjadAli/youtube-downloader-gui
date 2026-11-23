# YouTube Downloader Pro - Windows Installer
# One-command install: irm https://raw.githubusercontent.com/DevSajjadAli/youtube-downloader-gui/main/install.ps1 | iex

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   YouTube Downloader Pro - Installer" -ForegroundColor Cyan
Write-Host "   github.com/DevSajjadAli/youtube-downloader-gui" -ForegroundColor Gray
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$InstallDir = "$env:USERPROFILE\YoutubeDownloaderGUI"
$RepoZip    = "$env:TEMP\ytdl_pro.zip"
$RepoUrl    = "https://github.com/DevSajjadAli/youtube-downloader-gui/archive/refs/heads/main.zip"
$RepoExtracted = "$env:TEMP\youtube-downloader-gui-main"

# Step 1: Check Python
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Yellow
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $v = & $cmd --version 2>&1
        if ($v -match "Python 3\.(\d+)") {
            if ([int]$matches[1] -ge 10) {
                $python = $cmd
                Write-Host "      Found: $v" -ForegroundColor Green
                break
            }
        }
    } catch {}
}

if (-not $python) {
    Write-Host ""
    Write-Host "ERROR: Python 3.10 or newer is required." -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during install." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 2: Download latest release
Write-Host "[2/5] Downloading latest release from GitHub..." -ForegroundColor Yellow
try {
    if (Test-Path $RepoZip) { Remove-Item $RepoZip -Force }
    if (Test-Path $RepoExtracted) { Remove-Item $RepoExtracted -Recurse -Force }
    Invoke-WebRequest -Uri $RepoUrl -OutFile $RepoZip -UseBasicParsing
    Expand-Archive -Path $RepoZip -DestinationPath $env:TEMP -Force
    Write-Host "      Downloaded and extracted." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to download: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Install to user directory
Write-Host "[3/5] Installing to $InstallDir ..." -ForegroundColor Yellow
if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force }
Move-Item $RepoExtracted $InstallDir
Remove-Item $RepoZip -Force -ErrorAction SilentlyContinue
Write-Host "      Files installed." -ForegroundColor Green

# Step 4: Install Python packages and generate icons
Write-Host "[4/5] Installing Python packages..." -ForegroundColor Yellow
$reqFile = Join-Path $InstallDir "requirements.txt"
& $python -m pip install --upgrade pip --quiet
& $python -m pip install -r $reqFile --quiet
Write-Host "      Packages installed." -ForegroundColor Green

Write-Host "      Generating application icons..." -ForegroundColor Yellow
$iconScript = Join-Path $InstallDir "assets\generate_icons.py"
if (Test-Path $iconScript) {
    Set-Location $InstallDir
    & $python $iconScript 2>&1 | Out-Null
    Write-Host "      Icons generated." -ForegroundColor Green
}

# Step 5: Check FFmpeg
Write-Host "[5/5] Checking FFmpeg..." -ForegroundColor Yellow
$ffmpegFound = $false
try {
    $ffv = & ffmpeg -version 2>&1 | Select-Object -First 1
    if ($ffv -match "ffmpeg") {
        $ffmpegFound = $true
        Write-Host "      FFmpeg found: $($ffv.ToString().Substring(0, [Math]::Min(60, $ffv.ToString().Length)))" -ForegroundColor Green
    }
} catch {}

if (-not $ffmpegFound) {
    Write-Host "      FFmpeg not found. Installing via winget..." -ForegroundColor Yellow
    try {
        winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements --silent 2>&1 | Out-Null
        Write-Host "      FFmpeg installed via winget." -ForegroundColor Green
    } catch {
        Write-Host "      Could not auto-install FFmpeg. Use Settings > Install via winget in the app." -ForegroundColor Yellow
    }
}

# Create shortcuts using WScript.Shell COM object
$WshShell = New-Object -comObject WScript.Shell

$pythonwPath = & $python -c "import sys, os; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))" 2>&1
if (-not (Test-Path $pythonwPath)) {
    $pythonwPath = & $python -c "import sys; print(sys.executable)" 2>&1
}

$mainScript = Join-Path $InstallDir "main.py"
$iconFile   = Join-Path $InstallDir "assets\icon.ico"

# Desktop shortcut
$DesktopPath = $WshShell.SpecialFolders("Desktop")
$DesktopLink = Join-Path $DesktopPath "YouTube Downloader Pro.lnk"
$shortcut = $WshShell.CreateShortcut($DesktopLink)
$shortcut.TargetPath       = $pythonwPath
$shortcut.Arguments        = "`"$mainScript`""
$shortcut.WorkingDirectory = $InstallDir
if (Test-Path $iconFile) { $shortcut.IconLocation = $iconFile }
$shortcut.Description      = "YouTube Downloader Pro"
$shortcut.Save()

# Start Menu shortcut
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\YouTube Downloader Pro"
if (-not (Test-Path $StartMenuDir)) { New-Item -ItemType Directory $StartMenuDir | Out-Null }
$StartLink = Join-Path $StartMenuDir "YouTube Downloader Pro.lnk"
$shortcut2 = $WshShell.CreateShortcut($StartLink)
$shortcut2.TargetPath       = $pythonwPath
$shortcut2.Arguments        = "`"$mainScript`""
$shortcut2.WorkingDirectory = $InstallDir
if (Test-Path $iconFile) { $shortcut2.IconLocation = $iconFile }
$shortcut2.Description      = "YouTube Downloader Pro"
$shortcut2.Save()

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "   Installation Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "   - Desktop shortcut created" -ForegroundColor White
Write-Host "   - Start Menu entry added" -ForegroundColor White
Write-Host "   - Installed to: $InstallDir" -ForegroundColor Gray
Write-Host ""
Write-Host "   Double-click 'YouTube Downloader Pro' on your Desktop to launch." -ForegroundColor Cyan
Write-Host ""
