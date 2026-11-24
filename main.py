#!/usr/bin/env python3
"""
YouTube Downloader Pro — Desktop Application
Author: DevSajjadAli
Repository: https://github.com/DevSajjadAli/youtube-downloader-gui
"""

import sys
import os

# ── Frozen-EXE / PyInstaller support ─────────────────────────────────────────
# When packaged by PyInstaller, __file__ is inside a temp _MEIPASS directory.
# We expose BASE_DIR so all modules can call get_base_dir() to find assets.
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller bundle
    BASE_DIR = sys._MEIPASS          # type: ignore[attr-defined]
    ROOT_DIR  = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR  = BASE_DIR

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Make BASE_DIR available globally so gui/ and core/ can import it
os.environ['_YTDL_BASE_DIR'] = BASE_DIR

# Ensure Windows terminal handles UTF-8 gracefully
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DevSajjadAli.YouTubeDownloaderPro.App.v3")
    except Exception:
        pass

def launch_gui():
    """Launch the CustomTkinter GUI interface."""
    try:
        import customtkinter as ctk
        from gui.app import YouTubeDownloaderApp

        app = YouTubeDownloaderApp()
        app.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "YouTube Downloader Pro - Startup Error",
                f"An error occurred while launching the interface:\n\n{e}\n\nFalling back to terminal CLI mode."
            )
            root.destroy()
        except Exception:
            pass
        print(f"Warning: Could not launch GUI ({e}). Falling back to Terminal CLI mode.\n")
        launch_cli()

def launch_cli():
    """Launch the interactive terminal interface."""
    from cli import main as cli_main
    cli_main()

def main():
    # If explicitly asked for CLI mode
    if "--cli" in sys.argv or "-c" in sys.argv:
        launch_cli()
    else:
        launch_gui()

if __name__ == "__main__":
    main()
