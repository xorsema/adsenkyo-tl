# Text encoding (banks 1 and 2 hold the script)

Strings are byte sequences. Verified by decoding real strings and matching
the live screen (BizHawk nametable) — see tools/text_probe.py.

| Codes | Meaning | Evidence |
|---|---|---|
| 00 | space / pad | strings like `__` between words |
| 04-30 | hiragana あ..を, gojuon order, no small kana | 05=い 0B=く 0E=さ 13=た 16=て 30=を; live nametable |
| 31 | ん | live nametable |
| 32-35 | (unverified) っゃゅょ? | hiragana small kana not seen yet |
| 36-62 | katakana ア..ン, gojuon order, **no ヲ** | ボタン = 53 6D 45 62 |
| 63-6B | small ァィゥェォッャュョ | コンティニュー, スコット, プッシュ |
| 6C | ー | データ, ロバート |
| 6D | ゛ dakuten (applies to preceding kana) | live nametable: 6D above voiced kana |
| 6E | ゜ handakuten | プロフィール, ペネロープ |
| 6F | `.` after list number (unverified) | `[71][6F]` = "1." |
| 70-79 | digits 0-9 | 50000ドル |
| 7B | ？ | よろしいでしょうか？ |
| 7E / 7F | 「 / 」 | 「プロフィールをみる」 |
| 80 / 81 | A / B | "Aボタン", "Bボタンでもどります" |
| 84+ | kanji, 1 byte = 1 glyph (see below) | title 政策項目を選んでください = 93 94 95 96 を 91 んで... |
| FE | line break (separator) | |
| FF | end of string | |

## Kanji

One byte per kanji. On screen each kanji is a 2x2 tile block whose top-left
tile is `(4*code + 0x74) & 0xFF` in the menu screen (政=93→C0, 策=94→C4,
項=95→C8, 目=96→CC, 選=91→B8, in that screen's CHR mapping). The glyph
images come from CHR-ROM banks that are switched per screen, so the
code -> glyph table is per-kanji-bank, not global. TODO: work out which CHR
banks belong to which script sections (CDL: CHR banks 0,3,4,11,13,14,15 used).

## Kanji sets (verified pages)

Text uses BG pattern table $1000; the mapped 4 KB CHR page holds the kana font
(tiles 04-7F) plus 31 kanji as 2x2 blocks (TL,TR,BL,BR consecutive) at tiles
0x84.. : code c -> TL tile 4c-0x18C. Only pages 1, 2, 19 carry the kana font, each with
a different kanji set (tools/kanji.py, glyphs in chr/sheets/kanji_pNN.png):

  A = CHR page 1  (campaign menus: policy, survey, campaign activity, speeches)
  B = CHR page 2  (registration, campaign-finance law, health)
  C = CHR page 19 (primaries and results: candidates, delegates, majority, nomination)

A message's set is chosen by the scene that shows it, not by its table/bank
(e.g. bank1 #14 uses B). tools/pick_sets.py scores each message; 3 overrides were
checked by eye. Codes E0-F9 in a few strings are lowercase Latin a-z (the English
presidential oath), so some scenes already load a Latin font page.

## Special tiles are per page (chr/sheets/special_tiles.png)

| code | set A (p1) | set B (p2) | set C (p19) |
|---|---|---|---|
| 02 | C | C | W |
| 03 | 万 | 万 | S |
| 7C / 7D | ! / ・ | ! / ・ | D / C |
| 80 / 81 | A / B | A / B | 百 / 万 |
| 82 / 83 | N / S | 人 / 。 | N / ヲ |

7A = %, 7B = ?, 7E/7F = round parentheses. FC (in the state-schedule lines) is the last kanji-slot tile,
kept as a raw {FC} token. All encoded in tools/kanji.py (SPECIAL) and tools/script_io.py.

## Script workflow

    python tools/mkscript.py        # regenerate script/script.txt (keeps EN/NOTE lines by id)
    python tools/check_script.py -v # validate EN lines: glyphs, fit-in-place, line widths

script/script.txt = 260 translatable messages (12,420 bytes); script/nontext.txt = keyboard/tile rows
(125), the English oath (2). JP <-> bytes round-trips exactly for all 387 messages.
