"""Redraw the title logo (アメリカ / 大統領選挙) as English: AMERICA / PRESIDENTIAL / ELECTION.

Where the logo lives (found by disassembly/dumps):
  * layout: bank 6 as 2x2 METATILES (4 bytes: TL TR BL BR), left-to-right per block row:
        $9126  48 bytes   AMERICA area   cols 10-21, rows 16-19          (6 x 2 metatiles)
        $9166  60 bytes   rows 20-21     cols  2-31                      (15 metatiles)
        $91A2  64 bytes   rows 22-23     cols  0-31                      (16 metatiles)
        $91E2  64 bytes   rows 24-25     cols  0-31                      (16 metatiles)
        $9222  attribute table follows (untouched)
  * pixels: CHR page 8 (the title's $1000 table). Pixel values: 1 = background, 3 = white fill, 0 = dark shadow.
The stream extents are fixed, so we keep them and rewrite only the tile ids (from the ids the logo already owns)
and the tile pixels.

  python tools/title_logo.py     # writes chr/sheets/title_logo_preview.png and prints the tile budget
"""
import functools
import os
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = r"C:\Windows\Fonts\georgiab.ttf"
PAGE = 8
BG, FILL, SHADOW = 1, 3, 0
K = 8                                        # supersampling factor for crisp 1-bit letters


def load_nt():
    t = [int(x, 16) for x in open(os.path.join(ROOT, "chr", "title_nt1.hex")).read().split()][:960]
    return [t[r * 32:(r + 1) * 32] for r in range(30)]


NT = load_nt()
LOGO_ROWS = list(range(16, 19)) + list(range(20, 26))
MASK = {(r, c): NT[r][c] for r in LOGO_ROWS for c in range(32) if NT[r][c] != 0x31}


@functools.lru_cache(maxsize=None)
def glyph_mask(ch, cap_px, font_path=FONT):
    """1-bit mask of one letter at the given cap height, plus its advance width, both in pixels."""
    size = 10
    while True:                                    # find the font size whose 'H' is cap_px tall (at K x scale)
        f = ImageFont.truetype(font_path, size)
        bb = f.getbbox("H")
        if bb[3] - bb[1] >= cap_px * K or size > 600:
            break
        size += 2
    f = ImageFont.truetype(font_path, size)
    bb = f.getbbox(ch)
    w = max(1, (bb[2] - bb[0] + K - 1) // K + 1)
    img = Image.new("L", (w * K, (cap_px + 4) * K), 0)
    d = ImageDraw.Draw(img)
    ref = f.getbbox("H")
    d.text((-bb[0], -ref[1] + 2 * K), ch, font=f, fill=255)
    small = img.resize((w, cap_px + 4), Image.BOX)
    m = [[1 if small.getpixel((x, y)) >= 118 else 0 for x in range(w)] for y in range(cap_px + 4)]
    return m, w


def layout_line(text, cap_px, x0, y0, tracking, pixels):
    """Draw text into `pixels` (set of (x,y)); returns the x extent used."""
    x = x0
    for ch in text:
        if ch == " ":
            x += cap_px // 2 + tracking
            continue
        m, w = glyph_mask(ch, cap_px)
        for yy, row in enumerate(m):
            for xx, v in enumerate(row):
                if v:
                    pixels.add((x + xx, y0 + yy - 2))
        x += w + tracking
    return x


def canvas_from(lines):
    """lines: [(text, cap_px, x0, y0, tracking)] -> canvas dict {(x,y): value}."""
    fill = set()
    for text, cap, x0, y0, tr in lines:
        layout_line(text, cap, x0, y0, tr, fill)
    shadow = {(x + dx, y + dy) for x, y in fill for dx, dy in ((1, 1), (2, 2), (1, 2), (2, 1))} - fill
    return fill, shadow



# small credit line shown above the logo (edit the text here; at 4 px per character ~22 characters fit)
CREDIT_TEXT = "ENGLISH FAN PATCH V0.1"
CREDIT_Y = 130                                  # top pixel row (inside tile row 16, y 128..135)
CREDIT_BOX = (80, 176)                          # x range of the AMERICA metatile area

TINY = {
    "A": ("010", "101", "111", "101", "101"), "B": ("110", "101", "110", "101", "110"),
    "C": ("011", "100", "100", "100", "011"), "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"), "F": ("111", "100", "110", "100", "100"),
    "G": ("011", "100", "101", "101", "011"), "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"), "J": ("001", "001", "001", "101", "010"),
    "K": ("101", "101", "110", "101", "101"), "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"), "N": ("111", "101", "101", "101", "101"),
    "O": ("010", "101", "101", "101", "010"), "P": ("110", "101", "110", "100", "100"),
    "R": ("110", "101", "110", "101", "101"), "S": ("011", "100", "010", "001", "110"),
    "T": ("111", "010", "010", "010", "010"), "U": ("101", "101", "101", "101", "111"),
    "V": ("101", "101", "101", "101", "010"), "Y": ("101", "101", "010", "010", "010"),
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    ".": ("000", "000", "000", "000", "010"),
}


def tiny_width(text):
    return sum(2 if ch == " " else 4 for ch in text) - 1


def tiny_pixels(text, x0, y0):
    pix, x = set(), x0
    for ch in text:
        if ch == " ":
            x += 2
            continue
        for yy, row in enumerate(TINY[ch]):
            for xx, bit in enumerate(row):
                if bit == "1":
                    pix.add((x + xx, y0 + yy))
        x += 4
    return pix


# stream layout: (rom address in bank 6, first row, first col, metatiles per block row, block rows)
STREAMS = [(0x9126, 16, 10, 6, 2), (0x9166, 20, 2, 15, 1), (0x91A2, 22, 0, 16, 2)]
BLANK = 0x31


def prg_bank6():
    d = open(os.path.join(ROOT, "prg", "bank6.bin"), "rb").read()
    return d


def stream_cells():
    """-> ({(row, col): orig tile id}, [(addr, r0, c0, w, h)]) for the three streams."""
    d = prg_bank6()
    cells = {}
    for addr, r0, c0, w, h in STREAMS:
        a = addr - 0x8000
        for br in range(h):
            for mc in range(w):
                tl, tr, bl, brr = d[a:a + 4]
                a += 4
                r, c = r0 + 2 * br, c0 + 2 * mc
                cells[(r, c)], cells[(r, c + 1)], cells[(r + 1, c)], cells[(r + 1, c + 1)] = tl, tr, bl, brr
    return cells


CELLS = stream_cells()


def id_pool():
    """Tile ids the logo owns: used in the streams, blank excluded, and not used anywhere else on the title."""
    nt = load_nt()
    other = {nt[r][c] for r in range(30) for c in range(32) if (r, c) not in CELLS}
    return sorted(set(CELLS.values()) - other - {BLANK})


def plan_lines():
    # (text, cap px, x0, y0 of the cap top, tracking); all inside the stream extents
    return [("AMERICA", 14, 84, 136, 2),
            ("PRESIDENTIAL", 18, 20, 163, 1),
            ("ELECTION", 18, 20, 187, 8)]


def text_width(text, cap_px, tracking):
    tmp = set()
    return layout_line(text, cap_px, 0, 0, tracking, tmp)


def centred(text, cap, y0, tracking, x_lo, x_hi):
    w = text_width(text, cap, tracking)
    return (text, cap, x_lo + (x_hi - x_lo - w) // 2, y0, tracking)


def specs():
    return [centred("AMERICA", 10, 139, 0, 80, 176),
            centred("PRESIDENTIAL", 15, 166, 1, 20, 236),
            centred("ELECTION", 16, 189, 8, 0, 256)]


def build():
    lines = specs()
    fill, shadow = canvas_from(lines)
    if CREDIT_TEXT:
        cf = tiny_pixels(CREDIT_TEXT, CREDIT_BOX[0] + (CREDIT_BOX[1] - CREDIT_BOX[0] - tiny_width(CREDIT_TEXT)) // 2, CREDIT_Y)
        fill = fill | cf
        shadow = (shadow | {(x + 1, y + 1) for x, y in cf}) - fill
    outside = [(x, y) for x, y in fill | shadow if (y // 8, x // 8) not in CELLS]
    blocks = {}
    for (r, c) in CELLS:
        blk = [[BG] * 8 for _ in range(8)]
        for y in range(8):
            for x in range(8):
                p = (c * 8 + x, r * 8 + y)
                blk[y][x] = FILL if p in fill else SHADOW if p in shadow else BG
        blocks[(r, c)] = blk
    return lines, fill, shadow, blocks, outside


def assign(blocks):
    """Dedupe identical blocks; blank blocks use the background tile. -> ({(r,c): id}, {id: 16 bytes}, needed)."""
    blank = [[BG] * 8 for _ in range(8)]
    pool = id_pool()
    by_block, tiles, ids = {}, {}, {}
    for cell in sorted(blocks):
        blk = blocks[cell]
        if blk == blank:
            ids[cell] = BLANK
            continue
        key = tuple(tuple(row) for row in blk)
        if key not in by_block:
            if not pool:
                raise SystemExit("title logo: out of tile ids")
            tid = pool.pop(0)
            by_block[key] = tid
            tiles[tid] = tile_bytes(blk)
        ids[cell] = by_block[key]
    return ids, tiles, len(tiles), len(id_pool())


def new_streams(ids):
    """-> {rom offset in bank 6: bytes} with the rewritten metatile streams."""
    out = {}
    for addr, r0, c0, w, h in STREAMS:
        buf = bytearray()
        for br in range(h):
            for mc in range(w):
                r, c = r0 + 2 * br, c0 + 2 * mc
                buf += bytes([ids[(r, c)], ids[(r, c + 1)], ids[(r + 1, c)], ids[(r + 1, c + 1)]])
        out[addr - 0x8000] = bytes(buf)
    return out


def tile_bytes(block):
    out0, out1 = [], []
    for y in range(8):
        a = b = 0
        for x in range(8):
            v = block[y][x]
            a |= (v & 1) << (7 - x)
            b |= ((v >> 1) & 1) << (7 - x)
        out0.append(a); out1.append(b)
    return bytes(out0) + bytes(out1)


CACHE = os.path.join(ROOT, "chr", "title_logo.json")


def generated():
    """(streams {offset: bytes}, tiles {id: bytes}); cached in chr/title_logo.json (delete it to regenerate)."""
    import json
    if os.path.exists(CACHE):
        j = json.load(open(CACHE))
        return ({int(k): bytes.fromhex(v) for k, v in j["streams"].items()},
                {int(k): bytes.fromhex(v) for k, v in j["tiles"].items()})
    lines, fill, shadow, blocks, outside = build()
    if outside:
        raise SystemExit(f"title logo: {len(outside)} pixels fall outside the stream cells")
    ids, tiles, needed, avail = assign(blocks)
    streams = new_streams(ids)
    json.dump({"streams": {str(k): v.hex() for k, v in streams.items()},
               "tiles": {str(k): v.hex() for k, v in tiles.items()}}, open(CACHE, "w"))
    return streams, tiles


def apply(rom, prg0, chr0):
    """Patch a bytearray ROM: bank 6 streams (prg0 = file offset of PRG) and page 8 tiles (chr0)."""
    streams, tiles = generated()
    for off, data in streams.items():
        o = prg0 + 6 * 16384 + off
        rom[o:o + len(data)] = data
    for tid, tb in tiles.items():
        o = chr0 + PAGE * 4096 + tid * 16
        rom[o:o + 16] = tb
    return len(tiles)


def preview(path):
    lines, fill, shadow, blocks, outside = build()
    ids, tiles, needed, avail = assign(blocks)
    nt = load_nt()
    S = 3
    pal = [(35, 35, 45), (225, 185, 60), (200, 60, 50), (245, 245, 245)]
    img = Image.new("RGB", (32 * 8 * S, 12 * 8 * S), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for r in range(15, 27):
        for c in range(32):
            if (r, c) in ids:
                tb = tiles.get(ids[(r, c)], bytes([0xFF] * 8 + [0] * 8))
            else:
                tb = bytes([0xFF] * 8 + [0] * 8)
            for y in range(8):
                for x in range(8):
                    v = ((tb[y] >> (7 - x)) & 1) | (((tb[y + 8] >> (7 - x)) & 1) << 1)
                    d.rectangle([(c * 8 + x) * S, ((r - 15) * 8 + y) * S, (c * 8 + x) * S + S - 1, ((r - 15) * 8 + y) * S + S - 1], fill=pal[v])
    img.save(path)
    return lines, needed, avail, outside


if __name__ == "__main__":
    out = os.path.join(ROOT, "chr", "sheets", "title_logo_preview.png")
    lines, needed, avail, outside = preview(out)
    print("preview:", out)
    for l in lines:
        print(f"  {l[0]:13} cap {l[1]}px at x={l[2]} y={l[3]} tracking {l[4]}")
    print(f"unique non-blank tiles needed: {needed}   ids the logo owns: {avail}   left over: {avail - needed}")
    print("text/shadow pixels outside the stream cells:", len(outside))
