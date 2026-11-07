#!/usr/bin/env python3
"""Render a dark label bar PNG (Chinese-capable) for demo video composites.

Usage: make_label.py OUT.png WIDTH HEIGHT "line1" "line2" ...
Wrap text in {c}...{/c} to render that segment in cyan (legend color for the
reference ghost in ghost-comparison renders). Font auto-shrinks to fit width.
"""
import sys

from PIL import Image, ImageDraw, ImageFont

WHITE = (235, 235, 240)
CYAN = (0, 210, 230)


def load_font(size):
    for path in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def parse(line):
    segs, rest = [], line
    while rest:
        i = rest.find("{c}")
        if i < 0:
            segs.append((rest, WHITE))
            break
        if i > 0:
            segs.append((rest[:i], WHITE))
        rest = rest[i + 3:]
        j = rest.find("{/c}")
        if j < 0:
            segs.append((rest, CYAN))
            break
        segs.append((rest[:j], CYAN))
        rest = rest[j + 4:]
    return segs


def main():
    out, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    lines = sys.argv[4:]
    img = Image.new("RGB", (W, H), (16, 17, 22))
    d = ImageDraw.Draw(img)
    size = 28
    while size > 12:
        font = load_font(size)
        widths = [sum(d.textlength(t, font=font) for t, _ in parse(ln)) for ln in lines]
        if max(widths) <= W - 32:
            break
        size -= 1
    line_h = (H - 16) / len(lines)
    y = 8.0
    for ln in lines:
        x = 16.0
        for text, color in parse(ln):
            d.text((x, y + max(0.0, (line_h - size) / 2 - 2)), text, font=font, fill=color)
            x += d.textlength(text, font=font)
        y += line_h
    img.save(out)
    print(f"wrote {out} {W}x{H} font_size={size}")


if __name__ == "__main__":
    main()
