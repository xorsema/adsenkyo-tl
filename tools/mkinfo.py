"""Code-flow analysis for the MMC1 ROM -> da65 info files (disasm/bankN.info).

Memory model (MMC1 PRG mode 3, which the boot code appears to select):
  $8000-$BFFF  switchable 16 KB bank (0-7)
  $C000-$FFFF  fixed bank 7

Seeds: RESET/NMI/IRQ vectors, plus (if rom/mesen.cdl exists) every Mesen CDL
jump-target / sub-entry byte and the start of every run of CDL "code" bytes.
Flow follows branches, JSR and JMP abs. A JSR/JMP into $8000-$BFFF from the
fixed bank has an unknown target bank and is reported, not followed.

Anything not proven to be code is emitted as a ByteTable, so reassembly is
byte-exact by construction. Refine later via tools/hints.txt (not yet used).
"""
import os
import sys

from m6502 import OPS, TERMINATORS, BRANCHES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = 16384
FIXED = 7

CDL_CODE, CDL_DATA, CDL_JUMP, CDL_SUB = 0x01, 0x02, 0x04, 0x08


def load():
    rom = open(os.path.join(ROOT, "rom", "original.nes"), "rb").read()
    prg = [rom[16 + i * BANK:16 + (i + 1) * BANK] for i in range(8)]
    # every rom/mesen*.cdl is OR-merged, so new logs only ever add coverage
    merged = None
    for name in sorted(os.listdir(os.path.join(ROOT, "rom"))):
        if name.startswith("mesen") and name.endswith(".cdl"):
            raw = open(os.path.join(ROOT, "rom", name), "rb").read()
            assert raw[:5] == b"CDLv2", f"unexpected CDL magic in {name}"
            flags = raw[9:9 + 8 * BANK]
            merged = flags if merged is None else bytes(a | b for a, b in zip(merged, flags))
    cdl = None if merged is None else [merged[i * BANK:(i + 1) * BANK] for i in range(8)]
    return prg, cdl


def cpu_base(bank):
    return 0xC000 if bank == FIXED else 0x8000


def resolve(addr, swap):
    """CPU address -> (bank, offset), or None if the bank is unknown."""
    if addr >= 0xC000:
        return FIXED, addr - 0xC000
    if addr >= 0x8000 and swap is not None:
        return swap, addr - 0x8000
    return None


# Jump-table dispatcher: JSR to this routine is followed by an inline table of
# .addr entries; A = index. Signature (operand bytes wildcarded as None):
#   asl a / tay / iny / pla / sta zp / pla / sta zp / lda (zp),y / sta zp /
#   iny / lda (zp),y / sta zp / jmp (abs)
DISPATCH_SIG = [0x0A, 0xA8, 0xC8, 0x68, 0x85, None, 0x68, 0x85, None,
                0xB1, None, 0x85, None, 0xC8, 0xB1, None, 0x85, None, 0x6C]
MAX_TABLE = 128

# MMC1 helpers in the fixed bank (each does the 5-write serial sequence with A):
#   $C1C4 control  $C1D8 CHR0  $C1EC CHR1  $C200 PRG bank
PRG_BANK_SET = 0xC200
HOME_BANK = 6   # resident at $8000 by default; code restores it with `lda #6`


def find_dispatchers(prg):
    """(bank, offset) of every routine matching DISPATCH_SIG."""
    found = set()
    n = len(DISPATCH_SIG)
    for b in range(8):
        d = prg[b]
        for o in range(BANK - n):
            if all(s is None or d[o + i] == s for i, s in enumerate(DISPATCH_SIG)):
                found.add((b, o))
    return found


def analyse(prg, cdl):
    mark = [bytearray(BANK) for _ in range(8)]   # 0 unknown, 1 insn start, 2 operand, 3 table
    labels = [set() for _ in range(8)]            # offsets that are branch/call targets
    invalid, conflicts, unresolved, switches = [], [], [], []
    tables = []                                   # (bank, offset, entries)
    dispatchers = find_dispatchers(prg)
    stats = {"seeds": 0, "dispatchers": sorted(dispatchers)}

    vec = prg[FIXED][-6:]
    vectors = {"NMI": vec[0] | vec[1] << 8, "RESET": vec[2] | vec[3] << 8,
               "IRQ": vec[4] | vec[5] << 8}

    work = []
    for name, addr in vectors.items():
        b, o = resolve(addr, None)
        work.append((b, o, None, name))

    if cdl:
        for b in range(8):
            f = cdl[b]
            for o in range(BANK):
                if f[o] & (CDL_JUMP | CDL_SUB):
                    work.append((b, o, b if b != FIXED else None, None))
                elif f[o] & CDL_CODE and (o == 0 or not f[o - 1] & CDL_CODE):
                    work.append((b, o, b if b != FIXED else None, None))
    stats["seeds"] = len(work)

    assumed = []

    def pick_bank(target, kind):
        """Guess the bank mapped at $8000-$BFFF for a call from the fixed bank.

        Only banks 0-6 can be there. Evidence order: (1) the one bank whose CDL
        shows code executed at that address; (2) for direct jsr/jmp, home bank 6
        (the bank that is resident by default) when the CDL has no objection.
        """
        cands = [i for i in range(7) if cdl and cdl[i][target - 0x8000] & CDL_CODE]
        if len(cands) == 1:
            return cands[0], "cdl"
        if kind in ("jsr", "jmp") and (HOME_BANK in cands or not cands):
            return HOME_BANK, "home"
        return None

    stats["assumed"] = assumed

    def cdl_data_only(b, o, n):
        return cdl and any(cdl[b][o + i] & CDL_DATA and not cdl[b][o + i] & CDL_CODE
                           for i in range(n))

    while work:
        b, o, swap, why = work.pop()
        if why:
            labels[b].add(o)
        elif cdl:
            labels[b].add(o) if cdl[b][o] & (CDL_JUMP | CDL_SUB) else None
        if b != FIXED:
            swap = b
        a_imm = None   # value of A if the previous instruction was `lda #imm`
        while True:
            if o >= BANK or mark[b][o]:
                break
            info = OPS.get(prg[b][o])
            if info is None:
                invalid.append((b, o))
                break
            mn, mode, ln = info
            if o + ln > BANK:
                break
            if cdl_data_only(b, o, ln):
                conflicts.append((b, o))
                break
            mark[b][o] = 1
            for i in range(1, ln):
                mark[b][o + i] = 2
            pc = cpu_base(b) + o
            if mode == "rel":
                rel = prg[b][o + 1]
                target = pc + 2 + (rel - 256 if rel & 0x80 else rel)
            elif mn in ("jmp", "jsr") and mode == "abs":
                target = prg[b][o + 1] | prg[b][o + 2] << 8
            else:
                target = None
            is_dispatch = False
            if target is not None:
                r = resolve(target, swap)
                if r is None and 0x8000 <= target < 0xC000 and b == FIXED:
                    pick = pick_bank(target, mn)
                    if pick:
                        r = (pick[0], target - 0x8000)
                        assumed.append((b, pc, mn, target, *pick))
                if r is None:
                    unresolved.append((b, pc, mn, target))
                else:
                    labels[r[0]].add(r[1])
                    # a called routine may have many callers with different
                    # banks mapped, so its bank context is unknown; branches and
                    # tail-jumps stay in the same context
                    work.append((r[0], r[1], None if mn == "jsr" else swap, None))
                    is_dispatch = mn == "jsr" and r in dispatchers
                # `lda #N` / `jsr PRG_BANK_SET` maps bank N at $8000 from here on
                if mn == "jsr" and target == PRG_BANK_SET and a_imm is not None and b == FIXED:
                    swap = a_imm & 7
                    switches.append((b, pc, a_imm))
            a_imm = prg[b][o + 1] if (mn, mode) == ("lda", "imm") else None
            if is_dispatch:
                # inline .addr table follows the JSR; execution never falls through
                n = read_table(prg, mark, b, o + ln, swap, labels, work, unresolved,
                               pick_bank, assumed)
                tables.append((b, o + ln, n))
                break
            if mn in TERMINATORS:
                break
            o += ln
    stats["tables"] = tables
    return mark, labels, invalid, conflicts, unresolved, stats, vectors


def read_table(prg, mark, b, o, swap, labels, work, unresolved, pick_bank, assumed):
    """Read an inline .addr table at bank b offset o. Returns entry count.

    An entry is accepted while its target is $8000+ and (when resolvable) lands
    on a valid opcode, and the table bytes aren't already claimed as code.
    """
    n = 0
    while n < MAX_TABLE and o + 2 <= BANK:
        if mark[b][o] in (1, 2) or mark[b][o + 1] in (1, 2):
            break
        addr = prg[b][o] | prg[b][o + 1] << 8
        if addr < 0x8000:
            break
        r = resolve(addr, swap)
        if r is None and addr < 0xC000 and b == FIXED:
            pick = pick_bank(addr, "table")
            if pick:
                r = (pick[0], addr - 0x8000)
                assumed.append((b, cpu_base(b) + o, "table", addr, *pick))
        if r is not None:
            if prg[r[0]][r[1]] not in OPS:
                break
            labels[r[0]].add(r[1])
            work.append((r[0], r[1], swap, None))
        else:
            unresolved.append((b, cpu_base(b) + o, "table", addr))
        mark[b][o] = mark[b][o + 1] = 3
        o += 2
        n += 1
    return n


def ranges(mark_b):
    """Split a bank's marks into (start, end_exclusive, kind) runs.

    kind: 'Code' | 'AddrTable' | 'ByteTable'
    """
    def kind_of(m):
        return "Code" if m in (1, 2) else "AddrTable" if m == 3 else "ByteTable"
    out, start, cur = [], 0, None
    for o in range(BANK):
        k = kind_of(mark_b[o])
        if cur is None:
            cur = k
        elif k != cur:
            out.append((start, o, cur))
            start, cur = o, k
    out.append((start, BANK, cur))
    return out


def write_info(prg, mark, labels, cdl):
    outdir = os.path.join(ROOT, "disasm")
    os.makedirs(outdir, exist_ok=True)
    for b in range(8):
        base = cpu_base(b)
        # bank data is written as a raw .bin next to the info file
        open(os.path.join(outdir, f"bank{b}.bin"), "wb").write(prg[b])
        lines = ["GLOBAL {",
                 f'    INPUTNAME "disasm/bank{b}.bin";',
                 f'    OUTPUTNAME "disasm/bank{b}.asm";',
                 f"    STARTADDR ${base:04X};",
                 '    CPU "6502";',
                 "    COMMENTS 3;",
                 "};", ""]
        for s, e, kind in ranges(mark[b]):
            lines += ["RANGE {", f"    START ${base + s:04X};", f"    END ${base + e - 1:04X};",
                      f"    TYPE {kind};", "};"]
        for o in sorted(labels[b]):
            if mark[b][o] == 1:
                lines += ["LABEL {", f'    NAME "L{b}_{base + o:04X}";',
                          f"    ADDR ${base + o:04X};", "};"]
        open(os.path.join(outdir, f"bank{b}.info"), "w").write("\n".join(lines) + "\n")


def report(prg, mark, invalid, conflicts, unresolved, stats, vectors):
    notes = os.path.join(ROOT, "notes")
    os.makedirs(notes, exist_ok=True)
    out = [f"seeds: {stats['seeds']}",
           "vectors: " + ", ".join(f"{k}=${v:04X}" for k, v in vectors.items()),
           "", "bank  code-bytes  covered%"]
    for b in range(8):
        n = sum(1 for x in mark[b] if x)
        out.append(f"{b:>4}  {n:>10}  {100 * n / BANK:6.1f}")
    out += ["", "dispatchers: " + ", ".join(f"b{b} ${cpu_base(b) + o:04X}"
                                            for b, o in stats["dispatchers"]),
            f"inline jump tables: {len(stats['tables'])} "
            f"({sum(n for *_, n in stats['tables'])} entries)"]
    out += ["", f"invalid opcodes reached: {len(invalid)}",
            f"flow stopped at CDL data (possible inline data after a JSR): {len(conflicts)}",
            f"jumps/calls into $8000-$BFFF from fixed bank (bank unknown): {len(unresolved)}"]
    out += ["", f"bank guesses for fixed-bank -> $8000 calls: {len(stats['assumed'])} "
                f"(cdl={sum(1 for a in stats['assumed'] if a[5] == 'cdl')}, "
                f"home={sum(1 for a in stats['assumed'] if a[5] == 'home')})"]
    out += ["", "-- first 40 conflicts (bank, cpu addr) --"]
    out += [f"  b{b} ${cpu_base(b) + o:04X}" for b, o in conflicts[:40]]
    out += ["", "-- first 40 invalid --"]
    out += [f"  b{b} ${cpu_base(b) + o:04X}  op={prg[b][o]:02X}" for b, o in invalid[:40]]
    out += ["", "-- bank guesses (site, kind, target -> bank, basis) --"]
    out += [f"  ${a[1]:04X} {a[2]} ${a[3]:04X} -> bank {a[4]} ({a[5]})" for a in sorted(stats["assumed"], key=lambda a: a[1])]
    out += ["", "-- unresolved bank-switched targets (from, insn, target), unique targets --"]
    seen = sorted({t for *_, t in unresolved})
    out += ["  " + " ".join(f"${t:04X}" for t in seen[:200])]
    text = "\n".join(out) + "\n"
    open(os.path.join(notes, "flow_report.txt"), "w").write(text)
    print(text.split("-- first 40")[0])


def main():
    prg, cdl = load()
    print("CDL:", "loaded" if cdl else "none (static flow only)")
    mark, labels, invalid, conflicts, unresolved, stats, vectors = analyse(prg, cdl)
    write_info(prg, mark, labels, cdl)
    report(prg, mark, invalid, conflicts, unresolved, stats, vectors)


if __name__ == "__main__":
    main()
