"""Live JSON-driven Bid Spotlight sidebar ad widget for CustomTkinter."""

import concurrent.futures
import io
import json
import threading
import urllib.request
import webbrowser
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps


_ADS_JSON_URL = "https://bidspotlight.com/ads.json"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_RANK_COLORS = {
    1: ("#F5B301", "#111827"),  # Gold
    2: ("#9CA3AF", "#111827"),  # Silver
    3: ("#D97706", "#FFFFFF"),  # Bronze
}


def _fetch_bytes(url: str, timeout: int = 12) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _round_image(img: Image.Image, size: tuple[int, int], radius: int = 8) -> Image.Image:
    """Resize/crop image with aspect-fill and apply rounded corners."""
    fitted = ImageOps.fit(img.convert("RGBA"), size, method=Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(fitted, (0, 0), mask)
    return out


def _make_rank_badge(rank: int, size: int = 18) -> ctk.CTkImage:
    """Draw a crisp circular rank disc (1=Gold, 2=Silver, 3=Bronze)."""
    bg, _fg = _RANK_COLORS.get(rank, ("#6B7280", "#FFFFFF"))
    scale = 3
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, s - 1, s - 1), fill=bg)
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


class SidebarAdWidget(ctk.CTkFrame):
    """
    Fetches https://bidspotlight.com/ads.json on startup and periodically,
    rendering the Bid Spotlight 1x1 layout (#1 Hero + Brand bar + #2/#3 Mini cards).
    Automatically updates the UI whenever ads.json listings change.
    """

    def __init__(
        self,
        master,
        url: str = _ADS_JSON_URL,
        width: int = 235,
        height: int = 250,
        refresh_ms: int = 300_000,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=10,
            fg_color="#131522",
            border_width=1,
            border_color="#262A3E",
            **kwargs,
        )
        self.json_url = _ADS_JSON_URL if "ads1x1" in url else url
        self._width = width
        self._refresh_ms = refresh_ms
        self._last_signature = None
        self._image_refs: list = []
        self._fetching = False

        self.grid_columnconfigure(0, weight=1)

        # ── Top utility bar ──────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent", height=20)
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(5, 2))
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_propagate(False)

        ctk.CTkLabel(
            hdr, text="Sponsored",
            font=ctk.CTkFont(size=9, weight="bold"), text_color="#6B7280"
        ).grid(row=0, column=0, sticky="w")

        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            btn_box, text="⟳", width=20, height=16, corner_radius=3,
            font=ctk.CTkFont(size=10), fg_color="transparent", hover_color="#1F2937",
            text_color="#6B7280", command=lambda: self.refresh(force=True)
        ).pack(side="left", padx=(0, 2))

        ctk.CTkButton(
            btn_box, text="↗", width=20, height=16, corner_radius=3,
            font=ctk.CTkFont(size=10), fg_color="transparent", hover_color="#1F2937",
            text_color="#6B7280", command=lambda: webbrowser.open("https://bidspotlight.com/ads1x1")
        ).pack(side="left")

        # ── Dynamic content container ────────────────────────────────────────
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.body.grid_columnconfigure(0, weight=1)

        self._show_loading()

        # Fetch immediately on startup, then auto-poll
        self.after(100, lambda: self.refresh(force=True))
        self.after(self._refresh_ms, self._auto_poll)

    # ── Data Fetching ────────────────────────────────────────────────────────

    def _auto_poll(self):
        self.refresh(force=False)
        self.after(self._refresh_ms, self._auto_poll)

    def refresh(self, force: bool = False):
        """Fetch ads.json in a background thread and update UI if data changed."""
        if self._fetching:
            return
        self._fetching = True

        def _worker():
            try:
                raw = _fetch_bytes(self.json_url, timeout=12)
                data = json.loads(raw.decode("utf-8"))
                top = (data.get("top") or [])[:3]
                site = data.get("site") or {}

                sig = tuple(
                    (
                        item.get("position"),
                        item.get("name"),
                        item.get("url") or item.get("listing_url"),
                        item.get("ad_image_url") or item.get("image_url"),
                        item.get("price"),
                    )
                    for item in top
                )

                if not force and sig == self._last_signature:
                    return

                # Download images in parallel while off the UI thread
                def _dl_img(idx_item):
                    idx, item = idx_item
                    img_url = item.get("ad_image_url") or item.get("image_url") or item.get("card_image_url")
                    if not img_url:
                        return idx, None
                    try:
                        img_bytes = _fetch_bytes(img_url, timeout=12)
                        return idx, Image.open(io.BytesIO(img_bytes))
                    except Exception:
                        return idx, None

                images = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                    for idx, im in pool.map(_dl_img, enumerate(top)):
                        images[idx] = im

                self.after(0, lambda: self._render_ads(data, top, site, images, sig))
            except Exception:
                if self._last_signature is None:
                    self.after(0, self._show_fallback)
            finally:
                self._fetching = False

        threading.Thread(target=_worker, daemon=True).start()

    # ── UI Rendering ─────────────────────────────────────────────────────────

    def _clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._image_refs.clear()

    def _show_loading(self):
        self._clear_body()
        ctk.CTkLabel(
            self.body, text="Loading live deals...",
            font=ctk.CTkFont(size=10), text_color="#6B7280", height=120
        ).grid(row=0, column=0, sticky="ew")

    def _show_fallback(self):
        self._clear_body()
        ctk.CTkButton(
            self.body,
            text="🏆  Bid Spotlight\nView Top 3 Live Deals",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=74, corner_radius=8,
            fg_color="#1E3A8A", hover_color="#1D4ED8",
            command=lambda: webbrowser.open("https://bidspotlight.com/ads1x1"),
        ).grid(row=0, column=0, sticky="ew")

    def _bind_click(self, widget, url: str):
        widget.configure(cursor="hand2")
        widget.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))
        for child in widget.winfo_children():
            self._bind_click(child, url)

    def _render_ads(self, data: dict, top: list, site: dict, images: dict, sig: tuple):
        if not top:
            self._show_fallback()
            return

        self._last_signature = sig
        self._clear_body()

        # ── 1. Hero Card (#1) ────────────────────────────────────────────────
        hero = top[0]
        hero_url = hero.get("url") or hero.get("listing_url") or site.get("homepage", "https://bidspotlight.com")
        hero_card = ctk.CTkFrame(
            self.body, corner_radius=8, fg_color="#1A1D2E",
            border_width=1, border_color="#2E334D"
        )
        hero_card.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        hero_card.grid_columnconfigure(0, weight=1)

        hero_w = max(self._width - 20, 200)
        hero_h = 66
        pil_hero = images.get(0)
        if pil_hero is not None:
            rounded = _round_image(pil_hero, (hero_w, hero_h), radius=6)
            ctk_img = ctk.CTkImage(light_image=rounded, dark_image=rounded, size=(hero_w, hero_h))
            self._image_refs.append(ctk_img)
            ctk.CTkLabel(hero_card, image=ctk_img, text="").grid(
                row=0, column=0, sticky="ew", padx=3, pady=(3, 0)
            )

        hero_bar = ctk.CTkFrame(hero_card, fg_color="transparent")
        hero_bar.grid(row=1, column=0, sticky="ew", padx=6, pady=(3, 4))
        hero_bar.grid_columnconfigure(1, weight=1)

        badge1 = _make_rank_badge(1, size=16)
        self._image_refs.append(badge1)
        ctk.CTkLabel(
            hero_bar, image=badge1, text="1",
            font=ctk.CTkFont(size=9, weight="bold"), text_color="#111827"
        ).grid(row=0, column=0, rowspan=2, padx=(0, 5), sticky="n", pady=(1, 0))

        name1 = (hero.get("name") or "Featured").strip()
        if len(name1) > 17:
            name1 = name1[:16] + "…"
        tag1 = (hero.get("tagline") or hero.get("domain") or "").strip()
        if len(tag1) > 22:
            tag1 = tag1[:21] + "…"

        ctk.CTkLabel(
            hero_bar, text=name1, anchor="w", height=14,
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#F9FAFB"
        ).grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(
            hero_bar, text=tag1, anchor="w", height=12,
            font=ctk.CTkFont(size=8), text_color="#9CA3AF"
        ).grid(row=1, column=1, sticky="ew")

        price1 = (hero.get("price") or "").strip()
        if price1:
            if len(price1) > 13:
                price1 = price1[:12] + "…"
            pill = ctk.CTkFrame(hero_bar, fg_color="#23273D", corner_radius=4)
            pill.grid(row=0, column=2, rowspan=2, padx=(4, 0), sticky="e")
            ctk.CTkLabel(
                pill, text=price1, height=14,
                font=ctk.CTkFont(size=8, weight="bold"),
                text_color="#F5B301"
            ).pack(padx=5, pady=1)

        self._bind_click(hero_card, hero_url)

        # ── 2. Brand Strip ("Bid Spotlight  ────  Top 3") ────────────────────
        brand_row = ctk.CTkFrame(self.body, fg_color="transparent", height=16)
        brand_row.grid(row=1, column=0, sticky="ew", pady=(0, 3))
        brand_row.grid_columnconfigure(1, weight=1)

        brand_title = ctk.CTkFrame(brand_row, fg_color="transparent")
        brand_title.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            brand_title, text="Bid ", height=14,
            font=ctk.CTkFont(size=9, weight="bold"), text_color="#F9FAFB"
        ).pack(side="left")
        ctk.CTkLabel(
            brand_title, text="Spotlight", height=14,
            font=ctk.CTkFont(size=9, weight="bold"), text_color="#F5B301"
        ).pack(side="left")

        ctk.CTkFrame(brand_row, height=1, fg_color="#2D3148").grid(
            row=0, column=1, sticky="ew", padx=6
        )

        ctk.CTkLabel(
            brand_row, text="Top 3", height=14,
            font=ctk.CTkFont(size=8), text_color="#6B7280"
        ).grid(row=0, column=2, sticky="e")

        self._bind_click(brand_row, site.get("homepage", "https://bidspotlight.com"))

        # ── 3. Bottom Row: #2 and #3 Mini Cards ──────────────────────────────
        if len(top) > 1:
            mini_row = ctk.CTkFrame(self.body, fg_color="transparent")
            mini_row.grid(row=2, column=0, sticky="ew")
            mini_row.grid_columnconfigure(0, weight=1, uniform="mini")
            mini_row.grid_columnconfigure(1, weight=1, uniform="mini")

            mini_w = max((self._width - 28) // 2, 92)
            mini_h = 38

            for idx in range(1, min(3, len(top))):
                item = top[idx]
                rank = item.get("position") or (idx + 1)
                item_url = item.get("url") or item.get("listing_url") or site.get("homepage", "https://bidspotlight.com")

                card = ctk.CTkFrame(
                    mini_row, corner_radius=7, fg_color="#1A1D2E",
                    border_width=1, border_color="#2E334D"
                )
                pad = (0, 3) if idx == 1 else (3, 0)
                card.grid(row=0, column=idx - 1, sticky="nsew", padx=pad)
                card.grid_columnconfigure(0, weight=1)

                pil_mini = images.get(idx)
                if pil_mini is not None:
                    rounded = _round_image(pil_mini, (mini_w, mini_h), radius=5)
                    ctk_m = ctk.CTkImage(light_image=rounded, dark_image=rounded, size=(mini_w, mini_h))
                    self._image_refs.append(ctk_m)
                    ctk.CTkLabel(card, image=ctk_m, text="").grid(
                        row=0, column=0, sticky="ew", padx=2, pady=(2, 0)
                    )

                info = ctk.CTkFrame(card, fg_color="transparent")
                info.grid(row=1, column=0, sticky="ew", padx=4, pady=(2, 3))
                info.grid_columnconfigure(1, weight=1)

                badge = _make_rank_badge(rank, size=14)
                self._image_refs.append(badge)
                _, fg_txt = _RANK_COLORS.get(rank, ("#6B7280", "#FFFFFF"))
                ctk.CTkLabel(
                    info, image=badge, text=str(rank),
                    font=ctk.CTkFont(size=8, weight="bold"), text_color=fg_txt
                ).grid(row=0, column=0, rowspan=2, padx=(0, 4), sticky="n", pady=(1, 0))

                m_name = (item.get("name") or "Listing").strip()
                if len(m_name) > 11:
                    m_name = m_name[:10] + "…"
                m_price = (item.get("price") or item.get("domain") or "").strip()
                if len(m_price) > 12:
                    m_price = m_price[:11] + "…"

                ctk.CTkLabel(
                    info, text=m_name, anchor="w", height=12,
                    font=ctk.CTkFont(size=9, weight="bold"), text_color="#F9FAFB"
                ).grid(row=0, column=1, sticky="ew")

                ctk.CTkLabel(
                    info, text=m_price, anchor="w", height=11,
                    font=ctk.CTkFont(size=8), text_color="#9CA3AF"
                ).grid(row=1, column=1, sticky="ew")

                self._bind_click(card, item_url)
