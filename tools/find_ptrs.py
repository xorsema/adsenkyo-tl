"""Find runs of 16-bit pointers that land on likely string starts.

String starts in bank T: offset 0 and every offset right after an FF byte.
A candidate pointer table is >=MINRUN consecutive little-endian words (in any
bank) whose value-0x8000 is a string start of bank T.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkinfo import load, BANK

MINRUN = 3


def starts(bank_bytes):
    s = {0}
    for i, x in enumerate(bank_bytes[:-1]):
        if x == 0xFF:
            s.add(i + 1)
    return s


def main():
    prg, _ = load()
    tgt = [int(a) for a in sys.argv[1:]] or [1, 2]
    for t in tgt:
        S = starts(prg[t])
        print(f"== targets in bank {t}: {len(S)} candidate string starts")
        for b in range(8):
            d = prg[b]
            o = 0
            while o < BANK - 1:
                run = 0
                while o + 2 * run + 1 < BANK:
                    w = d[o + 2 * run] | d[o + 2 * run + 1] << 8
                    if 0x8000 <= w < 0xC000 and (w - 0x8000) in S:
                        run += 1
                    else:
                        break
                if run >= MINRUN:
                    ws = [d[o + 2 * i] | d[o + 2 * i + 1] << 8 for i in range(run)]
                    print(f"  in bank {b} @ ${(0xC000 if b == 7 else 0x8000) + o:04X} "
                          f"(off {o:04X}): {run} ptrs  {' '.join('%04X' % w for w in ws[:8])}{' ...' if run > 8 else ''}")
                    o += 2 * run
                else:
                    o += 1


if __name__ == "__main__":
    main()
