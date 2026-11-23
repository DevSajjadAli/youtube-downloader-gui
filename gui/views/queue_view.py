import os
import subprocess
import threading
import customtkinter as ctk
from gui import icon_loader as icons
from core.engine import QUALITY_PRESETS


class QueueView(ctk.CTkFrame):
    """Futuristic batch queue view with per-item live telemetry, pause/resume, and direct playback."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.items = []
        self.is_processing = False
        self._item_bars = {}  # idx -> CTkProgressBar

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="  Batch Download Queue",
            image=icons.queue(26), compound="left",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")
        self.subtitle_lbl = ctk.CTkLabel(
            hdr, text="0 items in batch line",
            font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w"
        )
        self.subtitle_lbl.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ── Controls Bar ────────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self, corner_radius=10)
        ctrl.grid(row=1, column=0, sticky="ew", padx=20, pady=6)

        btns = ctk.CTkFrame(ctrl, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=10)

        self.start_btn = ctk.CTkButton(
            btns, text="  Start Batch",
            image=icons.download(16), compound="left",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#065F46", hover_color="#064E3B",
            corner_radius=6, height=36, command=self.start_queue
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        self.pause_btn = ctk.CTkButton(
            btns, text="  Stop Batch",
            image=icons.cancel(16), compound="left",
            font=ctk.CTkFont(size=13),
            fg_color="#7F1D1D", hover_color="#991B1B",
            corner_radius=6, height=36, command=self.pause_queue, state="disabled"
        )
        self.pause_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btns, text="Clear Done",
            fg_color="#374151", hover_color="#4B5563",
            corner_radius=6, height=36, command=self.clear_finished
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            btns, text="Clear All",
            fg_color="#374151", hover_color="#4B5563",
            corner_radius=6, height=36, command=self.clear_all
        ).pack(side="right", padx=4)

        # ── Queue List ───────────────────────────────────────────────────────
        self.list_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=5)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="📭  Your download queue is empty.\nAdd videos or playlists from their tabs to download sequentially.",
            font=ctk.CTkFont(size=14), text_color="#6B7280", justify="center"
        )
        self.empty_label.pack(pady=60)

        # ── Overall Queue Progress ──────────────────────────────────────────
        prog = ctk.CTkFrame(self, corner_radius=10)
        prog.grid(row=3, column=0, sticky="ew", padx=20, pady=(5, 18))
        prog.grid_columnconfigure(0, weight=1)

        self.queue_status = ctk.CTkLabel(prog, text="Queue Idle — Ready",
                                         font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
        self.queue_status.grid(row=0, column=0, sticky="w", padx=16, pady=(10, 2))

        self.queue_bar = ctk.CTkProgressBar(prog, height=12, corner_radius=6)
        self.queue_bar.set(0.0)
        self.queue_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 12))

    # ── Queue Management ─────────────────────────────────────────────────────

    def add_item(self, item_dict):
        self.items.append(item_dict)
        self.refresh_list()
        self.app.update_queue_badge(len(self.items))

    def remove_item(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.refresh_list()
            self.app.update_queue_badge(len(self.items))

    def clear_finished(self):
        self.items = [i for i in self.items if i.get("status") in ("Pending", "Downloading")]
        self.refresh_list()
        self.app.update_queue_badge(len(self.items))

    def clear_all(self):
        if not self.is_processing:
            self.items.clear()
            self.refresh_list()
            self.app.update_queue_badge(0)

    def refresh_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self._item_bars.clear()

        count = len(self.items)
        self.subtitle_lbl.configure(text=f"{count} item{'s' if count != 1 else ''} in queue")

        if not self.items:
            lbl = ctk.CTkLabel(
                self.list_frame,
                text="📭  Your download queue is empty.\nAdd videos or playlists from their tabs to download sequentially.",
                font=ctk.CTkFont(size=14), text_color="#6B7280", justify="center"
            )
            lbl.pack(pady=60)
            return

        for idx, item in enumerate(self.items):
            self._make_card(idx, item)

    def _make_card(self, idx: int, item: dict):
        status = item.get("status", "Pending")
        alt_bg = ("#1F2937", "#1F2937") if idx % 2 == 0 else ("#111827", "#111827")

        card = ctk.CTkFrame(self.list_frame, corner_radius=8, fg_color=alt_bg)
        card.pack(fill="x", pady=3, padx=0)
        card.grid_columnconfigure(2, weight=1)

        # Number badge
        ctk.CTkLabel(card, text=f"{idx+1}.", font=ctk.CTkFont(size=13, weight="bold"),
                     width=30).grid(row=0, column=0, padx=(10, 2), pady=10)

        # Type icon
        ico = icons.video(18) if item.get("type") == "single" else icons.playlist(18)
        ctk.CTkLabel(card, image=ico, text="").grid(row=0, column=1, padx=(2, 6), pady=10, sticky="w")

        # Info column
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=2, sticky="ew", pady=8)
        info.grid_columnconfigure(0, weight=1)

        title = item.get("title", item.get("url", "Item"))
        ctk.CTkLabel(info, text=title[:75] + ("…" if len(title) > 75 else ""),
                     font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
                     ).grid(row=0, column=0, sticky="w")

        q_key = item.get("quality_key", "1")
        q_name = QUALITY_PRESETS.get(q_key, QUALITY_PRESETS["1"])["badge"]
        type_tag = "Single Video" if item.get("type") == "single" else "Playlist"
        ctk.CTkLabel(info, text=f"{type_tag}  •  {q_name}",
                     font=ctk.CTkFont(size=11), text_color="#9CA3AF", anchor="w"
                     ).grid(row=1, column=0, sticky="w")

        # If currently downloading, show live item progress bar
        if status == "Downloading":
            item_prog = ctk.CTkProgressBar(info, height=6, corner_radius=3)
            item_prog.set(item.get("progress", 0.0))
            item_prog.grid(row=2, column=0, sticky="ew", pady=(4, 2))
            self._item_bars[idx] = item_prog

        # Status badge
        badge_colors = {
            "Completed": "#166534", "Failed": "#7F1D1D",
            "Downloading": "#1E3A8A", "Pending": "#78350F"
        }
        ctk.CTkLabel(card, text=status, font=ctk.CTkFont(size=11, weight="bold"),
                     fg_color=badge_colors.get(status, "#374151"),
                     corner_radius=4, width=86, padx=6
                     ).grid(row=0, column=3, padx=8, pady=10)

        # Action buttons
        act_f = ctk.CTkFrame(card, fg_color="transparent")
        act_f.grid(row=0, column=4, padx=(0, 10), pady=10, sticky="e")

        # If completed, show Play button
        saved_path = item.get("saved_path")
        if status == "Completed" and saved_path and os.path.isfile(saved_path):
            ctk.CTkButton(
                act_f, text="▶", width=28, height=28, corner_radius=4,
                fg_color="#059669", hover_color="#047857",
                command=lambda p=saved_path: os.startfile(p)
            ).pack(side="left", padx=2)

        # Delete from queue
        if status != "Downloading":
            ctk.CTkButton(
                act_f, text="✕", width=28, height=28, corner_radius=4,
                fg_color="#374151", hover_color="#EF4444",
                command=lambda i=idx: self.remove_item(i)
            ).pack(side="left", padx=2)

    # ── Execution ────────────────────────────────────────────────────────────

    def start_queue(self):
        if self.is_processing or not self.items:
            return
        self.is_processing = True
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.app.cancel_queue_event = threading.Event()
        self.app.set_active(True)
        threading.Thread(target=self._process_queue_worker, daemon=True).start()

    def pause_queue(self):
        if self.app.cancel_queue_event:
            self.app.cancel_queue_event.set()
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled")
        self.queue_status.configure(text="Queue Paused by User")
        self.app.set_active(False)

    def _process_queue_worker(self):
        total = len(self.items)
        spd_limit = self.app.config.get("speed_limit", "")

        for idx, item in enumerate(self.items):
            if self.app.cancel_queue_event and self.app.cancel_queue_event.is_set():
                break
            if item.get("status") == "Completed":
                continue

            item["status"] = "Downloading"
            item["progress"] = 0.0
            self.after(0, self.refresh_list)
            self.after(0, lambda i=idx, t=total: self.queue_bar.set(i / t))
            self.after(0, lambda i=idx, t=total: self.queue_status.configure(
                text=f"Batch Progress: [{i+1}/{t}] — {item.get('title', 'Media')[:50]}"
            ))

            url = item.get("url")
            q_key = item.get("quality_key", "1")
            save_dir = item.get("save_dir")

            def per_item_progress(pct, dl, tot, spd, eta):
                frac = pct / 100.0
                item["progress"] = frac
                if idx in self._item_bars:
                    self.after(0, lambda f=frac: self._item_bars[idx].set(f))

            if item.get("type") == "single":
                success, path = self.app.engine.download_single(
                    url, save_dir, quality_key=q_key,
                    progress_cb=per_item_progress,
                    cancel_event=self.app.cancel_queue_event,
                    speed_limit=spd_limit
                )
            else:
                success, paths = self.app.engine.download_playlist(
                    url, save_dir,
                    folder_name=item.get("folder_name"),
                    quality_key=q_key,
                    selected_indices=item.get("selected_indices"),
                    skip_existing=item.get("skip_existing", True),
                    filename_format=item.get("filename_format", "numbered_title"),
                    cancel_event=self.app.cancel_queue_event,
                    speed_limit=spd_limit
                )
                path = paths[0] if paths else None

            item["status"] = "Completed" if success else "Failed"
            if success and path:
                item["saved_path"] = path

            self.after(0, self.refresh_list)

        self.after(0, self._on_queue_finished)

    def _on_queue_finished(self):
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled")
        self.queue_bar.set(1.0)
        self.queue_status.configure(text="✓ Batch Queue Processing Complete")
        self.app.log("Batch queue execution finished.", "success")
        self.app.set_active(False)
