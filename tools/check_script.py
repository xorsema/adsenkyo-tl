"""Validate the EN lines of script/script.txt.

  python tools/check_script.py          # summary + problems
  python tools/check_script.py -v       # also list every translated entry

For each entry with an EN line: every character must have a glyph in the English font,
and we report whether it fits in place (bytes incl. FF <= cap) and how each line's width
(1 tile per character) compares with the Japanese (w=...) and the 32-tile screen.
"""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkinfo import ROOT
from script_io import encode_en
from wrap import wrap_text

SCREEN = 32


def parse(path):
    entries, cur = [], None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = re.match(r"=== (\S+)\s+set=(\S+)\s+src=(\S+)\s+cap=(\d+)\s+ptr=(\$\w+)\s+copies=(\S+)\s+w=(\S+)", line)
        if m:
            sb, so = re.match(r"bank(\d+):([0-9A-Fa-f]+)", m.group(3)).groups()
            cur = dict(id=m.group(1), set=m.group(2), src=m.group(3), cap=int(m.group(4)),
                       bank=int(sb), off=int(so, 16), ptr=int(m.group(5)[1:], 16),
                       copies=m.group(6), w=[int(x) for x in m.group(7).split("/")], jp="", en="")
            entries.append(cur)
        elif cur and line.startswith("JP:"):
            cur["jp"] = line[3:].strip()
        elif cur and line.startswith("EN:"):
            cur["en"] = line[4:] if line[3:4] == " " else line[3:]
    return entries


def widths(text):
    return [len(re.sub(r"\{[0-9A-Fa-f]{2}\}", "x", ln)) for ln in text.split("|")]


def capacity_report(entries, done):
    """Space budget per copy-group. A message can only use space freed by messages whose
    copy set contains its own (so shared messages compete for the least space)."""
    from collections import defaultdict
    groups = defaultdict(list)
    for e in entries:
        groups[e["copies"]].append(e)
    sets = {k: set(map(int, k.split(","))) for k in groups}
    print("space budget (bytes)   copies: pool = freed JP space usable by that group | EN needed so far")
    for k, l in sorted(groups.items()):
        pool = sum(x["cap"] for kk, ll in groups.items() if sets[k] <= sets[kk] for x in ll)
        need = 0
        for x in l:
            if x["en"]:
                try:
                    need += len(encode_en(x["en"], x["set"])) + 1
                except ValueError:
                    pass
        print(f"  {k:6} {len(l):4} msgs  JP={sum(x['cap'] for x in l):5}  pool={pool:5}  EN so far={need:5}")


def main():
    verbose = "-v" in sys.argv
    path = next((a for a in sys.argv[1:] if not a.startswith("-")), os.path.join(ROOT, "script", "script.txt"))
    entries = parse(path)
    done = [e for e in entries if e["en"]]
    errors, reloc, wide = [], [], []
    for e in done:
        e["en"] = wrap_text(e["en"])[0]          # judge what insert.py will actually build
        try:
            b = encode_en(e["en"], e["set"]) + b"\xff"
        except ValueError as ex:
            errors.append((e["id"], str(ex))); continue
        need = len(b)
        fits = need <= e["cap"]
        w = widths(e["en"])
        note = []
        if not fits:
            reloc.append((e["id"], need, e["cap"]))
            note.append(f"RELOCATE +{need - e['cap']}B")
        if max(w) > SCREEN:
            wide.append((e["id"], max(w))); note.append(f"LINE>{SCREEN}")
        elif max(w) > max(e["w"]):
            note.append(f"wider than JP ({max(w)}>{max(e['w'])})")
        if e["copies"] != "1":
            note.append(f"shared copies={e['copies']}")
        if verbose:
            print(f"{e['id']}: {need}/{e['cap']}B  w={'/'.join(map(str, w))}  {'; '.join(note)}")
    capacity_report(entries, done)
    print(f"{len(entries)} messages, {len(done)} translated ({100 * len(done) // max(1, len(entries))}%)")
    print(f"  in place: {len(done) - len(errors) - len(reloc)}   need relocation: {len(reloc)}   "
          f"lines wider than {SCREEN}: {len(wide)}   errors: {len(errors)}")
    for i, msg in errors:
        print(f"  ERROR {i}: {msg}")
    for i, need, cap in reloc:
        print(f"  reloc {i}: needs {need}B, has {cap}B")
    for i, w in wide:
        print(f"  wide  {i}: {w} tiles")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
