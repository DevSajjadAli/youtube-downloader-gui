import os
import threading
import subprocess
import urllib.request
import io
import customtkinter as ctk
from PIL import Image

from core.engine import QUALITY_PRESETS
from gui import icon_loader as icons
from gui.views.history_view import append_history
import datetime


class SingleVideoView(ctk.CTkScrollableFrame):
    """View for downloading individual YouTube videos with live preview, metadata, and icon buttons."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.engine = app.engine
        self.config = app.config

        self.current_info = None
        self.cancel_event = None
        self.is_downloading = False
        self._last_save_path = ""

        self.grid_columnconfigure(0, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        hdr_frame = ctk.CTkFrame(self, fg_color="transparent")
        hdr_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 6))
        hdr_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr_frame, text="  Single Video Download",
            image=icons.video(26), compound="left",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            hdr_frame, text="Paste any YouTube link to fetch info, choose quality and download",
            font=ctk.CTkFont(size=12), text_color="#6B7280", anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ── URL Card ────────────────────────────────────────────────────────
        url_card = ctk.CTkFrame(self, corner_radius=10)
        url_card.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        url_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(url_card, text="YouTube Video URL",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
                     ).grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(12, 4))

        inner = ctk.CTkFrame(url_card, fg_color="transparent")
        inner.grid(row=1, column=0, columnspan=4, sticky="ew", padx=15, pady=(0, 14))
        inner.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            inner, placeholder_text="https://www.youtube.com/watch?v=...",
            height=40, font=ctk.CTkFont(size=13)
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self.on_fetch_info())

        ctk.CTkButton(
            inner, text="Paste", image=icons.paste(16), compound="left",
            width=82, height=40, fg_color="#374151", hover_color="#4B5563",
            command=self.paste_from_clipboard
        ).grid(row=0, column=1, padx=(0, 8))

        self.fetch_btn = ctk.CTkButton(
            inner, text="Fetch Info", image=icons.video(16), compound="left",
            width=108, height=40,
            command=self.on_fetch_info
        )
        self.fetch_btn.grid(row=0, column=2)

        # Clipboard-watch checkbox
        self.clip_watch_var = ctk.BooleanVar(value=self.config.get("clipboard_watch", False))
        ctk.CTkCheckBox(
            url_card, text="Auto-detect YouTube URLs from clipboard",
            variable=self.clip_watch_var,
            font=ctk.CTkFont(size=11),
            command=self._toggle_clip_watch
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=15, pady=(0, 10))

        # ── Preview Card ────────────────────────────────────────────────────
        self.info_card = ctk.CTkFrame(self, corner_radius=10)
        self.info_card.grid(row=2, column=0, sticky="ew", padx=20, pady=8)
        self.info_card.grid_columnconfigure(1, weight=1)

        self.thumb_label = ctk.CTkLabel(
            self.info_card, text="No Preview",
            width=190, height=108,
            fg_color="#1F2937", corner_radius=8
        )
        self.thumb_label.grid(row=0, column=0, rowspan=5, padx=15, pady=15, sticky="n")

        self.title_label = ctk.CTkLabel(
            self.info_card, text="Enter a URL and click 'Fetch Info' to preview",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w", wraplength=540, justify="left"
        )
        self.title_label.grid(row=0, column=1, sticky="w", padx=(0, 15), pady=(15, 4))

        self.channel_label = ctk.CTkLabel(self.info_card, text="Channel: —",
                                          font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w")
        self.channel_label.grid(row=1, column=1, sticky="w", padx=(0, 15), pady=2)

        self.duration_label = ctk.CTkLabel(self.info_card, text="Duration: —  •  Views: —",
                                           font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w")
        self.duration_label.grid(row=2, column=1, sticky="w", padx=(0, 15), pady=2)

        self.like_label = ctk.CTkLabel(self.info_card, text="Likes: —  •  Upload date: —",
                                       font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w")
        self.like_label.grid(row=3, column=1, sticky="w", padx=(0, 15), pady=(2, 15))

        # ── Config Card ─────────────────────────────────────────────────────
        cfg_card = ctk.CTkFrame(self, corner_radius=10)
        cfg_card.grid(row=3, column=0, sticky="ew", padx=20, pady=8)
        cfg_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cfg_card, text="Quality & Options",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
                     ).grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(12, 6))

        # Quality
        ctk.CTkLabel(cfg_card, text="Media Quality:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=15, pady=8)

        quality_names = [f"[{k}] {v['name']}" for k, v in QUALITY_PRESETS.items()]
        default_q_key = self.config.get("default_quality", "1")
        default_q_name = f"[{default_q_key}] {QUALITY_PRESETS.get(default_q_key, QUALITY_PRESETS['1'])['name']}"

        self.quality_menu = ctk.CTkOptionMenu(cfg_card, values=quality_names, height=34, width=320)
        self.quality_menu.set(default_q_name)
        self.quality_menu.grid(row=1, column=1, sticky="w", padx=10, pady=8)

        # Save folder
        ctk.CTkLabel(cfg_card, text="Save Folder:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=0, sticky="w", padx=15, pady=8)

        dir_sub = ctk.CTkFrame(cfg_card, fg_color="transparent")
        dir_sub.grid(row=2, column=1, sticky="ew", padx=10, pady=8)
        dir_sub.grid_columnconfigure(0, weight=1)

        self.dir_entry = ctk.CTkEntry(dir_sub, height=34, font=ctk.CTkFont(size=12))
        self.dir_entry.insert(0, self.config.get("download_dir", ""))
        self.dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            dir_sub, text="Browse", image=icons.folder(15), compound="left",
            width=90, height=34, fg_color="#374151", hover_color="#4B5563",
            command=self.browse_folder
        ).grid(row=0, column=1)

        # Toggles row
        toggle_frame = ctk.CTkFrame(cfg_card, fg_color="transparent")
        toggle_frame.grid(row=3, column=0, columnspan=3, sticky="w", padx=15, pady=(4, 14))

        self.subs_var = ctk.BooleanVar(value=self.config.get("download_subtitles", False))
        ctk.CTkCheckBox(toggle_frame, text="Download subtitles / captions",
                        variable=self.subs_var, font=ctk.CTkFont(size=12),
                        command=lambda: self.config.set("download_subtitles", self.subs_var.get())
                        ).pack(side="left", padx=(0, 20))

        self.thumb_dl_var = ctk.BooleanVar(value=self.config.get("embed_thumbnail", False))
        ctk.CTkCheckBox(toggle_frame, text="Embed thumbnail in file",
                        variable=self.thumb_dl_var, font=ctk.CTkFont(size=12),
                        command=lambda: self.config.set("embed_thumbnail", self.thumb_dl_var.get())
                        ).pack(side="left")

        # ── Action Buttons ───────────────────────────────────────────────────
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=20, pady=8)
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        actions.grid_columnconfigure(2, weight=0)

        self.download_btn = ctk.CTkButton(
            actions, text="  Download Now",
            image=icons.download(18), compound="left",
            font=ctk.CTkFont(size=14, weight="bold"), height=46,
            fg_color="#1D4ED8", hover_color="#1E40AF",
            command=self.start_download
        )
        self.download_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.queue_btn = ctk.CTkButton(
            actions, text="  Add to Queue",
            image=icons.queue(18), compound="left",
            font=ctk.CTkFont(size=14, weight="bold"), height=46,
            fg_color="#065F46", hover_color="#064E3B",
            command=self.add_to_queue
        )
        self.queue_btn.grid(row=0, column=1, sticky="ew", padx=(8, 8))

        self.open_folder_btn = ctk.CTkButton(
            actions, text="  Open Folder",
            image=icons.folder(16), compound="left",
            font=ctk.CTkFont(size=13), height=46, width=130,
            fg_color="#374151", hover_color="#4B5563",
            command=self.open_save_folder
        )
        self.open_folder_btn.grid(row=0, column=2, sticky="e")

        # ── Progress Card ────────────────────────────────────────────────────
        prog_card = ctk.CTkFrame(self, corner_radius=10)
        prog_card.grid(row=5, column=0, sticky="ew", padx=20, pady=(8, 22))
        prog_card.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(prog_card, text="Ready",
                                         font=ctk.CTkFont(size=13), anchor="w")
        self.status_label.grid(row=0, column=0, sticky="w", padx=15, pady=(12, 4))

        self.progress_bar = ctk.CTkProgressBar(prog_card, height=14, corner_radius=6)
        self.progress_bar.set(0.0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=15, pady=4)

        bot = ctk.CTkFrame(prog_card, fg_color="transparent")
        bot.grid(row=2, column=0, sticky="ew", padx=15, pady=(4, 14))
        bot.grid_columnconfigure(0, weight=1)

        self.stats_label = ctk.CTkLabel(
            bot, text="Speed: —  •  ETA: —  •  Size: —",
            font=ctk.CTkFont(size=12), text_color="#6B7280", anchor="w"
        )
        self.stats_label.grid(row=0, column=0, sticky="w")

        self.cancel_btn = ctk.CTkButton(
            bot, text="  Cancel",
            image=icons.cancel(14), compound="left",
            width=80, height=28,
            fg_color="#7F1D1D", hover_color="#991B1B",
            command=self.cancel_download, state="disabled"
        )
        self.cancel_btn.grid(row=0, column=1, sticky="e")

        # Start clipboard watcher if enabled
        self._clip_prev = ""
        if self.clip_watch_var.get():
            self._start_clip_watch()

    # ── Clipboard Watch ──────────────────────────────────────────────────────

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
            self.app.log(f"Clipboard URL detected: {url[:60]}...", "info")
            if self.config.get("auto_fetch_info", True):
                self.on_fetch_info()

    # ── UI helpers ───────────────────────────────────────────────────────────

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
        folder = os.path.dirname(path) if path and os.path.isfile(path) else path
        if folder and os.path.isdir(folder):
            subprocess.Popen(["explorer", folder])

    def get_selected_quality_key(self) -> str:
        val = self.quality_menu.get()
        if val.startswith("[") and "]" in val:
            return val[1:val.index("]")]
        return "1"

    # ── Fetch Info ───────────────────────────────────────────────────────────

    def on_fetch_info(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self.fetch_btn.configure(state="disabled", text="Fetching…")
        self.status_label.configure(text="Fetching video metadata…", text_color=("#FFFFFF","#FFFFFF"))

        def worker():
            info = self.engine.fetch_info(url)
            self.after(0, lambda: self.display_fetched_info(info))

        threading.Thread(target=worker, daemon=True).start()

    def display_fetched_info(self, info):
        self.fetch_btn.configure(state="normal", text="Fetch Info")
        if not info or info.get("error"):
            err = (info.get("error", "Could not fetch video info.") if info else "Unknown error")
            self.status_label.configure(text=f"Error: {err}", text_color="#EF4444")
            self.app.log(f"Error fetching video info: {err}", "error")
            return

        if info.get("is_playlist"):
            self.status_label.configure(
                text="ℹ This URL is a playlist — switch to the Playlists & Shows tab.",
                text_color="#F59E0B"
            )
            return

        self.current_info = info
        self.title_label.configure(text=info.get("title", "Untitled"))
        self.channel_label.configure(text=f"Channel: {info.get('uploader', 'Unknown')}")

        dur = info.get("duration", 0) or 0
        mins, secs = divmod(int(dur), 60)
        hours, mins = divmod(mins, 60)
        dur_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours else f"{mins:02d}:{secs:02d}"
        views = info.get("view_count")
        view_str = f"{views:,}" if views else "—"
        self.duration_label.configure(text=f"Duration: {dur_str}  •  Views: {view_str}")

        likes = info.get("like_count")
        like_str = f"{likes:,}" if likes else "—"
        upload = info.get("upload_date", "")
        if upload and len(upload) == 8:
            upload = f"{upload[6:8]}/{upload[4:6]}/{upload[:4]}"
        self.like_label.configure(text=f"Likes: {like_str}  •  Uploaded: {upload or '—'}")

        self.status_label.configure(text="✓ Metadata loaded successfully", text_color="#22C55E")
        self.app.log(f"Loaded: {info.get('title')}", "info")

        thumb_url = info.get("thumbnail")
        if thumb_url:
            threading.Thread(target=self.load_thumbnail, args=(thumb_url,), daemon=True).start()

    def load_thumbnail(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = r.read()
            pil_img = Image.open(io.BytesIO(data)).resize((190, 108), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(190, 108))
            self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
        except Exception as e:
            print("Thumbnail load error:", e)

    # ── Download ─────────────────────────────────────────────────────────────

    def start_download(self):
        if self.is_downloading:
            return
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Please enter a valid YouTube URL.", text_color="#EF4444")
            return

        save_dir = self.dir_entry.get().strip() or self.config.get("download_dir", "")
        q_key = self.get_selected_quality_key()
        dl_subs = self.subs_var.get()
        embed_thumb = self.thumb_dl_var.get()

        self.is_downloading = True
        self.cancel_event = threading.Event()
        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0.0)
        self.progress_bar.configure(progress_color="#3B82F6")
        self.app.set_active(True)

        def progress_cb(pct, downloaded, total, speed, eta):
            def update():
                self.progress_bar.set(pct / 100.0)
                dl_mb = downloaded / 1048576
                tot_mb = total / 1048576 if total > 0 else 0
                self.stats_label.configure(
                    text=f"Speed: {speed}  •  ETA: {eta}  •  {dl_mb:.1f} / {tot_mb:.1f} MB ({pct:.1f}%)"
                )
            self.after(0, update)

        def status_cb(msg, level="info"):
            colors = {"success": "#22C55E", "error": "#EF4444", "warning": "#F59E0B"}
            color = colors.get(level, "#F3F4F6")
            self.after(0, lambda: self.status_label.configure(text=msg, text_color=color))
            self.app.log(msg, level)

        def worker():
            extra_opts = {}
            if dl_subs:
                extra_opts["writesubtitles"] = True
                extra_opts["subtitleslangs"] = ["en", "auto"]
            if embed_thumb:
                extra_opts["writethumbnail"] = True

            success, path = self.engine.download_single(
                url, save_dir,
                quality_key=q_key,
                progress_cb=progress_cb,
                status_cb=status_cb,
                cancel_event=self.cancel_event,
                extra_opts=extra_opts
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
                self.cancel_btn.configure(state="disabled")
                self.app.set_active(False)
                if success:
                    self.progress_bar.set(1.0)
                    self.progress_bar.configure(progress_color="#22C55E")
                    self._last_save_path = path or save_dir
                else:
                    self.progress_bar.configure(progress_color="#EF4444")

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def cancel_download(self):
        if self.cancel_event:
            self.cancel_event.set()
            self.cancel_btn.configure(state="disabled")
            self.status_label.configure(text="Cancelling…", text_color="#F59E0B")

    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Please enter a valid YouTube URL first.", text_color="#EF4444")
            return
        q_key = self.get_selected_quality_key()
        save_dir = self.dir_entry.get().strip() or self.config.get("download_dir", "")
        title = self.current_info.get("title") if self.current_info else url

        self.app.queue_view.add_item({
            "type": "single",
            "url": url,
            "title": title,
            "quality_key": q_key,
            "save_dir": save_dir,
            "status": "Pending"
        })
        self.app.log(f"Added to queue: {title}", "info")
        self.status_label.configure(text="✓ Added to download queue", text_color="#22C55E")
