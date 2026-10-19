# ADC10/12 y RADIO — 17/10/2026

Perfiles CH1 incorporados al código: ADC10 a 1.250.000 muestras/s (128 ticks, N5568), ADC12 a 1.066.666,667 muestras/s (150 ticks, N7488). Mejoras de aproximadamente 7,03% y 8,67% respecto de los máximos anteriores. ADC14/16 siguen pospuestos.

Calificación ADC aislado: pantalla de 60 s y tres repeticiones independientes de 120 s por resolución, sin pérdidas/fatales, cola máxima 3 y slack positivo. Margen medio de envío alrededor de 19,4% en ADC10 y 17,7% en ADC12. Fuentes y binario idénticos entre etapas; restauración y recuperación verificadas.

Evidencias: `experimentos/otros_bits_crc_v17/qualification_20261017_131439/report.json` y `qualification_20261017_132133/report.json`. Firmware candidato: `42cff22046d3dbebc4678bd18c62b36e2ee8e4dc6d2d2eb39d69adf2cae30e29`.

Primera integración conjunta: `deployment_20261017_134020/report.json`. RADIO directo pasó 120 s a ADC8/1,6M (margen16,71%, cola6); FILTER pasó60 s (17,14%, cola5). ADC10/1,25M sufrió underrun DAC a unos27 s, con fuentePC disponible y ADC íntegro, cola2. Se revirtió automáticamente al firmware e8d8411b y ajustes originales; recuperación10 s sin pérdidas. No constituye aceptación conjunta de las nuevas tasas.

Diagnóstico con Astra: ACK agrupados de hasta241 ms exceden los192 ms cubiertos por16 bloques en vuelo; ráfaga4 recupera sólo48 ms ante pausas host96 ms. Se evalúa ventana30 exclusivaRADIO, limitada por capacidad y huecos confirmados, con ráfaga8. Mantener40 kHz y registros de Stop; repetir prueba física antes de cerrar instalación.

## Instalación final aceptada

`experimentos/otros_bits_crc_v17/deployment_20261017_134849/report.json`: ok, installed y settings_restored verdaderos. Ventana30 exclusivaRADIO limitada por queue_slots anunciados, ráfaga8 e intervalo6ms; fuentes restantes conservan límite16. 22 pruebas locales de créditos, FILTER y contratos correctas, además de25 pruebas de integración de perfiles.

| Adquisición CH1 | IN A0 | Duración | Margen conjunto | Cola pico |
|---|---|---|---|---|
| ADC10 / 1.250.000 | FILTER | 60s | 12,19% | 4 |
| ADC12 / 1.066.666,667 | FILTER | 60s | 10,76% | 3 |
| ADC8 / 1.600.000 | RADIO | 120s | 16,98% | 5 |
| ADC8 / 1.600.000 | FILTER | 60s | 16,95% | 4 |

Todas sin underrun, pérdidas ni fatales, con volumen, resintonía y Stop. PCM→RadioTest→PCM pasó. Ajustes originales restaurados y continuidad final10s verificada. La holgura ADC aislado está aceptada; RADIO conjunto en8/10 no cumple cola<4. No equivale a aceptación por escucha ni FPS visibles. Firmware instalado42cff220; no confundir con el e8 restaurado en el intento fallido anterior.
