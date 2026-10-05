# Diagnóstico de pérdida de nodos a 125 kHz · 4 de octubre de 2026

## Resultado

Se confirmó un atraso sostenido en el consumidor MCU↔MPU: el ciclo del relay
supera el presupuesto de 125 kHz incluso sin enviar datos al PC. No se modificó
el firmware ni el relay normal. La medición usa una copia aislada del relay,
con estadísticas en RAM y salida únicamente al detenerse o fallar.

[Evidencia con PC](resultados/20261004_191638_423914/latencias_relay.json),
[sin PC](resultados/20261004_191638_423914/sin_pc.json),
[captura y estados](resultados/20261004_191638_423914/informe.json).

## Localización del fallo

`acquisition::producer()` incrementa `dropped_nodes` cuando no consigue un
espacio en `empty_slots`. Hay cuatro espacios; el nodo prestado al consumidor
ocupa uno hasta terminar su envío. El mismo productor sigue verificando
continuidad de timestamps, rango y propiedad de DMA aun si no consigue espacio.
La trama rechazada tiene CRC correcto, dropped=1 y fatal=0: el indicador
observado corresponde a cola llena, sin un fallo fatal reportado por el productor.
Esto no demuestra precisión analógica ni garantiza ausencia de otros fallos.

Cada nodo tiene 2048 pares y se fragmenta en 39 tramas de 512 bytes (38 de
53 pares y una de 34). A 125 kHz llega un nodo cada 16,384 ms; el presupuesto
medio de envío es 420,103 µs por trama. A 100 kHz es 525,128 µs.

| Ensayo | READY medio | SPI ioctl medio | Procesamiento Linux medio | Ciclo medio | Resultado |
|---|---:|---:|---:|---:|---|
| 100 kHz con PC | 155,914 µs | 239,841 µs | 107,609 µs | 503,363 µs | 10 s, 997077 pares recibidos, sin huecos |
| 125 kHz con PC | 136,252 µs | 236,299 µs | 100,619 µs | 473,169 µs | dropped=1 |
| 125 kHz sin PC | 207,760 µs | 229,961 µs | 26,784 µs | 464,505 µs | dropped=1 |

Sin PC se configuró 125 kHz y se cerró la conexión; el relay siguió drenando
SPI. Falló antes de terminar los 10 segundos previstos. El ciclo máximo del
perfil 125 kHz fue 1676,211 µs con PC y 1594,804 µs sin PC; estos ensayos no
registraron una pausa de decenas de milisegundos en ese perfil.

Como estimación a partir del promedio (no una tasa independiente medida),
473,169 µs por trama permiten aproximadamente 111 kpares/s de envío útil.
464,505 µs permiten aproximadamente 113 kpares/s. Ambos quedan debajo de 125.
El atraso acumulado explica que una cola finita se llene aunque el tramo
recibido conserve timestamps continuos.

## Interpretación y límites

- READY incluye preparación/handoff del MCU, planificación de Linux y espera
  de disponibilidad; no es una medición exclusiva del tiempo de CPU del MCU.
- SPI mide la llamada ioctl completa. A 32 MHz, los 512 bytes requieren
  idealmente 128 µs de reloj; el tiempo observado incluye driver y planificación.
- Procesamiento incluye validación, recv/accept y envío no bloqueante al PC.
  El primer/final intercambio y cambios de configuración pueden influir.
- El ensayo sin PC reduce procesamiento pero aumenta READY: las etapas no son
  independientes y sus diferencias no permiten atribuir causalidad a una sola.
- Se agregan llamadas de reloj y acumulación de estadísticas. No se da por
  equivalente al rendimiento exacto del relay original; el fallo ya estaba
  reproducido previamente con el relay original.
- Los histogramas usan límites superiores 100/250/420/1000/5000/16000 µs y
  un último intervalo mayor que 16000. Se separan por período y época ADC.
- Antes de este ensayo se encontró el relay normal detenido con CRC válido,
  dropped=1, fatal=0 a 100 kHz, tras más de 37 millones de pares en el log.
  Ese evento previo no tiene estas medidas de latencia y necesita otra captura
  para distinguir una pausa ocasional de atraso sostenido.

## Próxima prueba propuesta

Instrumentar en firmware diagnóstico separado los tiempos completos de
preparación, armado DMA, espera al maestro y entrega de cada fragmento,
además de ocupación máxima de cola y duración completa por nodo. Guardarlos
en RAM y leerlos después de detener la captura. Comparar sin generador y con
él activo. Esto permitirá separar el costo MCU del driver/planificador Linux.

Aumentar la cola sólo posterga un desborde por atraso sostenido; aumentar
el reloj SPI sólo reduce parte del ciclo. Se mantienen 125/200/250 kHz fuera
del monitor y las validaciones existentes de 100 kHz conservan sus límites.

## Código y restauración

[Generador de la copia diagnóstica](preparar_relay_diagnostico.py) y
[relay generado](relay/unoq_timing_stream.c). Compilación real en Linux ARM64
con `cc -O2 -std=c11 -Wall -Wextra -Werror`, aprobada.

El relay diagnóstico se retiró al terminar; se reinició el relay V9 Fast normal.
[Comprobación del perfil restaurado](resultados/20261004_191638_423914/restauracion.json).

## Medición MCU posterior

[Dos instantáneas válidas](resultados/mcu_20261004/README.md) con contenedor
exclusivo: envío de nodo 18,365 ms con cuadrada de 2,5 Hz y 18,171 ms con
DAC apagado, frente a 16,384 ms disponibles. Cola 4/4 y dropped=1/fatal=0.
Armado DMA ~20 µs, limpieza/retorno ~13–15 µs; preparación/verificación
~55/~74–75 µs, READY→IRQ ~241–245 µs. Copia ADC ~432–434 µs por nodo.
La cuadrada probada no explica el déficit. La ventana READY→IRQ incluye
al maestro Linux y SPI, por lo que no separa todavía espera Linux de reloj físico.
