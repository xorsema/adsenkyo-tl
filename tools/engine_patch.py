"""Engine hooks that let message text live in bank 5.

How the game prints a message (found with tools/bridge mmc1 trace + bank probe):
    DC26  lda $02EF ; bne DC2F        ; flag: table 2 ?
    DC2B  lda #1 ; bne DC31           ; table 1 -> bank 1
    DC2F  lda #2                      ; table 2 -> bank 2
    DC31  jsr $C200                   ; map bank A at $8000
    DC34  jsr $F63F                   ; message engine (reads text with lda ($15),y at F815)
    DC37  lda #6 ; jsr $C200          ; back to the home bank
Bank 5 is a dead byte-for-byte copy of the fixed bank, so its 16 KB can hold English.

Hooks (both live in the zero-filled run at $FE40-$FE8A of the fixed bank):
  1. bank chooser  ($DC26 -> jmp $FE40): if the message pointer's high byte ($0225) >= $C0,
     map bank 5, otherwise choose bank 1/2 exactly as before.
  2. fetch         ($F815 -> jmp $FE60): if the pointer high byte >= $C0, subtract $40 so
     $C000+off is read at $8000+off (bank 5 is mapped there); otherwise identical to the original.

A message pointer of $C000+off in the pointer tables therefore means "off within bank 5".
"""
FIXED = 7
CHOOSER = 0xFE40
FETCH = 0xFE60

# lda $0225 / cmp #$C0 / bcc normal / lda #5 / jmp $DC31 /
# normal: lda $02EF / bne two / lda #1 / jmp $DC31 / two: lda #2 / jmp $DC31
CHOOSER_CODE = bytes.fromhex(
    "AD2502 C9C0 9005 A905 4C31DC"
    "AD EF02 D005 A901 4C31DC A902 4C31DC".replace(" ", ""))
# ldy $0220 / lda $0224 / sta $15 / lda $0225 / cmp #$C0 / bcc +2 / sbc #$40 /
# sta $16 / lda ($15),y / rts
FETCH_CODE = bytes.fromhex("AC2002 AD2402 8515 AD2502 C9C0 9002 E940 8516 B115 60".replace(" ", ""))

SITE_CHOOSER = (0xDC26, bytes.fromhex("ADEF02"), bytes([0x4C, CHOOSER & 255, CHOOSER >> 8]))
SITE_FETCH_OLD = bytes.fromhex("AC2002AD24028515AD25028516B11560")
SITE_FETCH = (0xF815, SITE_FETCH_OLD, bytes([0x4C, FETCH & 255, FETCH >> 8]) + bytes([0xEA]) * (len(SITE_FETCH_OLD) - 3))


def apply(rom, poff):
    """Patch a bytearray ROM in place. poff(bank, off) -> file offset. Raises if a site differs."""
    def at(addr):
        return poff(FIXED, addr - 0xC000)

    for addr, old, new in (SITE_CHOOSER, SITE_FETCH):
        cur = bytes(rom[at(addr):at(addr) + len(old)])
        if cur != old:
            raise SystemExit(f"engine patch: unexpected bytes at ${addr:04X}: {cur.hex(' ')}")
        rom[at(addr):at(addr) + len(new)] = new
    for addr, code in ((CHOOSER, CHOOSER_CODE), (FETCH, FETCH_CODE)):
        if any(rom[at(addr) + k] != 0 for k in range(len(code))):
            raise SystemExit(f"engine patch: hook area ${addr:04X} is not zero-filled")
        rom[at(addr):at(addr) + len(code)] = code
    assert CHOOSER + len(CHOOSER_CODE) <= FETCH and FETCH + len(FETCH_CODE) <= 0xFE8B


def selftest():
    """Disassemble the hooks with the project's own decoder and check the control flow."""
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from m6502 import OPS

    def dis(code, base):
        o, out = 0, []
        while o < len(code):
            mn, mode, ln = OPS[code[o]]
            raw = code[o:o + ln]
            if mode == "rel":
                r = raw[1]
                tgt = base + o + 2 + (r - 256 if r & 0x80 else r)
                out.append((base + o, mn, tgt))
            elif ln == 3:
                out.append((base + o, mn, raw[1] | raw[2] << 8))
            else:
                out.append((base + o, mn, raw[1] if ln == 2 else None))
            o += ln
        return out
    c = dis(CHOOSER_CODE, CHOOSER)
    f = dis(FETCH_CODE, FETCH)
    starts = {a for a, _, _ in c}
    for a, mn, t in c:
        if mn in ("bcc", "bne"):
            assert t in starts, (hex(a), mn, hex(t))       # branches land on instruction starts
        if mn == "jmp":
            assert t == 0xDC31
    fstarts = {a for a, _, _ in f}
    for a, mn, t in f:
        if mn == "bcc":
            assert t in fstarts, (hex(a), hex(t))
    assert f[-1][1] == "rts"
    return c, f


if __name__ == "__main__":
    c, f = selftest()
    for name, listing in (("chooser", c), ("fetch", f)):
        print(name)
        for a, mn, t in listing:
            print(f"  ${a:04X}: {mn:4} {'' if t is None else '$%04X' % t if isinstance(t, int) and t > 255 else '$%02X' % t}")
