import os
import subprocess
import threading
import datetime
import customtkinter as ctk
from PIL import Image

try:
    import winsound
except ImportError:
    winsound = None

from gui import icon_loader as icons
from core.engine import QUALITY_PRESETS
from gui.views.history_view import append_history


class QueueView(ctk.CTkFrame):
    """Futuristic batch queue view with detailed active item telemetry,
    live dual progress bars, per-item telemetry cards, pause/resume, and direct playback."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.items = []
        self.is_processing = False
        self._item_bars = {}    # idx -> CTkProgressBar
        self._item_stats = {}   # idx -> CTkLabel

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="  Batch Download Queue & Live Monitor",
            image=icons.queue(26), compound="left",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")
        self.subtitle_lbl = ctk.CTkLabel(
            hdr, text="0 items in queue line — Add videos or playlists to process sequentially",
            font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w"
        )
        self.subtitle_lbl.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ── Controls Bar ────────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self, corner_radius=10)
        ctrl.grid(row=1, column=0, sticky="ew", padx=20, pady=6)

        btns = ctk.CTkFrame(ctrl, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=10)

        self.start_btn = ctk.CTkButton(
            btns, text="  Start Batch Queue",
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
            btns, text="Clear Completed",
            fg_color="#374151", hover_color="#4B5563",
            corner_radius=6, height=36, command=self.clear_finished
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            btns, text="Clear All",
            fg_color="#374151", hover_color="#4B5563",
            corner_radius=6, height=36, command=self.clear_all
        ).pack(side="right", padx=4)

        # ── Live Active Download Telemetry Dashboard (Futuristic Hero Card) ─
        self.monitor_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#181825", border_width=1, border_color="#2D2D40")
        self.monitor_card.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 6))
        self.monitor_card.grid_columnconfigure(0, weight=1)

        # Monitor Header
        mon_hdr = ctk.CTkFrame(self.monitor_card, fg_color="transparent")
        mon_hdr.pack(fill="x", padx=16, pady=(12, 4))
        mon_hdr.grid_columnconfigure(0, weight=1)

        self.mon_title = ctk.CTkLabel(
            mon_hdr, text="Active Stream: Ready",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w", justify="left"
        )
        self.mon_title.pack(side="left", fill="x", expand=True)

        self.mon_badge = ctk.CTkLabel(
            mon_hdr, text="Queue Idle",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#374151", text_color="#E5E7EB",
            corner_radius=4, padx=10, pady=2
        )
        self.mon_badge.pack(side="right")

        # Active item progress bar with label
        prog_row1 = ctk.CTkFrame(self.monitor_card, fg_color="transparent")
        prog_row1.pack(fill="x", padx=16, pady=(4, 2))
        prog_row1.grid_columnconfigure(0, weight=1)

        self.active_item_label = ctk.CTkLabel(
            prog_row1, text="Current Item Progress: —",
            font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w"
        )
        self.active_item_label.pack(side="left")

        self.active_pct_label = ctk.CTkLabel(
            prog_row1, text="0.0%",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#93C5FD", anchor="e"
        )
        self.active_pct_label.pack(side="right")

        self.active_bar = ctk.CTkProgressBar(self.monitor_card, height=12, corner_radius=6)
        self.active_bar.set(0.0)
        self.active_bar.pack(fill="x", padx=16, pady=(2, 6))

        # Telemetry metrics row (4 cards: Speed, ETA, Transferred, Engine Stage)
        metrics_frame = ctk.CTkFrame(self.monitor_card, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=16, pady=(4, 12))
        metrics_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def _make_metric(col, label, init_val, icon_fn=None):
            box = ctk.CTkFrame(metrics_frame, fg_color="#1F1F30", corner_radius=6)
            box.grid(row=0, column=col, padx=4, sticky="nsew")
            lbl_f = ctk.CTkFrame(box, fg_color="transparent")
            lbl_f.pack(anchor="w", padx=8, pady=(6, 2))
            if icon_fn:
                ico = icon_fn(12)
                if ico:
                    ctk.CTkLabel(lbl_f, image=ico, text="").pack(side="left", padx=(0, 4))
            ctk.CTkLabel(lbl_f, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color="#9CA3AF").pack(side="left")
            val_lbl = ctk.CTkLabel(box, text=init_val, font=ctk.CTkFont(size=12, weight="bold"), text_color="#F3F4F6")
            val_lbl.pack(anchor="w", padx=8, pady=(0, 6))
            return val_lbl

        self.metric_speed = _make_metric(0, "SPEED", "— MB/s", icons.speed)
        self.metric_eta   = _make_metric(1, "ESTIMATED TIME", "— ETA")
        self.metric_size  = _make_metric(2, "TRANSFERRED", "0.0 / 0.0 MB")
        self.metric_stage = _make_metric(3, "ENGINE STATUS", "Idle")

        # ── Queue List (Scrollable items) ───────────────────────────────────
        self.list_frame = ctk.CTkScrollableFrame(self, corner_radius=10, fg_color="#13131F")
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=5)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="📭  Your download queue is empty.\nAdd videos or playlists from their tabs to download sequentially.",
            font=ctk.CTkFont(size=14), text_color="#6B7280", justify="center"
        )
        self.empty_label.pack(pady=60)

        # ── Overall Queue Progress Card ─────────────────────────────────────
        prog = ctk.CTkFrame(self, corner_radius=10)
        prog.grid(row=4, column=0, sticky="ew", padx=20, pady=(5, 14))
        prog.grid_columnconfigure(0, weight=1)

        self.queue_status = ctk.CTkLabel(
            prog, text="Queue Idle — Ready",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        )
        self.queue_status.grid(row=0, column=0, sticky="w", padx=16, pady=(10, 2))

        self.queue_bar = ctk.CTkProgressBar(prog, height=10, corner_radius=5)
        self.queue_bar.set(0.0)
        self.queue_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 10))

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
            self._reset_monitor()

    def _reset_monitor(self):
        self.mon_title.configure(text="Active Stream: Ready", text_color="#F3F4F6")
        self.mon_badge.configure(text="Queue Idle", fg_color="#374151", text_color="#E5E7EB")
        self.active_item_label.configure(text="Current Item Progress: —")
        self.active_pct_label.configure(text="0.0%")
        self.active_bar.set(0.0)
        self.active_bar.configure(progress_color="#3B82F6")
        self.metric_speed.configure(text="— MB/s")
        self.metric_eta.configure(text="— ETA")
        self.metric_size.configure(text="0.0 / 0.0 MB")
        self.metric_stage.configure(text="Idle")

    def refresh_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self._item_bars.clear()
        self._item_stats.clear()

        count = len(self.items)
        self.subtitle_lbl.configure(text=f"{count} item{'s' if count != 1 else ''} in queue line")

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
        is_active = (status == "Downloading")
        bg_color = "#1E293B" if is_active else ("#1A1A28" if idx % 2 == 0 else "#151522")
        border_col = "#3B82F6" if is_active else "#2D2D3E"

        card = ctk.CTkFrame(self.list_frame, corner_radius=8, fg_color=bg_color, border_width=1, border_color=border_col)
        card.pack(fill="x", pady=4, padx=4)
        card.grid_columnconfigure(2, weight=1)

        # Number badge
        ctk.CTkLabel(
            card, text=f"#{idx+1}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#93C5FD" if is_active else "#9CA3AF",
            width=32
        ).grid(row=0, column=0, padx=(12, 4), pady=12)

        # Type icon
        ico = icons.video(20) if item.get("type") == "single" else icons.playlist(20)
        ctk.CTkLabel(card, image=ico, text="").grid(row=0, column=1, padx=(2, 8), pady=12, sticky="w")

        # Info column
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=2, sticky="ew", pady=10, padx=(0, 10))
        info.grid_columnconfigure(0, weight=1)

        title = item.get("title", item.get("url", "Item"))
        title_lbl = ctk.CTkLabel(
            info, text=title[:80] + ("…" if len(title) > 80 else ""),
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
            text_color="#60A5FA" if is_active else "#F9FAFB"
        )
        title_lbl.grid(row=0, column=0, sticky="w")

        q_key = item.get("quality_key", "1")
        q_name = QUALITY_PRESETS.get(q_key, QUALITY_PRESETS["1"])["badge"]
        type_tag = "Single Video" if item.get("type") == "single" else "Playlist"
        save_dest = os.path.basename(item.get("save_dir", "")) or "Downloads"

        sub_text = f"{type_tag}  •  {q_name}  •  Save: {save_dest}"
        ctk.CTkLabel(
            info, text=sub_text,
            font=ctk.CTkFont(size=11), text_color="#9CA3AF", anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Live item progress & telemetry row
        prog_row = ctk.CTkFrame(info, fg_color="transparent")
        prog_row.grid(row=2, column=0, sticky="ew", pady=(4, 2))
        prog_row.grid_columnconfigure(0, weight=1)

        item_prog = ctk.CTkProgressBar(prog_row, height=6, corner_radius=3)
        item_prog.set(item.get("progress", 0.0))
        item_prog.grid(row=0, column=0, sticky="ew")
        self._item_bars[idx] = item_prog

        item_stat_lbl = ctk.CTkLabel(
            prog_row,
            text=item.get("stat_text", ""),
            font=ctk.CTkFont(size=10), text_color="#9CA3AF", anchor="e"
        )
        item_stat_lbl.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self._item_stats[idx] = item_stat_lbl

        # Status badge
        badge_configs = {
            "Completed":   ("#166534", "#BBF7D0", "✓ Done"),
            "Failed":      ("#7F1D1D", "#FECACA", "✕ Failed"),
            "Downloading": ("#1E3A8A", "#BFDBFE", "● Active"),
            "Pending":     ("#78350F", "#FED7AA", "Pending")
        }
        bg, fg, label_txt = badge_configs.get(status, ("#374151", "#E5E7EB", status))
        ctk.CTkLabel(
            card, text=label_txt, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=bg, text_color=fg,
            corner_radius=4, width=82, padx=4, pady=3
        ).grid(row=0, column=3, padx=8, pady=12)

        # Action buttons
        act_f = ctk.CTkFrame(card, fg_color="transparent")
        act_f.grid(row=0, column=4, padx=(0, 12), pady=12, sticky="e")

        # Play button if completed
        saved_path = item.get("saved_path")
        if status == "Completed" and saved_path and (os.path.isfile(saved_path) or os.path.isdir(saved_path)):
            ctk.CTkButton(
                act_f, text="▶ Play", width=60, height=28, corner_radius=4,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#059669", hover_color="#047857",
                command=lambda p=saved_path: os.startfile(p)
            ).pack(side="left", padx=2)

        # Open destination folder
        dl_dir = item.get("save_dir")
        if dl_dir and os.path.isdir(dl_dir):
            ctk.CTkButton(
                act_f, text="📂", width=30, height=28, corner_radius=4,
                font=ctk.CTkFont(size=11),
                fg_color="#374151", hover_color="#4B5563",
                command=lambda d=dl_dir: subprocess.Popen(["explorer", d])
            ).pack(side="left", padx=2)

        # Remove from queue if not downloading
        if status != "Downloading":
            ctk.CTkButton(
                act_f, text="✕", width=28, height=28, corner_radius=4,
                font=ctk.CTkFont(size=11),
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
        self.queue_status.configure(text="Queue Stopped by User", text_color="#F59E0B")
        self.metric_stage.configure(text="Stopped")
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

            title = item.get("title", item.get("url", "Media"))
            is_single = (item.get("type") == "single")

            # Update monitor card for active item
            def setup_active_ui(i=idx, t=title, s=is_single):
                self.mon_title.configure(text=f"▶ Downloading: {t[:65]}", text_color="#60A5FA")
                self.mon_badge.configure(
                    text=f"Item {i+1} of {total}",
                    fg_color="#1E3A8A", text_color="#BFDBFE"
                )
                self.active_item_label.configure(text=f"Processing {t[:50]}")
                self.active_pct_label.configure(text="0.0%")
                self.active_bar.set(0.0)
                self.active_bar.configure(progress_color="#3B82F6")
                self.metric_stage.configure(text="Connecting...")
                self.queue_status.configure(
                    text=f"Batch Progress: [{i+1}/{total}] — {t[:50]}",
                    text_color="#F9FAFB"
                )
                self.queue_bar.set(i / total if total > 0 else 0)
                self.refresh_list()

            self.after(0, setup_active_ui)

            url = item.get("url")
            q_key = item.get("quality_key", "1")
            save_dir = item.get("save_dir")

            # Detailed live telemetry callbacks
            def per_item_progress(pct, dl, tot, spd, eta):
                frac = pct / 100.0
                item["progress"] = frac
                dl_mb = dl / 1048576
                tot_mb = tot / 1048576 if tot > 0 else 0
                stat_str = f"{pct:.1f}% • {spd} • ETA: {eta}"
                item["stat_text"] = stat_str

                def update_mon():
                    self.active_bar.set(frac)
                    self.active_pct_label.configure(text=f"{pct:.1f}%")
                    self.metric_speed.configure(text=spd if spd else "—")
                    self.metric_eta.configure(text=eta if eta else "—")
                    self.metric_size.configure(text=f"{dl_mb:.1f} / {tot_mb:.1f} MB")
                    if idx in self._item_bars:
                        self._item_bars[idx].set(frac)
                    if idx in self._item_stats:
                        self._item_stats[idx].configure(text=f"{pct:.1f}% ({spd})")
                    if total > 0:
                        overall_q_pct = ((idx + frac) / total) * 100.0
                        self.app.set_taskbar_progress(overall_q_pct)
                        self.queue_bar.set((idx + frac) / total)

                self.after(0, update_mon)

            def per_item_status(msg, level="info"):
                self.after(0, lambda m=msg: self.metric_stage.configure(text=m[:28]))
                self.app.log(f"[Queue Item {idx+1}] {msg}", level)

            if is_single:
                success, path = self.app.engine.download_single(
                    url, save_dir, quality_key=q_key,
                    progress_cb=per_item_progress,
                    status_cb=per_item_status,
                    cancel_event=self.app.cancel_queue_event,
                    speed_limit=spd_limit
                )
            else:
                # Playlist item in queue with full live callbacks
                def pl_overall_cb(step, tot_eps, ep_title):
                    def update_pl():
                        self.active_item_label.configure(text=f"Episode {step}/{tot_eps}: {ep_title[:45]}")
                        self.metric_stage.configure(text=f"Ep {step}/{tot_eps}")
                    self.after(0, update_pl)

                success, paths = self.app.engine.download_playlist(
                    url, save_dir,
                    folder_name=item.get("folder_name"),
                    quality_key=q_key,
                    selected_indices=item.get("selected_indices"),
                    skip_existing=item.get("skip_existing", True),
                    filename_format=item.get("filename_format", "numbered_title"),
                    overall_progress_cb=pl_overall_cb,
                    video_progress_cb=per_item_progress,
                    status_cb=per_item_status,
                    cancel_event=self.app.cancel_queue_event,
                    speed_limit=spd_limit,
                    cached_info=item.get("cached_info")
                )
                path = paths[0] if paths else (os.path.join(save_dir, item.get("folder_name", "")) if success else None)

            item["status"] = "Completed" if success else "Failed"
            if success and path:
                item["saved_path"] = path
                append_history(self.app.config, {
                    "title": item.get("title", url),
                    "url": url,
                    "type": item.get("type", "single"),
                    "quality": QUALITY_PRESETS.get(q_key, {}).get("name", q_key),
                    "status": "success",
                    "path": path,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })

            self.after(0, self.refresh_list)

        self.after(0, self._on_queue_finished)

    def _on_queue_finished(self):
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled")
        self.queue_bar.set(1.0)
        self.active_bar.set(1.0)
        self.active_bar.configure(progress_color="#22C55E")

        completed_count = sum(1 for i in self.items if i.get("status") == "Completed")
        failed_count = sum(1 for i in self.items if i.get("status") == "Failed")

        self.mon_title.configure(text="✓ Batch Queue Processing Finished!", text_color="#A7F3D0")
        self.mon_badge.configure(text="Done", fg_color="#166534", text_color="#BBF7D0")
        self.metric_stage.configure(text="Finished")
        self.queue_status.configure(
            text=f"✓ All tasks completed: {completed_count} succeeded, {failed_count} failed.",
            text_color="#22C55E"
        )
        self.app.log(f"Batch queue finished: {completed_count} succeeded, {failed_count} failed.", "success")
        self.app.set_active(False)

        # Chime
        if self.app.config.get("sound_notify", True) and winsound:
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass
