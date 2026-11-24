"""
Centralized icon loader for the YouTube Downloader Pro GUI.
Loads all icons once and provides them as CTkImage objects.
Falls back gracefully if any icon file is missing.
"""

import os
import customtkinter as ctk
from PIL import Image

_ICON_DIR = os.path.join(os.environ.get("_YTDL_BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icons")
_CACHE: dict = {}


def _load(name: str, size: int = 22) -> ctk.CTkImage | None:
    key = f"{name}@{size}"
    if key in _CACHE:
        return _CACHE[key]
    path = os.path.join(_ICON_DIR, f"{name}.png")
    if not os.path.isfile(path):
        _CACHE[key] = None
        return None
    try:
        pil = Image.open(path).resize((size, size), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(size, size))
        _CACHE[key] = img
        return img
    except Exception:
        _CACHE[key] = None
        return None


# Convenience accessors — call with optional size
def video(size=22):     return _load("icon_video",    size)
def playlist(size=22):  return _load("icon_playlist", size)
def queue(size=22):     return _load("icon_queue",    size)
def settings(size=22):  return _load("icon_settings", size)
def logs(size=22):      return _load("icon_logs",     size)
def history(size=22):   return _load("icon_history",  size)
def download(size=22):  return _load("icon_download", size)
def paste(size=22):     return _load("icon_paste",    size)
def folder(size=22):    return _load("icon_folder",   size)
def cancel(size=22):    return _load("icon_cancel",   size)
def check(size=22):     return _load("icon_check",    size)
def warning(size=22):   return _load("icon_warning",  size)
def error(size=22):     return _load("icon_error",    size)
def speed(size=22):     return _load("icon_speed",    size)
