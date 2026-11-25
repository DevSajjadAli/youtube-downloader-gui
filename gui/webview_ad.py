"""Native Microsoft Edge WebView2 sidebar ad widget for CustomTkinter."""

import ctypes
import os
import threading
import webbrowser
import customtkinter as ctk


class SidebarAdWidget(ctk.CTkFrame):
    """
    Embeds a live Chromium (Edge WebView2) viewport directly inside a CTkFrame.
    Falls back to tkinterweb or a clickable banner if WebView2 is unavailable.
    """

    def __init__(self, master, url: str, width: int = 238, height: int = 238,
                 refresh_ms: int = 300_000, **kwargs):
        super().__init__(
            master,
            corner_radius=10,
            fg_color="#161625",
            border_width=1,
            border_color="#2D2D3A",
            **kwargs,
        )
        self.url = url
        self._width = width
        self._height = height
        self._refresh_ms = refresh_ms
        self._ctrl = None
        self._wv = None
        self._chwnd = None
        self._tkweb = None

        self.grid_columnconfigure(0, weight=1)

        # ── Header strip ─────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent", height=22)
        hdr.grid(row=0, column=0, sticky="ew", padx=6, pady=(5, 2))
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_propagate(False)

        ctk.CTkLabel(
            hdr, text="Sponsored",
            font=ctk.CTkFont(size=9), text_color="#6B7280"
        ).grid(row=0, column=0, sticky="w")

        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            btn_box, text="⟳", width=20, height=18, corner_radius=3,
            font=ctk.CTkFont(size=10), fg_color="transparent", hover_color="#1F2937",
            text_color="#6B7280", command=self.reload
        ).pack(side="left", padx=(0, 2))

        ctk.CTkButton(
            btn_box, text="↗", width=20, height=18, corner_radius=3,
            font=ctk.CTkFont(size=10), fg_color="transparent", hover_color="#1F2937",
            text_color="#6B7280", command=lambda: webbrowser.open(self.url)
        ).pack(side="left")

        # ── Viewport container ───────────────────────────────────────────────
        self.viewport = ctk.CTkFrame(
            self, width=self._width, height=self._height,
            corner_radius=6, fg_color="#0F172A"
        )
        self.viewport.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.viewport.grid_propagate(False)
        self.viewport.pack_propagate(False)

        # Defer embedding until Tk has a valid HWND
        self.after(150, self._init_embed)

    def _init_embed(self):
        if self._try_webview2():
            self.after(self._refresh_ms, self._auto_refresh)
            return
        if self._try_tkinterweb():
            self.after(self._refresh_ms, self._auto_refresh)
            return
        self._build_fallback()

    def _try_webview2(self) -> bool:
        """Embed real Edge WebView2 (Chromium) on a dedicated .NET STA thread."""
        try:
            import clr
            import webview

            clr.AddReference("System.Windows.Forms")
            clr.AddReference("System.Drawing")
            clr.AddReference("System.Threading")

            wv2_dir = os.path.join(os.path.dirname(webview.__file__), "lib")
            clr.AddReference(os.path.join(wv2_dir, "Microsoft.Web.WebView2.Core.dll"))
            clr.AddReference(os.path.join(wv2_dir, "Microsoft.Web.WebView2.WinForms.dll"))

            import System
            from System.Windows.Forms import Control, DockStyle, Application
            from System.Threading import Thread as NetThread, ThreadStart, ApartmentState
            from Microsoft.Web.WebView2.WinForms import WebView2 as NetWebView2, CoreWebView2CreationProperties

            self.viewport.update_idletasks()
            parent_hwnd = self.viewport.winfo_id()
            w = max(self.viewport.winfo_width(), self._width)
            h = max(self.viewport.winfo_height(), self._height)

            user_data = os.path.join(os.path.expanduser("~"), ".ytdl_pro", "webview2_cache")
            os.makedirs(user_data, exist_ok=True)

            ready = threading.Event()
            err_box = []

            def _sta_main():
                try:
                    ctrl = Control()
                    ctrl.Width = w
                    ctrl.Height = h

                    props = CoreWebView2CreationProperties()
                    props.UserDataFolder = user_data

                    wv = NetWebView2()
                    wv.CreationProperties = props
                    wv.Dock = DockStyle.Fill
                    ctrl.Controls.Add(wv)

                    chwnd = int(str(ctrl.Handle))
                    ctypes.windll.user32.SetParent(chwnd, parent_hwnd)
                    ctypes.windll.user32.MoveWindow(chwnd, 0, 0, w, h, True)

                    def _on_core_ready(sender, args):
                        try:
                            if args.IsSuccess and wv.CoreWebView2 is not None:
                                settings = wv.CoreWebView2.Settings
                                settings.AreDefaultContextMenusEnabled = False
                                settings.IsStatusBarEnabled = False

                                def _on_new_window(s, e):
                                    try:
                                        e.Handled = True
                                        if e.Uri:
                                            webbrowser.open(str(e.Uri))
                                    except Exception:
                                        pass

                                wv.CoreWebView2.NewWindowRequested += _on_new_window
                        except Exception:
                            pass

                    wv.CoreWebView2InitializationCompleted += _on_core_ready
                    wv.Source = System.Uri(self.url)

                    self._ctrl = ctrl
                    self._wv = wv
                    self._chwnd = chwnd
                    ready.set()
                    Application.Run()
                except Exception as exc:
                    err_box.append(exc)
                    ready.set()

            t = NetThread(ThreadStart(_sta_main))
            t.SetApartmentState(ApartmentState.STA)
            t.IsBackground = True
            t.Start()

            ready.wait(5)
            if err_box or not self._chwnd:
                return False

            self.viewport.bind("<Configure>", self._on_resize)
            self.bind("<Destroy>", self._on_destroy)
            return True
        except Exception:
            return False

    def _on_resize(self, _event=None):
        if self._chwnd:
            try:
                w = self.viewport.winfo_width()
                h = self.viewport.winfo_height()
                if w > 10 and h > 10:
                    ctypes.windll.user32.MoveWindow(self._chwnd, 0, 0, w, h, True)
            except Exception:
                pass

    def _on_destroy(self, event=None):
        if event is not None and event.widget is not self:
            return
        if self._ctrl and self._wv:
            try:
                from System import Action
                self._ctrl.BeginInvoke(Action(lambda: self._wv.Dispose()))
            except Exception:
                pass

    def _try_tkinterweb(self) -> bool:
        try:
            from tkinterweb import HtmlFrame
            web = HtmlFrame(
                self.viewport,
                messages_enabled=False,
                vertical_scrollbar=False,
                horizontal_scrollbar=False,
            )
            web.pack(fill="both", expand=True)
            web.load_url(self.url)
            self._tkweb = web
            return True
        except Exception:
            return False

    def _build_fallback(self):
        banner = ctk.CTkButton(
            self.viewport,
            text="🏆  Top 3 Deals\nBid Spotlight — View Now",
            font=ctk.CTkFont(size=11),
            corner_radius=8,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            command=lambda: webbrowser.open(self.url),
        )
        banner.pack(fill="both", expand=True)

    def reload(self):
        """Reload the live ad page."""
        if self._ctrl and self._wv:
            try:
                from System import Action
                self._ctrl.BeginInvoke(Action(lambda: self._wv.Reload()))
                return
            except Exception:
                pass
        if self._tkweb:
            try:
                self._tkweb.load_url(self.url)
            except Exception:
                pass

    def _auto_refresh(self):
        self.reload()
        self.after(self._refresh_ms, self._auto_refresh)
