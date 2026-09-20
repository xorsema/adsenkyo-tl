"""Guess each message's kanji set (A/B/C) by counting known compounds in the decoded text.

Usage: python pick_sets.py   -> prints per-message pick, plus ambiguous ones
The compound list is a heuristic aid, not ground truth; ambiguous messages need eyes.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkinfo import load
from script_io import decode_jp
from extract_text import messages, TABLES
from kanji import SETS

WORDS = """選挙 大統領 候補者 候補 政策 調査 世論 予算 運動 演説 演説会 資金 支出 献金 獲得 代議員 過半数 指名 結果 受諾
援助 発表 完了 登録 衰弱 限度額 規制法 州 数 変更 政府 断念 内容 決定 設定 選挙運動 選挙資金 世論調査 政策値 資金援助
支出限度額 大統領選挙 候補者予算 回数 運動内容 演説内容 決定 体 使用 制限 出限 過半 戦 政治献金""".split()


import re
# patterns that only make sense under one set's special tiles (see kanji.SPECIAL)
BONUS = [(r"\d万人", 8), (r"\d万ドル", 6), (r"[NSW]\.[ァ-ヶ]", 8), (r"NBC|ABC|CBS", 8), (r"百万ドル", 8)]


def score(text):
    s = sum(text.count(w) * len(w) ** 2 for w in WORDS)
    return s + sum(v * len(re.findall(pat, text)) for pat, v in BONUS)


def main():
    prg, _ = load()
    picks, amb = [], []
    for name, base, n, bank in TABLES:
        for i, p, b in messages(prg, base, n, bank):
            if not any(0x84 <= x <= 0xA2 for x in b):
                continue
            sc = {k: score(decode_jp(b[:-1], k)) for k in SETS}
            best = max(sc.values())
            winners = [k for k, v in sc.items() if v == best]
            picks.append((name, i, winners, best, b))
            if best == 0 or len(winners) > 1:
                amb.append((name, i, sc, b))
    print(f"{len(picks)} messages contain kanji codes; {len(amb)} ambiguous (score 0 or tie)")
    from collections import Counter
    print("picked sets:", Counter("".join(w) for _, _, w, _, _ in picks))
    return picks, amb


if __name__ == "__main__":
    picks, amb = main()
    for name, i, w, best, b in picks:
        if len(w) == 1 and best > 0:
            print(f"{name}#{i:03d} [{w[0]} s={best:2}] " + decode_jp(b[:-1], w[0]).replace("|", " / ")[:90])
