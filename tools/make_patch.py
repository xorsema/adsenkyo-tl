"""Build release patches (IPS + BPS) from the original ROM to the English ROM, and verify them.

  python tools/make_patch.py [--version 0.1-beta]      # builds via insert.py first, then writes release/

The patches contain only the CHANGED bytes, never the original game data, so they can be shared;
you apply them to your own copy of the Japanese ROM (No-Intro-style dump, SHA-1 below).
"""
import hashlib
import os
import struct
import subprocess
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "rom", "original.nes")
BUILT = os.path.join(ROOT, "build", "english.nes")
REL = os.path.join(ROOT, "release")


# ---------------------------------------------------------------- IPS
def make_ips(a, b):
    assert len(a) == len(b), "IPS writer here needs same-size ROMs"
    out = bytearray(b"PATCH")
    i, n = 0, len(a)
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        j = i
        gap = 0
        while j < n and gap <= 8:                      # merge runs separated by short unchanged gaps
            gap = 0 if a[j] != b[j] else gap + 1
            j += 1
        end = j - gap
        for s in range(i, end, 0xFFFF):
            e = min(end, s + 0xFFFF)
            chunk = b[s:e]
            if s == 0x454F46:                          # would read as the "EOF" marker: start one byte earlier
                raise SystemExit("IPS offset collides with EOF marker")
            if len(chunk) > 3 and chunk.count(chunk[0]) == len(chunk):
                out += s.to_bytes(3, "big") + b"\x00\x00" + len(chunk).to_bytes(2, "big") + bytes([chunk[0]])
            else:
                out += s.to_bytes(3, "big") + len(chunk).to_bytes(2, "big") + bytes(chunk)
        i = end
    out += b"EOF"
    return bytes(out)


def apply_ips(src, patch):
    assert patch[:5] == b"PATCH"
    out = bytearray(src)
    p = 5
    while patch[p:p + 3] != b"EOF":
        off = int.from_bytes(patch[p:p + 3], "big"); p += 3
        size = int.from_bytes(patch[p:p + 2], "big"); p += 2
        if size == 0:
            run = int.from_bytes(patch[p:p + 2], "big"); p += 2
            out[off:off + run] = bytes([patch[p]]) * run; p += 1
        else:
            out[off:off + size] = patch[p:p + size]; p += size
    return bytes(out)


# ---------------------------------------------------------------- BPS
def _varint(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def make_bps(a, b, metadata=b""):
    assert len(a) == len(b)
    out = bytearray(b"BPS1") + _varint(len(a)) + _varint(len(b)) + _varint(len(metadata)) + metadata
    i, n = 0, len(a)
    while i < n:
        if a[i] == b[i]:
            j = i
            while j < n and a[j] == b[j]:
                j += 1
            if j - i >= 4 or j == n:                   # SourceRead
                out += _varint(((j - i - 1) << 2) | 0)
                i = j
                continue
        # TargetRead of a changed run (plus tiny unchanged gaps)
        j, gap = i, 0
        while j < n and gap < 4:
            gap = 0 if a[j] != b[j] else gap + 1
            j += 1
        j -= gap
        j = max(j, i + 1)
        out += _varint(((j - i - 1) << 2) | 1) + bytes(b[i:j])
        i = j
    out += struct.pack("<I", zlib.crc32(a)) + struct.pack("<I", zlib.crc32(b))
    out += struct.pack("<I", zlib.crc32(bytes(out)))
    return bytes(out)


def _read_varint(buf, p):
    data, shift = 0, 1
    while True:
        x = buf[p]; p += 1
        data += (x & 0x7F) * shift
        if x & 0x80:
            return data, p
        shift <<= 7
        data += shift


def apply_bps(src, patch):
    assert patch[:4] == b"BPS1"
    assert struct.unpack("<I", patch[-4:])[0] == zlib.crc32(patch[:-4]), "patch checksum"
    p = 4
    ssz, p = _read_varint(patch, p)
    tsz, p = _read_varint(patch, p)
    msz, p = _read_varint(patch, p)
    p += msz
    assert ssz == len(src) and struct.unpack("<I", patch[-12:-8])[0] == zlib.crc32(src), "wrong source ROM"
    out = bytearray()
    end = len(patch) - 12
    while p < end:
        v, p = _read_varint(patch, p)
        mode, length = v & 3, (v >> 2) + 1
        if mode == 0:
            out += src[len(out):len(out) + length]
        elif mode == 1:
            out += patch[p:p + length]; p += length
        else:
            raise SystemExit("unsupported BPS action")
    assert len(out) == tsz
    assert zlib.crc32(bytes(out)) == struct.unpack("<I", patch[-8:-4])[0]
    return bytes(out)


# ---------------------------------------------------------------- main
def main():
    version = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else "0.1-beta"
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "insert.py")], check=True, cwd=ROOT,
                   env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    a, b = open(ORIG, "rb").read(), open(BUILT, "rb").read()
    os.makedirs(REL, exist_ok=True)
    stem = f"America_Daitouryou_Senkyo_EN_v{version}"
    ips, bps = make_ips(a, b), make_bps(a, b, f"AmDaiSenkyo EN {version}".encode())
    assert apply_ips(a, ips) == b, "IPS does not reproduce the built ROM"
    assert apply_bps(a, bps) == b, "BPS does not reproduce the built ROM"
    open(os.path.join(REL, stem + ".ips"), "wb").write(ips)
    open(os.path.join(REL, stem + ".bps"), "wb").write(bps)
    changed = sum(1 for x, y in zip(a, b) if x != y)
    print(f"IPS {len(ips):,} bytes, BPS {len(bps):,} bytes; {changed:,} of {len(a):,} ROM bytes differ; both verified")
    print("source ROM  SHA-1", hashlib.sha1(a).hexdigest().upper(), " CRC32 %08X" % zlib.crc32(a))
    print("patched ROM SHA-1", hashlib.sha1(b).hexdigest().upper(), " CRC32 %08X" % zlib.crc32(b))
    # keep the README's checksum lines in sync with what was just built
    import re
    rp = os.path.join(REL, "README.txt")
    if os.path.exists(rp):
        t = open(rp, encoding="utf-8").read()
        t = re.sub(r"(PATCHED ROM SHOULD BE\n  SHA-1:  )[0-9A-F]{40}(\n  CRC32:  )[0-9A-F]{8}",
                   lambda m: m.group(1) + hashlib.sha1(b).hexdigest().upper() + m.group(2) + "%08X" % zlib.crc32(b), t)
        t = re.sub(r"Version [^\n]+", f"Version {version.upper().replace('-', ' ')} (work in progress)", t, count=1)
        open(rp, "w", encoding="utf-8").write(t)
        print("README checksums updated")
    return stem, a, b


if __name__ == "__main__":
    main()
