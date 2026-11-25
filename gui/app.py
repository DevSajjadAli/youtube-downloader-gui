import os
import sys
import subprocess
import webbrowser
import customtkinter as ctk
from PIL import Image

try:
    from tkinterweb import HtmlFrame as _HtmlFrame
    _TKINTERWEB_OK = True
except Exception:
    _TKINTERWEB_OK = False

from core.config import ConfigManager
from core.engine import DownloadEngine
from core.ffmpeg_utils import is_ffmpeg_available
from gui import icon_loader as icons
from gui.taskbar import TaskbarProgress, set_app_user_model_id

from .views.single_view import SingleVideoView
from .views.playlist_view import PlaylistView
from .views.queue_view import QueueView
from .views.settings_view import SettingsView
from .views.log_view import LogView
from .views.history_view import HistoryView


# Accent palette
ACCENT_ACTIVE   = ("#1D4ED8", "#2563EB")   # blue-700 / blue-600
ACCENT_HOVER    = ("#1E40AF", "#1D4ED8")
BTN_TRANSPARENT = ("transparent", "transparent")
SIDEBAR_BG      = ("#1A1A2E", "#1A1A2E")


class YouTubeDownloaderApp(ctk.CTk):
    """Main Application Window — YouTube Downloader Pro."""

    def __init__(self):
        super().__init__()

        # Register Windows AppUserModelID so taskbar button shows custom icon instead of generic Python
        set_app_user_model_id("DevSajjadAli.YouTubeDownloaderPro.App.v3")

        # Core services
        self.config = ConfigManager()
        self.engine = DownloadEngine()
        self.cancel_queue_event = None

        # Appearance
        ctk.set_appearance_mode(self.config.get("appearance_mode", "Dark"))
        ctk.set_default_color_theme(self.config.get("color_theme", "blue"))

        # Window
        self.title("YouTube Downloader Pro — 4K · 1080p · Playlists · MP3")
        self.geometry("1150x740")
        self.minsize(960, 640)

        # High-res Window & Taskbar Icons
        assets_dir = os.path.join(os.environ.get("_YTDL_BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets")
        ico_file = os.path.join(assets_dir, "icon.ico")
        png_file = os.path.join(assets_dir, "icon.png")

        if os.path.isfile(ico_file):
            try:
                self.iconbitmap(ico_file)
            except Exception:
                pass

        if os.path.isfile(png_file):
            try:
                from PIL import ImageTk
                img = ImageTk.PhotoImage(file=png_file)
                self.wm_iconphoto(True, img)
                self._taskbar_icon_ref = img
            except Exception:
                pass

        # Layout: sidebar (col 0) + content (col 1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)  # status bar

        # ── Sidebar ──────────────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=255, corner_radius=0, fg_color=("#1E1E2E", "#1E1E2E"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(10, weight=1)  # spacer
        self.sidebar.grid_columnconfigure(0, weight=1)

        # Brand block
        brand_outer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_outer.grid(row=0, column=0, padx=14, pady=(22, 8), sticky="ew")

        # Logo image
        logo_path = os.path.join(assets_dir, "logo_small.png")
        if os.path.isfile(logo_path):
            try:
                pil_logo = Image.open(logo_path).resize((42, 42), Image.Resampling.LANCZOS)
                self.ctk_logo = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(42, 42))
                ctk.CTkLabel(brand_outer, image=self.ctk_logo, text="").pack(side="left", padx=(0, 10))
            except Exception:
                pass

        text_block = ctk.CTkFrame(brand_outer, fg_color="transparent")
        text_block.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(text_block, text="YouTube DL", font=ctk.CTkFont(size=19, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(text_block, text="Pro Desktop Edition", font=ctk.CTkFont(size=11),
                     text_color="#6B7280").pack(anchor="w")

        # Divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#2D2D3A").grid(
            row=1, column=0, sticky="ew", padx=10, pady=(2, 10)
        )

        # Section label
        ctk.CTkLabel(self.sidebar, text="DOWNLOADS", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#6B7280", anchor="w").grid(
            row=2, column=0, sticky="w", padx=18, pady=(0, 4)
        )

        # Nav buttons — (row, key, label, icon_fn)
        nav_items = [
            (3,  "single",   "Single Video",       icons.video),
            (4,  "playlist", "Playlists & Shows",  icons.playlist),
            (5,  "queue",    "Download Queue",      icons.queue),
            (6,  "history",  "History",             icons.history),
        ]

        ctk.CTkLabel(self.sidebar, text="TOOLS", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#6B7280", anchor="w").grid(
            row=7, column=0, sticky="w", padx=18, pady=(10, 4)
        )

        nav_items_tools = [
            (8,  "logs",     "Live Logs",           icons.logs),
            (9,  "settings", "Settings",            icons.settings),
        ]

        self.nav_buttons: dict = {}

        def _make_nav(row, key, label, icon_fn):
            ico = icon_fn(18)
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {label}",
                image=ico,
                compound="left",
                height=38,
                anchor="w",
                font=ctk.CTkFont(size=13),
                corner_radius=8,
                fg_color="transparent",
                hover_color="#2D2D40",
                text_color=("#E5E7EB", "#E5E7EB"),
                command=lambda k=key: self.select_tab(k)
            )
            btn.grid(row=row, column=0, padx=10, pady=2, sticky="ew")
            self.nav_buttons[key] = btn

        for r, k, lbl, ico_fn in nav_items:
            _make_nav(r, k, lbl, ico_fn)
        for r, k, lbl, ico_fn in nav_items_tools:
            _make_nav(r, k, lbl, ico_fn)

        # Queue badge stored separately
        self._queue_count = 0

        # Spacer row already set via grid_rowconfigure(10, weight=1)

        # ── Sidebar Ad Panel (visible on all pages) ───────────────────────────
        self._build_sidebar_ad()

        # Version label at bottom
        ctk.CTkLabel(self.sidebar, text="v2.1.0  •  yt-dlp powered",
                     font=ctk.CTkFont(size=10), text_color="#4B5563").grid(
            row=12, column=0, padx=14, pady=(0, 14), sticky="w"
        )

        # ── Content Area ─────────────────────────────────────────────────────
        self.views: dict = {}
        kw = dict(corner_radius=0, fg_color="transparent")

        self.single_view   = SingleVideoView(self, self, **kw)
        self.playlist_view = PlaylistView(self, self, **kw)
        self.queue_view    = QueueView(self, self, **kw)
        self.history_view  = HistoryView(self, self, **kw)
        self.log_view      = LogView(self, **kw)
        self.settings_view = SettingsView(self, self, **kw)

        self.views["single"]   = self.single_view
        self.views["playlist"] = self.playlist_view
        self.views["queue"]    = self.queue_view
        self.views["history"]  = self.history_view
        self.views["logs"]     = self.log_view
        self.views["settings"] = self.settings_view

        # ── Status Bar ───────────────────────────────────────────────────────
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=0,
                                       fg_color=("#111827", "#111827"))
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_bar.grid_columnconfigure(1, weight=1)
        self.status_bar.grid_propagate(False)

        ff_ok = is_ffmpeg_available()
        self.ff_indicator = ctk.CTkLabel(
            self.status_bar,
            text="● FFmpeg",
            font=ctk.CTkFont(size=11),
            text_color="#22C55E" if ff_ok else "#F59E0B"
        )
        self.ff_indicator.grid(row=0, column=0, padx=(14, 6), pady=0, sticky="w")

        self.status_text = ctk.CTkLabel(
            self.status_bar,
            text=f"Ready  •  Save: {self.config.get('download_dir', '')}",
            font=ctk.CTkFont(size=11),
            text_color="#6B7280",
            anchor="w"
        )
        self.status_text.grid(row=0, column=1, sticky="w", padx=4, pady=0)

        self.active_badge = ctk.CTkLabel(
            self.status_bar,
            text="Idle",
            font=ctk.CTkFont(size=11),
            text_color="#4B5563",
            anchor="e"
        )
        self.active_badge.grid(row=0, column=2, padx=(4, 8), pady=0, sticky="e")

        open_dl_btn = ctk.CTkButton(
            self.status_bar,
            text="📂 Downloads",
            width=85,
            height=20,
            font=ctk.CTkFont(size=10),
            corner_radius=4,
            fg_color="#1F2937",
            hover_color="#374151",
            command=self.open_downloads_folder
        )
        open_dl_btn.grid(row=0, column=3, padx=(0, 12), pady=0, sticky="e")

        # Default tab
        self.select_tab("single")

        # Initialize Windows Taskbar Download Progress Bar (Chrome-style live fill)
        # Also set custom icon via WM_SETICON & SetClassLongPtr so Python logo is replaced
        self.taskbar = None
        if sys.platform == "win32":
            self.update_idletasks()
            self._init_win32_taskbar()
            self.after(100, self._init_win32_taskbar)
            self.after(500, self._init_win32_taskbar)

    def _build_sidebar_ad(self):
        """
        Embed the full live webpage https://bidspotlight.com/ads1x1 in the sidebar.
        Strategy (best → fallback):
          1. tkinterweb HtmlFrame.load_url()  — renders actual page, no iframe wrapper needed
          2. pywebview floating WebView2 panel — Chromium engine, opens on click
          3. Styled clickable banner           — always-visible last resort
        Auto-refreshes every 5 minutes so ad content stays current.
        """
        _AD_URL = "https://bidspotlight.com/ads1x1"

        # Outer container — no extra border so the web content fills flush
        ad_outer = ctk.CTkFrame(self.sidebar, corner_radius=10,
                                fg_color="#161625", border_width=1, border_color="#2D2D3A")
        ad_outer.grid(row=11, column=0, padx=8, pady=(0, 6), sticky="ew")
        ad_outer.grid_columnconfigure(0, weight=1)

        # Thin header: "Sponsored" text + ↗ open-in-browser micro-button
        hdr = ctk.CTkFrame(ad_outer, fg_color="transparent", height=22)
        hdr.grid(row=0, column=0, sticky="ew", padx=6, pady=(5, 1))
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_propagate(False)

        ctk.CTkLabel(
            hdr, text="Sponsored",
            font=ctk.CTkFont(size=9), text_color="#374151"
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            hdr, text="↗", width=20, height=18, corner_radius=3,
            font=ctk.CTkFont(size=9), fg_color="transparent", hover_color="#1F2937",
            text_color="#4B5563",
            command=lambda: webbrowser.open(_AD_URL)
        ).grid(row=0, column=1, sticky="e")

        # ── Method 1: tkinterweb — load full URL directly (best embedded option) ──
        if _TKINTERWEB_OK:
            try:
                web = _HtmlFrame(
                    ad_outer,
                    messages_enabled=False,
                    vertical_scrollbar=False,
                    horizontal_scrollbar=False,
                )
                # ~235 px tall fits the sidebar nicely; sidebar is 255 px wide
                web.configure(height=235)
                web.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 5))

                # Load the actual URL — no iframe wrapper, renders the real page
                web.load_url(_AD_URL)

                # Auto-refresh every 5 minutes so ad content updates live
                def _auto_refresh():
                    try:
                        web.load_url(_AD_URL)
                    except Exception:
                        pass
                    # Schedule next refresh (5 min = 300 000 ms)
                    self.after(300_000, _auto_refresh)

                self.after(300_000, _auto_refresh)

                # Manual refresh button (tiny, below the ad)
                refresh_row = ctk.CTkFrame(ad_outer, fg_color="transparent")
                refresh_row.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 4))
                refresh_row.grid_columnconfigure(0, weight=1)

                ctk.CTkButton(
                    refresh_row,
                    text="⟳  Refresh Ad",
                    height=20, corner_radius=4,
                    font=ctk.CTkFont(size=9),
                    fg_color="#1F2937", hover_color="#374151",
                    text_color="#6B7280",
                    command=lambda: web.load_url(_AD_URL)
                ).grid(row=0, column=0, sticky="e")

                return   # ✅ success — full page embedded
            except Exception:
                pass  # fall through

        # ── Method 2: pywebview — Chromium WebView2 floating panel ───────────
        try:
            import webview as _webview  # pywebview

            def _open_webview_panel():
                """Open a compact always-on-top WebView2 panel next to the app."""
                import threading
                def _run():
                    win = _webview.create_window(
                        "BidSpotlight Ads",
                        _AD_URL,
                        width=320, height=350,
                        resizable=True,
                        on_top=True,
                        frameless=False,
                    )
                    _webview.start()
                threading.Thread(target=_run, daemon=True).start()

            # Show a premium-looking launch card
            launch_card = ctk.CTkFrame(ad_outer, corner_radius=8, fg_color="#0D1117", height=90)
            launch_card.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
            launch_card.grid_propagate(False)
            launch_card.grid_columnconfigure(0, weight=1)
            launch_card.grid_rowconfigure(0, weight=1)

            inner = ctk.CTkFrame(launch_card, fg_color="transparent")
            inner.place(relx=0.5, rely=0.5, anchor="center")

            ctk.CTkLabel(inner, text="🏆  BidSpotlight",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#F9FAFB").pack()
            ctk.CTkLabel(inner, text="Top 3 Live Deals",
                         font=ctk.CTkFont(size=10), text_color="#6B7280").pack(pady=(2, 8))
            ctk.CTkButton(
                inner, text="Open Ad Panel", width=140, height=28, corner_radius=6,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color="#1E3A8A", hover_color="#1D4ED8",
                command=_open_webview_panel
            ).pack()
            return  # ✅ pywebview launcher embedded

        except Exception:
            pass  # fall through to last-resort

        # ── Method 3: styled clickable fallback banner ────────────────────────
        banner = ctk.CTkButton(
            ad_outer,
            text="🏆  Top 3 Deals\nBid Spotlight — View Now",
            font=ctk.CTkFont(size=11),
            height=80, corner_radius=8,
            fg_color="#1E3A8A", hover_color="#1D4ED8",
            command=lambda: webbrowser.open(_AD_URL)
        )
        banner.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))

    def _init_win32_taskbar(self):
        """
        Properly wire up:
          1. Chrome-style ITaskbarList3 progress bar
          2. WM_SETICON & SetClassLongPtrW so Windows 11 shows the app's logo
             instead of the python.exe snake icon on both titlebar and taskbar button.
        """
        try:
            import ctypes
            user32 = ctypes.windll.user32

            tk_hwnd = self.winfo_id()
            hwnd = user32.GetParent(tk_hwnd) or tk_hwnd

            assets_dir = os.path.join(
                os.environ.get("_YTDL_BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets"
            )
            ico_file = os.path.join(assets_dir, "icon.ico")
            if os.path.isfile(ico_file):
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010

                # Big icon (shown in taskbar / Alt+Tab)
                hicon_big = user32.LoadImageW(None, ico_file, IMAGE_ICON, 256, 256, LR_LOADFROMFILE)
                if not hicon_big:
                    hicon_big = user32.LoadImageW(None, ico_file, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)

                # Small icon (shown in title bar)
                hicon_small = user32.LoadImageW(None, ico_file, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG   = 1
                GCLP_HICON   = -14
                GCLP_HICONSM = -34

                try:
                    sclp = user32.SetClassLongPtrW
                except AttributeError:
                    sclp = user32.SetClassLongW

                for target_hwnd in (hwnd, tk_hwnd):
                    if target_hwnd:
                        if hicon_big:
                            user32.SendMessageW(target_hwnd, WM_SETICON, ICON_BIG, hicon_big)
                            try:
                                sclp(target_hwnd, GCLP_HICON, hicon_big)
                            except Exception:
                                pass
                        if hicon_small:
                            user32.SendMessageW(target_hwnd, WM_SETICON, ICON_SMALL, hicon_small)
                            try:
                                sclp(target_hwnd, GCLP_HICONSM, hicon_small)
                            except Exception:
                                pass

            # ── ITaskbarList3 progress (Chrome-style green fill) ───────────────
            if not self.taskbar:
                self.taskbar = TaskbarProgress(hwnd)

        except Exception:
            self.taskbar = None

    def open_downloads_folder(self):
        d = self.config.get("download_dir", "")
        if not os.path.isdir(d):
            try:
                os.makedirs(d, exist_ok=True)
            except OSError:
                pass
        if os.path.isdir(d):
            subprocess.Popen(["explorer", d])

    def set_taskbar_progress(self, percent: float):
        """Update live taskbar progress bar (0 to 100) exactly like Google Chrome."""
        if self.taskbar:
            self.taskbar.set_progress(percent)

    def set_taskbar_indeterminate(self):
        """Show pulsing/marquee progress on taskbar icon."""
        if self.taskbar:
            self.taskbar.set_indeterminate()

    def set_taskbar_error(self):
        """Show red error indicator on taskbar icon."""
        if self.taskbar:
            self.taskbar.set_error()

    def set_taskbar_paused(self):
        """Show yellow paused indicator on taskbar icon."""
        if self.taskbar:
            self.taskbar.set_paused()

    def clear_taskbar_progress(self):
        """Clear taskbar progress bar."""
        if self.taskbar:
            self.taskbar.clear()

    def set_active(self, downloading: bool):
        if downloading:
            self.active_badge.configure(text="● Downloading...", text_color="#22C55E")
        else:
            self.active_badge.configure(text="Idle", text_color="#4B5563")
            self.clear_taskbar_progress()

    # ── Tab Navigation ───────────────────────────────────────────────────────

    def select_tab(self, tab_key: str):
        for view in self.views.values():
            view.grid_forget()

        for key, btn in self.nav_buttons.items():
            if key == tab_key:
                btn.configure(fg_color=("#1D4ED8", "#1D4ED8"), text_color=("white", "white"))
            else:
                btn.configure(fg_color="transparent", text_color=("#E5E7EB", "#E5E7EB"))

        if tab_key in self.views:
            self.views[tab_key].grid(row=0, column=1, sticky="nsew")

        # Refresh history when switching to it
        if tab_key == "history":
            self.history_view.load_entries()

    # ── Queue badge ──────────────────────────────────────────────────────────

    def update_queue_badge(self, count: int):
        self._queue_count = count
        btn = self.nav_buttons.get("queue")
        if btn:
            suffix = f"  ({count})" if count else ""
            btn.configure(text=f"  Download Queue{suffix}")

    # ── Logging ──────────────────────────────────────────────────────────────

    def log(self, message: str, level: str = "info"):
        self.log_view.append_log(message, level)
        preview = message[:72] + "..." if len(message) > 72 else message
        self.status_text.configure(text=preview)

    # ── Appearance ───────────────────────────────────────────────────────────

    def change_appearance_mode(self, mode: str):
        ctk.set_appearance_mode(mode)
        self.config.set("appearance_mode", mode)
