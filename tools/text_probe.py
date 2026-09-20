"""Probe: decode CDL-flagged data runs with a hypothesised kana table.

Kana codes 04.. follow gojuon order; 6D = dakuten (voices the previous kana),
6E = handakuten. FE/FF are control codes (shown as | and $). Unknown = [xx].
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkinfo import load, BANK

HIRA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんっゃゅょ"
TABLE = {0x04 + i: c for i, c in enumerate(HIRA)}
# katakana: gojuon from ア=0x36, no ヲ (evidence: ボタン = 53 6D 45 62 -> ホ゛タン)
KATA = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン"
TABLE.update({0x36 + i: c for i, c in enumerate(KATA)})
TABLE.update({0x63 + i: c for i, c in enumerate("ァィゥェォッャュョ")})   # 68=ッ 6A=ュ ...
TABLE.update({0x70 + i: str(i) for i in range(10)})
TABLE.update({0x6C: "ー", 0x7A: "%", 0x7B: "?", 0x7E: "(", 0x7F: ")", 0x80: "A", 0x81: "B", 0x6F: "."})
DAKUTEN, HANDAKUTEN = 0x6D, 0x6E
VOICED = dict(zip("かきくけこさしすせそたちつてとはひふへほ", "がぎぐげござじずぜぞだぢづでどばびぶべぼ"))
VOICED.update(zip("カキクケコサシスセソタチツテトハヒフヘホ", "ガギグゲゴザジズゼゾダヂヅデドバビブベボ"))
SEMI = dict(zip("はひふへほ", "ぱぴぷぺぽ"))
SEMI.update(zip("ハヒフヘホ", "パピプペポ"))


def decode(b, kset=None):
    kan = {} if kset is None else __import__('kanji').SETS[kset]
    out = []
    for x in b:
        if x == 0x6D and out and out[-1] in VOICED:
            out[-1] = VOICED[out[-1]]
        elif x == 0x6E and out and out[-1] in SEMI:
            out[-1] = SEMI[out[-1]]
        elif x in TABLE:
            out.append(TABLE[x])
        elif x in kan:
            out.append(kan[x])
        elif x == 0xFE:
            out.append("|")
        elif x == 0xFF:
            out.append("$")
        elif x == 0x00:
            out.append("_")
        else:
            out.append(f"[{x:02X}]")
    return "".join(out)


def main():
    prg, cdl = load()
    bank = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    s = None
    for o in range(BANK + 1):
        f = o < BANK and cdl[bank][o] & 2
        if f and s is None:
            s = o
        if not f and s is not None:
            print(f"--- {s:04X}-{o - 1:04X}")
            # split on FE/FF for readability
            chunk = bytearray()
            for x in prg[bank][s:o]:
                chunk.append(x)
                if x in (0xFE, 0xFF):
                    print("  ", decode(chunk))
                    chunk = bytearray()
            if chunk:
                print("  ", decode(chunk))
            s = None


if __name__ == "__main__":
    main()
