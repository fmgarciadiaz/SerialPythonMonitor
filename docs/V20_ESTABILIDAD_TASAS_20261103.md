# V20: estabilidad a 2 MS/s y candidatos de más bits

**Estado de calificación:** las tasas siguen privadas. Con Generador Radio/EQ y controles RADIO visibles aparecieron cortes en transiciones US; la candidata con instrumentación detallada apagada pasó tres corridas60s; dos tuvieron exposición100% y una76%. El control sin precarga privada también pasó60s dos veces, con visibilidadparcial. Los antecedentes siguientes no verificaban esa carga completa de GUI.

**Antecedente de transporte: 2 MS/s pasó 60 s y tres corridas independientes de 120 s con RADIO/A0**, sin pérdidas de transporte ni interrupciones registradas. El margen durante reproducción quedó entre el 0,60% y el 0,82%, con cola pico hasta 10/16. Es evidencia de estabilidad observada con esa carga; la reserva sigue siendo muy ajustada.

El usuario autorizó explorar estabilidad aun por debajo del 10%. Se conserva ese porcentaje como dato separado, sin usarlo para descartar automáticamente un ensayo que mantiene continuidad. No se cambiaron firmware, relay ni tasas públicas. V17/V18/V19 permanecieron intactas.

[Resumen verificable y hashes de los reportes](../diagnosticos/resultados_v20/stability_campaign_20261103/summary.json).

## RADIO/A0 a 2 MS/s

ADC8/CH1, FFT de 16.384 puntos, RADIO sintonizada a 710 kHz, salida A0 de 40 kHz, sin retune durante el sostén. Todas las ventanas estuvieron expuestas el 100% de las observaciones. La fuente seguía activa y sin error antes de STOP; el contador DAC respalda el tiempo reproducido.

| Sostén real | Muestras DAC antes de STOP | Cola pico | Margen medio durante reproducción | Reporte |
|---|---:|---:|---:|---|
| 60,04 s | 2.399.040 | 7/16 | 0,82% | [Corrida 1](../diagnosticos/resultados_v20/installed_2000_radio60_r2_20261103/report.json) |
| 120,02 s | 4.797.120 | 9/16 | 0,69% | [Corrida 2](../diagnosticos/resultados_v20/installed_2000_radio120_20261103/report.json) |
| 120,00 s | 4.795.200 | 10/16 | 0,60% | [Corrida 3](../diagnosticos/resultados_v20/installed_2000_radio120_r2_20261103/report.json) |
| 120,04 s | 4.796.640 | 10/16 | 0,62% | [Corrida 4](../diagnosticos/resultados_v20/installed_2000_radio120_r3_20261103/report.json) |

El mínimo de reserva de audio observado fue 8.741 muestras. Cada corrida apagó la salida, restauró el snapshot original y lo verificó durante al menos 10 s, sin pérdidas/fatales y con las mismas identidades binarias. No se infiere calidad audible ni ausencia de clics a partir de estos contadores.

El primer intento `installed_2000_radio60_20261103` no arrancó A0 porque el producto mantiene este perfil pendiente de validación conjunta. Se conserva como intento bloqueado y **se excluye de aceptación de audio**. El arnés posterior habilita únicamente ADC8/80 ticks/3.488 muestras/CH1 en su proceso y restaura las funciones al cerrar. El guard del producto no cambió.

## Adquisición sola

Todos los casos siguientes validaron continuidad, CRC, índices y timestamps, con cero pérdidas/fatales. En ADC12, los tres sondeos de 20 s cambiaron de configuración en una sesión; la corrida de 120 s fue independiente. Estas pruebas de ADC10/12 todavía no acreditan GUI/audio ni precisión analógica.

| Bits | Tasa | Duración | Muestras válidas | Cola pico | Margen medio |
|---:|---:|---:|---:|---:|---:|
| 8 | 2.000.000 S/s | 60 s | 119.928.776 | 5/16 | 7,57% |
| 8 | 2.000.000 S/s | 120 s | 239.860.168 | 3/16 | 7,67% |
| 10 | 1.379.310 S/s | 60 s | 82.708.464 | 2/4 | 12,42% |
| 12 | 1.111.111 S/s | 20 s | 22.203.648 | 2/4 | 12,10% |
| 12 | 1.126.760 S/s | 20 s | 22.515.264 | 2/4 | 10,59% |
| 12 | 1.142.857 S/s | 20 s | 22.836.096 | 2/4 | 8,98% |
| 12 | 1.142.857 S/s | 120 s | 137.056.896 | 2/4 | 8,95% |

Los caminos de cada reporte están en el resumen verificable. ADC10 ticks 116 y ADC12 ticks 144/142/140 ya existen en las fuentes del MCU y relay vinculadas al binario instalado. El diagnóstico los registra sólo en su proceso y comprueba su presencia en ambas fuentes; no modifica el catálogo público. ADC14 por encima de 1 MS/s necesita un candidato de firmware nuevo: todavía no se ensayó.

## Qué aporta la cola

La cola absorbe demoras puntuales; no corrige un déficit sostenido de servicio. Comparar tiempo de almacenamiento, no sólo cantidad de nodos. La retención total nominal no descuenta nodos ocupados y no garantiza una pausa tolerable de esa duración.

| Perfil CH1 | Nodos | Muestras por nodo | Retención total nominal |
|---|---:|---:|---:|
| ADC8 / 2 MS/s | 16 | 3.488 | 27,90 ms |
| ADC10 / 1.379.310 S/s | 4 | 5.568 | 16,15 ms |
| ADC12 / 1.142.857 S/s | 4 | 7.488 | 26,21 ms |
| ADC14 / máximo actual 1 MS/s | 4 | 5.952 | 23,81 ms |

En adquisición sola a 2 MS/s, los registros de progreso volvieron a observar cola 1 tras los picos. El muestreo cada 5 s no describe cada transitorio; el pico acumulado del MCU conserva el máximo. Las corridas combinadas sostuvieron reproducción aun con picos 9–10/16, pero el margen inferior al 1% justifica mantener el perfil como candidato mientras se evalúan otras cargas.

## Verificación y estado final

- Suite V20: **167 tests PASS** en 44,59 s. [Log](../diagnosticos/resultados_v20/stability_suite_20261103/unittest.log). El intento restringido previo falló por permisos POSIX/nice; la repetición con esos permisos pasó completa.
- Los tests nuevos verifican registro y retiro de perfiles privados, rechazo de candidatos ausentes y excepción exacta del guard de audio sólo en el arnés.
- Q queda con la misma pareja V20, adquisición original ADC14/31.250 dual, generador apagado y sin cliente de pruebas. No se restauró V19 ni se alteró la biblioteca de AppLab.
- Antes de una incorporación general faltan otras cargas de análisis, Scan/US y transiciones de audio a 2 MS/s; para ADC10/12 también falta reproducción combinada. La estabilidad observada aquí no promete el mismo resultado para esas cargas.

## Continuación: Scan US y reanudación

La reproducción estable anterior no cubría cambios de tasa. Se encontró que US a2M elegía un auxiliar antiguo ADC8/143/8192 (1,119M), de una familia con antecedentes de pérdida de nodos. El candidato2M ahora hereda los auxiliares validados de1,86M:1,6M y1,4035M. Los candidatos ADC10/12 heredan también sus familias actuales. Se compararon180configuraciones públicas y conservan los mismos auxiliares; el catálogo no cambió.

`installed_2000_us_a0_transitions_20261103` completó Stop/reinicio manual, Scan US de tres perfiles, restauración de2M y reanudaciónA0. **Falló unos3,3s después de reanudar por UNDERRUN estado4/motivo2**. RF permaneció íntegro (pico11/16) y se restauró el snapshot V20 durante10s; identidad igual. Había19.558muestras de audio preparadas; ACKsend→read hasta186ms, read→decode18ms y14CHUNKsinconfirmar al corte. Es evidencia de fallo de entrega/confirmación, no demuestra cuál etapa causó la demora.

Astra propuso un único experimento privado: precargar A0 a1x (intervalo12ms) antes dePLAY, manteniendo30bloques, créditos/burst/tokens y cadencia habitual6ms durante reproducción. Sol prepara el envoltorio y tests; root conserva la propiedad exclusiva del Q. No se amplían buffers/límites ni prioridades.

En local,171testsPASS. La primera pasada tuvo un exit139 nativoPySide/QtQTimer observado una vez, sin reproducción en las siguientes; no se afirma que esté arreglado. La segunda detectó dosfixtures que omitían archivos nuevos y se corrigieron. Logs y diagnóstico reducido en `diagnosticos/resultados_v20/candidate_transitions_20261103/`.

### Carga visible y recuperación del control

El arnés ahora fuerza y comprueba Generador Radio/EQ y la solapa RADIO visibles. Los ensayos sostenidos anteriores activaban A0 pero no verificaban ese panel: mantienen su evidencia de transporte/audio, sin acreditar esa carga completa de GUI. El primer control con ambos paneles visibles falló al pausarA0 paraUS, con UNDERRUN y luego cierre del flujo; la restauración de esa sesión falló. La corrida no se oculta ni se convierte enPASS. Una recuperación posterior independiente (`recover_fullui_control_20261103/report.json`) restauró exactamente el snapshot durante10,04s sin pérdidas/fatal y con los mismos binarios, sin reset ni despliegue.

La primera candidata de priming12ms pasó20,08s tras reanudar, cola8/16 yACKrawmáx26ms; el control corto repetido también pasó. Todavía no demuestra corrección causal. Ahora se ensaya con paneles explícitos. Los candidatos ADC10 y12 pasaron20+60s de RADIO/A0 antes de añadir esa comprobación visual; requieren repetirla. Suiteactual177PASS; el cambio de cadencia de priming sigue exclusivamente privado.
