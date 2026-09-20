"""Dump each 8 KB CHR bank as a 16x32 tile sheet PNG (2 pattern tables side by side
would be 128 px wide each; here we lay out 32 tiles per row for easy reading).

Usage: python chr_sheets.py [scale]
Output: chr/sheets/bankNN.png
"""
import os
import sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHR = os.path.join(ROOT, "chr")
OUT = os.path.join(CHR, "sheets")
PAL = [(0, 0, 0), (110, 110, 110), (190, 190, 190), (255, 255, 255)]
COLS = 32


def decode_tile(b):
    """16 bytes -> 8x8 list of 2-bit pixels."""
    px = []
    for y in range(8):
        lo, hi = b[y], b[y + 8]
        px.append([((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1) for x in range(8)])
    return px


def sheet(data, scale):
    n = len(data) // 16
    rows = (n + COLS - 1) // COLS
    img = Image.new("RGB", (COLS * 8, rows * 8), PAL[0])
    for t in range(n):
        tx, ty = (t % COLS) * 8, (t // COLS) * 8
        for y, row in enumerate(decode_tile(data[t * 16:t * 16 + 16])):
            for x, v in enumerate(row):
                img.putpixel((tx + x, ty + y), PAL[v])
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


def main():
    scale = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    os.makedirs(OUT, exist_ok=True)
    for name in sorted(os.listdir(CHR)):
        if name.startswith("bank") and name.endswith(".bin"):
            data = open(os.path.join(CHR, name), "rb").read()
            path = os.path.join(OUT, name.replace(".bin", ".png"))
            sheet(data, scale).save(path)
            print(path)


if __name__ == "__main__":
    main()
