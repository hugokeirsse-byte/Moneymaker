#!/usr/bin/env python3
"""
overlay_patch_text.py — embroidery-style text on patch image.
Places outlined block letters (gold fill, navy stroke) in the lower
black felt area of an existing embroidery patch image.
Usage: python overlay_patch_text.py <image_path> <text> [output_path]
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arialbd.ttf",
]

# Embroidery palette: gold thread, navy outline — matches patch colors
COLOR_FILL      = (235, 185,  30, 255)  # gold thread
COLOR_OUTLINE   = ( 12,  18,  60, 255)  # deep navy border
COLOR_HIGHLIGHT = (255, 235, 120, 180)  # pale gold highlight (stitch texture)
OUTLINE_RADIUS  = 3                     # px — mimics embroidery border thread weight


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def add_patch_text(image_path, text, output_path=None):
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    # Lower black-felt area: ~79 – 95 % of image height
    text_y_start    = int(h * 0.795)
    text_area_height = int(h * 0.155)
    font_size       = int(text_area_height * 0.56)
    font            = load_font(font_size)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    # Fit text to 78 % of image width
    bbox   = draw.textbbox((0, 0), text, font=font, stroke_width=OUTLINE_RADIUS)
    text_w = bbox[2] - bbox[0]
    max_w  = w * 0.78
    if text_w > max_w:
        font_size = int(font_size * max_w / text_w)
        font      = load_font(font_size)
        bbox      = draw.textbbox((0, 0), text, font=font, stroke_width=OUTLINE_RADIUS)
        text_w    = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (w - text_w) // 2 - bbox[0]
    y = text_y_start + (text_area_height - text_h) // 2 - bbox[1]

    # Pass 1 — navy stroke + gold fill (embroidery outline)
    draw.text(
        (x, y), text, font=font,
        fill=COLOR_FILL,
        stroke_width=OUTLINE_RADIUS,
        stroke_fill=COLOR_OUTLINE,
    )
    # Pass 2 — pale-gold highlight offset for 3D stitch texture
    draw.text((x - 1, y - 1), text, font=font, fill=COLOR_HIGHLIGHT)

    img = Image.alpha_composite(img, overlay)
    if not output_path:
        base, ext = os.path.splitext(image_path)
        output_path = f"{base}_with_text{ext}"
    img.convert("RGB").save(output_path, quality=95)
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: overlay_patch_text.py <image> <text> [output]")
        sys.exit(1)
    out = add_patch_text(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(f"→ {out}")
