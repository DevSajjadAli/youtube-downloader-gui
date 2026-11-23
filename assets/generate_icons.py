"""
Generate all application icons and assets programmatically using Pillow.
Run this script once to create all icon files needed by the GUI.
"""

import os
from PIL import Image, ImageDraw, ImageFont

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
TRANSPARENT = (0, 0, 0, 0)

SIZE = 64  # Base icon size; resize for use

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

def save(img, name, size=32):
    img_resized = img.resize((size, size), Image.Resampling.LANCZOS)
    img_resized.save(os.path.join(ICONS, f"{name}.png"))
    # Also save at base size
    if size != SIZE:
        img.save(os.path.join(ICONS, f"{name}_64.png"))


# ── 1. icon_video — film strip ─────────────────────────────────────────────────
def make_video():
    img = new_img()
    d = ImageDraw.Draw(img)
    # Background circle
    d.ellipse([4, 4, 60, 60], fill=BLUE_MAIN)
    # Play triangle
    pts = [(22, 16), (22, 48), (50, 32)]
    d.polygon(pts, fill=WHITE)
    return img

# ── 2. icon_playlist — list lines with bullet ─────────────────────────────────
def make_playlist():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=PURPLE)
    for i, y in enumerate([18, 30, 42]):
        d.ellipse([13, y-4, 21, y+4], fill=WHITE)
        d.rectangle([26, y-3, 52, y+3], fill=WHITE)
    return img

# ── 3. icon_queue — stacked layers ────────────────────────────────────────────
def make_queue():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=TEAL)
    # Three stacked rounded rects
    for i, y in enumerate([14, 26, 38]):
        rounded_rect(d, [12, y, 52, y+9], 3, (255,255,255,200 if i < 2 else 255))
    return img

# ── 4. icon_settings — gear ────────────────────────────────────────────────────
def make_settings():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=GRAY)
    # Gear: outer teeth + inner circle
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

# ── 5. icon_logs — document with lines ────────────────────────────────────────
def make_logs():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=AMBER_WARN)
    # Document body
    rounded_rect(d, [16, 12, 48, 52], 4, WHITE)
    for y in [22, 29, 36, 43]:
        d.rectangle([21, y, 43, y+3], fill=AMBER_WARN)
    return img

# ── 6. icon_history — clock with arrow ────────────────────────────────────────
def make_history():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=ORANGE)
    d.ellipse([12, 12, 52, 52], outline=WHITE, width=4)
    d.line([32, 32, 32, 18], fill=WHITE, width=3)
    d.line([32, 32, 44, 32], fill=WHITE, width=3)
    # Arrow indicating history
    d.polygon([(12, 32), (8, 25), (8, 39)], fill=WHITE)
    return img

# ── 7. icon_download — arrow down into tray ────────────────────────────────────
def make_download():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=BLUE_MAIN)
    # Arrow body
    d.rectangle([27, 12, 37, 36], fill=WHITE)
    # Arrowhead
    d.polygon([(18, 36), (32, 52), (46, 36)], fill=WHITE)
    # Tray
    d.rectangle([12, 50, 52, 56], fill=WHITE)
    return img

# ── 8. icon_paste — clipboard ─────────────────────────────────────────────────
def make_paste():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=GRAY)
    rounded_rect(d, [16, 18, 48, 54], 4, WHITE)
    # Clip at top
    rounded_rect(d, [24, 12, 40, 24], 4, (180,180,180,255))
    for y in [29, 36, 43]:
        d.rectangle([22, y, 42, y+3], fill=GRAY)
    return img

# ── 9. icon_folder — open folder ──────────────────────────────────────────────
def make_folder():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=AMBER_WARN)
    # Folder body
    rounded_rect(d, [10, 26, 54, 52], 4, WHITE)
    # Folder tab
    rounded_rect(d, [10, 18, 32, 28], 4, WHITE)
    return img

# ── 10. icon_cancel — X in circle ─────────────────────────────────────────────
def make_cancel():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=(180, 30, 30, 255))
    d.line([18, 18, 46, 46], fill=WHITE, width=5)
    d.line([46, 18, 18, 46], fill=WHITE, width=5)
    return img

# ── 11. icon_check — checkmark ────────────────────────────────────────────────
def make_check():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=GREEN_OK)
    d.line([14, 34, 26, 46], fill=WHITE, width=5)
    d.line([26, 46, 50, 20], fill=WHITE, width=5)
    return img

# ── 12. icon_warning — triangle ! ─────────────────────────────────────────────
def make_warning():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.polygon([(32, 4), (60, 58), (4, 58)], fill=AMBER_WARN)
    d.rectangle([29, 22, 35, 40], fill=BG_DARK)
    d.ellipse([29, 44, 35, 50], fill=BG_DARK)
    return img

# ── 13. icon_error — circle X ─────────────────────────────────────────────────
def make_error():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=(220, 38, 38, 255))
    d.line([18, 18, 46, 46], fill=WHITE, width=5)
    d.line([46, 18, 18, 46], fill=WHITE, width=5)
    return img

# ── 14. icon_speed — speedometer ──────────────────────────────────────────────
def make_speed():
    img = new_img()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=(56, 189, 248, 255))
    import math
    cx, cy, r = 32, 38, 20
    # Arc background
    for angle in range(210, 331):
        rad = math.radians(angle)
        x = cx + r * math.cos(rad)
        y = cy + r * math.sin(rad)
        d.ellipse([x-2, y-2, x+2, y+2], fill=WHITE)
    # Needle
    needle_ang = math.radians(270)
    nx = cx + (r-4) * math.cos(needle_ang)
    ny = cy + (r-4) * math.sin(needle_ang)
    d.line([cx, cy, nx, ny], fill=(255, 100, 100), width=3)
    d.ellipse([cx-4, cy-4, cx+4, cy+4], fill=WHITE)
    return img

# ── 15. Main logo + small logo ────────────────────────────────────────────────
def make_logo(size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    # Rounded background
    rounded_rect(d, [0, 0, s, s], s // 10, RED_BRAND)
    # White play button
    margin = s // 5
    pts = [
        (margin + s//12, margin),
        (margin + s//12, s - margin),
        (s - margin, s // 2)
    ]
    d.polygon(pts, fill=WHITE)
    # Small download arrow at bottom
    aw = s // 5
    ax = s // 2 - aw // 2
    ay = s - margin - s // 10
    d.rectangle([ax + aw//3, ay - aw//2, ax + 2*aw//3, ay], fill=RED_BRAND)
    d.polygon([(ax, ay), (ax + aw//2, ay + aw//3), (ax + aw, ay)], fill=RED_BRAND)
    return img


# ── Generate all icons ────────────────────────────────────────────────────────
print("Generating icons...")

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
    print(f"  ✓ {name}.png")

# Main logo
logo = make_logo(512)
logo.save(os.path.join(ASSETS, "logo.png"))
logo.resize((128, 128), Image.Resampling.LANCZOS).save(os.path.join(ASSETS, "logo_small.png"))
print("  ✓ logo.png (512px)")
print("  ✓ logo_small.png (128px)")

# Windows .ico (multi-resolution)
icon_base = make_logo(256)
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
icon_imgs = [icon_base.resize(s, Image.Resampling.LANCZOS) for s in sizes]
# Convert to RGB+palette for .ico compatibility
rgb_imgs = []
for im in icon_imgs:
    bg = Image.new("RGB", im.size, (30, 30, 46))
    bg.paste(im, mask=im.split()[3])
    rgb_imgs.append(bg)
rgb_imgs[0].save(
    os.path.join(ASSETS, "icon.ico"),
    format="ICO",
    sizes=sizes,
    append_images=rgb_imgs[1:]
)
icon_base.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(ASSETS, "icon.png"))
print("  ✓ icon.ico (multi-resolution)")
print("  ✓ icon.png (256px)")
print("\nAll icons generated successfully!")
