"""Summarize only a complete, restored physical qualification."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=Path(sys.argv[1]) if len(sys.argv)>1 else sorted(HERE.glob('qualification_*/report.json'))[-1]
d=json.loads(p.read_text())
assert d['ok'] and d['restored'] and d['recovery']['ok'], 'Campaign incomplete or restoration not verified'
assert d['prior_identity']==d['final_identity'], 'Firmware changed'
summary=[]
for bits in (10,12,14):
 rows=[r for r in d['cases'] if r['adc']['bits']==bits and r['requested_seconds'] in (60,120)]
 assert sorted(r['requested_seconds'] for r in rows)==[60,120,120,120]
 assert all(r['ok'] and r['headroom_ok'] and not r['status']['dropped'] and not r['status']['fatal'] for r in rows)
 assert all(r['seconds']>=r['requested_seconds'] for r in rows)
 margins=[r['metrics']['mean_send_headroom'] for r in rows]
 summary.append({'bits':bits,'actual_rate':rows[0]['actual_rate'],'samples':sum(r['samples'] for r in rows),'margin_range':[min(margins),max(margins)],'queue_peak':max(r['metrics']['maxima']['queue_peak'] for r in rows),'slack_ticks_min':min(r['metrics']['maxima']['slack_ticks'] for r in rows)})
assert len(d['normal_policy_checks'])==12
assert all(r['policy']==d['normal_policy'] for r in d['normal_policy_checks'])
result={'ok':True,'scope':'Isolated relay qualification only; unchanged ADC rates and MCU; not production integration or analog/GUI acceptance','report':str(p),'profiles':summary,'restored':True}
(HERE/'qualified_summary.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# Relay CPU2/performance — aceptación aislada','','Cada perfil pasó60s +3 corridas independientes de120s. No hubo ensayos600s.','','| ADC | Muestras/s CH1 | Muestras validadas | Margen medio por etapa | Cola pico / capacidad |','|---|---:|---:|---:|---:|']
for r in summary:lines.append(f"| {r['bits']} | {r['actual_rate']:.3f} | {r['samples']} | {100*r['margin_range'][0]:.3f}–{100*r['margin_range'][1]:.3f}% | {r['queue_peak']} / 4 |")
lines+=['','Integridad y holgura pasaron: dropped=fatal=0, CRC/secuencia/epoch e','índices/timestamps sin errores, margen>=10%, cola<4 desde el arranque y','slack positivo. Después de cada caso pasó el regreso a40kHz durante3s','y la restauración de governor/afinidad/prioridad originales. Los controles',
'ADC10 duraron3s; ADC12/14 duraron10s en la revisión posterior del protocolo.','','Candidato limitado a relay aislado. No se agregaron tasas ni se modificó','firmware MCU, SPI38, formato o tamaño de nodo. Política CPU2/performance','para los tres máximos y cola TCP parcial acotada existente. Entrada desde','tasa baja; la futura integración debe conservar esa transición segura.','','Firmware/relay estables y ADC/generador originales restaurados. Identidad','MCU antes/después idéntica y recuperación10s sin errores. Los12 controles','de regreso verificaron la política CPU original. El candidato no queda','publicado en la GUI y no acredita precisión analógica ni cargas conjuntas.','',f'Informe: `{p.relative_to(HERE)}`.','Respaldo: `'+d['backup']+'`.','','16bits queda separado: formato CH1 validado localmente en','`../adc16_ch1_format_v17/`; todavía sin perfil físico nuevo.']
(HERE/'RESULTADOS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(result,indent=2))
