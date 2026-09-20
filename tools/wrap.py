"""Word-wrap English message text to the usable screen width.

Messages are drawn starting around column 4 of a 32-tile-wide screen, and the widest Japanese line in
the whole script is 28 tiles, so WIDTH = 28. A line wider than that is wrapped at spaces; wrapped
continuation lines keep the original line's indentation. Lines that are column-aligned (two or more
spaces between words, e.g. statistics tables) or contain raw {XX} codes are never touched - they are
reported instead.

  python tools/wrap.py [script.txt]      # preview what would change
"""
import os
import re
import sys

WIDTH = 28
_ALIGNED = re.compile(r"\S {2,}\S")
_TOKEN = re.compile(r"\{[0-9A-Fa-f]{2}\}")


def width(line):
    return len(_TOKEN.sub("x", line))


def wrap_line(line, limit=WIDTH):
    """-> (list of lines, reason) ; reason is None if wrapped/untouched, else why it was left alone."""
    if width(line) <= limit:
        return [line], None
    if _TOKEN.search(line):
        return [line], "contains raw codes"
    if _ALIGNED.search(line.strip(" ")):
        return [line], "column-aligned"
    indent = len(line) - len(line.lstrip(" "))
    pad = " " * indent
    room = limit - indent
    if room < 8:
        return [line], "indent too deep"
    out, cur = [], ""
    for word in line.strip(" ").split(" "):
        while len(word) > room:                       # a single over-long word: hard split
            if cur:
                out.append(pad + cur); cur = ""
            out.append(pad + word[:room]); word = word[room:]
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= room:
            cur += " " + word
        else:
            out.append(pad + cur); cur = word
    if cur:
        out.append(pad + cur)
    return out, None


def wrap_text(text, limit=WIDTH):
    """Wrap every line of a message ('|'-separated). -> (new text, [reasons for lines left too wide])."""
    lines, left = [], []
    for ln in text.split("|"):
        new, why = wrap_line(ln, limit)
        lines += new
        if why and width(ln) > limit:
            left.append((ln.strip(), why))
    return "|".join(lines), left


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from check_script import parse
    from mkinfo import ROOT
    path = next((a for a in sys.argv[1:] if not a.startswith("-")), os.path.join(ROOT, "script", "script.txt"))
    changed = added = 0
    stuck = []
    for e in parse(path):
        if not e["en"]:
            continue
        new, left = wrap_text(e["en"])
        if new != e["en"]:
            changed += 1
            added += new.count("|") - e["en"].count("|")
            if "-v" in sys.argv:
                print(f"{e['id']}: {e['en'].count('|') + 1} -> {new.count('|') + 1} lines")
                for ln in new.split("|"):
                    print("    " + ln)
        stuck += [(e["id"], ln, why) for ln, why in left]
    print(f"{changed} messages re-wrapped, {added} lines added in total")
    print(f"{len(stuck)} lines still wider than {WIDTH} (not safe to wrap automatically):")
    for i, ln, why in stuck:
        print(f"  {i}: [{why}] {ln[:60]}")


if __name__ == "__main__":
    main()
