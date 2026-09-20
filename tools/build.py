"""Regenerate disassembly and rebuild the ROM; verify it matches the original.

  python tools/build.py            # mkinfo -> da65 -> ca65 -> ld65 -> compare
  python tools/build.py --no-dis   # rebuild from existing disasm/*.asm (edited source)

Output: build/rebuilt.nes
"""
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "tools", "cc65", "bin")


def run(*args):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"FAILED: {' '.join(args)}\n{r.stdout}{r.stderr}")


def main():
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    if "--no-dis" not in sys.argv:
        run(sys.executable, "tools/mkinfo.py")
        for b in range(8):
            run(os.path.join(BIN, "da65.exe"), "-i", f"disasm/bank{b}.info")
    # per-bank wrappers put each da65 output into its own segment
    for b in range(8):
        open(os.path.join(ROOT, "build", f"bank{b}.s"), "w").write(
            f'.segment "BANK{b}"\n.include "disasm/bank{b}.asm"\n')
    with open(os.path.join(ROOT, "build", "fixed.s"), "w") as f:
        f.write('.segment "HEADER"\n.incbin "rom/header.bin"\n.segment "CHR"\n')
        for c in range(16):
            f.write(f'.incbin "chr/bank{c:02d}.bin"\n')
    objs = []
    for name in [f"bank{b}" for b in range(8)] + ["fixed"]:
        run(os.path.join(BIN, "ca65.exe"), "-I", ".", f"build/{name}.s", "-o", f"build/{name}.o")
        objs.append(f"build/{name}.o")
    run(os.path.join(BIN, "ld65.exe"), "-C", "src/nes.cfg", "-o", "build/rebuilt.nes", *objs)

    new = open(os.path.join(ROOT, "build", "rebuilt.nes"), "rb").read()
    old = open(os.path.join(ROOT, "rom", "original.nes"), "rb").read()
    if new == old:
        print("OK: rebuilt ROM is byte-identical to original")
        return
    diff = [i for i in range(min(len(new), len(old))) if new[i] != old[i]]
    print(f"MISMATCH: sizes {len(new)} vs {len(old)}, {len(diff)} differing bytes, first at 0x{diff[0]:X}" if diff
          else f"MISMATCH: sizes {len(new)} vs {len(old)}")
    sys.exit(1)


if __name__ == "__main__":
    main()
