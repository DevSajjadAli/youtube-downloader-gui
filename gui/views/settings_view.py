import os
import subprocess
import threading
import customtkinter as ctk

from core.ffmpeg_utils import is_ffmpeg_available, get_ffmpeg_version
from core.engine import QUALITY_PRESETS
from gui import icon_loader as icons


class SettingsView(ctk.CTkScrollableFrame):
    """View for adjusting preferences, speed limits, appearance, and FFmpeg diagnostics."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.config = app.config

        self.grid_columnconfigure(0, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        hdr_f = ctk.CTkFrame(self, fg_color="transparent")
        hdr_f.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 6))
        hdr_f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr_f, text="  Settings & Preferences",
            image=icons.settings(26), compound="left",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            hdr_f, text="Configure download defaults, appearance, speed limits, and FFmpeg",
            font=ctk.CTkFont(size=12), text_color="#6B7280", anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ── Downloads Card ───────────────────────────────────────────────────
        dl_card = ctk.CTkFrame(self, corner_radius=10)
        dl_card.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        dl_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dl_card, text="  Download Locations & Defaults",
                     image=icons.folder(16), compound="left",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(14, 8))

        # Default folder
        ctk.CTkLabel(dl_card, text="Default Save Directory:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=15, pady=6)

        sub = ctk.CTkFrame(dl_card, fg_color="transparent")
        sub.grid(row=1, column=1, sticky="ew", padx=10, pady=6)
        sub.grid_columnconfigure(0, weight=1)

        self.dir_entry = ctk.CTkEntry(sub, height=34)
        self.dir_entry.insert(0, self.config.get("download_dir", ""))
        self.dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            sub, text="Browse", image=icons.folder(15), compound="left",
            width=90, height=34, fg_color="#374151", hover_color="#4B5563",
            command=self.browse_dir
        ).grid(row=0, column=1)

        # Default quality
        ctk.CTkLabel(dl_card, text="Default Quality:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=0, sticky="w", padx=15, pady=6)

        q_names = [f"[{k}] {v['name']}" for k, v in QUALITY_PRESETS.items()]
        curr_q = self.config.get("default_quality", "1")
        curr_name = f"[{curr_q}] {QUALITY_PRESETS.get(curr_q, QUALITY_PRESETS['1'])['name']}"

        self.quality_menu = ctk.CTkOptionMenu(
            dl_card, values=q_names, height=34, width=320,
            command=self.on_quality_change
        )
        self.quality_menu.set(curr_name)
        self.quality_menu.grid(row=2, column=1, sticky="w", padx=10, pady=6)

        # Custom output template
        ctk.CTkLabel(dl_card, text="Output Template:", font=ctk.CTkFont(size=12)).grid(
            row=3, column=0, sticky="w", padx=15, pady=6)

        self.template_entry = ctk.CTkEntry(
            dl_card, height=34,
            placeholder_text="%(title)s.%(ext)s  or  %(uploader)s/%(title)s.%(ext)s"
        )
        self.template_entry.insert(0, self.config.get("output_template", "%(title)s.%(ext)s"))
        self.template_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=6)

        # Speed limit
        ctk.CTkLabel(dl_card, text="Download Speed Limit:", font=ctk.CTkFont(size=12)).grid(
            row=4, column=0, sticky="w", padx=15, pady=6)

        speed_sub = ctk.CTkFrame(dl_card, fg_color="transparent")
        speed_sub.grid(row=4, column=1, sticky="w", padx=10, pady=6)

        self.speed_entry = ctk.CTkEntry(speed_sub, width=100, height=34,
                                        placeholder_text="e.g. 5M")
        self.speed_entry.insert(0, self.config.get("speed_limit", ""))
        self.speed_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(speed_sub, text="Leave blank for unlimited  (e.g. 2M, 500K)",
                     font=ctk.CTkFont(size=11), text_color="#6B7280").pack(side="left")

        # Toggles
        toggle_row = ctk.CTkFrame(dl_card, fg_color="transparent")
        toggle_row.grid(row=5, column=0, columnspan=2, sticky="w", padx=15, pady=(4, 14))

        self.auto_fetch_var = ctk.BooleanVar(value=self.config.get("auto_fetch_info", True))
        ctk.CTkCheckBox(toggle_row, text="Auto-fetch info on paste",
                        variable=self.auto_fetch_var,
                        command=lambda: self.config.set("auto_fetch_info", self.auto_fetch_var.get())
                        ).pack(side="left", padx=(0, 20))

        self.clip_watch_var = ctk.BooleanVar(value=self.config.get("clipboard_watch", False))
        ctk.CTkCheckBox(toggle_row, text="Clipboard URL auto-detect",
                        variable=self.clip_watch_var,
                        command=lambda: self.config.set("clipboard_watch", self.clip_watch_var.get())
                        ).pack(side="left", padx=(0, 20))

        # Save button
        ctk.CTkButton(
            dl_card, text="  Save Changes", image=icons.check(15), compound="left",
            height=36, command=self.save_dl_settings
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 14))

        # ── Appearance Card ───────────────────────────────────────────────────
        app_card = ctk.CTkFrame(self, corner_radius=10)
        app_card.grid(row=2, column=0, sticky="ew", padx=20, pady=8)
        app_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(app_card, text="  Theme & Appearance",
                     image=icons.settings(16), compound="left",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(14, 8))

        ctk.CTkLabel(app_card, text="Interface Mode:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=15, pady=6)

        self.mode_menu = ctk.CTkOptionMenu(
            app_card, values=["Dark", "Light", "System"],
            height=34, width=180, command=self.on_mode_change
        )
        self.mode_menu.set(self.config.get("appearance_mode", "Dark"))
        self.mode_menu.grid(row=1, column=1, sticky="w", padx=10, pady=6)

        ctk.CTkLabel(app_card, text="Accent Color:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=0, sticky="w", padx=15, pady=(6, 14))

        self.theme_menu = ctk.CTkOptionMenu(
            app_card, values=["blue", "green", "dark-blue"],
            height=34, width=180, command=self.on_theme_change
        )
        self.theme_menu.set(self.config.get("color_theme", "blue"))
        self.theme_menu.grid(row=2, column=1, sticky="w", padx=10, pady=(6, 14))

        # ── FFmpeg Card ───────────────────────────────────────────────────────
        ff_card = ctk.CTkFrame(self, corner_radius=10)
        ff_card.grid(row=3, column=0, sticky="ew", padx=20, pady=8)
        ff_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ff_card, text="  FFmpeg Integration",
                     image=icons.speed(16), compound="left",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(14, 6))

        self.ff_status_label = ctk.CTkLabel(ff_card, text="Checking FFmpeg…",
                                            font=ctk.CTkFont(size=12), anchor="w")
        self.ff_status_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=15, pady=4)

        ff_btns = ctk.CTkFrame(ff_card, fg_color="transparent")
        ff_btns.grid(row=2, column=0, columnspan=2, sticky="w", padx=15, pady=(6, 14))

        ctk.CTkButton(ff_btns, text="🔄 Re-check FFmpeg", height=34, command=self.check_ffmpeg
                      ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(ff_btns, text="📦 Install via winget", height=34,
                      fg_color="#374151", hover_color="#4B5563",
                      command=self.install_ffmpeg_winget
                      ).pack(side="left")

        # ── About Card ────────────────────────────────────────────────────────
        about_card = ctk.CTkFrame(self, corner_radius=10)
        about_card.grid(row=4, column=0, sticky="ew", padx=20, pady=(8, 22))

        ctk.CTkLabel(
            about_card, text="YouTube Downloader Pro  v2.1.0",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(14, 4))

        ctk.CTkLabel(
            about_card,
            text=(
                "• 4K / 2K / 1080p Full HD  •  MP3 / MP4 / WebM formats\n"
                "• Full playlist & TV show management  •  Episode range & skip filters\n"
                "• Batch download queue  •  Download history  •  Clipboard watch\n"
                "• Subtitle download  •  Thumbnail embedding  •  Speed limit control\n"
                "• Auto-resume  •  Custom output templates\n\n"
                "Built with Python · CustomTkinter · yt-dlp · Pillow · FFmpeg\n"
                "GitHub: github.com/DevSajjadAli/youtube-downloader-gui"
            ),
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF",
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 14))

        self.check_ffmpeg()

    # ── Handlers ─────────────────────────────────────────────────────────────

    def browse_dir(self):
        folder = ctk.filedialog.askdirectory(initialdir=self.dir_entry.get())
        if folder:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, folder)
            self.config.set("download_dir", folder)
            # Sync to other views
            for view in [self.app.single_view, self.app.playlist_view]:
                view.dir_entry.delete(0, "end")
                view.dir_entry.insert(0, folder)

    def save_dl_settings(self):
        self.config.set("download_dir", self.dir_entry.get().strip())
        self.config.set("output_template", self.template_entry.get().strip() or "%(title)s.%(ext)s")
        spd = self.speed_entry.get().strip()
        self.config.set("speed_limit", spd)
        self.app.log("Settings saved.", "success")

    def on_quality_change(self, value):
        if value.startswith("[") and "]" in value:
            self.config.set("default_quality", value[1:value.index("]")])

    def on_mode_change(self, mode):
        ctk.set_appearance_mode(mode)
        self.config.set("appearance_mode", mode)

    def on_theme_change(self, theme):
        self.config.set("color_theme", theme)
        self.app.log("Accent color saved. Restart app to apply fully.", "info")

    def check_ffmpeg(self):
        self.app.engine.refresh_ffmpeg()
        if is_ffmpeg_available():
            ver = get_ffmpeg_version()
            self.ff_status_label.configure(
                text=f"✓ FFmpeg is installed & operational — {ver}",
                text_color="#22C55E"
            )
        else:
            self.ff_status_label.configure(
                text="✗ FFmpeg not detected. High-quality downloads require FFmpeg for format merging.",
                text_color="#F59E0B"
            )

    def install_ffmpeg_winget(self):
        self.ff_status_label.configure(text="Running winget install…", text_color="#93C5FD")

        def worker():
            try:
                cmd = "winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements"
                res = subprocess.run(["powershell", "-Command", cmd],
                                     capture_output=True, text=True, timeout=120)
                if res.returncode == 0:
                    self.after(0, lambda: self.ff_status_label.configure(
                        text="✓ FFmpeg installed! Click Re-check.", text_color="#22C55E"))
                else:
                    self.after(0, lambda: self.ff_status_label.configure(
                        text="Winget done. Click Re-check FFmpeg.", text_color="#F59E0B"))
            except Exception as e:
                self.after(0, lambda: self.ff_status_label.configure(
                    text=f"Install error: {e}", text_color="#EF4444"))

        threading.Thread(target=worker, daemon=True).start()
