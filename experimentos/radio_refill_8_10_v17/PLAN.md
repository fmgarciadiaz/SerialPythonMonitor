# Estabilidad A0 ADC8/10 — 18/10/2026

Medir host actual con corrección continuidadGain y guard endpoint; MCU/relay no cambian. Baseline120s por resolución. La instrumentación deja de copiar3000trazas por evento: snapshot1Hz, máximos por evento. Medición anterior podía añadir trabajoGIL al caminoACK; no es prueba de causa de underrun.

CandidatoHighRateRadioDacSource: mismoqueADC14calificado,ráfaga16,correlaciónfuera lockfuente.60s+3×120 porperfil conretune/volumen/Stop. Predicadoexacto alpromover;sólo despuésde restauracióncompleta. No trasladar aceptación entre8/10 ni afirmarheadroom si cola>=4.

Reporteprobe_20261018_164919: baseline10/1250000 pasó120s (cola4,12,22%); candidato10screenfallópor dropped1/EOF CRCcorrecto yse recuperóQ. No promover ráfaga16 para10. Baseline8/1600000 pasó120s (cola5,16,79%); candidato8screen60yprimeras2×120pasaron,cola5–6,~16%;tercera120encursoalredactar. Hostproducciónsinselecciónnuevaaún.

Siguiente para10: run_guard_only.py conserva8bloques y sólo libera correlaciónfuera lockaudio. Su fuente estáen guard_only.py. Repetir60+3×120; sinbajartasa ni tolerarerrores. Cada campaña tienepropietarioexclusivo,backup,identidad,restauraciónADC/generador/política y10srecuperación. No cambiarfuentesmedidasmientrascorren.
