import os
import sys
import threading
import subprocess
import urllib.request
import io
import datetime
import webbrowser
import customtkinter as ctk
from PIL import Image

try:
    import winsound
except ImportError:
    winsound = None

from core.engine import QUALITY_PRESETS, clean_single_video_url
from gui import icon_loader as icons
from gui.views.history_view import append_history


class SingleVideoView(ctk.CTkScrollableFrame):
    """Futuristic single video downloader with comprehensive stream intelligence,
    dynamic quality choices with estimated file sizes, multi-language subtitles,
    high-res thumbnail preview, channel statistics, and one-click media playback."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.engine = app.engine
        self.config = app.config

        self.current_info = None
        self.cancel_event = None
        self.is_downloading = False
        self._last_save_path = ""
        self._tag_badges = []
        self._desc_visible = False

        self.grid_columnconfigure(0, weight=1)

        # ── 1. Header ────────────────────────────────────────────────────────
        hdr_frame = ctk.CTkFrame(self, fg_color="transparent")
        hdr_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        hdr_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr_frame, text="  Single Video Downloader",
            image=icons.video(26), compound="left",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            hdr_frame,
            text="Query real-time stream intelligence, compare format file sizes, and download up to 4K Ultra HD",
            font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ── 2. URL Input Card ────────────────────────────────────────────────
        url_card = ctk.CTkFrame(self, corner_radius=12)
        url_card.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        url_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            url_card, text="YouTube Video Link",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(12, 4))

        inner = ctk.CTkFrame(url_card, fg_color="transparent")
        inner.grid(row=1, column=0, columnspan=4, sticky="ew", padx=16, pady=(0, 10))
        inner.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            inner, placeholder_text="Paste YouTube link (e.g. https://www.youtube.com/watch?v=... or Shorts)",
            height=42, font=ctk.CTkFont(size=13), corner_radius=8
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self.on_fetch_info())

        ctk.CTkButton(
            inner, text="Paste", image=icons.paste(16), compound="left",
            width=88, height=42, fg_color="#374151", hover_color="#4B5563",
            corner_radius=8, command=self.paste_from_clipboard
        ).grid(row=0, column=1, padx=(0, 6))

        self.fetch_btn = ctk.CTkButton(
            inner, text="Fetch Info", image=icons.video(16), compound="left",
            width=116, height=42, corner_radius=8,
            command=self.on_fetch_info
        )
        self.fetch_btn.grid(row=0, column=2, padx=(0, 6))

        ctk.CTkButton(
            inner, text="Clear", image=icons.cancel(14), compound="left",
            width=80, height=42, fg_color="#1F2937", hover_color="#374151",
            corner_radius=8, command=self.reset_form
        ).grid(row=0, column=3)

        # Quick toggles row
        toggles_row = ctk.CTkFrame(url_card, fg_color="transparent")
        toggles_row.grid(row=2, column=0, columnspan=4, sticky="w", padx=16, pady=(0, 12))

        self.clip_watch_var = ctk.BooleanVar(value=self.config.get("clipboard_watch", False))
        ctk.CTkCheckBox(
            toggles_row, text="Auto-detect YouTube links from clipboard",
            variable=self.clip_watch_var, font=ctk.CTkFont(size=11),
            command=self._toggle_clip_watch
        ).pack(side="left", padx=(0, 20))

        self.auto_fetch_var = ctk.BooleanVar(value=self.config.get("auto_fetch_info", True))
        ctk.CTkCheckBox(
            toggles_row, text="Auto-fetch upon paste",
            variable=self.auto_fetch_var, font=ctk.CTkFont(size=11),
            command=lambda: self.config.set("auto_fetch_info", self.auto_fetch_var.get())
        ).pack(side="left")

        # ── 3. Live Stream Intelligence Card (The Hero) ──────────────────────
        self.info_card = ctk.CTkFrame(self, corner_radius=12)
        self.info_card.grid(row=2, column=0, sticky="ew", padx=20, pady=8)
        self.info_card.grid_columnconfigure(1, weight=1)

        # High-res 16:9 Thumbnail preview box with duration badge
        thumb_container = ctk.CTkFrame(self.info_card, fg_color="transparent")
        thumb_container.grid(row=0, column=0, rowspan=6, padx=16, pady=16, sticky="nw")

        self.thumb_label = ctk.CTkLabel(
            thumb_container, text="No Preview\n(16:9)",
            width=240, height=135,
            fg_color="#181825", corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#6B7280"
        )
        self.thumb_label.pack()

        self.thumb_dur_badge = ctk.CTkLabel(
            thumb_container, text="00:00",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#000000", text_color="#FFFFFF",
            corner_radius=4, padx=6, pady=2
        )

        # Video Title and quick links
        title_box = ctk.CTkFrame(self.info_card, fg_color="transparent")
        title_box.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=(16, 4))
        title_box.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            title_box, text="Paste a link above and click 'Fetch Info' to inspect stream details",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w", wraplength=520, justify="left"
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        # Channel & subscriber row
        self.channel_label = ctk.CTkLabel(
            self.info_card, text="Channel: —",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#60A5FA", anchor="w"
        )
        self.channel_label.grid(row=1, column=1, sticky="w", padx=(0, 16), pady=2)

        # Runtime tags container for futuristic badges
        self.tags_frame = ctk.CTkFrame(self.info_card, fg_color="transparent")
        self.tags_frame.grid(row=2, column=1, sticky="w", padx=(0, 16), pady=4)

        # Stats rows
        self.stats_row_lbl = ctk.CTkLabel(
            self.info_card,
            text="Duration: —  •  Views: —  •  Likes: —  •  Uploaded: —",
            font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w"
        )
        self.stats_row_lbl.grid(row=3, column=1, sticky="w", padx=(0, 16), pady=2)

        # Quick action link bar inside card
        link_bar = ctk.CTkFrame(self.info_card, fg_color="transparent")
        link_bar.grid(row=4, column=1, sticky="w", padx=(0, 16), pady=(4, 16))

        self.copy_url_btn = ctk.CTkButton(
            link_bar, text="📋 Copy Link", width=95, height=26, corner_radius=5,
            font=ctk.CTkFont(size=11), fg_color="#374151", hover_color="#4B5563",
            command=self.copy_video_link
        )
        self.copy_url_btn.pack(side="left", padx=(0, 8))

        self.open_browser_btn = ctk.CTkButton(
            link_bar, text="🌐 View on YouTube", width=125, height=26, corner_radius=5,
            font=ctk.CTkFont(size=11), fg_color="#374151", hover_color="#4B5563",
            command=self.open_in_browser
        )
        self.open_browser_btn.pack(side="left", padx=(0, 8))

        self.desc_toggle_btn = ctk.CTkButton(
            link_bar, text="📖 Description ▼", width=120, height=26, corner_radius=5,
            font=ctk.CTkFont(size=11), fg_color="#1F2937", hover_color="#374151",
            command=self.toggle_description
        )
        self.desc_toggle_btn.pack(side="left")

        # Collapsible Description text box
        self.desc_frame = ctk.CTkFrame(self.info_card, fg_color="#181825", corner_radius=8)
        self.desc_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 16))
        self.desc_frame.grid_columnconfigure(0, weight=1)
        self.desc_frame.grid_remove()  # Hidden by default

        self.desc_textbox = ctk.CTkTextbox(
            self.desc_frame, height=130, corner_radius=6,
            font=ctk.CTkFont(size=11), fg_color="#11111B", wrap="word"
        )
        self.desc_textbox.pack(fill="x", padx=8, pady=8)

        # ── 4. Configuration Card (Dynamic Quality with Sizes) ───────────────
        cfg_card = ctk.CTkFrame(self, corner_radius=12)
        cfg_card.grid(row=3, column=0, sticky="ew", padx=20, pady=8)
        cfg_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            cfg_card, text="Quality & Target Options",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(12, 6))

        # Media Quality dropdown
        ctk.CTkLabel(cfg_card, text="Media Quality:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=16, pady=6
        )

        quality_names = [f"[{k}] {v['name']}" for k, v in QUALITY_PRESETS.items()]
        default_q_key = self.config.get("default_quality", "1")
        default_q_name = f"[{default_q_key}] {QUALITY_PRESETS.get(default_q_key, QUALITY_PRESETS['1'])['name']}"

        self.quality_menu = ctk.CTkOptionMenu(
            cfg_card, values=quality_names, height=36, width=440, corner_radius=6
        )
        self.quality_menu.set(default_q_name)
        self.quality_menu.grid(row=1, column=1, sticky="w", padx=10, pady=6)

        # Save Folder
        ctk.CTkLabel(cfg_card, text="Save Folder:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=0, sticky="w", padx=16, pady=6
        )

        dir_sub = ctk.CTkFrame(cfg_card, fg_color="transparent")
        dir_sub.grid(row=2, column=1, sticky="ew", padx=10, pady=6)
        dir_sub.grid_columnconfigure(0, weight=1)

        self.dir_entry = ctk.CTkEntry(dir_sub, height=36, font=ctk.CTkFont(size=12), corner_radius=6)
        self.dir_entry.insert(0, self.config.get("download_dir", ""))
        self.dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            dir_sub, text="Browse", image=icons.folder(15), compound="left",
            width=92, height=36, fg_color="#374151", hover_color="#4B5563",
            corner_radius=6, command=self.browse_folder
        ).grid(row=0, column=1)

        # Options checkboxes and Subtitle Language Picker
        opts_sub = ctk.CTkFrame(cfg_card, fg_color="transparent")
        opts_sub.grid(row=3, column=0, columnspan=3, sticky="w", padx=16, pady=(4, 14))

        self.subs_var = ctk.BooleanVar(value=self.config.get("download_subtitles", False))
        ctk.CTkCheckBox(
            opts_sub, text="Download subtitles:",
            variable=self.subs_var, font=ctk.CTkFont(size=12),
            command=self._on_sub_toggled
        ).pack(side="left", padx=(0, 8))

        self.sub_lang_menu = ctk.CTkOptionMenu(
            opts_sub, values=["all: All Available Languages", "en: English (Default)"],
            width=180, height=28, corner_radius=5, font=ctk.CTkFont(size=11),
            state="disabled" if not self.subs_var.get() else "normal"
        )
        self.sub_lang_menu.set("en: English (Default)")
        self.sub_lang_menu.pack(side="left", padx=(0, 20))

        self.thumb_dl_var = ctk.BooleanVar(value=self.config.get("embed_thumbnail", False))
        ctk.CTkCheckBox(
            opts_sub, text="Embed video thumbnail",
            variable=self.thumb_dl_var, font=ctk.CTkFont(size=12),
            command=lambda: self.config.set("embed_thumbnail", self.thumb_dl_var.get())
        ).pack(side="left", padx=(0, 20))

        self.embed_meta_var = ctk.BooleanVar(value=self.config.get("embed_metadata", True))
        ctk.CTkCheckBox(
            opts_sub, text="Embed chapters & metadata",
            variable=self.embed_meta_var, font=ctk.CTkFont(size=12),
            command=lambda: self.config.set("embed_metadata", self.embed_meta_var.get())
        ).pack(side="left")

        # ── 5. Action Buttons ────────────────────────────────────────────────
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=20, pady=8)
        actions.grid_columnconfigure((0, 1, 2), weight=1)
        actions.grid_columnconfigure(3, weight=0)

        self.download_btn = ctk.CTkButton(
            actions, text="  Download Video",
            image=icons.download(18), compound="left",
            font=ctk.CTkFont(size=14, weight="bold"), height=46,
            corner_radius=8, fg_color="#1D4ED8", hover_color="#1E40AF",
            command=self.start_download
        )
        self.download_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.download_mp3_btn = ctk.CTkButton(
            actions, text="  Download MP3",
            image=icons.download(18), compound="left",
            font=ctk.CTkFont(size=14, weight="bold"), height=46,
            corner_radius=8, fg_color="#047857", hover_color="#065F46",
            command=self.start_download_mp3
        )
        self.download_mp3_btn.grid(row=0, column=1, sticky="ew", padx=(6, 6))

        self.queue_btn = ctk.CTkButton(
            actions, text="  Add to Queue",
            image=icons.queue(18), compound="left",
            font=ctk.CTkFont(size=14, weight="bold"), height=46,
            corner_radius=8, fg_color="#0F766E", hover_color="#115E59",
            command=self.add_to_queue
        )
        self.queue_btn.grid(row=0, column=2, sticky="ew", padx=(6, 8))

        self.open_folder_btn = ctk.CTkButton(
            actions, text="  Open Folder",
            image=icons.folder(16), compound="left",
            font=ctk.CTkFont(size=13), height=46, width=130,
            corner_radius=8, fg_color="#374151", hover_color="#4B5563",
            command=self.open_save_folder
        )
        self.open_folder_btn.grid(row=0, column=3, sticky="e")

        # ── 6. Live Telemetry & Progress Card ────────────────────────────────
        prog_card = ctk.CTkFrame(self, corner_radius=12)
        prog_card.grid(row=5, column=0, sticky="ew", padx=20, pady=8)
        prog_card.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            prog_card, text="Ready for download",
            font=ctk.CTkFont(size=13), anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        self.progress_bar = ctk.CTkProgressBar(prog_card, height=14, corner_radius=6)
        self.progress_bar.set(0.0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=4)

        bot = ctk.CTkFrame(prog_card, fg_color="transparent")
        bot.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 12))
        bot.grid_columnconfigure(0, weight=1)

        self.stats_label = ctk.CTkLabel(
            bot, text="Speed: —  •  ETA: —  •  Progress: 0.0 MB",
            font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w"
        )
        self.stats_label.grid(row=0, column=0, sticky="w")

        self.cancel_btn = ctk.CTkButton(
            bot, text="  Cancel",
            image=icons.cancel(14), compound="left",
            width=84, height=28, corner_radius=6,
            fg_color="#7F1D1D", hover_color="#991B1B",
            command=self.cancel_download, state="disabled"
        )
        self.cancel_btn.grid(row=0, column=1, sticky="e")

        # ── 7. Completion Banner ─────────────────────────────────────────────
        self.completion_banner = ctk.CTkFrame(self, corner_radius=12, fg_color="#064E3B")
        self.completion_banner.grid(row=6, column=0, sticky="ew", padx=20, pady=(4, 20))
        self.completion_banner.grid_columnconfigure(1, weight=1)
        self.completion_banner.grid_remove()

        ctk.CTkLabel(
            self.completion_banner, text="✓ Download Finished Successfully!",
            image=icons.check(18), compound="left",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#A7F3D0"
        ).grid(row=0, column=0, padx=16, pady=12, sticky="w")

        banner_btns = ctk.CTkFrame(self.completion_banner, fg_color="transparent")
        banner_btns.grid(row=0, column=2, padx=16, pady=8, sticky="e")

        self.play_btn = ctk.CTkButton(
            banner_btns, text="▶ Play Media",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32, width=105, corner_radius=6,
            fg_color="#059669", hover_color="#047857",
            command=self.play_last_downloaded
        )
        self.play_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            banner_btns, text="📂 Open Folder",
            font=ctk.CTkFont(size=12),
            height=32, width=105, corner_radius=6,
            fg_color="#374151", hover_color="#4B5563",
            command=self.open_save_folder
        ).pack(side="left")

        # Start clipboard monitor if enabled
        self._clip_prev = ""
        if self.clip_watch_var.get():
            self._start_clip_watch()

    # ── Clipboard Watcher ────────────────────────────────────────────────────

    def _toggle_clip_watch(self):
        enabled = self.clip_watch_var.get()
        self.config.set("clipboard_watch", enabled)
        if enabled:
            self._start_clip_watch()

    def _start_clip_watch(self):
        def watch():
            while self.clip_watch_var.get():
                try:
                    text = self.clipboard_get().strip()
                    if text != self._clip_prev and ("youtube.com" in text or "youtu.be" in text):
                        self._clip_prev = text
                        self.after(0, lambda t=text: self._on_clipboard_url(t))
                except Exception:
                    pass
                import time; time.sleep(2)
        threading.Thread(target=watch, daemon=True).start()

    def _on_clipboard_url(self, url: str):
        cur = self.url_entry.get().strip()
        if cur != url:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, url)
            self.app.log(f"Clipboard link detected: {url[:60]}...", "info")
            if self.config.get("auto_fetch_info", True):
                self.on_fetch_info()

    def _on_sub_toggled(self):
        enabled = self.subs_var.get()
        self.config.set("download_subtitles", enabled)
        self.sub_lang_menu.configure(state="normal" if enabled else "disabled")

    # ── UI Actions ───────────────────────────────────────────────────────────

    def paste_from_clipboard(self):
        try:
            text = self.clipboard_get()
            if text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, text.strip())
                if self.config.get("auto_fetch_info", True):
                    self.on_fetch_info()
        except Exception:
            pass

    def browse_folder(self):
        folder = ctk.filedialog.askdirectory(initialdir=self.dir_entry.get())
        if folder:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, folder)
            self.config.set("download_dir", folder)

    def open_save_folder(self):
        path = self._last_save_path or self.dir_entry.get().strip() or self.config.get("download_dir", "")
        if path and os.path.isfile(path):
            subprocess.Popen(["explorer", "/select,", path])
        elif path and os.path.isdir(path):
            subprocess.Popen(["explorer", path])

    def play_last_downloaded(self):
        if self._last_save_path and os.path.isfile(self._last_save_path):
            try:
                os.startfile(self._last_save_path)
            except Exception as e:
                self.app.log(f"Could not launch media player: {e}", "warning")

    def copy_video_link(self):
        u = self.url_entry.get().strip()
        if u:
            self.clipboard_clear()
            self.clipboard_append(u)
            self.copy_url_btn.configure(text="✓ Copied!")
            self.after(1500, lambda: self.copy_url_btn.configure(text="📋 Copy Link"))

    def open_in_browser(self):
        u = self.url_entry.get().strip()
        if u:
            webbrowser.open(u)

    def toggle_description(self):
        if self._desc_visible:
            self.desc_frame.grid_remove()
            self.desc_toggle_btn.configure(text="📖 Description ▼")
            self._desc_visible = False
        else:
            self.desc_frame.grid()
            self.desc_toggle_btn.configure(text="📖 Description ▲")
            self._desc_visible = True

    def get_selected_quality_key(self) -> str:
        val = self.quality_menu.get()
        if val.startswith("[") and "]" in val:
            return val[1:val.index("]")]
        return "1"

    # ── Fetch Information ────────────────────────────────────────────────────

    def on_fetch_info(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self.fetch_btn.configure(state="disabled", text="Fetching…")
        self.status_label.configure(text="Querying stream intelligence & formats…", text_color="#93C5FD")
        self.completion_banner.grid_remove()

        def worker():
            # Pass force_single=True so yt-dlp extracts full single video formats even if URL contains &list=
            info = self.engine.fetch_info(url, force_single=True)
            self.after(0, lambda: self.display_fetched_info(info))

        threading.Thread(target=worker, daemon=True).start()

    def display_fetched_info(self, info):
        self.fetch_btn.configure(state="normal", text="Fetch Info")
        if not info or info.get("error"):
            err = (info.get("error", "Could not fetch video info.") if info else "Unknown error")
            self.status_label.configure(text=f"Error: {err}", text_color="#EF4444")
            self.app.log(f"Error fetching info: {err}", "error")
            return

        self.current_info = info
        self.title_label.configure(text=info.get("title", "Untitled Video"))

        # Channel & subscriber display
        uploader = info.get("uploader", "Unknown Channel")
        subs = info.get("subscribers_str", "")
        chan_text = f"Channel: {uploader}" + (f"  •  {subs}" if subs else "")
        self.channel_label.configure(text=chan_text)

        # Detailed stats row
        dur_str = info.get("duration_str", "—")
        views_str = info.get("view_count_str", "—")
        likes_str = info.get("like_count_str", "—")
        uploaded_str = info.get("upload_date_str", "—")
        dim_str = info.get("dimensions_str", "")
        stat_line = f"Duration: {dur_str}  •  {views_str}  •  {likes_str}  •  Uploaded: {uploaded_str}"
        if dim_str:
            stat_line += f"  •  {dim_str}"
        self.stats_row_lbl.configure(text=stat_line)

        # Set duration on thumbnail badge
        if dur_str and dur_str != "—":
            self.thumb_dur_badge.configure(text=dur_str)
            self.thumb_dur_badge.pack(pady=(4, 0))

        # Description box
        desc = info.get("description", "").strip()
        self.desc_textbox.delete("1.0", "end")
        if desc:
            self.desc_textbox.insert("1.0", desc)
        else:
            self.desc_textbox.insert("1.0", "No video description provided.")

        # Render futuristic resolution badges
        for b in self._tag_badges:
            try:
                b.destroy()
            except Exception:
                pass
        self._tag_badges.clear()

        badges = info.get("badges", [])
        badge_palette = [
            ("#1E3A8A", "#93C5FD"),  # Blue
            ("#065F46", "#A7F3D0"),  # Green
            ("#581C87", "#E9D5FF"),  # Purple
            ("#78350F", "#FED7AA"),  # Amber
            ("#0F766E", "#99F6E4"),  # Teal
        ]
        for idx, badge_text in enumerate(badges):
            bg, fg = badge_palette[idx % len(badge_palette)]
            lbl = ctk.CTkLabel(
                self.tags_frame, text=f"  {badge_text}  ",
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=bg, text_color=fg,
                corner_radius=4
            )
            lbl.pack(side="left", padx=(0, 6), pady=2)
            self._tag_badges.append(lbl)

        # Populate dynamic stream choices with real approximate sizes
        stream_opts = info.get("stream_options", [])
        if stream_opts:
            self.quality_menu.configure(values=stream_opts)
            # Find matching preset key or default to first
            def_key = self.config.get("default_quality", "1")
            matched = False
            for opt in stream_opts:
                if opt.startswith(f"[{def_key}]"):
                    self.quality_menu.set(opt)
                    matched = True
                    break
            if not matched and stream_opts:
                self.quality_menu.set(stream_opts[0])

        # Populate subtitles dropdown
        subs_list = info.get("subtitles_list", [])
        if subs_list:
            self.sub_lang_menu.configure(values=subs_list)
            self.sub_lang_menu.set(subs_list[1] if len(subs_list) > 1 else subs_list[0])

        self.status_label.configure(text="✓ Stream metadata & format options loaded successfully", text_color="#22C55E")
        self.app.log(f"Loaded: {info.get('title')}", "info")

        # Load crisp high-res thumbnail
        thumb_url = info.get("thumbnail")
        if thumb_url:
            threading.Thread(target=self.load_thumbnail, args=(thumb_url,), daemon=True).start()

    def load_thumbnail(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = r.read()
            pil_img = Image.open(io.BytesIO(data)).resize((240, 135), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(240, 135))
            self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
        except Exception:
            pass

    # ── Download Process ─────────────────────────────────────────────────────

    def start_download_mp3(self):
        """Fast one-click shortcut to download as MP3 audio."""
        # Find preset '6' in options
        for opt in self.quality_menu.cget("values"):
            if opt.startswith("[6]"):
                self.quality_menu.set(opt)
                break
        self.start_download()

    def start_download(self):
        if self.is_downloading:
            return
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Please enter a valid YouTube link.", text_color="#EF4444")
            return

        save_dir = self.dir_entry.get().strip() or self.config.get("download_dir", "")
        q_key = self.get_selected_quality_key()
        dl_subs = self.subs_var.get()
        embed_thumb = self.thumb_dl_var.get()
        embed_meta = self.embed_meta_var.get()
        spd_limit = self.config.get("speed_limit", "")

        # Get selected subtitle language code
        sub_choice = self.sub_lang_menu.get()
        sub_code = sub_choice.split(":")[0].strip() if ":" in sub_choice else "en"

        self.is_downloading = True
        self.cancel_event = threading.Event()
        self.download_btn.configure(state="disabled")
        self.download_mp3_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.completion_banner.grid_remove()
        self.progress_bar.set(0.0)
        self.progress_bar.configure(progress_color="#3B82F6")
        self.app.set_active(True)

        def progress_cb(pct, downloaded, total, speed, eta):
            def update():
                self.progress_bar.set(pct / 100.0)
                self.app.set_taskbar_progress(pct)
                dl_mb = downloaded / 1048576
                tot_mb = total / 1048576 if total > 0 else 0
                self.stats_label.configure(
                    text=f"Speed: {speed}  •  ETA: {eta}  •  {dl_mb:.1f} / {tot_mb:.1f} MB ({pct:.1f}%)"
                )
            self.after(0, update)

        def status_cb(msg, level="info"):
            colors = {"success": "#22C55E", "error": "#EF4444", "warning": "#F59E0B"}
            color = colors.get(level, "#F3F4F6")
            if "merging" in msg.lower() or "finalizing" in msg.lower():
                self.app.set_taskbar_indeterminate()
            self.after(0, lambda: self.status_label.configure(text=msg, text_color=color))
            self.app.log(msg, level)

        def worker():
            extra_opts = {}
            if dl_subs:
                extra_opts["writesubtitles"] = True
                if sub_code == "all":
                    extra_opts["allsubtitles"] = True
                else:
                    extra_opts["subtitleslangs"] = [sub_code, "en", "auto"]

            if embed_thumb:
                extra_opts["writethumbnail"] = True
            if embed_meta:
                extra_opts["embedchapters"] = True
                extra_opts["addmetadata"] = True

            target_clean_url = clean_single_video_url(url)
            success, path = self.engine.download_single(
                target_clean_url, save_dir,
                quality_key=q_key,
                progress_cb=progress_cb,
                status_cb=status_cb,
                cancel_event=self.cancel_event,
                extra_opts=extra_opts,
                speed_limit=spd_limit
            )

            # Record history
            title = self.current_info.get("title", url) if self.current_info else url
            append_history(self.config, {
                "title": title,
                "url": url,
                "type": "single",
                "quality": QUALITY_PRESETS.get(q_key, {}).get("name", q_key),
                "status": "success" if success else "failed",
                "path": path or "",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            })

            def finish():
                self.is_downloading = False
                self.download_btn.configure(state="normal")
                self.download_mp3_btn.configure(state="normal")
                self.cancel_btn.configure(state="disabled")
                self.app.set_active(False)

                if success:
                    self.progress_bar.set(1.0)
                    self.progress_bar.configure(progress_color="#22C55E")
                    self._last_save_path = path or save_dir
                    self.completion_banner.grid()

                    # Sound chime
                    if self.config.get("sound_notify", True) and winsound:
                        try:
                            winsound.MessageBeep(winsound.MB_OK)
                        except Exception:
                            pass

                    # Auto open folder if set
                    if self.config.get("auto_open_folder", False):
                        self.open_save_folder()
                else:
                    self.progress_bar.configure(progress_color="#EF4444")

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def reset_form(self):
        """Reset the download form fields back to pristine state."""
        self.url_entry.delete(0, "end")
        self.current_info = None
        self.title_label.configure(text="Paste a link above and click 'Fetch Info' to inspect stream details")
        self.thumb_label.configure(image=None, text="No Preview\n(16:9)")
        self.thumb_dur_badge.pack_forget()
        for b in self._tag_badges:
            try:
                b.destroy()
            except Exception:
                pass
        self._tag_badges.clear()
        self.channel_label.configure(text="Channel: —")
        self.stats_row_lbl.configure(text="Duration: —  •  Views: —  •  Likes: —  •  Uploaded: —")
        self.desc_textbox.delete("1.0", "end")
        self.desc_frame.grid_remove()
        self.desc_toggle_btn.configure(text="📖 Description ▼")
        self._desc_visible = False

        # Reset quality presets
        quality_names = [f"[{k}] {v['name']}" for k, v in QUALITY_PRESETS.items()]
        default_q_key = self.config.get("default_quality", "1")
        default_q_name = f"[{default_q_key}] {QUALITY_PRESETS.get(default_q_key, QUALITY_PRESETS['1'])['name']}"
        self.quality_menu.configure(values=quality_names)
        self.quality_menu.set(default_q_name)

        self.progress_bar.set(0.0)
        self.progress_bar.configure(progress_color="#3B82F6")
        self.stats_label.configure(text="Speed: —  •  ETA: —  •  Progress: 0.0 MB")
        self.completion_banner.grid_remove()
        self.status_label.configure(text="Ready for download", text_color="#F3F4F6")
        try:
            self.url_entry.focus_set()
        except Exception:
            pass

    def cancel_download(self):
        if self.cancel_event:
            self.cancel_event.set()
            self.cancel_btn.configure(state="disabled")
            self.status_label.configure(text="Cancelling download...", text_color="#F59E0B")
            self.app.clear_taskbar_progress()

    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Please enter a valid YouTube link first.", text_color="#EF4444")
            return
        q_key = self.get_selected_quality_key()
        save_dir = self.dir_entry.get().strip() or self.config.get("download_dir", "")
        title = self.current_info.get("title") if self.current_info else url
        uploader = self.current_info.get("uploader", "Unknown") if self.current_info else "Unknown"
        thumb = self.current_info.get("thumbnail") if self.current_info else None
        duration = self.current_info.get("duration", 0) if self.current_info else 0

        self.app.queue_view.add_item({
            "type": "single",
            "url": clean_single_video_url(url),
            "title": title,
            "uploader": uploader,
            "thumbnail": thumb,
            "duration": duration,
            "quality_key": q_key,
            "save_dir": save_dir,
            "status": "Pending"
        })
        self.app.log(f"Added to queue: {title}", "info")
        self.reset_form()
        self.status_label.configure(text=f"✓ '{title[:45]}' added to Queue! Form cleared.", text_color="#22C55E")
