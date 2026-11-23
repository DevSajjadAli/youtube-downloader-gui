import os
import threading
import subprocess
import datetime
import customtkinter as ctk

try:
    import winsound
except ImportError:
    winsound = None

from core.engine import QUALITY_PRESETS
from core.playlist_utils import parse_episodes, sanitize_folder_name
from gui import icon_loader as icons
from gui.views.history_view import append_history


class PlaylistView(ctk.CTkScrollableFrame):
    """Futuristic view for downloading playlists and TV shows with interactive live episode checklists,
    dedicated folder auto-sanitization, custom range filters, and batch controls."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.engine = app.engine
        self.config = app.config

        self.playlist_info = None
        self.cancel_event = None
        self.is_downloading = False
        self._last_save_path = ""
        self._episode_checks = []  # List of (int_idx, BooleanVar, CheckboxWidget, title)
        self._syncing = False

        self.grid_columnconfigure(0, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        hdr_f = ctk.CTkFrame(self, fg_color="transparent")
        hdr_f.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        hdr_f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr_f, text="  Playlists & Series Downloader",
            image=icons.playlist(26), compound="left",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            hdr_f,
            text="Download entire series or playlists into dedicated named folders with episode filtering and auto-resume",
            font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ── URL Input Card ───────────────────────────────────────────────────
        url_card = ctk.CTkFrame(self, corner_radius=12)
        url_card.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        url_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(url_card, text="Playlist or Series URL",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
                     ).grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(12, 4))

        inner = ctk.CTkFrame(url_card, fg_color="transparent")
        inner.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 14))
        inner.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            inner, placeholder_text="Paste YouTube Playlist link (e.g. https://www.youtube.com/playlist?list=...)",
            height=42, font=ctk.CTkFont(size=13), corner_radius=8
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self.on_fetch_playlist())

        ctk.CTkButton(
            inner, text="Paste", image=icons.paste(16), compound="left",
            width=88, height=42, fg_color="#374151", hover_color="#4B5563",
            corner_radius=8, command=self.paste_from_clipboard
        ).grid(row=0, column=1, padx=(0, 8))

        self.fetch_btn = ctk.CTkButton(
            inner, text="Fetch Playlist", image=icons.playlist(16), compound="left",
            width=140, height=42, corner_radius=8,
            command=self.on_fetch_playlist
        )
        self.fetch_btn.grid(row=0, column=2)

        # ── Playlist Overview Card ───────────────────────────────────────────
        self.info_card = ctk.CTkFrame(self, corner_radius=12)
        self.info_card.grid(row=2, column=0, sticky="ew", padx=20, pady=8)
        self.info_card.grid_columnconfigure(0, weight=1)

        self.pl_title_label = ctk.CTkLabel(
            self.info_card, text="Paste a playlist link above to inspect all episodes in real-time",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        )
        self.pl_title_label.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        self.meta_label = ctk.CTkLabel(
            self.info_card, text="Channel: —  •  Total Episodes: —",
            font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w"
        )
        self.meta_label.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))

        # ── Destination & Format Settings Card ───────────────────────────────
        cfg_card = ctk.CTkFrame(self, corner_radius=12)
        cfg_card.grid(row=3, column=0, sticky="ew", padx=20, pady=8)
        cfg_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cfg_card, text="Dedicated Storage & File Naming",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
                     ).grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(12, 6))

        # Dedicated playlist folder
        ctk.CTkLabel(cfg_card, text="Playlist Folder:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=16, pady=6)
        self.folder_entry = ctk.CTkEntry(
            cfg_card, height=36, corner_radius=6,
            placeholder_text="Dedicated folder name (auto-filled from series title)"
        )
        self.folder_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=6)

        # Base save directory
        ctk.CTkLabel(cfg_card, text="Save In Base:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=0, sticky="w", padx=16, pady=6)

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

        # Quality Preset
        ctk.CTkLabel(cfg_card, text="Quality Preset:", font=ctk.CTkFont(size=12)).grid(
            row=3, column=0, sticky="w", padx=16, pady=6)

        quality_names = [f"[{k}] {v['name']}" for k, v in QUALITY_PRESETS.items()]
        default_q_key = self.config.get("default_quality", "1")
        default_q_name = f"[{default_q_key}] {QUALITY_PRESETS.get(default_q_key, QUALITY_PRESETS['1'])['name']}"

        self.quality_menu = ctk.CTkOptionMenu(cfg_card, values=quality_names, height=36, width=320, corner_radius=6)
        self.quality_menu.set(default_q_name)
        self.quality_menu.grid(row=3, column=1, sticky="w", padx=10, pady=6)

        # File Naming
        ctk.CTkLabel(cfg_card, text="File Naming:", font=ctk.CTkFont(size=12)).grid(
            row=4, column=0, sticky="w", padx=16, pady=(6, 14))

        self.fn_menu = ctk.CTkOptionMenu(
            cfg_card,
            values=[
                "01 - Episode Title.mp4 (Recommended)",
                "1.mp4 (Numeric only)",
                "Original Title.mp4"
            ],
            height=36, width=320, corner_radius=6
        )
        self.fn_menu.set("01 - Episode Title.mp4 (Recommended)")
        self.fn_menu.grid(row=4, column=1, sticky="w", padx=10, pady=(6, 14))

        # ── Episode Selection Controls Card ───────────────────────────────────
        ep_card = ctk.CTkFrame(self, corner_radius=12)
        ep_card.grid(row=4, column=0, sticky="ew", padx=20, pady=8)
        ep_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            ep_card, text="  Episode Range & Skip Options",
            image=icons.playlist(18), compound="left",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 6))

        self.mode_var = ctk.StringVar(value="all")

        modes = [
            ("all",    "Download ALL episodes",                        None),
            ("range",  "Download Specific Range:",                     "e.g. 5-15 or 1-10"),
            ("skip",   "SKIP Range (download all except these):",       "e.g. 1-3  (skips these episodes)"),
            ("custom", "Custom Episode List:",                         "e.g. 1, 3, 5-8, 12"),
        ]

        self._mode_entries: dict = {}
        for i, (val, label, hint) in enumerate(modes, start=1):
            rb = ctk.CTkRadioButton(ep_card, text=label, variable=self.mode_var,
                                    value=val, command=self.update_range_inputs)
            rb.grid(row=i, column=0, sticky="w", padx=16, pady=4)
            if hint:
                e = ctk.CTkEntry(ep_card, placeholder_text=hint, height=32, width=280, corner_radius=6)
                e.grid(row=i, column=1, sticky="w", padx=10, pady=4)
                e.bind("<KeyRelease>", lambda evt: self._on_range_text_changed())
                self._mode_entries[val] = e

        self.skip_existing_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            ep_card,
            text="Skip already downloaded & verified episodes (Auto-Resume)",
            variable=self.skip_existing_var,
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 12))

        self.update_range_inputs()

        # ── Interactive Episode Checklist Card (Futuristic Reveal) ────────────
        self.table_card = ctk.CTkFrame(self, corner_radius=12)
        self.table_card.grid(row=5, column=0, sticky="ew", padx=20, pady=8)
        self.table_card.grid_columnconfigure(0, weight=1)
        self.table_card.grid_remove()  # Shown when playlist is fetched

        table_header = ctk.CTkFrame(self.table_card, fg_color="transparent")
        table_header.pack(fill="x", padx=16, pady=(12, 6))
        table_header.grid_columnconfigure(0, weight=1)

        self.checklist_title = ctk.CTkLabel(
            table_header, text="  Interactive Episode Selector",
            image=icons.check(16), compound="left",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.checklist_title.pack(side="left")

        self.selected_count_badge = ctk.CTkLabel(
            table_header, text="0 / 0 Selected",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1E3A8A", text_color="#93C5FD",
            corner_radius=4, padx=8, pady=2
        )
        self.selected_count_badge.pack(side="left", padx=12)

        # Selection shortcuts
        btn_box = ctk.CTkFrame(table_header, fg_color="transparent")
        btn_box.pack(side="right")

        ctk.CTkButton(btn_box, text="Select All", width=75, height=28, corner_radius=4,
                      fg_color="#374151", hover_color="#4B5563",
                      command=lambda: self._set_all_checks(True)).pack(side="left", padx=2)
        ctk.CTkButton(btn_box, text="Deselect All", width=82, height=28, corner_radius=4,
                      fg_color="#374151", hover_color="#4B5563",
                      command=lambda: self._set_all_checks(False)).pack(side="left", padx=2)
        ctk.CTkButton(btn_box, text="Invert", width=60, height=28, corner_radius=4,
                      fg_color="#374151", hover_color="#4B5563",
                      command=self._invert_checks).pack(side="left", padx=2)

        # Scrollable checklist
        self.checklist_scroll = ctk.CTkScrollableFrame(self.table_card, height=180, corner_radius=8)
        self.checklist_scroll.pack(fill="x", padx=16, pady=(0, 12))
        self.checklist_scroll.grid_columnconfigure(1, weight=1)

        # ── Action Buttons ───────────────────────────────────────────────────
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=6, column=0, sticky="ew", padx=20, pady=8)
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        actions.grid_columnconfigure(2, weight=0)

        self.download_btn = ctk.CTkButton(
            actions, text="  Download Playlist",
            image=icons.download(18), compound="left",
            font=ctk.CTkFont(size=14, weight="bold"), height=46,
            corner_radius=8, fg_color="#1D4ED8", hover_color="#1E40AF",
            command=self.start_download
        )
        self.download_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.queue_btn = ctk.CTkButton(
            actions, text="  Add to Queue",
            image=icons.queue(18), compound="left",
            font=ctk.CTkFont(size=14, weight="bold"), height=46,
            corner_radius=8, fg_color="#065F46", hover_color="#064E3B",
            command=self.add_to_queue
        )
        self.queue_btn.grid(row=0, column=1, sticky="ew", padx=(8, 8))

        self.open_folder_btn = ctk.CTkButton(
            actions, text="  Open Folder",
            image=icons.folder(16), compound="left",
            font=ctk.CTkFont(size=13), height=46, width=130,
            corner_radius=8, fg_color="#374151", hover_color="#4B5563",
            command=self.open_save_folder
        )
        self.open_folder_btn.grid(row=0, column=2, sticky="e")

        # ── Dual Progress & Live Telemetry Card ───────────────────────────────
        prog_card = ctk.CTkFrame(self, corner_radius=12)
        prog_card.grid(row=7, column=0, sticky="ew", padx=20, pady=8)
        prog_card.grid_columnconfigure(0, weight=1)

        self.overall_label = ctk.CTkLabel(prog_card, text="Overall Progress: Ready",
                                          font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        self.overall_label.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        self.overall_bar = ctk.CTkProgressBar(prog_card, height=14, corner_radius=6)
        self.overall_bar.set(0.0)
        self.overall_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=4)

        self.current_label = ctk.CTkLabel(prog_card, text="Current Video: —",
                                          font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w")
        self.current_label.grid(row=2, column=0, sticky="w", padx=16, pady=(8, 2))

        self.video_bar = ctk.CTkProgressBar(prog_card, height=8, corner_radius=4)
        self.video_bar.set(0.0)
        self.video_bar.grid(row=3, column=0, sticky="ew", padx=16, pady=2)

        bot = ctk.CTkFrame(prog_card, fg_color="transparent")
        bot.grid(row=4, column=0, sticky="ew", padx=16, pady=(4, 12))
        bot.grid_columnconfigure(0, weight=1)

        self.stats_label = ctk.CTkLabel(bot, text="Speed: —  •  ETA: —",
                                        font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w")
        self.stats_label.grid(row=0, column=0, sticky="w")

        self.cancel_btn = ctk.CTkButton(
            bot, text="  Cancel",
            image=icons.cancel(14), compound="left",
            width=84, height=28, corner_radius=6,
            fg_color="#7F1D1D", hover_color="#991B1B",
            command=self.cancel_download, state="disabled"
        )
        self.cancel_btn.grid(row=0, column=1, sticky="e")

        # ── Completion Banner (Runtime Reveal) ───────────────────────────────
        self.completion_banner = ctk.CTkFrame(self, corner_radius=12, fg_color="#064E3B")
        self.completion_banner.grid(row=8, column=0, sticky="ew", padx=20, pady=(4, 20))
        self.completion_banner.grid_columnconfigure(1, weight=1)
        self.completion_banner.grid_remove()

        ctk.CTkLabel(
            self.completion_banner, text="✓ Playlist Completed Successfully!",
            image=icons.check(18), compound="left",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#A7F3D0"
        ).grid(row=0, column=0, padx=16, pady=12, sticky="w")

        b_btns = ctk.CTkFrame(self.completion_banner, fg_color="transparent")
        b_btns.grid(row=0, column=2, padx=16, pady=8, sticky="e")

        ctk.CTkButton(
            b_btns, text="📂 Open Playlist Folder",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32, corner_radius=6,
            fg_color="#059669", hover_color="#047857",
            command=self.open_save_folder
        ).pack(side="left")

    # ── Helpers & Events ─────────────────────────────────────────────────────

    def update_range_inputs(self):
        val = self.mode_var.get()
        for key, entry in self._mode_entries.items():
            entry.configure(state="normal" if key == val else "disabled")
        self._sync_checks_from_range()

    def _on_range_text_changed(self):
        self._sync_checks_from_range()

    def _sync_checks_from_range(self):
        if self._syncing or not self._episode_checks:
            return
        self._syncing = True
        try:
            selected_set = set(self._calc_selected_from_inputs())
            for idx, var, cb, title in self._episode_checks:
                var.set(idx in selected_set)
            self._update_selected_count_badge(len(selected_set))
        finally:
            self._syncing = False

    def _on_check_toggled(self):
        if self._syncing:
            return
        self._syncing = True
        try:
            sel_count = sum(1 for _, var, _, _ in self._episode_checks if var.get())
            self._update_selected_count_badge(sel_count)
        finally:
            self._syncing = False

    def _set_all_checks(self, state: bool):
        self._syncing = True
        try:
            for _, var, _, _ in self._episode_checks:
                var.set(state)
            self._update_selected_count_badge(len(self._episode_checks) if state else 0)
        finally:
            self._syncing = False

    def _invert_checks(self):
        self._syncing = True
        try:
            sel_count = 0
            for _, var, _, _ in self._episode_checks:
                new_val = not var.get()
                var.set(new_val)
                if new_val:
                    sel_count += 1
            self._update_selected_count_badge(sel_count)
        finally:
            self._syncing = False

    def _update_selected_count_badge(self, count):
        tot = len(self._episode_checks)
        self.selected_count_badge.configure(text=f"{count} / {tot} Selected")

    def paste_from_clipboard(self):
        try:
            text = self.clipboard_get()
            if text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, text.strip())
                self.on_fetch_playlist()
        except Exception:
            pass

    def browse_folder(self):
        folder = ctk.filedialog.askdirectory(initialdir=self.dir_entry.get())
        if folder:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, folder)
            self.config.set("download_dir", folder)

    def open_save_folder(self):
        base = self.dir_entry.get().strip() or self.config.get("download_dir", "")
        folder_name = self.folder_entry.get().strip()
        full = os.path.join(base, folder_name) if folder_name else base
        if not os.path.isdir(full):
            os.makedirs(full, exist_ok=True)
        subprocess.Popen(["explorer", full])

    def get_selected_quality_key(self):
        val = self.quality_menu.get()
        if val.startswith("[") and "]" in val:
            return val[1:val.index("]")]
        return "1"

    def get_filename_format_key(self):
        val = self.fn_menu.get()
        if "Numeric" in val:
            return "numeric"
        elif "Original" in val:
            return "title"
        return "numbered_title"

    def _calc_selected_from_inputs(self):
        total = self.playlist_info.get("count", 0) if self.playlist_info else len(self._episode_checks) or 100
        mode = self.mode_var.get()
        if mode == "range":
            return parse_episodes(self._mode_entries["range"].get().strip(), total)
        elif mode == "skip":
            skip_set = set(parse_episodes(self._mode_entries["skip"].get().strip(), total))
            return [i for i in range(1, total + 1) if i not in skip_set]
        elif mode == "custom":
            return parse_episodes(self._mode_entries["custom"].get().strip(), total)
        return list(range(1, total + 1))

    def get_episodes_to_download(self):
        # If checklist is active and populated, respect individual checkbox state
        if self._episode_checks:
            return [idx for idx, var, _, _ in self._episode_checks if var.get()]
        return self._calc_selected_from_inputs()

    # ── Fetch Information ────────────────────────────────────────────────────

    def on_fetch_playlist(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self.fetch_btn.configure(state="disabled", text="Fetching…")
        self.pl_title_label.configure(text="Querying playlist architecture & episodes…", text_color="#93C5FD")
        self.completion_banner.grid_remove()

        def worker():
            info = self.engine.fetch_info(url)
            self.after(0, lambda: self.display_playlist_info(info))

        threading.Thread(target=worker, daemon=True).start()

    def display_playlist_info(self, info):
        self.fetch_btn.configure(state="normal", text="Fetch Playlist")
        if not info or info.get("error"):
            err = info.get("error", "Failed to retrieve playlist.") if info else "Unknown error"
            self.pl_title_label.configure(text=f"Error: {err}", text_color="#EF4444")
            self.app.log(f"Error fetching playlist: {err}", "error")
            return

        self.playlist_info = info
        detected_title = info.get("title", "YouTube Playlist")
        channel = info.get("uploader", "Unknown Channel")
        count = info.get("count", 0)

        self.pl_title_label.configure(text=f"📋  {detected_title}", text_color=("#F9FAFB", "#F9FAFB"))
        self.meta_label.configure(text=f"Channel: {channel}  •  Total Videos: {count}")

        suggested = sanitize_folder_name(detected_title)
        self.folder_entry.delete(0, "end")
        self.folder_entry.insert(0, suggested)

        # Build interactive checklist
        self._build_interactive_checklist(info.get("entries", []))

        self.overall_label.configure(text=f"Ready — {count} episodes loaded into checklist.")
        self.app.log(f"Loaded playlist: {detected_title} ({count} episodes)", "info")

    def _build_interactive_checklist(self, entries):
        for w in self.checklist_scroll.winfo_children():
            w.destroy()
        self._episode_checks.clear()

        if not entries:
            self.table_card.grid_remove()
            return

        self.table_card.grid()

        for idx, entry in enumerate(entries, 1):
            title = entry.get("title") or f"Episode {idx}"
            dur = entry.get("duration", 0) or 0
            m, s = divmod(int(dur), 60)
            dur_str = f" ({m}:{s:02d})" if dur else ""

            var = ctk.BooleanVar(value=True)

            row_f = ctk.CTkFrame(self.checklist_scroll, fg_color="#1E1E2E" if idx % 2 == 0 else "#252538", corner_radius=4)
            row_f.pack(fill="x", pady=1, padx=2)
            row_f.grid_columnconfigure(1, weight=1)

            cb = ctk.CTkCheckBox(
                row_f, text=f"Ep {idx:02d}", variable=var,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=65, command=self._on_check_toggled
            )
            cb.grid(row=0, column=0, padx=(8, 4), pady=4, sticky="w")

            t_lbl = ctk.CTkLabel(
                row_f, text=f"{title}{dur_str}",
                font=ctk.CTkFont(size=11), anchor="w"
            )
            t_lbl.grid(row=0, column=1, sticky="w", padx=4, pady=4)

            self._episode_checks.append((idx, var, cb, title))

        self._update_selected_count_badge(len(entries))

    # ── Download Process ─────────────────────────────────────────────────────

    def start_download(self):
        if self.is_downloading:
            return

        url = self.url_entry.get().strip()
        if not url:
            self.overall_label.configure(text="Please enter a valid playlist URL.", text_color="#EF4444")
            return

        base_dir = self.dir_entry.get().strip() or self.config.get("download_dir", "")
        folder = self.folder_entry.get().strip() or (self.playlist_info.get("title") if self.playlist_info else "Playlist")
        clean_folder = sanitize_folder_name(folder)
        q_key = self.get_selected_quality_key()
        fn_fmt = self.get_filename_format_key()
        skip_existing = self.skip_existing_var.get()
        selected_eps = self.get_episodes_to_download()
        spd_limit = self.config.get("speed_limit", "")

        if not selected_eps:
            self.overall_label.configure(text="No episodes selected. Check at least one episode.", text_color="#EF4444")
            return

        self.is_downloading = True
        self.cancel_event = threading.Event()
        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.completion_banner.grid_remove()
        self.overall_bar.set(0.0)
        self.video_bar.set(0.0)
        self.overall_bar.configure(progress_color="#3B82F6")
        self.app.set_active(True)

        def overall_progress_cb(step, total, video_title):
            def update():
                self.overall_bar.set(step / total if total > 0 else 0)
                self.overall_label.configure(
                    text=f"Overall Progress: [{step}/{total}] — {clean_folder}",
                    text_color="#F9FAFB"
                )
                self.current_label.configure(text=f"Current: {video_title}")
                self.video_bar.set(0.0)
            self.after(0, update)

        def video_progress_cb(pct, downloaded, total, speed, eta):
            def update():
                self.video_bar.set(pct / 100.0)
                dl_mb = downloaded / 1048576
                tot_mb = total / 1048576 if total > 0 else 0
                self.stats_label.configure(
                    text=f"Speed: {speed}  •  ETA: {eta}  •  {dl_mb:.1f} / {tot_mb:.1f} MB ({pct:.1f}%)"
                )
            self.after(0, update)

        def status_cb(msg, level="info"):
            colors = {"success": "#22C55E", "error": "#EF4444", "warning": "#F59E0B"}
            color = colors.get(level, "#F3F4F6")
            self.after(0, lambda: self.overall_label.configure(text=msg, text_color=color))
            self.app.log(msg, level)

        def worker():
            success, paths = self.engine.download_playlist(
                url, base_dir,
                folder_name=clean_folder,
                quality_key=q_key,
                selected_indices=selected_eps,
                skip_existing=skip_existing,
                filename_format=fn_fmt,
                overall_progress_cb=overall_progress_cb,
                video_progress_cb=video_progress_cb,
                status_cb=status_cb,
                cancel_event=self.cancel_event,
                speed_limit=spd_limit
            )
            title = self.playlist_info.get("title", clean_folder) if self.playlist_info else clean_folder
            append_history(self.config, {
                "title": title,
                "url": url,
                "type": "playlist",
                "quality": QUALITY_PRESETS.get(q_key, {}).get("name", q_key),
                "status": "success" if success else "failed",
                "path": os.path.join(base_dir, clean_folder),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            })

            def finish():
                self.is_downloading = False
                self.download_btn.configure(state="normal")
                self.cancel_btn.configure(state="disabled")
                self.app.set_active(False)
                self._last_save_path = os.path.join(base_dir, clean_folder)
                if success:
                    self.overall_bar.set(1.0)
                    self.video_bar.set(1.0)
                    self.overall_bar.configure(progress_color="#22C55E")
                    self.completion_banner.grid()

                    if self.config.get("sound_notify", True) and winsound:
                        try:
                            winsound.MessageBeep(winsound.MB_OK)
                        except Exception:
                            pass

                    if self.config.get("auto_open_folder", False):
                        self.open_save_folder()

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def cancel_download(self):
        if self.cancel_event:
            self.cancel_event.set()
            self.cancel_btn.configure(state="disabled")
            self.overall_label.configure(text="Stopping playlist download...", text_color="#F59E0B")

    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            self.overall_label.configure(text="Please enter a valid playlist link.", text_color="#EF4444")
            return
        base_dir = self.dir_entry.get().strip() or self.config.get("download_dir", "")
        folder = self.folder_entry.get().strip() or (self.playlist_info.get("title") if self.playlist_info else "Playlist")
        clean_folder = sanitize_folder_name(folder)
        q_key = self.get_selected_quality_key()
        fn_fmt = self.get_filename_format_key()
        skip_existing = self.skip_existing_var.get()
        selected_eps = self.get_episodes_to_download()
        title = self.playlist_info.get("title") if self.playlist_info else clean_folder

        self.app.queue_view.add_item({
            "type": "playlist",
            "url": url,
            "title": f"📋 {title} ({len(selected_eps)} eps)",
            "folder_name": clean_folder,
            "quality_key": q_key,
            "save_dir": base_dir,
            "selected_indices": selected_eps,
            "skip_existing": skip_existing,
            "filename_format": fn_fmt,
            "status": "Pending"
        })
        self.app.log(f"Added playlist to queue: {title}", "info")
        self.overall_label.configure(text="✓ Playlist added to download queue", text_color="#22C55E")
