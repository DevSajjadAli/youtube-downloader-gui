import os
import sys
import shutil
import subprocess

def get_ffmpeg_path():
    """Find ffmpeg binary executable path."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.isfile(path):
            return path
    except (ImportError, OSError):
        pass
    return None

def get_ffprobe_path():
    """Find ffprobe binary executable path."""
    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return system_ffprobe
    # Check next to ffmpeg
    ffmpeg_bin = get_ffmpeg_path()
    if ffmpeg_bin:
        neighbor = os.path.join(os.path.dirname(ffmpeg_bin), "ffprobe.exe")
        if os.path.isfile(neighbor):
            return neighbor
    return None

def get_ffmpeg_dir():
    """Return parent directory containing ffmpeg executable."""
    ffmpeg_bin = get_ffmpeg_path()
    if ffmpeg_bin:
        return os.path.dirname(os.path.abspath(ffmpeg_bin))
    return None

def is_ffmpeg_available():
    """Check if ffmpeg executable is reachable and operational."""
    path = get_ffmpeg_path()
    if not path:
        return False
    try:
        res = subprocess.run([path, "-version"], capture_output=True, timeout=5)
        return res.returncode == 0
    except Exception:
        return False

def get_ffmpeg_version():
    """Return version string of ffmpeg if installed."""
    path = get_ffmpeg_path()
    if not path:
        return "Not Installed"
    try:
        res = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=5)
        lines = res.stdout.splitlines()
        if lines:
            return lines[0].split("Copyright")[0].strip()
    except Exception:
        pass
    return "Detected"
