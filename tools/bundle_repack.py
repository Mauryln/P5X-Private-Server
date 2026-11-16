"""Reempaqueta un AssetBundle de Unity conservando el formato original.

Contexto (ver docs/03-client/UI_FIX_REPORT.md): el cliente espera nombres canónicos
con mayúsculas (`UI-..._EN.prefab`) mientras los bundles traen las claves de
`m_Container` en minúsculas. El lookup de Unity es case-sensitive y devuelve null.

`packer='original'` preserva los flags del header (0x243: blocksInfo al final,
directory info, LZ4HC). Usar `packer='lz4'` genera flags 0xC2 y Unity rechaza el
bundle con "not built with the right version or build target".

Uso:
    python bundle_repack.py --bundle in.bundle --out out.bundle \\
        --rename ui-x_en.prefab=UI-x_EN.prefab [--rename ...] [--packer original]

Requiere UnityPy (`pip install UnityPy`).
"""
from __future__ import annotations

import argparse
import hashlib
import struct
import sys

import UnityPy


def read_header(data: bytes, offset: int) -> dict:
    """Cabecera UnityFS: signature, versión, versión de Unity, tamaño, blocks, flags."""
    pos = offset + 8
    version = struct.unpack(">I", data[pos:pos + 4])[0]
    pos += 4

    def cstr(p: int) -> tuple[bytes, int]:
        end = data.index(b"\x00", p)
        return data[p:end], end + 1

    player, pos = cstr(pos)
    engine, pos = cstr(pos)
    size = struct.unpack(">q", data[pos:pos + 8])[0]
    pos += 8
    comp_blocks, uncomp_blocks, flags = struct.unpack(">III", data[pos:pos + 12])
    return {
        "version": version,
        "player": player.decode("ascii", "ignore"),
        "engine": engine.decode("ascii", "ignore"),
        "size": size,
        "compressed_blocks_info": comp_blocks,
        "uncompressed_blocks_info": uncomp_blocks,
        "flags": flags,
    }


def container_names(fs: bytes) -> list[str]:
    env = UnityPy.load(fs)
    names: list[str] = []
    for obj in env.objects:
        if obj.type.name == "AssetBundle":
            names = [k for k, _ in obj.read().m_Container]
    return names


def main() -> None:
    ap = argparse.ArgumentParser(description="Reempaqueta un AssetBundle preservando flags")
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rename", action="append", default=[], metavar="OLD=NEW")
    ap.add_argument("--packer", default="original",
                    choices=["original", "lz4", "lz4hc", "none"])
    ap.add_argument("--allow-flag-change", action="store_true",
                    help="permite que los flags difieran del original (no recomendado)")
    args = ap.parse_args()

    with open(args.bundle, "rb") as fh:
        data = fh.read()
    offset = data.find(b"UnityFS", 1)
    if offset < 0:
        sys.exit("no se encontró la cabecera UnityFS (¿bundle ofuscado distinto?)")
    prefix, fs = data[:offset], data[offset:]

    original = read_header(data, offset)
    print(f"entrada : {args.bundle}")
    print(f"prefijo Zeus: {offset} bytes | flags: {original['flags']:#x} | "
          f"sha256: {hashlib.sha256(data).hexdigest()}")

    renames: dict[str, str] = {}
    for item in args.rename:
        if "=" not in item:
            sys.exit(f"--rename inválido: {item!r} (formato OLD=NEW)")
        old, new = item.split("=", 1)
        if len(old) != len(new):
            print(f"[aviso] {old!r} -> {new!r}: distinto largo de cadena", file=sys.stderr)
        renames[old] = new

    env = UnityPy.load(fs)
    applied = 0
    for obj in env.objects:
        if obj.type.name != "AssetBundle":
            continue
        ab = obj.read()
        container = []
        for key, value in ab.m_Container:
            new_key = renames.get(key, key)
            if new_key != key:
                applied += 1
                print(f"  renombrada: {key} -> {new_key}")
            container.append((new_key, value))
        container.sort(key=lambda kv: kv[0])
        ab.m_Container = container
        ab.save()

    if applied == 0:
        sys.exit("no se aplicó ningún renombrado: verificá los nombres con --rename")

    saved = env.file.save(packer=args.packer)
    out_data = prefix + saved

    repacked = read_header(out_data, offset)
    if repacked["flags"] != original["flags"] and not args.allow_flag_change:
        sys.exit(f"flags cambiaron ({original['flags']:#x} -> {repacked['flags']:#x}); "
                 f"Unity rechazaría el bundle. Usá --packer original.")

    remaining = set(renames.values()) - set(container_names(saved))
    if remaining:
        sys.exit(f"claves ausentes tras reempaquetar: {sorted(remaining)}")

    with open(args.out, "wb") as fh:
        fh.write(out_data)
    print(f"salida  : {args.out}")
    print(f"flags   : {repacked['flags']:#x} (idénticos al original: "
          f"{repacked['flags'] == original['flags']})")
    print(f"tamaño  : {len(out_data)} bytes (original {len(data)})")
    print(f"sha256  : {hashlib.sha256(out_data).hexdigest()}")
    print("Recordá actualizar tamaño/checksum en SubpackageBundleInfo.txt y "
          "RedundantFileCheckSumInfoFB si el cliente verifica integridad.")


if __name__ == "__main__":
    main()
