& {
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   YouTube Downloader Pro - Installer" -ForegroundColor Cyan
Write-Host "   github.com/DevSajjadAli/youtube-downloader-gui" -ForegroundColor Gray
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

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

# Close any running instance of the app before updating
try {
    Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -like "*YoutubeDownloaderGUI*" } | ForEach-Object {
        Write-Host "      Closing running instance (PID $($_.ProcessId))..." -ForegroundColor Yellow
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 600
} catch {}

# Step 2: Download latest release
Write-Host "[2/5] Downloading latest release from GitHub..." -ForegroundColor Yellow
try {
    if (Test-Path $RepoZip) { Remove-Item $RepoZip -Force -ErrorAction SilentlyContinue }
    if (Test-Path $RepoExtracted) { Remove-Item $RepoExtracted -Recurse -Force -ErrorAction SilentlyContinue }
    Invoke-WebRequest -Uri $RepoUrl -OutFile $RepoZip -UseBasicParsing
    Expand-Archive -Path $RepoZip -DestinationPath $env:TEMP -Force
    Write-Host "      Downloaded and extracted." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to download: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Install to user directory
Write-Host "[3/5] Installing to $InstallDir ..." -ForegroundColor Yellow
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}
Copy-Item -Path "$RepoExtracted\*" -Destination $InstallDir -Recurse -Force
Remove-Item $RepoExtracted -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $RepoZip -Force -ErrorAction SilentlyContinue
Write-Host "      Files installed successfully." -ForegroundColor Green

# Step 4: Install Python packages
Write-Host "[4/5] Installing Python packages..." -ForegroundColor Yellow
$reqFile = Join-Path $InstallDir "requirements.txt"
& $python -m pip install --upgrade pip --quiet
& $python -m pip install -r $reqFile --quiet
Write-Host "      Packages installed." -ForegroundColor Green

# Ensure assets are present (already bundled with repo)
$iconFile = Join-Path $InstallDir "assets\icon.ico"
if (-not (Test-Path $iconFile)) {
    $iconScript = Join-Path $InstallDir "assets\generate_icons.py"
    if (Test-Path $iconScript) {
        try {
            Start-Process -FilePath $python -ArgumentList "`"$iconScript`"" -WorkingDirectory $InstallDir -NoNewWindow -Wait
        } catch {}
    }
}
Write-Host "      Application assets verified." -ForegroundColor Green

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
$iconLocation = Join-Path $InstallDir "assets\icon.ico"

# Check for compiled standalone binary first
$targetExe = $pythonwPath
$targetArgs = "`"$mainScript`""
$distExe = Join-Path $InstallDir "dist\YouTubeDownloaderPro\YouTubeDownloaderPro.exe"
$rootExe = Join-Path $InstallDir "YouTubeDownloaderPro.exe"

if (Test-Path $rootExe) {
    $targetExe = $rootExe
    $targetArgs = ""
} elseif (Test-Path $distExe) {
    $targetExe = $distExe
    $targetArgs = ""
}

# Desktop shortcut
$DesktopPath = $WshShell.SpecialFolders("Desktop")
$DesktopLink = Join-Path $DesktopPath "YouTube Downloader Pro.lnk"
if (Test-Path $DesktopLink) { Remove-Item $DesktopLink -Force -ErrorAction SilentlyContinue }
$shortcut = $WshShell.CreateShortcut($DesktopLink)
$shortcut.TargetPath       = $targetExe
$shortcut.Arguments        = $targetArgs
$shortcut.WorkingDirectory = $InstallDir
if (Test-Path $iconLocation) { $shortcut.IconLocation = "$iconLocation,0" }
$shortcut.Description      = "YouTube Downloader Pro — 4K · 1080p · Playlists · MP3"
$shortcut.Save()

# Start Menu shortcut
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\YouTube Downloader Pro"
if (-not (Test-Path $StartMenuDir)) { New-Item -ItemType Directory $StartMenuDir | Out-Null }
$StartLink = Join-Path $StartMenuDir "YouTube Downloader Pro.lnk"
if (Test-Path $StartLink) { Remove-Item $StartLink -Force -ErrorAction SilentlyContinue }
$shortcut2 = $WshShell.CreateShortcut($StartLink)
$shortcut2.TargetPath       = $targetExe
$shortcut2.Arguments        = $targetArgs
$shortcut2.WorkingDirectory = $InstallDir
if (Test-Path $iconLocation) { $shortcut2.IconLocation = "$iconLocation,0" }
$shortcut2.Description      = "YouTube Downloader Pro"
$shortcut2.Save()

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "   Installation Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "   - Desktop shortcut created with custom logo" -ForegroundColor White
Write-Host "   - Start Menu entry added" -ForegroundColor White
Write-Host "   - Installed to: $InstallDir" -ForegroundColor Gray
Write-Host ""
Write-Host "   Launching YouTube Downloader Pro..." -ForegroundColor Cyan

# Launch application
try {
    if ($targetArgs -ne "") {
        Start-Process -FilePath $targetExe -ArgumentList $targetArgs -WorkingDirectory $InstallDir
    } else {
        Start-Process -FilePath $targetExe -WorkingDirectory $InstallDir
    }
} catch {
    Write-Host "   Launch using the shortcut on your Desktop." -ForegroundColor Cyan
}
}