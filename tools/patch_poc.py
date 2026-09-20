"""Proof-of-concept English patch -> build/poc.nes

1. Overwrites kana tiles in CHR text page 1 (CHR bank 0, upper 4 KB) with the Latin font.
2. Replaces table-1 message #1 (bank 1 @ 0x0023, was 候補者を選んでください) with English,
   in place (must fit the original 17 bytes incl. the FF terminator).

Works on a copy of rom/original.nes; refuses to write if the bytes it expects are not found.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from latin_font import glyph_tiles, encode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRG_BASE = 16
CHR_BASE = 16 + 8 * 16384
MSG_BANK, MSG_OFF, MSG_LEN = 1, 0x0023, 17
TEXT = "Pick a candidate"
EXPECT = bytes.fromhex("8c 8d 8e 00 30 00 91 31 16 6d 00 0b 13 6d 0e 05 ff")   # original message, 17 bytes incl. FF


def main():
    rom = bytearray(open(os.path.join(ROOT, "rom", "original.nes"), "rb").read())
    orig = bytes(rom)

    # --- message, in place
    base = PRG_BASE + MSG_BANK * 16384 + MSG_OFF
    cur = bytes(rom[base:base + len(EXPECT)])
    if cur != EXPECT:
        sys.exit(f"unexpected bytes at message site: {cur.hex(' ')}")
    new = encode(TEXT) + b"\xff"
    if len(new) > MSG_LEN:
        sys.exit(f"message too long: {len(new)} > {MSG_LEN}")
    new = new.ljust(MSG_LEN, b"\x00")          # pad after FF (never read)
    rom[base:base + MSG_LEN] = new

    # --- font: CHR page 1 = bank 0 upper half = CHR offset 0x1000
    tiles = glyph_tiles()
    for code, t in tiles.items():
        o = CHR_BASE + 0x1000 + code * 16
        rom[o:o + 16] = t

    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    out = os.path.join(ROOT, "build", "poc.nes")
    open(out, "wb").write(rom)

    diff = [i for i in range(len(rom)) if rom[i] != orig[i]]
    print(f"wrote {out}")
    print(f"message bytes: {new.hex(' ')}")
    print(f"{len(tiles)} glyph tiles written, {len(diff)} bytes differ from original")
    prg_diff = [i for i in diff if i < CHR_BASE]
    print(f"PRG bytes changed: {len(prg_diff)} (expected <= {MSG_LEN})")


if __name__ == "__main__":
    main()
