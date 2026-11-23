"""History View — shows a log of all completed downloads with open-folder and clear options."""

import os
import json
import threading
import subprocess
import customtkinter as ctk
from gui import icon_loader as icons


HISTORY_FILE_NAME = "download_history.json"


def get_history_file(config) -> str:
    dl_dir = config.get("download_dir", os.path.expanduser("~"))
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
    """View for browsing all completed download history."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.config = app.config
        self._entries: list = []
        self._row_widgets: list = []

        self.grid_columnconfigure(0, weight=1)

        # ── Header bar ──
        hdr_frame = ctk.CTkFrame(self, fg_color="transparent")
        hdr_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        hdr_frame.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkLabel(
            hdr_frame,
            text="  Download History",
            image=icons.history(26),
            compound="left",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w"
        )
        hdr.grid(row=0, column=0, sticky="w")

        sub = ctk.CTkLabel(
            hdr_frame,
            text="All completed and failed downloads from this session and past sessions",
            font=ctk.CTkFont(size=12),
            text_color="#888888",
            anchor="w"
        )
        sub.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Action buttons
        btn_frame = ctk.CTkFrame(hdr_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=2, sticky="e")

        self.refresh_btn = ctk.CTkButton(
            btn_frame,
            text="⟳ Refresh",
            width=90,
            height=32,
            fg_color="#3A3A3A",
            hover_color="#505050",
            command=self.load_entries
        )
        self.refresh_btn.pack(side="left", padx=(0, 8))

        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="🗑 Clear All",
            width=90,
            height=32,
            fg_color="#7F1D1D",
            hover_color="#991B1B",
            command=self.clear_history
        )
        self.clear_btn.pack(side="left")

        # Divider
        ctk.CTkFrame(self, height=1, fg_color="#333333").grid(
            row=1, column=0, sticky="ew", padx=20, pady=5
        )

        # Empty-state label (shown when no history)
        self.empty_label = ctk.CTkLabel(
            self,
            text="📭  No download history yet.\nComplete a download and it will appear here.",
            font=ctk.CTkFont(size=14),
            text_color="#666666",
            justify="center"
        )
        self.empty_label.grid(row=2, column=0, pady=60)

        # Container for history rows
        self.list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.list_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=5)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.load_entries()

    def load_entries(self):
        path = get_history_file(self.config)
        self._entries = load_history(path)
        self._rebuild_list()

    def _rebuild_list(self):
        for w in self._row_widgets:
            w.destroy()
        self._row_widgets.clear()

        if not self._entries:
            self.empty_label.grid()
            return
        self.empty_label.grid_remove()

        for i, entry in enumerate(reversed(self._entries)):
            row = self._make_row(entry, i)
            row.grid(row=i, column=0, sticky="ew", pady=3)
            self._row_widgets.append(row)

    def _make_row(self, entry: dict, idx: int) -> ctk.CTkFrame:
        status = entry.get("status", "unknown")
        is_ok = status == "success"

        card = ctk.CTkFrame(self.list_frame, corner_radius=8)
        card.grid_columnconfigure(1, weight=1)

        # Status badge
        badge_color = "#166534" if is_ok else "#7F1D1D"
        badge_text = "✓  Done" if is_ok else "✗  Failed"
        badge = ctk.CTkLabel(
            card,
            text=badge_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=badge_color,
            corner_radius=4,
            width=70,
            padx=4
        )
        badge.grid(row=0, column=0, padx=(12, 8), pady=(10, 4), sticky="n")

        # Main info
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", pady=(10, 4))
        info.grid_columnconfigure(0, weight=1)

        title_text = entry.get("title", entry.get("url", "Unknown"))
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
        if entry.get("path"):
            short = entry["path"]
            if len(short) > 60:
                short = "..." + short[-57:]
            meta.append(short)

        ctk.CTkLabel(
            info, text="  •  ".join(meta),
            font=ctk.CTkFont(size=11),
            text_color="#888888",
            anchor="w"
        ).grid(row=1, column=0, sticky="w")

        # Open folder button
        path = entry.get("path", "")
        folder_path = os.path.dirname(path) if path and os.path.isfile(path) else path

        if folder_path and os.path.isdir(folder_path):
            open_btn = ctk.CTkButton(
                card,
                text="📂 Open",
                width=70,
                height=28,
                font=ctk.CTkFont(size=11),
                fg_color="#3A3A3A",
                hover_color="#505050",
                command=lambda fp=folder_path: subprocess.Popen(["explorer", fp])
            )
            open_btn.grid(row=0, column=2, padx=(4, 12), pady=10, sticky="e")

        return card

    def clear_history(self):
        path = get_history_file(self.config)
        save_history(path, [])
        self._entries = []
        self._rebuild_list()
        self.app.log("Download history cleared.", "info")
