"""Catálogo de assets de Zeus (FlatBuffers assetMapName.txt).

Lee el catálogo que mapea hash(BKDR-131, 31 bits) de nombre de asset -> bundle y
permite comprobar si un nombre está indexado y a qué bundle apunta.

Uso:
    python parse_asset_map.py --map <ruta assetMapName.txt> --lookup UI-foo_EN.prefab
    python parse_asset_map.py --map ... --lookup A --lookup B --dump-json out.json

El catálogo es material del juego: no se versiona, se lee de una copia local.
"""
from __future__ import annotations

import argparse
import json
import struct


def zeus_crc(text: str) -> int:
    """BKDR-131 truncado a 31 bits, sobre code points (equivale a bytes en ASCII)."""
    h = 0
    for ch in text:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h & 0x7FFFFFFF


def read_catalog(path: str) -> dict[int, str]:
    with open(path, "rb") as fh:
        data = fh.read()

    root = struct.unpack("<I", data[:4])[0]
    vtable = root - struct.unpack("<i", data[root:root + 4])[0]
    field0 = struct.unpack("<H", data[vtable + 4:vtable + 6])[0]
    field_ptr = root + field0
    vec_rel = struct.unpack("<I", data[field_ptr:field_ptr + 4])[0]
    vec = field_ptr + vec_rel
    count = struct.unpack("<I", data[vec:vec + 4])[0]

    catalog: dict[int, str] = {}
    for i in range(count):
        elem = vec + 4 + i * 4
        table = elem + struct.unpack("<I", data[elem:elem + 4])[0]
        name_hash = struct.unpack("<I", data[table + 4:table + 8])[0]
        str_rel = struct.unpack("<I", data[table + 8:table + 12])[0]
        str_pos = table + 8 + str_rel
        length = struct.unpack("<I", data[str_pos:str_pos + 4])[0]
        catalog[name_hash] = data[str_pos + 4:str_pos + 4 + length].decode("utf-8", "ignore")
    return catalog


def main() -> None:
    ap = argparse.ArgumentParser(description="Consulta el catálogo de assets de Zeus")
    ap.add_argument("--map", required=True, help="ruta a 105/assetMapName.txt")
    ap.add_argument("--lookup", action="append", default=[], help="nombre de asset a consultar")
    ap.add_argument("--dump-json", help="volcar el catálogo completo a JSON")
    args = ap.parse_args()

    catalog = read_catalog(args.map)
    print(f"entradas indexadas: {len(catalog)}")

    for name in args.lookup:
        digest = zeus_crc(name)
        bundle = catalog.get(digest)
        if bundle is None:
            print(f"NO INDEXADA  {name}  (hash {digest} / {digest:#010x})")
        else:
            print(f"INDEXADA     {name}  (hash {digest} / {digest:#010x}) -> {bundle}")

    if args.dump_json:
        with open(args.dump_json, "w", encoding="utf-8") as fh:
            json.dump({str(k): v for k, v in catalog.items()}, fh, indent=1)
        print(f"catálogo volcado en {args.dump_json} ({len(catalog)} entradas)")


if __name__ == "__main__":
    main()
