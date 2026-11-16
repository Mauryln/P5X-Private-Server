"""Verificación y restauración de archivos del cliente por SHA-256.

Sirve para dos cosas:
  1. demostrar que una copia de trabajo está intacta (o qué difiere), y
  2. revertir parches locales desde los `.bak` generados antes de experimentar.

Uso:
    # crear manifiesto de referencia
    python verify_assets.py --root D:\\P5X --manifest manifest.json --create \\
        --path client/OuterPackage/Bundles/Windows/005/ui_mainui498d6b82.bundle

    # comparar
    python verify_assets.py --root D:\\P5X --manifest manifest.json

    # restaurar los que difieran desde <archivo>.bak
    python verify_assets.py --root D:\\P5X --manifest manifest.json --restore

El manifiesto no contiene datos del juego: solo rutas relativas y hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description="Verifica/restaura archivos del cliente")
    ap.add_argument("--root", required=True, help="raíz de la copia del juego")
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--create", action="store_true", help="crear manifiesto con --path")
    ap.add_argument("--path", action="append", default=[], help="ruta relativa (repetible)")
    ap.add_argument("--restore", action="store_true", help="restaurar desde <archivo>.bak")
    args = ap.parse_args()

    if args.create:
        if not args.path:
            sys.exit("--create requiere al menos un --path")
        data = {}
        for rel in args.path:
            full = os.path.join(args.root, rel)
            if not os.path.isfile(full):
                sys.exit(f"no existe: {full}")
            key = rel.replace("\\", "/")
            data[key] = sha256(full)
            print(f"ok  {key}  {data[key]}")
        with open(args.manifest, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        print(f"manifiesto escrito: {args.manifest} ({len(data)} archivos)")
        return

    with open(args.manifest, "r", encoding="utf-8") as fh:
        expected = json.load(fh)

    clean = patched = missing = 0
    for rel, want in sorted(expected.items()):
        full = os.path.join(args.root, rel.replace("/", os.sep))
        if not os.path.isfile(full):
            print(f"FALTA     {rel}")
            missing += 1
            continue
        have = sha256(full)
        if have == want:
            clean += 1
            continue
        patched += 1
        print(f"DIFIERE   {rel}\n          esperado {want}\n          actual   {have}")
        if args.restore:
            backup = full + ".bak"
            if not os.path.isfile(backup):
                print(f"          sin backup: {backup}")
                continue
            shutil.copy2(backup, full)
            restored = sha256(full)
            status = "restaurado" if restored == want else "ERROR tras restaurar"
            print(f"          {status}: {restored}")

    print(f"\nresumen: intactos={clean} distintos={patched} faltantes={missing}")
    if patched or missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
