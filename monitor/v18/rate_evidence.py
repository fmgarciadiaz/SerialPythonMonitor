"""Display-only evidence scoped to one accepted binary pair and exact geometry."""
import json
import math
from pathlib import Path

_BASE = Path(__file__).resolve().parent


def load_evidence(base=None):
    base = Path(base) if base is not None else _BASE
    try:
        receipt = json.loads((base/'q_support/accepted/acceptance.json').read_text())
        data = json.loads((base/'rate_evidence.json').read_text())
        if not isinstance(receipt, dict) or not isinstance(data, dict):
            return None
        pair = dict(firmware_sha256=receipt['firmware']['sha256'],
                    relay_sha256=receipt['relay']['sha256'])
        if receipt.get('accepted') is not True or data.get('schema') != 1 or data['pair'] != pair:
            return None
        if not isinstance(data.get('profiles'), list):
            return None
        seen=set()
        for row in data['profiles']:
            key=tuple(row[name] for name in ('bits','channels','ticks','node_pairs'))
            if (not all(type(value) is int and value>0 for value in key)
                    or key[0] not in (8,10,12,14,16) or key[1] not in (1,2) or key in seen):
                return None
            seen.add(key)
            for scope,flag in (('adc_only','headroom_measured'),('radio_a0','visible')):
                if scope not in row:continue
                record=row[scope]
                seconds=record['seconds']
                if (type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<=0
                        or type(record[flag]) is not bool):
                    return None
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


def evidence_text(config, data):
    key = (config.bits, config.channels, config.period, config.node_pairs)
    row = next((row for row in (data or {}).get('profiles', [])
                if tuple(row.get(name) for name in ('bits','channels','ticks','node_pairs')) == key), None)
    lines = ['Evidencia para la pareja Q aceptada:']
    if row is None:
        lines.append('Sin medición registrada para esta geometría.')
    else:
        adc = row.get('adc_only')
        if adc:
            duration = f"{adc['seconds']:g} s"
            lines.append(f'ADC sin audio: integridad medida ({duration}).')
            if adc.get('headroom_measured'):
                lines.append(f'Holgura ADC sin audio: medida ({duration}).')
        audio = row.get('radio_a0')
        if audio:
            lines.append(f"RADIO/A0: prueba funcional de {audio['seconds']:g} s.")
            lines.append('Dibujo visible: ' + ('comprobado en esa prueba.' if audio.get('visible') else 'pendiente.'))
        else:
            lines.append('RADIO/A0 y dibujo visible: sin medición registrada.')
    lines.append('Holgura con RADIO/A0: sin medición registrada.')
    if (config._native or {}).get('evidence'):
        lines.append('Historial de validación disponible; sus alcances se conservan por separado.')
    lines.append('Precisión analógica: sin calificación.')
    return '\n'.join(lines)
