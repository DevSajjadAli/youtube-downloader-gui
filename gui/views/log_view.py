import datetime
import customtkinter as ctk
from gui import icon_loader as icons


class LogView(ctk.CTkFrame):
    """Real-time scrolling log console with color-coded entries and icons."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 6))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="  Activity & Logs",
            image=icons.logs(26), compound="left",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            hdr,
            text="Live feed of all download actions, status updates, and system events",
            font=ctk.CTkFont(size=12), text_color="#6B7280", anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        ctk.CTkButton(
            hdr, text="Clear Logs", width=100, height=30,
            fg_color="#374151", hover_color="#4B5563",
            command=self.clear_logs
        ).grid(row=0, column=1, padx=(8, 0), rowspan=2, sticky="e")

        # ── Textbox ──────────────────────────────────────────────────────────
        self.textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            corner_radius=8
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=20, pady=(4, 20))

        self.textbox.tag_config("info",    foreground="#93C5FD")
        self.textbox.tag_config("success", foreground="#86EFAC")
        self.textbox.tag_config("warning", foreground="#FCD34D")
        self.textbox.tag_config("error",   foreground="#FCA5A5")
        self.textbox.tag_config("dim",     foreground="#4B5563")

        self.append_log("YouTube Downloader Pro initialized and ready.", "success")

    def append_log(self, message: str, level: str = "info"):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        tag = level.lower() if level.lower() in ("info", "success", "warning", "error") else "info"
        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"[{now}] ", "dim")
        self.textbox.insert("end", f"{message}\n", tag)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear_logs(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
