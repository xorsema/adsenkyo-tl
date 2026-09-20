"""Build the English ROM from script/script.txt  ->  build/english.nes

  python tools/insert.py                 # build + verify
  python tools/insert.py -v              # list every placement
  python tools/insert.py --all-bank5     # put every translated message in bank 5 (exercises the engine hook)
  python tools/insert.py --no-font       # leave CHR untouched
  python tools/insert.py --no-wrap       # do not word-wrap lines wider than 28 tiles
  python tools/insert.py --no-profiles   # skip script/profiles.txt
  python tools/insert.py --script F --out G

Placement
  * An EN line that fits its original slot (bytes incl. FF <= cap) is written in place, in every bank
    that carries a copy of the message. This path is the game's original mechanism and needs no hook.
  * Otherwise the text goes into bank 5 (a dead copy of the fixed bank; its first 0x400 bytes and the
    vector area are kept) and the pointer in bank 7's table becomes $C000+offset. tools/engine_patch.py
    installs the two small hooks that make the game read such pointers from bank 5.
Then the ROM is read back through the pointer tables exactly the way the hooked engine reads it,
and every message is compared; untranslated messages must be byte-identical to the original.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkinfo import ROOT, BANK
from check_script import parse
from script_io import encode_en
from latin_font import glyph_tiles
import engine_patch
from wrap import wrap_text
import profiles
import bitmap_text
import title_logo

PRG0 = 16
CHR0 = 16 + 8 * BANK
FIXED, EBANK = 7, 5
POOL = (0x0400, 0x3FF0)         # usable range inside bank 5
PROFILE_PAGE = 1               # profile text is drawn from CHR page 1 (pages 6/7/9/18 also hold the title art)
SCENE_PAGE_TABLE = 0xCA4E      # 10 bytes in the fixed bank: text page ($44) for each profile scene
TEXT_PAGES = (1, 2, 19)         # CHR 4 KB pages carrying the kana font + kanji sets
FF = 0xFF
MAXLEN = 255                    # the engine indexes the message with an 8-bit Y


def poff(bank, off):
    return PRG0 + bank * BANK + off


def banks_of(e):
    return [int(x) for x in e["copies"].split(",")]


def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    verbose = "-v" in sys.argv
    orig = open(os.path.join(ROOT, "rom", "original.nes"), "rb").read()
    rom = bytearray(orig)
    script = opt("--script", os.path.join(ROOT, "script", "script.txt"))
    out = opt("--out", os.path.join(ROOT, "build", "english.nes"))
    entries = parse(script)
    prof_pages = set()
    if "--no-profiles" not in sys.argv:
        from mkscript import build as _build
        base = {e["id"]: e for e in _build()}
        for pr in profiles.load():
            probs = profiles.check(pr)
            if probs:
                sys.exit(f"{pr['id']}: {probs}")
            b = base[pr["id"]]
            entries.append(dict(id=pr["id"], set="-", bank=b["bank"], off=b["off"], cap=b["cap"], ptr=b["ptr"],
                                copies=b["copies"], jp=pr["jp"], en=pr["en"], profile=True, page=pr["page"]))
            prof_pages.add(PROFILE_PAGE)
    todo = [e for e in entries if e["en"]]
    if not todo:
        sys.exit("no EN lines in " + script)

    rewrapped = 0
    for e in todo:
        if e.get("profile"):
            e["bytes"] = profiles.encode_profile(e["en"]) + bytes([FF])
            continue
        if "--no-wrap" not in sys.argv:
            new, _ = wrap_text(e["en"])
            rewrapped += new != e["en"]
            e["en"] = new
        try:
            e["bytes"] = encode_en(e["en"], e["set"]) + bytes([FF])
        except ValueError as ex:
            sys.exit(f"{e['id']}: {ex}")
        if len(e["bytes"]) > MAXLEN:
            sys.exit(f"{e['id']}: {len(e['bytes'])} bytes is over the {MAXLEN}-byte message limit")

    # --- placement
    pool_at = POOL[0]
    pool_index = {}                                   # message bytes -> offset (identical text shares)
    for e in todo:
        if len(e["bytes"]) <= e["cap"] and "--all-bank5" not in sys.argv:
            for b in banks_of(e):
                rom[poff(b, e["off"]):poff(b, e["off"]) + len(e["bytes"])] = e["bytes"]
            e["how"], e["dest"] = "in place", e["off"]
            continue
        off = pool_index.get(e["bytes"])
        if off is None:
            if pool_at + len(e["bytes"]) > POOL[1]:
                sys.exit(f"bank 5 pool full at {e['id']} ({pool_at - POOL[0]} of {POOL[1] - POOL[0]} bytes used)")
            off = pool_at
            rom[poff(EBANK, off):poff(EBANK, off) + len(e["bytes"])] = e["bytes"]
            pool_index[e["bytes"]] = off
            pool_at += len(e["bytes"])
        po = e["ptr"] - 0xC000
        cur = rom[poff(FIXED, po)] | rom[poff(FIXED, po + 1)] << 8
        if cur != 0x8000 + e["off"]:
            sys.exit(f"{e['id']}: pointer is ${cur:04X}, expected ${0x8000 + e['off']:04X}")
        new = 0xC000 + off
        rom[poff(FIXED, po)], rom[poff(FIXED, po + 1)] = new & 255, new >> 8
        e["how"], e["dest"] = "bank 5", off

    used_pool = pool_at - POOL[0]
    if used_pool:
        engine_patch.apply(rom, poff)

    # --- font
    if "--no-font" not in sys.argv:
        tiles = glyph_tiles()
        for page in TEXT_PAGES:
            for code, t in tiles.items():
                o = CHR0 + page * 4096 + code * 16
                rom[o:o + 16] = t

    # --- profile pages: Latin glyphs at raw tile codes 84..CF, and point the scene table at that page
    if prof_pages:
        o = poff(FIXED, SCENE_PAGE_TABLE - 0xC000)
        assert bytes(rom[o:o + 10]) == bytes.fromhex("06 06 07 09 09 07 12 12 12 06"), "scene page table changed?"
        rom[o:o + 10] = bytes([PROFILE_PAGE]) * 10
        gm = profiles.glyph_tile_map()
        for page in sorted(prof_pages):
            for raw, t in gm.items():
                o = CHR0 + page * 4096 + raw * 16
                rom[o:o + 16] = t

    # --- bitmap (picture) text: party labels etc.
    if "--no-bitmap" not in sys.argv:
        bitmap_text.apply(rom, CHR0)
        title_logo.apply(rom, PRG0, CHR0)

    # --- verify, reading the way the (hooked) engine reads
    exp = {e["id"]: e for e in todo}
    bad = 0
    for e in entries:
        po = e["ptr"] - 0xC000
        ptr = rom[poff(FIXED, po)] | rom[poff(FIXED, po + 1)] << 8
        if ptr >= 0xC000:
            reads = [(EBANK, ptr - 0xC000)]           # hook: hi >= $C0 -> bank 5 at (ptr - $4000) - $8000
        else:
            reads = [(b, ptr - 0x8000) for b in banks_of(e)]
        want = exp[e["id"]]["bytes"] if e["id"] in exp else orig[poff(e["bank"], e["off"]):poff(e["bank"], e["off"]) + e["cap"]]
        if e["id"] not in exp and ptr != 0x8000 + e["off"]:
            print(f"  VERIFY {e['id']}: untranslated message moved!"); bad += 1
        for b, off in reads:
            end = off
            while rom[poff(b, end)] != FF:
                end += 1
            got = bytes(rom[poff(b, off):poff(b, end) + 1])
            if got != want:
                bad += 1
                print(f"  VERIFY FAIL {e['id']} bank{b}:{off:04X}: got {got.hex(' ')[:48]} want {want.hex(' ')[:48]}")
    # nothing outside the intended regions may have changed
    allowed = [(poff(FIXED, 0xDC26 - 0xC000), poff(FIXED, 0xDC29 - 0xC000)),
               (poff(FIXED, 0xF815 - 0xC000), poff(FIXED, 0xF825 - 0xC000)),
               (poff(FIXED, 0xFE40 - 0xC000), poff(FIXED, 0xFE8B - 0xC000)),
               (poff(FIXED, 0xF879 - 0xC000), poff(FIXED, 0xFBBA - 0xC000)),    # pointer tables
               (poff(FIXED, SCENE_PAGE_TABLE - 0xC000), poff(FIXED, SCENE_PAGE_TABLE - 0xC000 + 10)),
               (poff(6, 0x9126 - 0x8000), poff(6, 0x9222 - 0x8000)),      # title logo metatile streams
               (poff(EBANK, POOL[0]), poff(EBANK, POOL[1])), (CHR0, len(rom))]
    for e in todo:
        if e["how"] == "in place":
            for b in banks_of(e):
                allowed.append((poff(b, e["off"]), poff(b, e["off"]) + e["cap"]))
    stray = [i for i in range(len(rom)) if rom[i] != orig[i] and not any(a <= i < z for a, z in allowed)]
    if stray:
        bad += 1
        print(f"  STRAY CHANGES outside expected regions: {len(stray)} bytes, first at 0x{stray[0]:X}")
    if bad:
        sys.exit(f"{bad} verification problem(s); ROM not written")

    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(rom)

    n_in = sum(1 for e in todo if e["how"] == "in place")
    n_b5 = len(todo) - n_in
    prg = sum(1 for i in range(PRG0, CHR0) if rom[i] != orig[i])
    chrb = sum(1 for i in range(CHR0, len(rom)) if rom[i] != orig[i])
    print(f"wrote {out}")
    print(f"{len(todo)} messages: {n_in} in place, {n_b5} in bank 5; all verified through the pointer tables")
    print(f"{rewrapped} messages word-wrapped to {28} tiles (--no-wrap to disable); "
          f"{sum(1 for e in todo if e.get('profile'))} profile screens, CHR pages {sorted(prof_pages)}")
    print(f"bank 5 pool: {used_pool} of {POOL[1] - POOL[0]} bytes used ({POOL[1] - POOL[0] - used_pool} free)")
    changed_pages = sorted({(i - CHR0) // 4096 for i in range(CHR0, len(rom)) if rom[i] != orig[i]})
    print(f"bytes changed: PRG {prg}, CHR {chrb} in pages {changed_pages}; engine hooks: {'installed' if used_pool else 'not needed'}")
    if verbose:
        for e in todo:
            print(f"  {e['id']}: {e['how']:9} -> {'bank5' if e['how'] == 'bank 5' else 'bank%d' % e['bank']}:{e['dest']:04X}  {len(e['bytes'])}/{e['cap']}B")


if __name__ == "__main__":
    main()
