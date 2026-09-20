"""Kanji sets: byte code (0x84..0xA2) -> glyph, per 4 KB CHR text page.

Transcribed by eye from chr/sheets/kanji_pNN.png (tools/kanji_sheet.py).
Each set is 31 glyphs starting at code 0x84. Set is chosen by the CHR page the
game maps at $1000 (variables $43/$44), see notes/text_encoding.md.
'■' = graphic block, not a kanji. Confidence: sets A and B cross-checked
against decoded sentences; set C only by reading the glyphs.
"""

def _mk(s):
    assert len(s) == 31, len(s)
    return {0x84 + i: c for i, c in enumerate(s)}

SETS = {
    "A": _mk("数変更世論調査州候補者予算選挙政策項目値決設定運動内容回演説会"),   # CHR page 1  (bank 1 / table 1)
    "B": _mk("大統領選挙登録完了衰弱州体援助運動使資金規制法支出限度額用■■"),   # CHR page 2  (bank 2 / table 2)
    "C": _mk("発表候補戦州獲得代議員数過半指名結果受諾献金政府援助選挙資断念"),   # CHR page 19
}
PAGE = {"A": 1, "B": 2, "C": 19}

# Special single tiles differ per text page (checked in chr/sheets/special_tiles.png).
# These override the shared table in text_probe.TABLE for messages using that set.
SPECIAL = {
    "A": {0x02: "C", 0x03: "万", 0x7C: "!", 0x7D: "・", 0x82: "N", 0x83: "S"},
    "B": {0x02: "C", 0x03: "万", 0x7C: "!", 0x7D: "・", 0x82: "人", 0x83: "。"},
    "C": {0x02: "W", 0x03: "S", 0x7C: "D", 0x7D: "C", 0x80: "百", 0x81: "万", 0x82: "N", 0x83: "ヲ"},
}
