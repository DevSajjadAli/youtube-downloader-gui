"""
Generate all application icons and assets programmatically using Pillow.
Run this script once to create all icon files needed by the GUI.
"""

import os
from PIL import Image, ImageDraw

ASSETS = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(ASSETS, "icons")
os.makedirs(ICONS, exist_ok=True)

# ── Color Palette ──────────────────────────────────────────────────────────────
BG_DARK    = (30, 30, 46)
RED_BRAND  = (220, 38, 38)
BLUE_MAIN  = (37, 99, 235)
GREEN_OK   = (34, 197, 94)
AMBER_WARN = (245, 158, 11)
PURPLE     = (139, 92, 246)
TEAL       = (20, 184, 166)
ORANGE     = (249, 115, 22)
GRAY       = (100, 116, 139)
WHITE      = (255, 255, 255)
SIZE = 64

def new_img(size=SIZE):
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))

def rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    r = radius
    draw.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill)
    draw.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill)
    draw.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill)
    draw.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill)
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)

def safe_save(img, path, **kwargs):
    try:
        img.save(path, **kwargs)
    except Exception:
        pass

def save(img, name, size=32):
    img_resized = img.resize((size, size), Image.Resampling.LANCZOS)
    safe_save(img_resized, os.path.join(ICONS, f"{name}.png"))
    if size != SIZE:
        safe_save(img, os.path.join(ICONS, f"{name}_64.png"))

def make_video():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=BLUE_MAIN)
    d.polygon([(22, 16), (22, 48), (50, 32)], fill=WHITE)
    return img

def make_playlist():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=PURPLE)
    for y in [18, 30, 42]:
        d.ellipse([13, y-4, 21, y+4], fill=WHITE)
        d.rectangle([26, y-3, 52, y+3], fill=WHITE)
    return img

def make_queue():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=TEAL)
    for i, y in enumerate([14, 26, 38]):
        rounded_rect(d, [12, y, 52, y+9], 3, (255,255,255,200 if i < 2 else 255))
    return img

def make_settings():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=GRAY)
    cx, cy, ro, ri = 32, 32, 20, 11
    import math
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        tx = cx + ro * math.cos(rad)
        ty = cy + ro * math.sin(rad)
        d.ellipse([tx-5, ty-5, tx+5, ty+5], fill=WHITE)
    d.ellipse([cx-ri, cy-ri, cx+ri, cy+ri], fill=GRAY)
    d.ellipse([cx-7, cy-7, cx+7, cy+7], fill=WHITE)
    return img

def make_logs():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=AMBER_WARN)
    rounded_rect(d, [16, 12, 48, 52], 4, WHITE)
    for y in [22, 29, 36, 43]:
        d.rectangle([21, y, 43, y+3], fill=AMBER_WARN)
    return img

def make_history():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=ORANGE)
    d.ellipse([12, 12, 52, 52], outline=WHITE, width=4)
    d.line([32, 32, 32, 18], fill=WHITE, width=3)
    d.line([32, 32, 44, 32], fill=WHITE, width=3)
    d.polygon([(12, 32), (8, 25), (8, 39)], fill=WHITE)
    return img

def make_download():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=BLUE_MAIN)
    d.rectangle([27, 12, 37, 36], fill=WHITE)
    d.polygon([(18, 36), (32, 52), (46, 36)], fill=WHITE)
    d.rectangle([12, 50, 52, 56], fill=WHITE)
    return img

def make_paste():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=GRAY)
    rounded_rect(d, [16, 18, 48, 54], 4, WHITE)
    rounded_rect(d, [24, 12, 40, 24], 4, (180,180,180,255))
    for y in [29, 36, 43]:
        d.rectangle([22, y, 42, y+3], fill=GRAY)
    return img

def make_folder():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=AMBER_WARN)
    rounded_rect(d, [10, 26, 54, 52], 4, WHITE)
    rounded_rect(d, [10, 18, 32, 28], 4, WHITE)
    return img

def make_cancel():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=(180, 30, 30, 255))
    d.line([18, 18, 46, 46], fill=WHITE, width=5)
    d.line([46, 18, 18, 46], fill=WHITE, width=5)
    return img

def make_check():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=GREEN_OK)
    d.line([14, 34, 26, 46], fill=WHITE, width=5)
    d.line([26, 46, 50, 20], fill=WHITE, width=5)
    return img

def make_warning():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.polygon([(32, 4), (60, 58), (4, 58)], fill=AMBER_WARN)
    d.rectangle([29, 22, 35, 40], fill=BG_DARK)
    d.ellipse([29, 44, 35, 50], fill=BG_DARK)
    return img

def make_error():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=(220, 38, 38, 255))
    d.line([18, 18, 46, 46], fill=WHITE, width=5)
    d.line([46, 18, 18, 46], fill=WHITE, width=5)
    return img

def make_speed():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=(56, 189, 248, 255))
    import math
    cx, cy, r = 32, 38, 20
    for angle in range(210, 331):
        rad = math.radians(angle)
        x = cx + r * math.cos(rad)
        y = cy + r * math.sin(rad)
        d.ellipse([x-2, y-2, x+2, y+2], fill=WHITE)
    needle_ang = math.radians(270)
    nx = cx + (r-4) * math.cos(needle_ang)
    ny = cy + (r-4) * math.sin(needle_ang)
    d.line([cx, cy, nx, ny], fill=(255, 100, 100), width=3)
    d.ellipse([cx-4, cy-4, cx+4, cy+4], fill=WHITE)
    return img

def make_logo(size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    rounded_rect(d, [0, 0, s, s], s // 10, RED_BRAND)
    margin = s // 5
    pts = [
        (margin + s//12, margin),
        (margin + s//12, s - margin),
        (s - margin, s // 2)
    ]
    d.polygon(pts, fill=WHITE)
    aw = s // 5
    ax = s // 2 - aw // 2
    ay = s - margin - s // 10
    d.rectangle([ax + aw//3, ay - aw//2, ax + 2*aw//3, ay], fill=RED_BRAND)
    d.polygon([(ax, ay), (ax + aw//2, ay + aw//3), (ax + aw, ay)], fill=RED_BRAND)
    return img

def main():
    icons_map = {
        "icon_video":    make_video(),
        "icon_playlist": make_playlist(),
        "icon_queue":    make_queue(),
        "icon_settings": make_settings(),
        "icon_logs":     make_logs(),
        "icon_history":  make_history(),
        "icon_download": make_download(),
        "icon_paste":    make_paste(),
        "icon_folder":   make_folder(),
        "icon_cancel":   make_cancel(),
        "icon_check":    make_check(),
        "icon_warning":  make_warning(),
        "icon_error":    make_error(),
        "icon_speed":    make_speed(),
    }

    for name, img in icons_map.items():
        save(img, name, 32)

    logo = make_logo(512)
    safe_save(logo, os.path.join(ASSETS, "logo.png"))
    safe_save(logo.resize((128, 128), Image.Resampling.LANCZOS), os.path.join(ASSETS, "logo_small.png"))

    icon_base = make_logo(256)
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon_imgs = [icon_base.resize(s, Image.Resampling.LANCZOS) for s in sizes]
    rgb_imgs = []
    for im in icon_imgs:
        bg = Image.new("RGB", im.size, (30, 30, 46))
        bg.paste(im, mask=im.split()[3])
        rgb_imgs.append(bg)
    try:
        rgb_imgs[0].save(
            os.path.join(ASSETS, "icon.ico"),
            format="ICO",
            sizes=sizes,
            append_images=rgb_imgs[1:]
        )
    except Exception:
        pass
    safe_save(icon_base.resize((256, 256), Image.Resampling.LANCZOS), os.path.join(ASSETS, "icon.png"))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
