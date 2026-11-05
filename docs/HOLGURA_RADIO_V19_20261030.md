# Holgura de RADIO/A0 · 30/10/2026

Se realizaron ocho ensayos físicos a ADC8/1.860.465 S/s con FFT16k, RADIO
y A0 a 40 kHz. Todas las ventanas estuvieron expuestas en las observaciones
periódicas. No se incorporó ningún candidato ni se modificaron tasas públicas.
V17/V18 permanecen intactas.

## Resultados

| Ensayo | Duración solicitada de audio | Margen medio MCU durante PLAY | Cola pico acumulada | Resultado |
|---|---:|---:|---:|---|
| Control, ráfaga 8 / 6 ms | 20 s | 10,20 % | 5 | Funcional; sin holgura |
| Ráfaga 4 / 6 ms | 20 s | 10,43 % | 3 | Pasa sólo el sondeo breve |
| Ráfaga 4 / 6 ms, extendido | 60 s | 10,44 % | 4 | UNDERRUN a unos 55 s; descartado |
| O2 privado + ráfaga 4 / 6 ms | 20 s | 11,13 % | 4 | Funcional; sin holgura |
| Ráfaga 8 / 8 ms | 20 s | 10,30 % | 4 | Funcional; sin holgura |
| Prellenado 4 / 8 ms; PLAY 8 / 6 ms | 20 s | 10,38 % | 4 | Funcional; sin holgura |
| O2 + prellenado 4 / 8 ms; PLAY 8 / 6 ms | 20 s | 11,49 % | 4 | Funcional; sin holgura |
| Interrupción SPI en CPU2; host original | 20 s | 10,36 % | 4 | Funcional; sin holgura |

El criterio conserva margen medio ≥10 %, pico acumulado <4 y slack positivo,
además de integridad, audio, dibujo y restauración. El sondeo breve de ráfaga 4
no se convirtió en aceptación: su extensión falló y no se ejecutó 3×120 s.
Los demás candidatos fallaron ya el sondeo de holgura.

Los porcentajes son mediciones por caso, no una estimación estadística de
mejora causal. Los casos O2 usan la sintonía 710 kHz del harness privado; los
casos con firmware aceptado usan 550 kHz. No se promedian éxitos y fallos.

## Cambios privados y límites

`tools/radio_burst_inline_v19.py` selecciona el descriptor de RADIO40k al crear
la fuente remota. Conserva el ACK-refresh inline de producción, bloques de 480
muestras, créditos y reservas. Las variantes continuas modifican ráfaga o
intervalo; la variante de prellenado recupera 8/6 ms al enviar PLAY.
Ocho milisegundos permiten una reposición nominal de 1,5 veces el consumo,
frente a 2 veces con 6 ms; se midió como variante, sin adoptarla.

O2 corresponde al candidato compilado y revisado previamente: sólo el atributo
de optimización de `prepare_batch_half`. Se instaló de forma temporal con
respaldo y rollback completos; no se cambió el firmware aceptado. Sus builds
se hicieron con la adquisición detenida.

En el fallo largo, el registro `pcm_underrun` conserva audio disponible en el
host y ACK demorados hasta 284,28 ms. La demora máxima de render de audio fue
0,67 ms y la ida/vuelta PCM 16,46 ms. Esto orienta hacia entrega/retorno de
comandos; no identifica por sí solo cuál componente produjo la pausa.

La inspección en reposo encontró SPI atendido en CPU0 mientras el relay rápido
usa CPU2. Se probó sólo la interrupción dedicada `4a94000.spi`, sin modificar
el GPIO READY ni las demás interrupciones. La escritura directa con sudo fue
rechazada antes de aplicar cambios. El ensayo físico posterior utilizó el
mismo patrón de bind acotado de Docker empleado por Preparar Q: imagen ya
instalada, helper efímero, sin red, sin capacidades y sólo el archivo de
afinidad montado para escritura. No aprobó holgura; se restauraron máscara
`0-3` y CPU efectiva `0`, verificadas.

## Costo del observador y siguientes límites

Tres repeticiones offline de 40.000 frames sintéticos midieron 10,98–11,15 µs
de CPU por frame del observador completo. A 5.500 frames/s equivaldría a
6,04–6,13 % de un núcleo del host. No es una medición física de utilización ni
prueba que el observador causara los picos. Los criterios no se rebajaron ni
se retiró instrumentación para declarar un pase.

La siguiente investigación debe separar esperas de READY, `SPI_IOC_MESSAGE`,
TCP y procesamiento del receptor antes de modificar políticas. No hay evidencia
suficiente para subir tasas con RADIO/A0. Los antecedentes de 1,882/1,905 MS/s
y de escalones superiores en otros bits incluyen UNDERRUN o cierre de flujo;
sus pases aislados no justifican reincorporarlos.

## Cierre verificable

- 19 pruebas offline de binding, descriptores, ACK, selección de IRQ y restauración.
- Todos los ensayos restauraron el Q. El último verificó 10,027 s y 313.344
  muestras continuas sin pérdidas/fatales.
- Firmware aceptado `37f049fa…`, relay `27da0bc4…`; sólo Scope V19 y su relay
  activos. Sin candidatos ni helpers activos al terminar.
- La corrección de apertura/recursos de V19 se conserva; no se modificó el
  runtime del monitor durante esta campaña.

[Consolidado](../diagnosticos/resultados_v19/headroom_burst4_20261030/summary.json)
· [Identidad final](../diagnosticos/resultados_v19/headroom_burst4_20261030/final_identity.json).
Cada directorio conserva GUI, métricas, errores y restauración propios.
