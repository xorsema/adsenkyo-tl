"""English for the profile screens (big-mode messages: T1 index >= 128).

These messages are drawn from a per-scene CHR text page, so English is expressed as RAW TILE codes
(>= $4F) that point at Latin glyph tiles we add to that page:

    A-Z = 84..9D    a-z = 9E..B7    0-9 = B8..C1
    . C2  , C3  - C4  ' C5  ( C6  ) C7  / C8  : C9  ! CA  ? CB  & CC  " CD  % CE  $ CF   space = 00

(F5/F6/FE/FF are engine codes and are never used.) Text goes on one tile row per line; the engine
moves 2 tile rows down at each newline. Format of script/profiles.txt:

    === T1-207  page=6
    JP: プッシュ候補 64才 A型 | テキサス州 | ...           (reference only)
    EN: Bush          Age 64 Type A|Texas|Vice President|...
"""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkinfo import ROOT
import latin_font

ORDER = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ" + "abcdefghijklmnopqrstuvwxyz" + "0123456789" + ".,-'()/:!?&\"%$")
CODE = {c: 0x84 + i for i, c in enumerate(ORDER)}
CODE[" "] = 0x00
assert max(CODE.values()) < 0xF5 and len(set(CODE.values())) == len(CODE)
WIDTH = 28


def encode_profile(text):
    out = bytearray()
    for ch in text:
        if ch == "|":
            out.append(0xFE)
        elif ch in CODE:
            out.append(CODE[ch])
        else:
            raise ValueError(f"no glyph for {ch!r}")
    return bytes(out)


def glyph_tile_map():
    """{raw code: 16-byte tile} for every Latin glyph (same tile format as the text pages)."""
    tiles = latin_font.glyph_tiles()               # letters + some punctuation, keyed by text-page code
    chr_ = b"".join(open(os.path.join(ROOT, "chr", f"bank{i:02d}.bin"), "rb").read() for i in range(16))
    page1 = chr_[4096:8192]                        # digits, '.', '?', '%' already exist in the text page
    out = {}
    for ch, raw in CODE.items():
        if ch == " ":
            continue
        code = latin_font.CODE.get(ch)
        if code is not None and code in tiles:
            out[raw] = tiles[code]
        elif code is not None:
            out[raw] = page1[code * 16:code * 16 + 16]
        else:
            raise ValueError(f"glyph for {ch!r} not available")
    return out


def load(path=None):
    path = path or os.path.join(ROOT, "script", "profiles.txt")
    out, cur = [], None
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = re.match(r"=== (T1-\d+)\s+page=(\d+)", line)
        if m:
            cur = dict(id=m.group(1), page=int(m.group(2)), jp="", en="")
            out.append(cur)
        elif cur and line.startswith("JP:"):
            cur["jp"] = line[3:].strip()
        elif cur and line.startswith("EN:"):
            cur["en"] = line[4:] if line[3:4] == " " else line[3:]
    return out


def check(p):
    """-> list of problems for one profile entry."""
    bad = []
    try:
        encode_profile(p["en"])
    except ValueError as ex:
        bad.append(str(ex))
    for ln in p["en"].split("|"):
        if len(ln) > WIDTH:
            bad.append(f"line too wide ({len(ln)}): {ln!r}")
    return bad


if __name__ == "__main__":
    for p in load():
        print(p["id"], p["page"], check(p) or "ok")
