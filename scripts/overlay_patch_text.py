#!/usr/bin/env python3
"""
overlay_patch_text.py — add styled text to an embroidery patch image.

Usage:
  python overlay_patch_text.py <image_path> <text> [output_path]

The text is placed inside the existing black felt area, below the circular
patch illustration. The image keeps its original square dimensions.

Example:
  python overlay_patch_text.py overthinker.png OVERTHINKER
  python overlay_patch_text.py overthinker.png OVERTHINKER overthinker_final.png
"""

import sys
import os
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def add_patch_text(image_path: str, text: str, output_path: str = None) -> str:
    """
    Place bold uppercase text inside the black felt border at the bottom of
    the patch image. No extra canvas added — fits within existing space.
    """
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    # The circular patch sits in roughly the top 78% of the image.
    # We target the band from 79% to 95% for text placement.
    text_y_start = int(h * 0.79)
    text_area_height = int(h * 0.16)

    font_size = int(text_area_height * 0.60)
    font = load_font(font_size)

    draw = ImageDraw.Draw(img)

    # Measure and scale down if text is wider than 85% of the image
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    if text_w > w * 0.85:
        scale = (w * 0.85) / text_w
        font_size = int(font_size * scale)
        font = load_font(font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]

    text_h = bbox[3] - bbox[1]
    x = (w - text_w) // 2
    y = text_y_start + (text_area_height - text_h) // 2

    # Shadow (dark grey, 2px offset)
    draw.text((x + 2, y + 2), text, font=font, fill=(30, 30, 30, 200))
    # Main text: warm white — matches the white thread in the palette
    draw.text((x, y), text, font=font, fill=(240, 235, 220, 255))

    if output_path is None:
        base, ext = os.path.splitext(image_path)
        output_path = f"{base}_with_text{ext}"

    result = img.convert("RGB")
    result.save(output_path, quality=95)
    print(f"Saved: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    img_path = sys.argv[1]
    overlay_text = sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else None

    add_patch_text(img_path, overlay_text, out_path)
