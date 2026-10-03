# ADC → SPI → MPU: avance del paso uno

Fecha: 2026-10-01. Aplicación `Scope ADC SPI V6`, carpeta
[`arduino/historico/v6_adc`](../arduino/historico/v6_adc/README.md), independiente de V5 y de
los benchmarks sintéticos V6. Última variante experimental dejada en la placa;
no se restaura V5 después de medir.

## Relación con el plan

Se conserva el [Plan de trabajo](../Plan%20de%20trabajo.md) del usuario.
El enlace sintético superó el requisito previo (824.169 B/s verificados,
dos minutos sin errores, SPI 20 MHz con DMA y READY).

| Etapa del plan | Estado |
|---|---|
| Requisito: enlace MCU–MPU suficiente | Validado con datos sintéticos |
| Paso uno: misma adquisición sin R4 | ADC → SPI → Linux validado; continuación USB/Python en [V8](USB_Q_V8.md) |
| Paso dos: elegir UART/R4 o SPI/Q | Pendiente; adquisición separada del consumidor para permitir ambos |
| Paso tres: bits y frecuencia configurables | Pendiente; metadatos explícitos, configuración todavía fija |
| Paso cuatro: generador controlable | Pendiente; se mantiene A2 conmutando cada 200 ms |
| Paso cinco: FFT/heatmap/transferencia | Pendiente |
| Paso seis: grabar/reproducir WAV | Pendiente |

Este informe conserva la validación aislada; el avance posterior está en
[USB directo y V8](USB_Q_V8.md). No se considera terminado el paso uno hasta integrar el transporte USB,
conservar las funciones del monitor y validar la ruta completa en el PC.
PING/ACK comprueba el retorno MPU → MCU, pero todavía no implementa comandos
de configuración o del generador.

## Implementación y verificaciones

- Dos canales, 14 bits, 31.250 pares/s, TIM2 a 32 µs y timestamps TIM5 por DMA.
- Dos nodos ADC/timestamps alternados y cuatro nodos en una cola separada.
- SPI 20 MHz, DMA TX/RX, callbacks por bloque y READY interno, pausa fija cero.
- Muestras de 8 bytes como V5, fragmentadas en bloques SCP1 tipo 3 con CRC.
- Desbordamiento de cola registrado por nodo; índices y timestamps conservan el hueco.
- Error hardware, incoherencia de timestamps o propiedad DMA ambigua detienen TIM2.
- Compilación Arduino: 84.820 bytes de programa, 140.412 bytes globales;
  quedan 121.732 bytes de RAM según el compilador.
- 64 pruebas locales pasan, incluidas continuidad, wrap de timestamp/índice,
  CRC, metadatos, rango ADC, huecos y notificación fatal.

## Ensayo corto

[Log de 10 s](resultados_spi/20261001_210019_429292.log):
5.930 bloques válidos, 311.402 pares, 10,0368 s.
248.209 B/s de muestras verificados. Cero errores SPI, CRC, ACK, adquisición,
secuencia, timestamps o rango; cero nodos descartados.
La pequeña diferencia respecto a 250.000 B/s incluye arranque y entrega por nodos.

## Pausa deliberada del receptor

Tras cerrar el receptor del ensayo corto, se dejó el ADC adquirir y se
volvió a abrir el receptor sin reiniciar el MCU.
[Log de reanudación](resultados_spi/20261001_210059_239091.log):
451 nodos descartados, exactamente **923.648 pares faltantes = 451 × 2.048**.
El verificador devolvió `integrity_pass=false`, como corresponde.
No hubo CRC corruptos, fallos SPI/ACK, errores de rango ni errores de timestamps:
el salto temporal coincidió con el salto del índice. La cola no mezcló muestras
viejas y nuevas ni ocultó la pérdida. La tasa al reanudar incluye vaciado de cola;
no debe interpretarse como un aumento de la frecuencia del ADC.

## Ensayo continuo de dos minutos

[Log completo](resultados_spi/20261001_210306_863904.log), arranque limpio:

| Medida | Resultado |
|---|---:|
| Duración | 120,0088 s |
| Bloques válidos | 71.333 / 71.333 |
| Pares de muestras recibidos | 3.745.898 |
| Caudal de muestras verificado | 249.708 B/s |
| Caudal total SPI | 304.332 B/s |
| Huecos, duplicados, CRC y ACK incorrectos | 0 |
| Errores SPI, DMA/adquisición y rango ADC | 0 |
| Saltos incorrectos de timestamp | 0 |
| Nodos descartados | 0 |
| Mayor espera por READY | 68,370 ms |
| Mayor ioctl SPI | 1,209 ms |

`integrity_pass`, `throughput_pass` y `pass`: **true**.
El período observado entre pares consecutivos fue siempre 32 µs. El caudal
medio de entrega incluye el arranque y los nodos aún pendientes al cortar;
no indica que TIM2 haya cambiado su frecuencia. READY espera ahora también
la disponibilidad de un nodo ADC, además del rearme SPI.

Esto valida esta configuración y duración. El margen máximo del transporte
se midió por separado con el benchmark sintético; aquí el caudal lo limita
la fuente ADC de 250.000 bytes/s.

## Límites

La validación comprueba continuidad digital y transporte, no precisión,
amplitud, ruido, ancho de banda ni desfase analógico entre canales.
No valida aún USB hacia PC, gráfico, reconexión automática ni mandos del generador.
El verificador informa caudal de **muestras** en `verified_sample_Bps`; los
ensayos sintéticos anteriores informan `verified_pattern_Bps`.

El ADC continúa al desconectar el verificador. Reiniciar con
`python3 tools/unoq.py start --version v6_adc` antes de una nueva prueba limpia.
No ejecutar dos consumidores SPI/GPIO simultáneos.
