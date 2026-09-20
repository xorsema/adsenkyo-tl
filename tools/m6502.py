"""Documented-opcode 6502 decode table.

OPS[opcode] = (mnemonic, mode, length). Undocumented opcodes are absent, so the
flow analyser treats them as "not code" and stops.
"""

LEN = {"imp": 1, "acc": 1, "imm": 2, "zp": 2, "zpx": 2, "zpy": 2, "rel": 2,
       "indx": 2, "indy": 2, "abs": 3, "absx": 3, "absy": 3, "ind": 3}

OPS = {}


def _add(op, mn, mode):
    assert op not in OPS, hex(op)
    OPS[op] = (mn, mode, LEN[mode])


# ora/and/eor/adc/sta/lda/cmp/sbc share the same addressing-mode layout
_ALU_MODES = {"imm": 0x09, "zp": 0x05, "zpx": 0x15, "abs": 0x0D,
              "absx": 0x1D, "absy": 0x19, "indx": 0x01, "indy": 0x11}
for mn, base in (("ora", 0x00), ("and", 0x20), ("eor", 0x40), ("adc", 0x60),
                 ("sta", 0x80), ("lda", 0xA0), ("cmp", 0xC0), ("sbc", 0xE0)):
    for mode, off in _ALU_MODES.items():
        if mn == "sta" and mode == "imm":
            continue
        _add(base + off, mn, mode)

# shifts/rotates and inc/dec
_SHIFT_MODES = {"zp": 0x06, "zpx": 0x16, "abs": 0x0E, "absx": 0x1E}
for mn, base in (("asl", 0x00), ("rol", 0x20), ("lsr", 0x40), ("ror", 0x60),
                 ("dec", 0xC0), ("inc", 0xE0)):
    for mode, off in _SHIFT_MODES.items():
        _add(base + off, mn, mode)
    if mn in ("asl", "rol", "lsr", "ror"):
        _add(base + 0x0A, mn, "acc")

for op, mn, mode in (
    (0xA2, "ldx", "imm"), (0xA6, "ldx", "zp"), (0xB6, "ldx", "zpy"),
    (0xAE, "ldx", "abs"), (0xBE, "ldx", "absy"),
    (0xA0, "ldy", "imm"), (0xA4, "ldy", "zp"), (0xB4, "ldy", "zpx"),
    (0xAC, "ldy", "abs"), (0xBC, "ldy", "absx"),
    (0x86, "stx", "zp"), (0x96, "stx", "zpy"), (0x8E, "stx", "abs"),
    (0x84, "sty", "zp"), (0x94, "sty", "zpx"), (0x8C, "sty", "abs"),
    (0xE0, "cpx", "imm"), (0xE4, "cpx", "zp"), (0xEC, "cpx", "abs"),
    (0xC0, "cpy", "imm"), (0xC4, "cpy", "zp"), (0xCC, "cpy", "abs"),
    (0x24, "bit", "zp"), (0x2C, "bit", "abs"),
    (0x4C, "jmp", "abs"), (0x6C, "jmp", "ind"), (0x20, "jsr", "abs"),
    (0x10, "bpl", "rel"), (0x30, "bmi", "rel"), (0x50, "bvc", "rel"),
    (0x70, "bvs", "rel"), (0x90, "bcc", "rel"), (0xB0, "bcs", "rel"),
    (0xD0, "bne", "rel"), (0xF0, "beq", "rel"),
    (0x00, "brk", "imp"), (0x40, "rti", "imp"), (0x60, "rts", "imp"),
    (0x18, "clc", "imp"), (0xD8, "cld", "imp"), (0x58, "cli", "imp"),
    (0xB8, "clv", "imp"), (0x38, "sec", "imp"), (0xF8, "sed", "imp"),
    (0x78, "sei", "imp"), (0xCA, "dex", "imp"), (0x88, "dey", "imp"),
    (0xE8, "inx", "imp"), (0xC8, "iny", "imp"), (0xEA, "nop", "imp"),
    (0x48, "pha", "imp"), (0x08, "php", "imp"), (0x68, "pla", "imp"),
    (0x28, "plp", "imp"), (0xAA, "tax", "imp"), (0xA8, "tay", "imp"),
    (0xBA, "tsx", "imp"), (0x8A, "txa", "imp"), (0x9A, "txs", "imp"),
    (0x98, "tya", "imp"),
):
    _add(op, mn, mode)

assert len(OPS) == 151, len(OPS)

# instructions after which execution does not fall through
TERMINATORS = {"rts", "rti", "brk", "jmp"}
BRANCHES = {"bpl", "bmi", "bvc", "bvs", "bcc", "bcs", "bne", "beq"}
