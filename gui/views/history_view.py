"""History View — shows a persistent log of all completed downloads with live search,
storage analytics, direct media playback, and folder explorer integration."""

import os
import json
import subprocess
import customtkinter as ctk
from gui import icon_loader as icons


HISTORY_FILE_NAME = "download_history.json"


def get_history_file(config) -> str:
    app_data = os.path.join(os.path.expanduser("~"), ".ytdl_pro")
    os.makedirs(app_data, exist_ok=True)
    return os.path.join(app_data, HISTORY_FILE_NAME)


def load_history(path: str) -> list:
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(path: str, entries: list):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries[-500:], f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def append_history(config, entry: dict):
    """Add a completed download to the persistent history file."""
    path = get_history_file(config)
    entries = load_history(path)
    entries.append(entry)
    save_history(path, entries)


class HistoryView(ctk.CTkScrollableFrame):
    """Futuristic view for browsing all downloaded media history with search, telemetry, and instant playback."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.config = app.config
        self._entries: list = []
        self._row_widgets: list = []

        self.grid_columnconfigure(0, weight=1)

        # ── Header bar ───────────────────────────────────────────────────────
        hdr_frame = ctk.CTkFrame(self, fg_color="transparent")
        hdr_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        hdr_frame.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkLabel(
            hdr_frame,
            text="  Download History & Library",
            image=icons.history(26),
            compound="left",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w"
        )
        hdr.grid(row=0, column=0, sticky="w")

        sub = ctk.CTkLabel(
            hdr_frame,
            text="Persistent record of all downloaded media with one-click player launch and storage metrics",
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF",
            anchor="w"
        )
        sub.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Top buttons
        btn_frame = ctk.CTkFrame(hdr_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=2, sticky="e")

        self.refresh_btn = ctk.CTkButton(
            btn_frame,
            text="⟳ Refresh",
            width=90,
            height=34,
            corner_radius=6,
            fg_color="#374151",
            hover_color="#4B5563",
            command=self.load_entries
        )
        self.refresh_btn.pack(side="left", padx=(0, 8))

        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="🗑 Clear All",
            width=90,
            height=34,
            corner_radius=6,
            fg_color="#7F1D1D",
            hover_color="#991B1B",
            command=self.clear_history
        )
        self.clear_btn.pack(side="left")

        # ── Analytics Telemetry Bar ──────────────────────────────────────────
        self.stats_card = ctk.CTkFrame(self, corner_radius=10, fg_color="#181825")
        self.stats_card.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        self.stats_card.grid_columnconfigure((0, 1, 2), weight=1)

        self.stat_total = ctk.CTkLabel(self.stats_card, text="Total: 0", font=ctk.CTkFont(size=12, weight="bold"))
        self.stat_total.grid(row=0, column=0, padx=12, pady=10)

        self.stat_success = ctk.CTkLabel(self.stats_card, text="Successful: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#34D399")
        self.stat_success.grid(row=0, column=1, padx=12, pady=10)

        self.stat_storage = ctk.CTkLabel(self.stats_card, text="Disk Space: 0 MB", font=ctk.CTkFont(size=12, weight="bold"), text_color="#60A5FA")
        self.stat_storage.grid(row=0, column=2, padx=12, pady=10)

        # ── Live Search Bar ──────────────────────────────────────────────────
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 6))
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Filter library by title, format, or date...",
            height=38,
            corner_radius=8
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self._filter_history())

        # Empty-state label
        self.empty_label = ctk.CTkLabel(
            self,
            text="📭  No download history found.\nDownloaded media will be indexed here automatically.",
            font=ctk.CTkFont(size=14),
            text_color="#6B7280",
            justify="center"
        )
        self.empty_label.grid(row=3, column=0, pady=60)

        # List frame
        self.list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.list_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=4)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.load_entries()

    def load_entries(self):
        path = get_history_file(self.config)
        self._entries = load_history(path)
        self._update_stats()
        self._rebuild_list(self._entries)

    def _update_stats(self):
        total = len(self._entries)
        succ = sum(1 for e in self._entries if e.get("status") == "success")
        total_bytes = 0
        for e in self._entries:
            p = e.get("path")
            if p and os.path.isfile(p):
                try:
                    total_bytes += os.path.getsize(p)
                except OSError:
                    pass
        mb = total_bytes / (1024 * 1024)
        gb = mb / 1024

        self.stat_total.configure(text=f"Total Media: {total}")
        self.stat_success.configure(text=f"Completed: {succ} ({int(succ/total*100) if total else 0}%)")
        size_str = f"{gb:.2f} GB" if gb >= 1.0 else f"{mb:.1f} MB"
        self.stat_storage.configure(text=f"Library Size: {size_str}")

    def _filter_history(self):
        q = self.search_entry.get().strip().lower()
        if not q:
            self._rebuild_list(self._entries)
            return

        filtered = [
            e for e in self._entries
            if q in e.get("title", "").lower()
            or q in e.get("url", "").lower()
            or q in e.get("quality", "").lower()
            or q in e.get("timestamp", "").lower()
        ]
        self._rebuild_list(filtered)

    def _rebuild_list(self, entries_to_render):
        for w in self._row_widgets:
            w.destroy()
        self._row_widgets.clear()

        if not entries_to_render:
            self.empty_label.grid()
            return
        self.empty_label.grid_remove()

        for i, entry in enumerate(reversed(entries_to_render)):
            row = self._make_row(entry, i)
            row.grid(row=i, column=0, sticky="ew", pady=3)
            self._row_widgets.append(row)

    def _make_row(self, entry: dict, idx: int) -> ctk.CTkFrame:
        status = entry.get("status", "unknown")
        is_ok = status == "success"
        path = entry.get("path", "")
        file_exists = path and (os.path.isfile(path) or os.path.isdir(path))

        card = ctk.CTkFrame(self.list_frame, corner_radius=8, fg_color="#1F2937" if idx % 2 == 0 else "#111827")
        card.grid_columnconfigure(1, weight=1)

        # Status badge
        badge_color = "#166534" if is_ok else "#7F1D1D"
        badge_text = "✓ Done" if is_ok else "✗ Failed"
        badge = ctk.CTkLabel(
            card, text=badge_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=badge_color, corner_radius=4,
            width=65, padx=4
        )
        badge.grid(row=0, column=0, padx=(12, 8), pady=(12, 4), sticky="n")

        # Main information
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", pady=(10, 4))
        info.grid_columnconfigure(0, weight=1)

        title_text = entry.get("title", entry.get("url", "Media"))
        if len(title_text) > 85:
            title_text = title_text[:82] + "..."
        ctk.CTkLabel(
            info, text=title_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="w")

        meta = []
        if entry.get("type"):
            meta.append(entry["type"].capitalize())
        if entry.get("quality"):
            meta.append(entry["quality"])
        if entry.get("timestamp"):
            meta.append(entry["timestamp"])

        if path and os.path.isfile(path):
            try:
                sz = os.path.getsize(path) / (1024 * 1024)
                meta.append(f"{sz:.1f} MB")
            except OSError:
                pass

        ctk.CTkLabel(
            info, text="  •  ".join(meta),
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF",
            anchor="w"
        ).grid(row=1, column=0, sticky="w")

        # Action Buttons frame
        act_f = ctk.CTkFrame(card, fg_color="transparent")
        act_f.grid(row=0, column=2, padx=(4, 12), pady=10, sticky="e")

        # Play Button (launch default media player)
        if file_exists and os.path.isfile(path):
            ctk.CTkButton(
                act_f, text="▶ Play",
                width=65, height=28, corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#059669", hover_color="#047857",
                command=lambda p=path: self._play_file(p)
            ).pack(side="left", padx=3)

        # Open in Folder button
        if file_exists:
            ctk.CTkButton(
                act_f, text="📂 Folder",
                width=65, height=28, corner_radius=6,
                font=ctk.CTkFont(size=11),
                fg_color="#374151", hover_color="#4B5563",
                command=lambda p=path: self._open_folder(p)
            ).pack(side="left", padx=3)

        # Delete single history entry
        ctk.CTkButton(
            act_f, text="✕",
            width=28, height=28, corner_radius=6,
            fg_color="#374151", hover_color="#EF4444",
            command=lambda e=entry: self._delete_entry(e)
        ).pack(side="left", padx=(3, 0))

        return card

    def _play_file(self, path):
        try:
            os.startfile(path)
        except Exception as e:
            self.app.log(f"Playback error: {e}", "warning")

    def _open_folder(self, path):
        if os.path.isfile(path):
            subprocess.Popen(["explorer", "/select,", path])
        elif os.path.isdir(path):
            subprocess.Popen(["explorer", path])

    def _delete_entry(self, entry):
        if entry in self._entries:
            self._entries.remove(entry)
            save_history(get_history_file(self.config), self._entries)
            self._update_stats()
            self._filter_history()

    def clear_history(self):
        path = get_history_file(self.config)
        save_history(path, [])
        self._entries = []
        self._update_stats()
        self._rebuild_list([])
        self.app.log("Download library history cleared.", "info")
