"""Render one 4 KB half of a CHR bank as a 16-wide tile grid with hex tile indices.

Usage: python chr_labeled.py <bank 0-15> <half 0|1> [scale]
Output: chr/sheets/labeled_bankNN_hH.png  (tile index shown = index within the 4 KB page)
"""
import os
import sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAL = [(0, 0, 0), (110, 110, 110), (190, 190, 190), (255, 255, 255)]


def main():
    bank, half = int(sys.argv[1]), int(sys.argv[2])
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    data = open(os.path.join(ROOT, "chr", f"bank{bank:02d}.bin"), "rb").read()[half * 4096:(half + 1) * 4096]
    cell = 8 * scale + 2
    lab = 22
    img = Image.new("RGB", (lab + 16 * cell, lab + 16 * cell), (30, 30, 30))
    d = ImageDraw.Draw(img)
    for i in range(16):
        d.text((lab + i * cell + 4, 4), f"{i:X}", fill=(255, 220, 90))
        d.text((2, lab + i * cell + 4), f"{i:X}0", fill=(255, 220, 90))
    for t in range(256):
        tx, ty = lab + (t % 16) * cell, lab + (t // 16) * cell
        for y in range(8):
            lo, hi = data[t * 16 + y], data[t * 16 + y + 8]
            for x in range(8):
                v = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
                d.rectangle([tx + x * scale, ty + y * scale, tx + x * scale + scale - 1, ty + y * scale + scale - 1], fill=PAL[v])
    out = os.path.join(ROOT, "chr", "sheets", f"labeled_bank{bank:02d}_h{half}.png")
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
