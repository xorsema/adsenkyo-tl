"""Render the kanji glyphs (2x2 tile blocks at tiles 0x84.., TL TR BL BR) of a 4 KB CHR page.

Usage: python kanji_sheet.py <page 0-31> [scale]
Glyph k (code 0x84+k) uses tiles 0x84+4k .. 0x87+4k, i.e. TL=t, TR=t+1, BL=t+2, BR=t+3.
Output: chr/sheets/kanji_pNN.png
"""
import os
import sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FG, BG = (255, 255, 255), (20, 20, 20)


def main():
    page = int(sys.argv[1])
    scale = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    chr_ = b"".join(open(os.path.join(ROOT, "chr", f"bank{i:02d}.bin"), "rb").read() for i in range(16))
    p = chr_[page * 4096:(page + 1) * 4096]
    n = 31                       # codes 0x84..0xA2 fit before tile 0x100
    cols = 8
    cw = 16 * scale + 8
    ch = 16 * scale + 22
    rows = (n + cols - 1) // cols
    img = Image.new("RGB", (cols * cw, rows * ch), (40, 40, 40))
    d = ImageDraw.Draw(img)
    for k in range(n):
        t0 = 0x84 + 4 * k
        ox, oy = (k % cols) * cw + 4, (k // cols) * ch + 16
        d.text((ox, oy - 14), f"{0x84 + k:02X}", fill=(255, 220, 90))
        for q, (dx, dy) in enumerate(((0, 0), (8, 0), (0, 8), (8, 8))):
            t = t0 + q
            for y in range(8):
                row = p[t * 16 + y]                      # plane 0 = glyph shape
                for x in range(8):
                    c = FG if (row >> (7 - x)) & 1 else BG
                    X, Y = ox + (dx + x) * scale, oy + (dy + y) * scale
                    d.rectangle([X, Y, X + scale - 1, Y + scale - 1], fill=c)
    out = os.path.join(ROOT, "chr", "sheets", f"kanji_p{page:02d}.png")
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
