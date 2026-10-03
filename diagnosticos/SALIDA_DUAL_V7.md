# Selección SPI/UART con control permanente del Q

Validación física del 2 de octubre de 2026. Aplicación experimental
[V7 dual](../arduino/historico/v7_dual/README.md), Q por USB/ADB y R4 con puente V5 a
3 Mbps, conservando ADC 14 bits, 31.250 pares/s y timestamps de 32 µs.

## Resultado

Dos ciclos SPI → UART → SPI aprobados. En ambos se envió PING al Q durante
UART y después de volver a SPI, con ACK del MCU, cero nodos perdidos y cero
errores de adquisición. Las confirmaciones APPLIED coincidieron con las
muestras de frontera de ambos receptores.

| Prueba | SPI inicial | UART | SPI final | Saltos de timestamp | ADC fuera de rango |
|---|---:|---:|---:|---:|---:|
| 5 s por etapa | 157.696 | 159.744 | 157.291 | 0 | 0 |
| 30 s por etapa | 937.984 | 940.032 | 937.984 | 0 | 0 |

El ensayo largo recibió **2.816.000 pares en 90,161 s**, equivalente a
31.232,94 pares/s, dentro de la tolerancia del 5 %. Los períodos entre todas
las muestras recibidas, incluidas las dos fronteras, fueron de 32 µs exactos.
No se perdió sincronización DATA del R4.

Informes completos:

- [Ensayo corto](resultados_usb/dual_5s.json).
- [Ensayo largo](resultados_usb/dual_30s.json).

## Implementación y comprobaciones

El consumidor de salida posee cada nodo ADC completo. En SPI usa un handoff
con semáforos: el intercambio físico termina antes de avanzar. En UART usa
los cuatro paquetes DATA de V5 y espera fin de transmisión antes de tomar
otro nodo. El control SPI funciona en su propio contexto y prioriza respuestas.
Una solicitud se aplica al comenzar el próximo nodo completo; el modo sigue
fijo durante todo ese nodo. Los buffers DMA SPI son exclusivos de su bucle.

La aplicación compiló con Arduino Zephyr 1.0.0 en la placa: 92.028 bytes de
programa y 150.824 bytes de variables globales, con 111.320 bytes restantes.
El relay dual compiló en Linux con `-Wall -Wextra -Werror`.
Pasaron **81 pruebas automáticas**, incluyendo pruebas C/Python de respuestas,
estados vacíos, secuencia global, CRC, continuidad y frontera de retorno, y
confirmación APPLIED separada de ACCEPTED.

Respaldo de la app V6 ADC anterior al ensayo:
[ZIP](../respaldos/unoq/osciloscopio_20261002_100335_459240.zip).

## Alcance y siguiente subpaso

Esto valida dos ciclos físicos, no una prueba de larga duración ni todas las
combinaciones de desconexiones/reintentos sobre hardware. Los reintentos y
rechazos están cubiertos por la máquina de estados y sus pruebas locales.
DATA UART conserva el protocolo sin CRC de V5: rango y timestamps correctos
no descartan toda corrupción de amplitud.

El monitor V8 conserva su contrato fijo. La siguiente etapa incorpora los
selectores de Q de control y transmisor Q/R4 en una nueva versión del monitor.
Los controles de resolución, muestreo y generador siguen pendientes según el
[plan](../Plan%20de%20trabajo.md).

## Estado final del Q

Después de probar se restauraron V6 ADC y su relay, compatibles con V8.
La [comprobación USB posterior](resultados_usb/20261002_101651_112180.json)
recibió 155.701 pares en 5,028 s con integridad y caudal aprobados.
V7 dual quedó importada, detenida y disponible para el siguiente subpaso.
