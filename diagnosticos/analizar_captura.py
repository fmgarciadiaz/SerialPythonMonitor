#!/usr/bin/env python3
"""
Analiza una captura de muestras del UNO Q / R4.

Formato esperado por línea:
    sample_index  timestamp_us  adc_in  volts_in  adc_out  volts_out

Ejemplo:
    0  1923585855  327  0.07  65  0.01

Uso:
    python diagnosticos/analizar_captura.py capturas/captura.txt

Opcional:
    python diagnosticos/analizar_captura.py capturas/captura.txt --sample-rate 10000
    python diagnosticos/analizar_captura.py capturas/captura.txt --block-size 512 --node-size 2048
    python diagnosticos/analizar_captura.py capturas/captura.txt --adc-outlier-z 8
"""

import argparse
import math
import statistics
from collections import Counter
from pathlib import Path


def read_file(path):
    rows = []
    bad_lines = []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue

            parts = s.replace(",", ".").split()
            if len(parts) < 6:
                bad_lines.append((lineno, line.rstrip(), "menos de 6 columnas"))
                continue

            try:
                idx = int(float(parts[0]))
                ts = int(float(parts[1]))
                ain = float(parts[2])
                vin = float(parts[3])
                aout = float(parts[4])
                vout = float(parts[5])
                rows.append({
                    "line": lineno,
                    "idx": idx,
                    "ts": ts,
                    "ain": ain,
                    "vin": vin,
                    "aout": aout,
                    "vout": vout,
                })
            except ValueError as e:
                bad_lines.append((lineno, line.rstrip(), f"error numérico: {e}"))

    return rows, bad_lines


def median_abs_deviation(values):
    if not values:
        return 0.0
    med = statistics.median(values)
    deviations = [abs(x - med) for x in values]
    return statistics.median(deviations)


def robust_outliers(values, z=8.0):
    """Outliers usando MAD; mucho más robusto que media/desvío para señales con saltos."""
    if len(values) < 10:
        return set()

    med = statistics.median(values)
    mad = median_abs_deviation(values)

    if mad == 0:
        # Si casi todos son idénticos, detectar valores distintos de la mediana.
        return {i for i, x in enumerate(values) if x != med}

    scale = 1.4826 * mad
    return {i for i, x in enumerate(values) if abs(x - med) > z * scale}


def print_section(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main():
    ap = argparse.ArgumentParser(description="Analiza problemas de timestamp, bloques y ADC.")
    ap.add_argument("file", help="archivo de datos")
    ap.add_argument("--sample-rate", type=float, default=10000.0,
                    help="frecuencia esperada en Hz (default: 10000)")
    ap.add_argument("--block-size", type=int, default=512,
                    help="muestras por bloque serial (default: 512)")
    ap.add_argument("--node-size", type=int, default=2048,
                    help="muestras por nodo DMA (default: 2048)")
    ap.add_argument("--timestamp-tolerance", type=float, default=3.0,
                    help="tolerancia absoluta en us para considerar normal un dt (default: 3)")
    ap.add_argument("--adc-outlier-z", type=float, default=8.0,
                    help="umbral robusto MAD para outliers ADC (default: 8)")
    args = ap.parse_args()

    path = Path(args.file)
    rows, bad_lines = read_file(path)

    if not rows:
        print("No se encontraron muestras válidas.")
        if bad_lines:
            print(f"Líneas inválidas: {len(bad_lines)}")
        return 2

    expected_dt = 1_000_000.0 / args.sample_rate

    print_section("RESUMEN")
    print(f"Archivo                 : {path}")
    print(f"Muestras válidas        : {len(rows):,}")
    print(f"Frecuencia esperada     : {args.sample_rate:g} Hz")
    print(f"dt esperado             : {expected_dt:g} us")
    print(f"Tamaño bloque serial    : {args.block_size}")
    print(f"Tamaño nodo DMA         : {args.node_size}")
    print(f"Líneas inválidas        : {len(bad_lines)}")

    # ------------------------------------------------------------
    # Índices
    # ------------------------------------------------------------
    print_section("1. ÍNDICES DE MUESTRA")

    index_gaps = []
    index_duplicates = []
    index_backwards = []

    for i in range(1, len(rows)):
        d = rows[i]["idx"] - rows[i - 1]["idx"]
        if d == 0:
            index_duplicates.append((i, rows[i - 1], rows[i]))
        elif d < 0:
            index_backwards.append((i, rows[i - 1], rows[i]))
        elif d != 1:
            index_gaps.append((i, rows[i - 1], rows[i], d))

    print(f"Saltos de índice        : {len(index_gaps)}")
    print(f"Índices duplicados      : {len(index_duplicates)}")
    print(f"Índices hacia atrás     : {len(index_backwards)}")

    for i, a, b, d in index_gaps[:20]:
        print(f"  GAP pos={i}: {a['idx']} -> {b['idx']}  (delta={d})")

    # ------------------------------------------------------------
    # Timestamp
    # ------------------------------------------------------------
    print_section("2. TIMESTAMP")

    dts = []
    ts_anomalies = []
    ts_forward_jumps = []
    ts_backwards = []
    ts_duplicates = []

    for i in range(1, len(rows)):
        dt = rows[i]["ts"] - rows[i - 1]["ts"]
        dts.append(dt)

        if dt == 0:
            ts_duplicates.append((i, rows[i - 1], rows[i], dt))
        if dt < 0:
            ts_backwards.append((i, rows[i - 1], rows[i], dt))

        if abs(dt - expected_dt) > args.timestamp_tolerance:
            ts_anomalies.append((i, rows[i - 1], rows[i], dt))

            if dt > expected_dt:
                ts_forward_jumps.append((i, rows[i - 1], rows[i], dt))

    print(f"dt mediano              : {statistics.median(dts):.3f} us")
    print(f"dt mínimo               : {min(dts):.3f} us")
    print(f"dt máximo               : {max(dts):.3f} us")
    print(f"dt anómalos             : {len(ts_anomalies)}")
    print(f"saltos hacia adelante   : {len(ts_forward_jumps)}")
    print(f"timestamps duplicados   : {len(ts_duplicates)}")
    print(f"timestamps hacia atrás  : {len(ts_backwards)}")

    if ts_anomalies:
        print("\nPrimeros timestamps anómalos:")
        for i, prev, cur, dt in ts_anomalies[:30]:
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            print(
                f"  pos={i:8d} idx={cur['idx']:8d} "
                f"prev={prev['ts']} curr={cur['ts']} "
                f"next={nxt['ts'] if nxt else '-'} "
                f"dt={dt:+.1f} us "
                f"bloque512={cur['idx'] // args.block_size} "
                f"offset512={cur['idx'] % args.block_size} "
                f"nodo2048={cur['idx'] // args.node_size} "
                f"offset2048={cur['idx'] % args.node_size}"
            )

    # Buscar el patrón "timestamp futuro y luego vuelve al camino normal".
    # Para cada salto grande, comparar el dt siguiente.
    print("\nSaltos grandes con contexto:")
    contextual = 0
    for i, prev, cur, dt in ts_forward_jumps:
        if i + 1 >= len(rows):
            continue
        nextrow = rows[i + 1]
        dt_next = nextrow["ts"] - cur["ts"]

        # Un patrón especialmente interesante:
        # dt actual grande y dt siguiente aproximadamente igual al esperado.
        if abs(dt_next - expected_dt) <= args.timestamp_tolerance:
            print(
                f"  pos={i:8d} idx={cur['idx']:8d}: "
                f"{prev['ts']} -> {cur['ts']} -> {nextrow['ts']} | "
                f"dt={dt:+.1f}, siguiente={dt_next:+.1f} us"
            )
            contextual += 1
            if contextual >= 30:
                break

    # Distribución de dts: ayuda a descubrir patrones de 512/2048.
    rounded = Counter(round(x, 1) for x in dts)
    print("\nValores de dt más frecuentes:")
    for dt, count in rounded.most_common(12):
        print(f"  {dt:10.1f} us : {count:,}")

    # ------------------------------------------------------------
    # Fronteras 512 / 2048
    # ------------------------------------------------------------
    print_section("3. FRONTERAS DE BLOQUES / NODOS")

    for size, name in [(args.block_size, "bloque serial"),
                       (args.node_size, "nodo DMA")]:
        hits = []
        for i, r in enumerate(rows):
            if r["idx"] % size == 0:
                hits.append(i)

        print(f"{name:20s}: {len(hits):,} fronteras detectadas")

        # Cuántas anomalías de timestamp caen cerca de una frontera.
        near = []
        for i, prev, cur, dt in ts_anomalies:
            offset = cur["idx"] % size
            distance = min(offset, size - offset)
            if distance <= 2:
                near.append((i, cur["idx"], offset, dt))

        print(f"  anomalías a ±2 muestras de frontera: {len(near)}")
        for item in near[:20]:
            print(f"    pos={item[0]} idx={item[1]} offset={item[2]} dt={item[3]:+.1f} us")

    # ------------------------------------------------------------
    # ADC
    # ------------------------------------------------------------
    print_section("4. ADC: VALORES SOSPECHOSOS")

    ain = [r["ain"] for r in rows]
    aout = [r["aout"] for r in rows]
    vin = [r["vin"] for r in rows]
    vout = [r["vout"] for r in rows]

    print(f"A0 min/max              : {min(ain):g} / {max(ain):g}")
    print(f"A1 min/max              : {min(aout):g} / {max(aout):g}")

    out_in = robust_outliers(ain, args.adc_outlier_z)
    out_out = robust_outliers(aout, args.adc_outlier_z)

    print(f"Outliers robustos A0    : {len(out_in)}")
    print(f"Outliers robustos A1    : {len(out_out)}")

    # Buscar cambios enormes respecto de la muestra anterior.
    jumps_in = []
    jumps_out = []

    if len(rows) > 1:
        dif_in = [abs(ain[i] - ain[i - 1]) for i in range(1, len(rows))]
        dif_out = [abs(aout[i] - aout[i - 1]) for i in range(1, len(rows))]

        med_di = statistics.median(dif_in)
        med_do = statistics.median(dif_out)

        # Umbral conservador, adaptativo.
        thr_in = max(20.0, med_di * 20.0)
        thr_out = max(20.0, med_do * 20.0)

        for i in range(1, len(rows)):
            if abs(ain[i] - ain[i - 1]) > thr_in:
                jumps_in.append((i, rows[i - 1], rows[i], ain[i] - ain[i - 1]))
            if abs(aout[i] - aout[i - 1]) > thr_out:
                jumps_out.append((i, rows[i - 1], rows[i], aout[i] - aout[i - 1]))

        print(f"Saltos grandes A0       : {len(jumps_in)} (umbral {thr_in:g})")
        print(f"Saltos grandes A1       : {len(jumps_out)} (umbral {thr_out:g})")

    print("\nPrimeros outliers/saltos ADC:")
    shown = 0
    interesting = sorted(
        [(i, "A0", rows[i]) for i in out_in] +
        [(i, "A1", rows[i]) for i in out_out],
        key=lambda x: x[0]
    )
    for i, ch, r in interesting[:30]:
        print(
            f"  {ch} pos={i:8d} idx={r['idx']:8d} "
            f"ts={r['ts']} value={r['ain'] if ch == 'A0' else r['aout']:g} "
            f"block={r['idx'] // args.block_size} "
            f"offset={r['idx'] % args.block_size}"
        )
        shown += 1

    # ------------------------------------------------------------
    # Correlación de errores
    # ------------------------------------------------------------
    print_section("5. CORRELACIÓN DE POSIBLES PROBLEMAS")

    ts_bad_idx = {i for i, *_ in ts_anomalies}
    adc_bad_idx = out_in | out_out
    both = sorted(ts_bad_idx & adc_bad_idx)

    print(f"Timestamp anómalo      : {len(ts_bad_idx)}")
    print(f"ADC outlier            : {len(adc_bad_idx)}")
    print(f"Ambos en misma muestra : {len(both)}")

    if both:
        print("\nMuestras donde timestamp Y ADC parecen malos:")
        for i in both[:30]:
            r = rows[i]
            print(
                f"  pos={i} idx={r['idx']} ts={r['ts']} "
                f"A0={r['ain']:g} A1={r['aout']:g}"
            )

    # ------------------------------------------------------------
    # Líneas inválidas
    # ------------------------------------------------------------
    if bad_lines:
        print_section("6. LÍNEAS INVÁLIDAS")
        for lineno, text, reason in bad_lines[:30]:
            print(f"Línea {lineno}: {reason}: {text}")

    # ------------------------------------------------------------
    # Diagnóstico final
    # ------------------------------------------------------------
    print_section("DIAGNÓSTICO ORIENTATIVO")

    findings = []

    if ts_anomalies:
        findings.append(
            f"Hay {len(ts_anomalies)} anomalías de timestamp. "
            "Conviene mirar su posición respecto de 512 y 2048."
        )

    if ts_forward_jumps:
        findings.append(
            "Se detectaron timestamps que saltan hacia adelante; "
            "esto coincide con el patrón que veníamos buscando."
        )

    if any(
        abs((rows[i]["idx"] % args.block_size)) <= 2 or
        abs((rows[i]["idx"] % args.block_size) - args.block_size) <= 2
        for i, *_ in ts_anomalies
    ):
        findings.append(
            "Algunas anomalías están cerca de una frontera de bloque serial."
        )

    if any(
        abs((rows[i]["idx"] % args.node_size)) <= 2 or
        abs((rows[i]["idx"] % args.node_size) - args.node_size) <= 2
        for i, *_ in ts_anomalies
    ):
        findings.append(
            "Algunas anomalías están cerca de una frontera de nodo DMA."
        )

    if len(bad_lines):
        findings.append(
            f"Hay {len(bad_lines)} líneas que no pudieron interpretarse."
        )

    if not findings:
        findings.append("No apareció una anomalía evidente con estos criterios.")

    for f in findings:
        print("•", f)

    print("\nAnálisis terminado.")


if __name__ == "__main__":
    raise SystemExit(main())
