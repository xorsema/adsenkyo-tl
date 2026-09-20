"""Write notes/drive_request.txt for the bridge's message driver, from a script file.

  python tools/drive_requests.py [script.txt] [--ids T1-001,T2-003] [--col 4] [--row 2]

Each request: <id> <table> <index> <kanji page> <col> <row>. Kanji page is chosen from the message's
set (A=1, B=2, C=19). Table-2 messages 128+ (three 1-byte stubs) are skipped.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkinfo import ROOT
from check_script import parse

PAGE = {"A": 1, "B": 2, "C": 19}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--") and not a.startswith("T")]
    script = args[0] if args else os.path.join(ROOT, "script", "script.txt")
    opts = {sys.argv[i]: sys.argv[i + 1] for i in range(1, len(sys.argv) - 1) if sys.argv[i].startswith("--")}
    only = set(opts["--ids"].split(",")) if "--ids" in opts else None
    col, row = int(opts.get("--col", 4)), int(opts.get("--row", 2))
    lines = ["# id table index page col row"]
    if "--profiles-only" in sys.argv or "--profiles" in sys.argv:
        import profiles
        for pr in profiles.load():
            lines.append(f"{pr['id']} 1 {int(pr['id'][3:])} 1 4 9")
    if "--profiles-only" in sys.argv:
        path = os.path.join(ROOT, "notes", "drive_request.txt")
        return path, lines
    for e in parse(script):
        if only and e["id"] not in only:
            continue
        tbl, idx = int(e["id"][1]), int(e["id"][3:])
        if tbl == 2 and idx >= 128:
            continue
        lines.append(f"{e['id']} {tbl} {idx} {PAGE[e['set']]} {col} {row}")
    path = os.path.join(ROOT, "notes", "drive_request.txt")
    return path, lines


if __name__ == "__main__":
    path, lines = main()
    open(path, "w").write("\n".join(lines) + "\n")
    print(f"wrote {len(lines) - 1} requests to {path}")
