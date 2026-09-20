"""Analyse nametable dumps written by the bridge's message driver (notes/shots/*.nt).

Each dump is 30 rows x 32 columns of tile numbers, taken after the real engine drew the message at
(col, row). Tile 0 is blank. Reports messages whose text spilled left of the start column (a line
wrapped past column 31) or touches the right edge.

  python tools/analyze_shots.py [--col 4]
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path):
    h = open(path).read().strip()
    t = [int(h[i:i + 2], 16) for i in range(0, len(h), 2)]
    return [t[r * 32:(r + 1) * 32] for r in range(30)]


def analyse(grid, col):
    rows = [r for r in range(30) if any(grid[r])]
    if not rows:
        return None
    left = min(min(c for c in range(32) if grid[r][c]) for r in rows)
    right = max(max(c for c in range(32) if grid[r][c]) for r in rows)
    spill = [r for r in rows if any(grid[r][c] for c in range(0, col))]
    return dict(rows=len(rows), first=rows[0], last=rows[-1], left=left, right=right, spill=spill)


def main():
    col = int(sys.argv[sys.argv.index("--col") + 1]) if "--col" in sys.argv else 4
    res = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "notes", "shots", "*.nt"))):
        res[os.path.basename(p)[:-3]] = analyse(load(p), col)
    empty = [k for k, v in res.items() if v is None]
    bad = {k: v for k, v in res.items() if v and v["spill"]}
    edge = [k for k, v in res.items() if v and not v["spill"] and v["right"] >= 31]
    print(f"{len(res)} dumps; blank (nothing drawn): {len(empty)}; OVERFLOW (text wrapped past col 31): {len(bad)}; "
          f"lines that exactly fill the screen: {len(edge)}")
    for k, v in sorted(bad.items()):
        print(f"  {k}: wrapped tail in rows {v['spill'][:5]} (message spans rows {v['first']}-{v['last']})")
    if empty:
        print("blank:", ", ".join(empty[:20]))
    return res


if __name__ == "__main__":
    main()
