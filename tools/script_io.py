"""Lossless text codec for the game's messages, plus English encoding.

Japanese ("JP") side, round-trip exact:
    bytes -> text -> bytes is the identity for every message (checked by mkscript.py).
    '_' = 00 (blank tile), '|' = FE (line break), {XX} = any byte with no known glyph,
    voiced kana are composed (か + 6D -> が). The FF terminator is implicit.
English ("EN") side:
    normal text, ' ' = 00, '|' = line break (FE), {XX} = raw byte, encoded through the
    Latin font table in latin_font.py.
"""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from text_probe import TABLE, VOICED, SEMI
from kanji import SETS, SPECIAL
import latin_font

FE, FF, DAKU, HANDAKU = 0xFE, 0xFF, 0x6D, 0x6E
_TOKEN = re.compile(r"\{([0-9A-Fa-f]{2})\}")


def _jp_maps(kset):
    kan = {} if kset in (None, "-") else {c: ch for c, ch in SETS[kset].items() if ch != "■"}
    dec = dict(TABLE)
    dec.update(SPECIAL.get(kset, {}))
    dec.update(kan)
    # a glyph must map back to exactly one code
    enc = {}
    for code, ch in dec.items():
        if ch in enc:
            raise ValueError(f"glyph {ch!r} ambiguous ({enc[ch]:02X} and {code:02X})")
        enc[ch] = code
    return dec, enc


def decode_jp(b, kset):
    """bytes (without terminator) -> lossless text."""
    dec, _ = _jp_maps(kset)
    out = []
    for x in b:
        if x == DAKU and out and out[-1] in VOICED and len(out[-1]) == 1:
            out[-1] = VOICED[out[-1]]
        elif x == HANDAKU and out and out[-1] in SEMI and len(out[-1]) == 1:
            out[-1] = SEMI[out[-1]]
        elif x == FE:
            out.append("|")
        elif x == 0x00:
            out.append("_")
        elif x in dec:
            out.append(dec[x])
        else:
            out.append("{%02X}" % x)
    return "".join(out)


def encode_jp(text, kset):
    _, enc = _jp_maps(kset)
    inv_v = {v: k for k, v in VOICED.items()}
    inv_s = {v: k for k, v in SEMI.items()}
    out = bytearray()
    i = 0
    while i < len(text):
        m = _TOKEN.match(text, i)
        if m:
            out.append(int(m.group(1), 16)); i = m.end(); continue
        ch = text[i]; i += 1
        if ch == "|":
            out.append(FE)
        elif ch == "_":
            out.append(0x00)
        elif ch in inv_v:
            out += bytes([enc[inv_v[ch]], DAKU])
        elif ch in inv_s:
            out += bytes([enc[inv_s[ch]], HANDAKU])
        elif ch in enc:
            out.append(enc[ch])
        else:
            raise ValueError(f"cannot encode JP char {ch!r}")
    return bytes(out)


def encode_en(text, kset=None):
    out = bytearray()
    i = 0
    while i < len(text):
        m = _TOKEN.match(text, i)
        if m:
            out.append(int(m.group(1), 16)); i = m.end(); continue
        ch = text[i]; i += 1
        if ch == "|":
            out.append(FE)
        elif ch == "・":
            if kset == "C":
                raise ValueError("the bullet '・' (code 7D) is a letter in kanji set C")
            out.append(0x7D)
        elif ch in latin_font.CODE:
            out.append(latin_font.CODE[ch])
        else:
            raise ValueError(f"no glyph for {ch!r} in the English font")
    return bytes(out)


def jp_width(b, kset):
    """Approximate on-screen width in 8px tiles per line (kanji = 2, everything else 1)."""
    kan = set() if kset in (None, "-") else set(SETS[kset])
    widths, w = [], 0
    for x in b:
        if x == FE:
            widths.append(w); w = 0
        elif x in (DAKU, HANDAKU):
            continue
        else:
            w += 2 if x in kan else 1
    widths.append(w)
    return widths
