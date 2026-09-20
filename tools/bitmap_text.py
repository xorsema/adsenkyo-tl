"""Replace Japanese *bitmap* text (pictures made of CHR tiles) with English.

Each patch names a CHR page and a list of tile columns; every column is a (top tile, bottom tile) pair
that together form one 8x16 cell. Letters are drawn as tall, narrow 8x16 capitals (the project's 6x7 caps,
stretched vertically). Sprite tiles use colour 1 only (plane1 = 0), like the originals.

PATCHES lists what is patched; see notes/bitmap_text.md for how each was found.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latin_font

# (page, label, [(top, bottom) x N columns], text)   text uses one letter per column; ' ' = blank column
PATCHES = [
    # party labels on the candidate screens (sprites, palette 1 = Republican/blue, 2 = Democratic/red).
    # Both labels share their 3rd glyph (党 = tiles B0-B3), which is blanked; the 4 unique columns carry the text.
    (0, "Republican label", [(0xA8, 0xAA), (0xA9, 0xAB), (0xAC, 0xAE), (0xAD, 0xAF)], "REP."),
    (0, "Democratic label", [(0xB4, 0xB6), (0xB5, 0xB7), (0xB8, 0xBA), (0xB9, 0xBB)], "DEM."),
    (0, "shared 'party' glyph (blanked)", [(0xB0, 0xB2), (0xB1, 0xB3)], "  "),
]


def letter_rows(ch):
    """16 row bytes for one 8x16 cell."""
    rows = [0] * 16
    if ch == " ":
        return rows
    if ch == ".":
        for y in (12, 13):
            rows[y] = 0b00011000
        return rows
    src = latin_font.CAPS[ch]                    # 7 rows x 6 columns
    for i, r in enumerate(src):
        v = 0
        for c, px in enumerate(r):
            if px == "#":
                v |= 1 << (7 - (1 + c))
        rows[1 + 2 * i] = v                      # each source row becomes two rows (1..14)
        rows[2 + 2 * i] = v
    return rows


def tile_pair(ch):
    r = letter_rows(ch)
    top = bytes(r[:8]) + bytes(8)                # plane0 = shape, plane1 = 0
    bot = bytes(r[8:]) + bytes(8)
    return top, bot


def apply(rom, chr0):
    """Patch a bytearray ROM (chr0 = file offset of CHR data). Returns the list of changed tile numbers per page."""
    changed = {}
    for page, _label, cols, text in PATCHES:
        assert len(cols) == len(text), _label
        for (t_top, t_bot), ch in zip(cols, text):
            top, bot = tile_pair(ch)
            for tile, data in ((t_top, top), (t_bot, bot)):
                o = chr0 + page * 4096 + tile * 16
                rom[o:o + 16] = data
                changed.setdefault(page, []).append(tile)
    return changed


def preview(path):
    from PIL import Image
    img = Image.new("L", (4 * 8 * 6, 16 * 6 * 2 + 6), 60)
    for row, text in enumerate(("REP.", "DEM.")):
        for k, ch in enumerate(text):
            r = letter_rows(ch)
            for y in range(16):
                for x in range(8):
                    if (r[y] >> (7 - x)) & 1:
                        for dy in range(6):
                            for dx in range(6):
                                img.putpixel(((k * 8 + x) * 6 + dx, (row * 16 + y) * 6 + dy + row * 6), 255)
    img.save(path)


if __name__ == "__main__":
    out = os.path.join(latin_font.ROOT, "chr", "sheets", "party_labels_preview.png")
    preview(out)
    print(out)
