import os
import subprocess
import threading
import customtkinter as ctk

try:
    import winsound
except ImportError:
    winsound = None

from core.ffmpeg_utils import is_ffmpeg_available, get_ffmpeg_version
from core.engine import QUALITY_PRESETS
from core.config import DEFAULT_CONFIG
from gui import icon_loader as icons


class SettingsView(ctk.CTkScrollableFrame):
    """Futuristic settings view with speed throttle presets, sound triggers, and system diagnostics."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.config = app.config

        self.grid_columnconfigure(0, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        hdr_f = ctk.CTkFrame(self, fg_color="transparent")
        hdr_f.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        hdr_f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr_f, text="  Settings & Preferences",
            image=icons.settings(26), compound="left",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            hdr_f, text="Configure storage defaults, telemetry triggers, download speed throttling, and FFmpeg",
            font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ── Storage & Download Preferences Card ──────────────────────────────
        dl_card = ctk.CTkFrame(self, corner_radius=12)
        dl_card.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        dl_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dl_card, text="  Storage & Download Engine",
                     image=icons.folder(16), compound="left",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8))

        # Default folder
        ctk.CTkLabel(dl_card, text="Default Save Directory:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=16, pady=6)

        sub = ctk.CTkFrame(dl_card, fg_color="transparent")
        sub.grid(row=1, column=1, sticky="ew", padx=10, pady=6)
        sub.grid_columnconfigure(0, weight=1)

        self.dir_entry = ctk.CTkEntry(sub, height=36, corner_radius=6)
        self.dir_entry.insert(0, self.config.get("download_dir", ""))
        self.dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            sub, text="Browse", image=icons.folder(15), compound="left",
            width=92, height=36, fg_color="#374151", hover_color="#4B5563",
            corner_radius=6, command=self.browse_dir
        ).grid(row=0, column=1)

        # Default quality
        ctk.CTkLabel(dl_card, text="Default Media Quality:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=0, sticky="w", padx=16, pady=6)

        q_names = [f"[{k}] {v['name']}" for k, v in QUALITY_PRESETS.items()]
        curr_q = self.config.get("default_quality", "1")
        curr_name = f"[{curr_q}] {QUALITY_PRESETS.get(curr_q, QUALITY_PRESETS['1'])['name']}"

        self.quality_menu = ctk.CTkOptionMenu(
            dl_card, values=q_names, height=36, width=320, corner_radius=6,
            command=self.on_quality_change
        )
        self.quality_menu.set(curr_name)
        self.quality_menu.grid(row=2, column=1, sticky="w", padx=10, pady=6)

        # Output template
        ctk.CTkLabel(dl_card, text="Naming Template:", font=ctk.CTkFont(size=12)).grid(
            row=3, column=0, sticky="w", padx=16, pady=6)

        self.template_entry = ctk.CTkEntry(
            dl_card, height=36, corner_radius=6,
            placeholder_text="%(title)s.%(ext)s  or  %(uploader)s/%(title)s.%(ext)s"
        )
        self.template_entry.insert(0, self.config.get("output_template", "%(title)s.%(ext)s"))
        self.template_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=6)

        # Speed limit & quick presets
        ctk.CTkLabel(dl_card, text="Speed Throttle:", font=ctk.CTkFont(size=12)).grid(
            row=4, column=0, sticky="w", padx=16, pady=6)

        speed_sub = ctk.CTkFrame(dl_card, fg_color="transparent")
        speed_sub.grid(row=4, column=1, sticky="w", padx=10, pady=6)

        self.speed_entry = ctk.CTkEntry(speed_sub, width=105, height=36, corner_radius=6,
                                        placeholder_text="Unlimited")
        self.speed_entry.insert(0, self.config.get("speed_limit", ""))
        self.speed_entry.pack(side="left", padx=(0, 10))

        # Preset pills
        for preset_val, preset_label in [("", "Unlimited"), ("1M", "1 MB/s"), ("2M", "2 MB/s"), ("5M", "5 MB/s")]:
            ctk.CTkButton(
                speed_sub, text=preset_label, width=72, height=30, corner_radius=4,
                fg_color="#374151", hover_color="#4B5563",
                command=lambda v=preset_val: self._set_speed_preset(v)
            ).pack(side="left", padx=2)

        # Save Button
        ctk.CTkButton(
            dl_card, text="  Save Engine Changes", image=icons.check(15), compound="left",
            height=36, corner_radius=6, command=self.save_dl_settings
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 16))

        # ── Notifications & Automation Card ──────────────────────────────────
        auto_card = ctk.CTkFrame(self, corner_radius=12)
        auto_card.grid(row=2, column=0, sticky="ew", padx=20, pady=8)
        auto_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(auto_card, text="  Automation & Audio Signals",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8))

        # Sound toggle + Test sound
        self.sound_var = ctk.BooleanVar(value=self.config.get("sound_notify", True))
        sound_sub = ctk.CTkFrame(auto_card, fg_color="transparent")
        sound_sub.grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=4)

        ctk.CTkCheckBox(sound_sub, text="Play audio chime when download finishes",
                        variable=self.sound_var,
                        command=lambda: self.config.set("sound_notify", self.sound_var.get())
                        ).pack(side="left", padx=(0, 14))

        ctk.CTkButton(sound_sub, text="🔊 Test Chime", width=95, height=26, corner_radius=4,
                      fg_color="#374151", hover_color="#4B5563",
                      command=self._test_chime
                      ).pack(side="left")

        # Auto-open folder
        self.auto_open_var = ctk.BooleanVar(value=self.config.get("auto_open_folder", False))
        ctk.CTkCheckBox(auto_card, text="Automatically reveal download location in File Explorer on finish",
                        variable=self.auto_open_var,
                        command=lambda: self.config.set("auto_open_folder", self.auto_open_var.get())
                        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(6, 14))

        # ── Theme & Appearance Card ──────────────────────────────────────────
        app_card = ctk.CTkFrame(self, corner_radius=12)
        app_card.grid(row=3, column=0, sticky="ew", padx=20, pady=8)
        app_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(app_card, text="  Theme & Appearance",
                     image=icons.settings(16), compound="left",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8))

        ctk.CTkLabel(app_card, text="Display Mode:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=16, pady=6)

        self.mode_menu = ctk.CTkOptionMenu(
            app_card, values=["Dark", "Light", "System"],
            height=34, width=180, corner_radius=6, command=self.on_mode_change
        )
        self.mode_menu.set(self.config.get("appearance_mode", "Dark"))
        self.mode_menu.grid(row=1, column=1, sticky="w", padx=10, pady=6)

        ctk.CTkLabel(app_card, text="Accent Color Theme:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=0, sticky="w", padx=16, pady=(6, 14))

        self.theme_menu = ctk.CTkOptionMenu(
            app_card, values=["blue", "green", "dark-blue"],
            height=34, width=180, corner_radius=6, command=self.on_theme_change
        )
        self.theme_menu.set(self.config.get("color_theme", "blue"))
        self.theme_menu.grid(row=2, column=1, sticky="w", padx=10, pady=(6, 14))

        # ── FFmpeg Core Diagnostics Card ─────────────────────────────────────
        ff_card = ctk.CTkFrame(self, corner_radius=12)
        ff_card.grid(row=4, column=0, sticky="ew", padx=20, pady=8)
        ff_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ff_card, text="  FFmpeg Processing Subsystem",
                     image=icons.speed(16), compound="left",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 6))

        self.ff_status_label = ctk.CTkLabel(ff_card, text="Checking FFmpeg status...",
                                            font=ctk.CTkFont(size=12), anchor="w")
        self.ff_status_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=4)

        ff_btns = ctk.CTkFrame(ff_card, fg_color="transparent")
        ff_btns.grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(6, 14))

        ctk.CTkButton(ff_btns, text="🔄 Re-check FFmpeg", height=34, corner_radius=6, command=self.check_ffmpeg
                      ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(ff_btns, text="📦 Install via winget", height=34, corner_radius=6,
                      fg_color="#374151", hover_color="#4B5563",
                      command=self.install_ffmpeg_winget
                      ).pack(side="left")

        # ── System Tools & Actions Card ──────────────────────────────────────
        tools_card = ctk.CTkFrame(self, corner_radius=12)
        tools_card.grid(row=5, column=0, sticky="ew", padx=20, pady=(8, 22))

        ctk.CTkLabel(tools_card, text="  Maintenance & Diagnostics",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).pack(anchor="w", padx=16, pady=(14, 8))

        t_btns = ctk.CTkFrame(tools_card, fg_color="transparent")
        t_btns.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkButton(
            t_btns, text="📂 Open Downloads Folder",
            height=34, corner_radius=6, fg_color="#374151", hover_color="#4B5563",
            command=self._open_downloads_folder
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            t_btns, text="📁 Open App Data Directory",
            height=34, corner_radius=6, fg_color="#374151", hover_color="#4B5563",
            command=self._open_app_data
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            t_btns, text="⚠️ Reset to Defaults",
            height=34, corner_radius=6, fg_color="#7F1D1D", hover_color="#991B1B",
            command=self._reset_defaults
        ).pack(side="left")

        self.check_ffmpeg()

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _set_speed_preset(self, val):
        self.speed_entry.delete(0, "end")
        self.speed_entry.insert(0, val)
        self.config.set("speed_limit", val)
        self.app.log(f"Speed limit set to: {val or 'Unlimited'}", "info")

    def _test_chime(self):
        if winsound:
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass

    def _open_downloads_folder(self):
        d = self.dir_entry.get().strip() or self.config.get("download_dir", "")
        if os.path.isdir(d):
            subprocess.Popen(["explorer", d])

    def _open_app_data(self):
        app_data = os.path.join(os.path.expanduser("~"), ".ytdl_pro")
        if not os.path.isdir(app_data):
            os.makedirs(app_data, exist_ok=True)
        subprocess.Popen(["explorer", app_data])

    def _reset_defaults(self):
        for k, v in DEFAULT_CONFIG.items():
            self.config.set(k, v)
        self.dir_entry.delete(0, "end")
        self.dir_entry.insert(0, self.config.get("download_dir", ""))
        self.template_entry.delete(0, "end")
        self.template_entry.insert(0, self.config.get("output_template", "%(title)s.%(ext)s"))
        self.speed_entry.delete(0, "end")
        self.app.log("All settings restored to factory defaults.", "warning")

    def browse_dir(self):
        folder = ctk.filedialog.askdirectory(initialdir=self.dir_entry.get())
        if folder:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, folder)
            self.config.set("download_dir", folder)
            for view in [self.app.single_view, self.app.playlist_view]:
                view.dir_entry.delete(0, "end")
                view.dir_entry.insert(0, folder)

    def save_dl_settings(self):
        self.config.set("download_dir", self.dir_entry.get().strip())
        self.config.set("output_template", self.template_entry.get().strip() or "%(title)s.%(ext)s")
        spd = self.speed_entry.get().strip()
        self.config.set("speed_limit", spd)
        self.app.log("Engine configuration saved successfully.", "success")

    def on_quality_change(self, value):
        if value.startswith("[") and "]" in value:
            self.config.set("default_quality", value[1:value.index("]")])

    def on_mode_change(self, mode):
        ctk.set_appearance_mode(mode)
        self.config.set("appearance_mode", mode)

    def on_theme_change(self, theme):
        self.config.set("color_theme", theme)
        self.app.log("Accent theme saved. Restart application to re-render all elements.", "info")

    def check_ffmpeg(self):
        self.app.engine.refresh_ffmpeg()
        if is_ffmpeg_available():
            ver = get_ffmpeg_version()
            self.ff_status_label.configure(
                text=f"✓ FFmpeg operational & ready for high-definition merging — {ver}",
                text_color="#22C55E"
            )
        else:
            self.ff_status_label.configure(
                text="✗ FFmpeg not detected. 4K/1080p stream merging requires FFmpeg.",
                text_color="#F59E0B"
            )

    def install_ffmpeg_winget(self):
        self.ff_status_label.configure(text="Installing FFmpeg via winget in background...", text_color="#93C5FD")

        def worker():
            try:
                cmd = "winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements"
                res = subprocess.run(["powershell", "-Command", cmd],
                                     capture_output=True, text=True, timeout=120)
                if res.returncode == 0:
                    self.after(0, lambda: self.ff_status_label.configure(
                        text="✓ FFmpeg installed successfully! Click Re-check.", text_color="#22C55E"))
                else:
                    self.after(0, lambda: self.ff_status_label.configure(
                        text="Winget completed. Click Re-check FFmpeg.", text_color="#F59E0B"))
            except Exception as e:
                self.after(0, lambda: self.ff_status_label.configure(
                    text=f"Install error: {e}", text_color="#EF4444"))

        threading.Thread(target=worker, daemon=True).start()
