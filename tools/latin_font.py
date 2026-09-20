"""8x8 Latin font for the text pages, plus the English character table.

Tile format (matches the game's kana tiles): plane0 = glyph shape, plane1 = ~plane0
(glyph pixels colour 1, background colour 2).

Lowercase a-z is reused from the game's own Latin page (CHR page 7). Capitals and
punctuation are drawn here (6 columns wide at x=1..6, cap height rows 0-6, baseline
row 6 to match the game's lowercase).

Code assignment (kana slots are overwritten; existing digits 70-79, '.'=6F, '?'=7B, '%'=7A stay):
    ' '=00   a-z = 04..1D   ,!'-:()/";&$ = 1E..29   A-Z = 36..4F
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CAPS = {
    "A": [".####.", "#....#", "#....#", "######", "#....#", "#....#", "#....#"],
    "B": ["#####.", "#....#", "#....#", "#####.", "#....#", "#....#", "#####."],
    "C": [".####.", "#....#", "#.....", "#.....", "#.....", "#....#", ".####."],
    "D": ["#####.", "#....#", "#....#", "#....#", "#....#", "#....#", "#####."],
    "E": ["######", "#.....", "#.....", "#####.", "#.....", "#.....", "######"],
    "F": ["######", "#.....", "#.....", "#####.", "#.....", "#.....", "#....."],
    "G": [".####.", "#....#", "#.....", "#..###", "#....#", "#....#", ".####."],
    "H": ["#....#", "#....#", "#....#", "######", "#....#", "#....#", "#....#"],
    "I": [".####.", "..##..", "..##..", "..##..", "..##..", "..##..", ".####."],
    "J": ["....##", ".....#", ".....#", ".....#", ".....#", "#....#", ".####."],
    "K": ["#....#", "#...#.", "#..#..", "###...", "#..#..", "#...#.", "#....#"],
    "L": ["#.....", "#.....", "#.....", "#.....", "#.....", "#.....", "######"],
    "M": ["#....#", "##..##", "#.##.#", "#.##.#", "#....#", "#....#", "#....#"],
    "N": ["#....#", "##...#", "#.#..#", "#..#.#", "#...##", "#....#", "#....#"],
    "O": [".####.", "#....#", "#....#", "#....#", "#....#", "#....#", ".####."],
    "P": ["#####.", "#....#", "#....#", "#####.", "#.....", "#.....", "#....."],
    "Q": [".####.", "#....#", "#....#", "#....#", "#..#.#", "#...#.", ".###.#"],
    "R": ["#####.", "#....#", "#....#", "#####.", "#..#..", "#...#.", "#....#"],
    "S": [".####.", "#....#", "#.....", ".####.", ".....#", "#....#", ".####."],
    "T": ["######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
    "U": ["#....#", "#....#", "#....#", "#....#", "#....#", "#....#", ".####."],
    "V": ["#....#", "#....#", "#....#", "#....#", ".#..#.", ".#..#.", "..##.."],
    "W": ["#....#", "#....#", "#....#", "#.##.#", "#.##.#", "##..##", "#....#"],
    "X": ["#....#", ".#..#.", "..##..", "..##..", "..##..", ".#..#.", "#....#"],
    "Y": ["#....#", ".#..#.", "..##..", "..##..", "..##..", "..##..", "..##.."],
    "Z": ["######", ".....#", "....#.", "...#..", "..#...", "#.....", "######"],
}

# punctuation: up to 8 rows (row 0 first)
PUNCT = {
    ",": ["......", "......", "......", "......", "......", "..##..", "..##..", ".##..."],
    "!": ["..##..", "..##..", "..##..", "..##..", "..##..", "......", "..##.."],
    "'": ["..##..", "..##..", ".##...", "......", "......", "......", "......"],
    "-": ["......", "......", "......", ".####.", "......", "......", "......"],
    ":": ["......", "..##..", "..##..", "......", "......", "..##..", "..##.."],
    "(": ["...##.", "..##..", ".##...", ".##...", ".##...", "..##..", "...##."],
    ")": [".##...", "..##..", "...##.", "...##.", "...##.", "..##..", ".##..."],
    "/": [".....#", "....#.", "...#..", "..#...", ".#....", "#.....", "......"],
    '"': [".#..#.", ".#..#.", "......", "......", "......", "......", "......"],
    ";": ["......", "..##..", "..##..", "......", "......", "..##..", "..##..", ".##..."],
    "$": ["..##..", ".####.", "#.##..", ".###..", "..###.", "..##.#", ".####.", "..##.."],
    "&": [".###..", "#...#.", "#..#..", ".##...", "#..#.#", "#...#.", ".###.#"],
}

PUNCT_ORDER = ",!'-:()/\";&$"         # -> codes 1E..29

# game's own lowercase: char -> (page 7 tile)
LOWER_TILE = {c: 0xE0 + i for i, c in enumerate("abcdefghijklmnopqrstu")}
LOWER_TILE.update({"v": 0xA0, "w": 0xA1, "x": 0xF7, "y": 0xF8, "z": 0xF9})

CODE = {" ": 0x00}
CODE.update({c: 0x04 + i for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")})
CODE.update({c: 0x1E + i for i, c in enumerate(PUNCT_ORDER)})
CODE.update({c: 0x36 + i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")})
CODE.update({c: 0x70 + i for i, c in enumerate("0123456789")})
CODE.update({".": 0x6F, "?": 0x7B, "%": 0x7A})


def _rows_to_plane0(rows, x0=1):
    out = []
    for r in rows + ["......"] * (8 - len(rows)):
        v = 0
        for c, ch in enumerate(r):
            if ch == "#":
                v |= 1 << (7 - (x0 + c))
        out.append(v)
    return out


def tile_bytes(plane0_rows):
    return bytes(plane0_rows) + bytes((~b) & 0xFF for b in plane0_rows)


def lower_plane0():
    chr_ = b"".join(open(os.path.join(ROOT, "chr", f"bank{i:02d}.bin"), "rb").read() for i in range(16))
    p7 = chr_[7 * 4096:8 * 4096]
    return {c: list(p7[t * 16:t * 16 + 8]) for c, t in LOWER_TILE.items()}


def glyph_tiles():
    """{code: 16-byte tile} for every new glyph."""
    lower = lower_plane0()
    tiles = {}
    for c, p0 in lower.items():
        tiles[CODE[c]] = tile_bytes(p0)
    for c, rows in CAPS.items():
        tiles[CODE[c]] = tile_bytes(_rows_to_plane0(rows))
    for c, rows in PUNCT.items():
        tiles[CODE[c]] = tile_bytes(_rows_to_plane0(rows))
    return tiles


def encode(text):
    return bytes(CODE[c] for c in text)


def preview(path, scale=6):
    from PIL import Image, ImageDraw
    tiles = glyph_tiles()
    chars = [c for c in CODE if c != " "]
    chars = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz,!'-:()/\";&$.?0123456789%"]
    cols = 16
    cell = 8 * scale + 6
    rows = (len(chars) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell, rows * (cell + 14)), (30, 30, 30))
    d = ImageDraw.Draw(img)
    for n, c in enumerate(chars):
        code = CODE[c]
        if code in tiles:
            t = tiles[code]
        else:   # existing game glyph (digits, '.', '?', '%') for reference
            chr_ = b"".join(open(os.path.join(ROOT, "chr", f"bank{i:02d}.bin"), "rb").read() for i in range(16))
            t = chr_[4096 + code * 16:4096 + code * 16 + 16]
        ox, oy = (n % cols) * cell + 3, (n // cols) * (cell + 14) + 14
        d.text((ox, oy - 12), f"{c} {code:02X}", fill=(255, 220, 90))
        for y in range(8):
            for x in range(8):
                if (t[y] >> (7 - x)) & 1:
                    d.rectangle([ox + x * scale, oy + y * scale, ox + x * scale + scale - 1, oy + y * scale + scale - 1], fill=(255, 255, 255))
    img.save(path)


if __name__ == "__main__":
    out = os.path.join(ROOT, "chr", "sheets", "latin_font_preview.png")
    preview(out)
    print(out)
    assert len(set(CODE.values())) == len(CODE), "duplicate codes"
