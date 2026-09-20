"""Generate script/script.txt (translatable messages) and script/nontext.txt (reference).

  python tools/mkscript.py            # (re)generate; existing EN/NOTE lines are preserved by id
  python tools/mkscript.py --check    # only run the JP round-trip check

Entry format in script.txt (edit only the EN line and, optionally, NOTE):

  === T1-001  set=A  src=bank1:0023  cap=17  ptr=$F87B  copies=1  w=20
  JP: 候補者_を_選んでください
  EN: Pick a candidate
  NOTE: anything you like

'cap' = bytes available in place (including the FF terminator). EN longer than that
needs relocation (handled by the insertion step). '|' = line break.
"""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkinfo import load, ROOT, BANK
from extract_text import messages, TABLES, best_set, OVERRIDE
from script_io import decode_jp, encode_jp, jp_width

OUT_DIR = os.path.join(ROOT, "script")
TABLE_ID = {"bank1": "T1", "bank2": "T2"}
PTR_BASE = {"bank1": 0xF879, "bank2": 0xFA79}
HEADER = """# America Daitouryou Senkyo - script
# Edit the EN: line of each entry (leave it empty to keep the Japanese). NOTE: is free text.
# In JP lines: '_' = blank tile, '|' = line break, {XX} = raw byte with no known glyph.
# In EN lines: write normal text; ' ' = blank tile, '|' = line break, {XX} = raw byte.
# cap = bytes available in place (incl. FF terminator). w = JP width in 8px tiles per line.
# Regenerate with: python tools/mkscript.py   (EN and NOTE lines are preserved by id)
"""


FORCE_LAYOUT = {f"T1-{i:03d}" for i in range(128, 183)} | {"T1-246"}   # keyboard/tile rows the heuristic misses
LOWER_A = {0xE0 + i: c for i, c in enumerate("abcdefghijklmnopqrstu")}
LOWER_A.update({0xA0: "v", 0xA1: "w", 0xF7: "x", 0xF8: "y", 0xF9: "z"})


def is_english(b):
    """Real English words encoded with the a-z codes (the oath), not tile-index rows."""
    s = "".join(LOWER_A.get(x, "_" if x in (0, 0xFE) else "?") for x in b[:-1])
    words = re.findall(r"[a-z]{4,}", s)
    return len(words) >= 4


def is_layout(b):
    """Tile/keyboard layout data rather than prose.

    - many high codes (>= B0), ignoring the FE/FF control bytes
    - a run of 5+ consecutive kana codes (gojuon keyboard rows: すせそたち...)
    (blank-padded lines are NOT layout: state stats and primary dates are padded for
    column alignment but are real, translatable labels)
    """
    body = b[:-1]
    hi = sum(1 for x in body if x >= 0xB0 and x != 0xFE)
    if hi > 4:
        return True
    run = 1
    for a, c in zip(body, body[1:]):
        run = run + 1 if (0x04 <= a <= 0x61 and c == a + 1) else 1
        if run >= 5:
            return True
    return False


def build():
    prg, _ = load()
    entries, seen = [], {}
    for name, base, n, bank in TABLES:
        for i, p, b in messages(prg, base, n, bank):
            body = b[:-1]
            eid = f"{TABLE_ID[name]}-{i:03d}"
            ks = OVERRIDE.get((name, i)) or best_set(name, b)
            e = dict(id=eid, table=name, index=i, bank=bank, off=p, raw=b, body=body, set=ks,
                     ptr=PTR_BASE[name] + 2 * i, cap=len(b))
            copies = [x for x in (1, 2, 3) if prg[x][p:p + len(b)] == b]
            e["copies"] = ",".join(map(str, copies))
            if (bank, p) in seen:
                e["kind"], e["alias"] = "alias", seen[(bank, p)]
            elif is_english(b):
                e["kind"] = "english"
            elif is_layout(b) or eid in FORCE_LAYOUT:
                e["kind"] = "layout"
            else:
                e["kind"] = "text"
            seen.setdefault((bank, p), eid)
            entries.append(e)
    return entries


def parse_existing(path):
    """id -> {'EN': str, 'NOTE': str} from an existing script.txt."""
    keep, cur = {}, None
    if not os.path.exists(path):
        return keep
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = re.match(r"=== (\S+)", line)
        if m:
            cur = m.group(1); keep[cur] = {"EN": "", "NOTE": ""}
        elif cur and line.startswith("EN:"):
            keep[cur]["EN"] = line[4:] if line[3:4] == " " else line[3:]
        elif cur and line.startswith("NOTE:"):
            keep[cur]["NOTE"] = line[5:].strip()
    return keep


def write(entries):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "script.txt")
    keep = parse_existing(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(HEADER)
        for e in entries:
            if e["kind"] != "text":
                continue
            k = keep.get(e["id"], {"EN": "", "NOTE": ""})
            w = "/".join(map(str, jp_width(e["body"], e["set"])))
            f.write(f"\n=== {e['id']}  set={e['set']}  src=bank{e['bank']}:{e['off']:04X}  cap={e['cap']}"
                    f"  ptr=${e['ptr']:04X}  copies={e['copies']}  w={w}\n")
            f.write(f"JP: {decode_jp(e['body'], e['set'])}\n")
            f.write(f"EN: {k['EN']}\n")
            if k["NOTE"]:
                f.write(f"NOTE: {k['NOTE']}\n")
    npath = os.path.join(OUT_DIR, "nontext.txt")
    with open(npath, "w", encoding="utf-8") as f:
        f.write("# Not translatable through script.txt: name-entry/keyboard layout rows, already-English text,\n"
                "# and duplicate pointers. Reference only.\n")
        for e in entries:
            if e["kind"] == "text":
                continue
            extra = f" alias-of={e['alias']}" if e["kind"] == "alias" else ""
            f.write(f"\n=== {e['id']}  kind={e['kind']}{extra}  src=bank{e['bank']}:{e['off']:04X}  cap={e['cap']}\n")
            f.write(f"HEX: {e['body'].hex(' ')}\n")
    return path, npath


def check(entries):
    bad = 0
    for e in entries:
        if decode_jp_roundtrip(e) is False:
            bad += 1
    return bad


def decode_jp_roundtrip(e):
    try:
        return encode_jp(decode_jp(e["body"], e["set"]), e["set"]) == e["body"]
    except ValueError:
        return False


def main():
    entries = build()
    bad = check(entries)
    from collections import Counter
    c = Counter(e["kind"] for e in entries)
    print(f"{len(entries)} messages: {dict(c)}; JP round-trip failures: {bad}")
    if bad:
        sys.exit(1)
    if "--check" in sys.argv:
        return
    print("wrote", *write(entries))


if __name__ == "__main__":
    main()
