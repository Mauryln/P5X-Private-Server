"""Arnés de prueba: servidor + cliente + aserciones sobre Player.log.

Automatiza el ciclo que más tiempo consume: levantar el servidor, iniciar el cliente,
esperar marcadores en el log y reportar PASS/FAIL sin intervención manual.

Uso:
    python run_test.py --server ..\\server\\poc_login_server.py ^
        --client "D:\\P5X\\client\\pc\\P5X.exe" ^
        --log "%USERPROFILE%\\AppData\\LocalLow\\SEGA\\p5x_en\\Player.log" ^
        --expect "SCSceneEnterEnd" --expect "System Language" ^
        --reject "Release Asset Error" --timeout 180

Cada --expect debe aparecer; cada --reject NO debe aparecer. Las líneas se evalúan
solo desde el arranque del cliente, y el log nuevo se archiva en runs/<timestamp>/.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime


def wait_for_port(port: int, timeout: float) -> bool:
    import socket

    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.2)
    return False


def read_new(path: str, offset: int) -> tuple[str, int]:
    if not os.path.isfile(path):
        return "", offset
    size = os.path.getsize(path)
    if size < offset:
        offset = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        fh.seek(offset)
        chunk = fh.read()
        return chunk, fh.tell()


def main() -> None:
    ap = argparse.ArgumentParser(description="Arnés de prueba cliente+servidor")
    ap.add_argument("--server", required=True, help="ruta a poc_login_server.py")
    ap.add_argument("--port", type=int, default=10403)
    ap.add_argument("--client", required=True, help="ruta al P5X.exe de tu copia")
    ap.add_argument("--log", required=True, help="ruta a Player.log")
    ap.add_argument("--expect", action="append", default=[], help="regex que debe aparecer")
    ap.add_argument("--reject", action="append", default=[], help="regex que no debe aparecer")
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--settle", type=float, default=8.0,
                    help="segundos extra tras cumplir todas las expectativas")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runs", stamp)
    run_dir = os.path.abspath(run_dir)
    os.makedirs(run_dir, exist_ok=True)

    start_offset = os.path.getsize(args.log) if os.path.isfile(args.log) else 0
    server = subprocess.Popen([sys.executable, args.server, "--port", str(args.port)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    client = None
    try:
        if not wait_for_port(args.port, 15):
            sys.exit("el servidor no abrió el puerto")
        print(f"servidor arriba en 127.0.0.1:{args.port}")

        client = subprocess.Popen([args.client], cwd=os.path.dirname(args.client))
        print(f"cliente lanzado (pid {client.pid})")

        deadline = time.time() + args.timeout
        seen: list[str] = []
        all_text = ""
        satisfied_at = None
        while time.time() < deadline:
            chunk, start_offset = read_new(args.log, start_offset)
            all_text += chunk
            for pattern in args.expect:
                if pattern not in seen and re.search(pattern, all_text):
                    seen.append(pattern)
                    print(f"  [ok] {pattern}")
            if len(seen) == len(args.expect) and satisfied_at is None:
                satisfied_at = time.time()
            if satisfied_at and time.time() - satisfied_at > args.settle:
                break
            if client.poll() is not None and len(seen) < len(args.expect):
                break
            time.sleep(0.5)

        with open(os.path.join(run_dir, "player.log"), "w", encoding="utf-8") as fh:
            fh.write(all_text)

        failures: list[str] = []
        for pattern in args.expect:
            if pattern not in seen:
                failures.append(f"no apareció: {pattern}")
        for pattern in args.reject:
            match = re.search(pattern, all_text)
            if match:
                failures.append(f"apareció (rechazado): {pattern} -> {match.group(0)}")

        print(f"\nlog archivado en {run_dir}")
        if failures:
            print("RESULTADO: FAIL")
            for item in failures:
                print(f"  - {item}")
            sys.exit(1)
        print("RESULTADO: PASS")
    finally:
        for proc in (client, server):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    main()
