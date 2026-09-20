"""Extract all messages reachable through the known pointer tables.

Tables live in the fixed bank (7) as 16-bit little-endian pointers into $8000-$BFFF:
  $F879  256 msgs -> bank 1
  $FA79  131 msgs -> bank 2
Output: notes/script_bankN.txt  (index, ROM offset, raw hex, decoded)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkinfo import load, ROOT
from text_probe import decode

TABLES = [("bank1", 0xF879, 256, 1), ("bank2", 0xFA79, 131, 2)]
KSET = {"bank1": "A", "bank2": "B"}      # default kanji set per table (see pick_sets.py)
OVERRIDE = {("bank1", 34): "A", ("bank1", 86): "A", ("bank1", 99): "A"}   # checked by eye

# encoded English (codes E0-F9 = a-z) and keyboard-grid rows are not prose
def is_layout(b):
    hi = sum(1 for x in b if x >= 0xB0)
    return hi > 6 or (b.count(0x00) > len(b) // 2)


def messages(prg, base, n, bank):
    d = prg[7]
    o = base - 0xC000
    for i in range(n):
        p = (d[o + 2 * i] | d[o + 2 * i + 1] << 8) - 0x8000
        e = p
        while prg[bank][e] != 0xFF:
            e += 1
        yield i, p, bytes(prg[bank][p:e + 1])


def best_set(name, b):
    from kanji import SETS
    from pick_sets import score
    from script_io import decode_jp
    sc = {k: score(decode_jp(b[:-1], k)) for k in SETS}
    top = max(sc.values())
    if top == 0:
        return KSET[name]
    w = [k for k, v in sc.items() if v == top]
    return KSET[name] if KSET[name] in w else w[0]


def main():
    prg, _ = load()
    for name, base, n, bank in TABLES:
        path = os.path.join(ROOT, "notes", f"script_{name}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {name}: pointer table ${base:04X}, {n} messages, source bank {bank}\n")
            for i, p, b in messages(prg, base, n, bank):
                kset = OVERRIDE.get((name, i)) or best_set(name, b)
                tag = "  [layout/non-prose]" if is_layout(b) else f"  kanji-set={kset}"
                f.write(f"\n#{i:03d} bank{bank}:{p:04X} len={len(b)}{tag}\n  {b.hex(' ')}\n")
                for line in decode(b, kset).split("|"):
                    f.write(f"  > {line}\n")
        print(path)


if __name__ == "__main__":
    main()
