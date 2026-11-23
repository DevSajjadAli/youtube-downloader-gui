#!/usr/bin/env python3
"""
YouTube Downloader Pro — Desktop Application
Author: DevSajjadAli
Repository: https://github.com/DevSajjadAli/youtube-downloader-gui
"""

import sys
import os

# Ensure project root is at the head of sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Ensure Windows terminal handles UTF-8 gracefully
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DevSajjadAli.YouTubeDownloaderPro.Desktop.v2")
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
