#!/usr/bin/env python3
"""Recibe el volcado del sketch diagnostico_dma a traves del R4.

Conserva el stream original en .bin y el informe del firmware en .txt.
No interpreta CSV ni cambia sus separadores. Para analizar capturas CSV
(comas en V6 o tabs en versiones anteriores), usar analizar_captura.py.
"""
import argparse
from datetime import datetime
from pathlib import Path
import time

import serial
from serial.tools import list_ports

BEGIN = b"UNOQ_DIAG_BEGIN_V1"
END = b"UNOQ_DIAG_END_V1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", nargs="?", help="Puerto USB del R4")
    parser.add_argument("--baud", type=int, default=2000000)
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    if not args.port:
        for port in list_ports.comports():
            print(f"{port.device}: {port.description}")
        print("Ejemplo: python3 diagnosticos/recibir_diagnostico.py /dev/cu.usbmodemXXXX")
        return 0

    name = "diagnostico_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    capture_dir = Path(__file__).resolve().parent.parent / "capturas" / "diagnosticos"
    raw_path = capture_dir / (name + ".bin")
    report_path = capture_dir / (name + ".txt")
    pending = bytearray()
    reporting = False
    try:
        capture_dir.mkdir(parents=True, exist_ok=True)
        with serial.Serial(args.port, args.baud, timeout=0.2) as port, raw_path.open("xb") as raw:
            print("Receptor listo. Ahora REINICIA EL Q (no el R4).", flush=True)
            print(f"Guardando stream en {raw_path}", flush=True)
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                chunk = port.read(min(max(port.in_waiting, 1), 65536))
                if not chunk:
                    continue
                raw.write(chunk)
                pending.extend(chunk)
                if not reporting:
                    start = pending.find(BEGIN)
                    if start < 0:
                        del pending[:max(0, len(pending) - len(BEGIN) + 1)]
                        continue
                    del pending[:start]
                    reporting = True
                    print("Adquisicion detenida; recibiendo diagnostico...", flush=True)
                end = pending.find(END)
                if end >= 0:
                    report = bytes(pending[:end + len(END)]).decode("ascii", errors="replace")
                    report_path.write_text(report + "\n", encoding="utf-8")
                    print("\n".join(report.splitlines()[:10]))
                    print(f"\nListo: {report_path}\nStream: {raw_path}")
                    return 0
                if len(pending) > 2_000_000:
                    raise RuntimeError("Volcado demasiado grande o marcador final perdido")
        if reporting:
            report_path.write_bytes(pending)
            print(f"Volcado incompleto conservado en {report_path}")
        print(f"Tiempo agotado. Stream conservado en {raw_path}. Reinicia el Q despues de abrir el receptor.")
        return 1
    except (serial.SerialException, OSError, RuntimeError) as exc:
        print(f"Error: {exc}")
        return 1
    except KeyboardInterrupt:
        print(f"\nInterrumpido. Stream recibido conservado en {raw_path}")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
