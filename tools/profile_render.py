"""Offline renderer for the game's "big mode" messages (profiles).

Engine facts (found by disassembling $F6E8-$F825):
  * table-1 messages with index >= 128 run in big mode ($0241 = $FF) with the block table at $FBFB.
  * byte 00-03            : raw tile number (00 = blank), 1 column
  * byte 04-4E            : 2x2 glyph block. k = (byte - $10) & $FF ; entries T[4k..4k+3] of the block table:
                            top row = (T[4k], T[4k+1]), bottom row = (T[4k+2], T[4k+3]); 2 columns wide.
                            (the engine writes the bottom row first, then $F825 moves the VRAM address UP a row)
                            A line's base row is its BOTTOM row; raw tiles sit on it.
  * byte 4F-FD (not FE/FF): raw tile number, 1 column. If the NEXT byte is F5 or F6, that tile is drawn
                            directly below (a diacritic) and the byte is consumed.
  * FE = newline (2 tile rows down, back to the start column)   FF = end
All tile numbers refer to the 4 KB CHR page mapped at $1000 for the lower half of the screen ($44).

  python tools/profile_render.py T1-248 18 [scale]  -> notes/prof/render_T1-248_p18.png
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from mkinfo import load, ROOT
from extract_text import messages, TABLES

BLOCK_TABLE = 0xFBFB


def chr_pages():
    chr_ = b"".join(open(os.path.join(ROOT, "chr", f"bank{i:02d}.bin"), "rb").read() for i in range(16))
    return [chr_[i * 4096:(i + 1) * 4096] for i in range(32)]


def block_table(prg):
    o = BLOCK_TABLE - 0xC000
    return prg[7][o:o + 0x100]


def layout(b, T):
    """-> dict {(row, col): tile} for message bytes b (incl. FF)."""
    cells, row, col = {}, 1, 0          # row 1 = first line's bottom row; row 0 = its top row
    i = 0
    while i < len(b) and b[i] != 0xFF:
        c = b[i]
        if c == 0xFE:
            row += 2; col = 0
        elif c < 4:
            cells[(row, col)] = c; col += 1
        elif c < 0x4F:
            k = (c - 0x10) & 0xFF
            idx = (k * 4) & 0xFF
            cells[(row - 1, col)] = T[idx]; cells[(row - 1, col + 1)] = T[idx + 1]
            cells[(row, col)] = T[idx + 2]; cells[(row, col + 1)] = T[idx + 3]
            col += 2
        else:
            cells[(row, col)] = c
            if i + 1 < len(b) and b[i + 1] in (0xF5, 0xF6):
                cells[(row - 1, col)] = b[i + 1]
                i += 1
            col += 1
        i += 1
    return cells


def render(b, page_data, T, scale=3):
    cells = layout(b, T)
    rows = max(r for r, _ in cells) + 1 if cells else 1
    cols = max(c for _, c in cells) + 1 if cells else 1
    img = Image.new("L", (cols * 8, rows * 8), 40)
    for (r, c), t in cells.items():
        for y in range(8):
            lo, hi = page_data[t * 16 + y], page_data[t * 16 + y + 8]
            for x in range(8):
                v = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
                img.putpixel((c * 8 + x, r * 8 + y), (40, 110, 200, 255)[v] if v else 40)
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


def message_bytes(prg, ident):
    tbl, idx = int(ident[1]), int(ident[3:])
    name = {1: "bank1", 2: "bank2"}[tbl]
    for n, base, cnt, bank in TABLES:
        if n == name:
            for i, p, b in messages(prg, base, cnt, bank):
                if i == idx:
                    return b
    raise KeyError(ident)


def main():
    ident, page = sys.argv[1], int(sys.argv[2])
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    prg, _ = load()
    T = block_table(prg)
    img = render(message_bytes(prg, ident), chr_pages()[page], T, scale)
    out = os.path.join(ROOT, "notes", "prof", f"render_{ident}_p{page}.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print(out, img.size)


if __name__ == "__main__":
    main()


def from_rom(path):
    """(chr pages, block table, message reader) for a built .nes, reading text through the pointer table."""
    rom = open(path, "rb").read()
    chr_ = rom[16 + 8 * 16384:]
    pages = [chr_[i * 4096:(i + 1) * 4096] for i in range(32)]
    prg = [rom[16 + i * 16384:16 + (i + 1) * 16384] for i in range(8)]
    T = prg[7][BLOCK_TABLE - 0xC000:BLOCK_TABLE - 0xC000 + 0x100]

    def msg(ident):
        idx = int(ident[3:])
        o = 0xF879 - 0xC000 + 2 * idx
        ptr = prg[7][o] | prg[7][o + 1] << 8
        bank, off = (5, ptr - 0xC000) if ptr >= 0xC000 else (1, ptr - 0x8000)
        e = off
        while prg[bank][e] != 0xFF:
            e += 1
        return bytes(prg[bank][off:e + 1])
    return pages, T, msg
