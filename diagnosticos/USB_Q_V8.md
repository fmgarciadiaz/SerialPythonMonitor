# USB directo del UNO Q y monitor V8

Actualizado: 2026-10-02. Etapa correspondiente al **paso uno** del
[Plan de trabajo](../Plan%20de%20trabajo.md): conservar el osciloscopio y
reemplazar el transporte por Q → USB → Python, sin R4.

## Ruta implementada

ADC/TIM2/TIM5/DMA de V6 ADC permanece sin cambios. Un relay C independiente
consume SPI3/READY continuamente en Linux y reenvía los bloques SCP1 íntegros
al PC, que verifica CRC, secuencia, ACK, metadatos, errores MCU, índices,
rango de 14 bits y timestamps de 32 µs antes de entregar las muestras a Qt.

El Q tiene las funciones USB `acm.GS0` y `ffs.adb`. `ttyGS0` está reservado por
`arduino-router-serial.service`, por lo que se utilizó **ADB sobre el USB
existente**, con un túnel a un socket que escucha exclusivamente en loopback.
No se cambiaron los servicios de Arduino ni la configuración del gadget.

V8 partió de la interfaz de V7, sustituyendo el lector y la selección del Q.
Ahora su implementación está consolidada en `monitor/historico/v8/app.py`, sin importar V7.
Cada sesión conserva las funciones de gráfico, trigger, mediciones y CSV;
la resolución permanece fija. Las capturas V8 tienen su propia carpeta.

[Instrucciones de inicio y uso](../monitor/historico/v8/README.md).

## Verificación en el PC

| Ensayo | Bloques | Pares | Caudal útil | Resultado |
|---|---:|---:|---:|---|
| [10 s](resultados_usb/20261001_213531_081884.json) | 5.944 | 312.125 | 248.611 B/s | Sin errores |
| [120 s inicial](resultados_usb/20261001_213827_930338.json) | 71.371 | 3.747.893 | 249.761 B/s | Sin errores |
| [120 s, relay corregido](resultados_usb/20261002_014959_430310.json) | 71.366 | 3.747.628 | 249.794 B/s | Sin errores |

El ensayo final duró 120,023 s, incluyendo cierre del túnel. El caudal total
con envoltura SCP1 fue 304.437 B/s. Todas las pruebas verificaron la integridad
en el PC, no sólo en Linux del Q. No se descartaron bytes de resincronización:
una trama incorrecta habría terminado la prueba.

## Primera prueba de interfaz y corrección de reconexión

El [primer ensayo Qt](resultados_usb/20261001_213922_142476_monitor.json)
recibió 300.704 pares en la sesión inicial, calculó 31.250 Hz y grabó
271.979 filas CSV sin huecos. Falló al reconectar: el relay comprobaba cierres
solamente al enviar, pero ADB podía cerrar sólo la dirección PC → relay.

Se corrigió comprobando también EOF en recepción antes de aceptar un nuevo
cliente. Un segundo cliente mientras el primero sigue activo continúa siendo
rechazado. Una cola TCP llena o escritura parcial termina esa sesión, con
buffer de envío acotado; SPI sigue consumiéndose para no desbordar el ADC.
Los resultados del primer intento se conservan y no cuentan como prueba exitosa
de reconexión.

## Interfaz, CSV y reconexión: versión corregida

[Ensayo Qt del 2 de octubre](resultados_usb/20261002_014737_635562_monitor.json):

- 321.589 pares procesados en la primera sesión; frecuencia indicada: 31.250 Hz.
- 293.163 filas CSV, sin huecos de timestamp.
- 137.269 pares después de desconectar y reconectar, sin reiniciar el Q.
- 458.858 pares totales y 849 llamadas de dibujo en la prueba offscreen.
- Cero errores; `pass=true`.

Las **70 pruebas locales** pasan. Incluyen lecturas USB fragmentadas,
CRC/cabecera/metadatos corruptos, errores MCU, pérdida de bloques/muestras,
ACK discontinuo, wrap de timestamps/índices y limpieza del túnel propio.

## Alcance dentro del plan

El paso uno ya tiene una primera versión funcional con recepción USB,
interfaz, CSV y reconexión comprobados. Se verificó por SHA-256 que todos
los archivos del sketch coinciden con el ensayo ADC validado antes de esta
etapa; no se cambió la adquisición para integrar USB.

Esta versión mantiene dos canales a 31,25 kHz y 14 bits. No agrega selección
de transmisor, configuración de adquisición ni mandos del generador.
La conexión es dúplex, pero los comandos PC → MCU corresponden a los pasos
siguientes. En la validación original el PING/ACK se originaba en Linux;
la [etapa posterior](CONTROL_Q_V8.md) prueba también consultas originadas en el PC.

El inicio del relay sigue siendo explícito mediante `tools/usb_stream.py`;
no está empaquetado dentro de la aplicación App Lab ni se inicia solo después
de reiniciar el Q. V4/V5, R4 y monitores V6/V7 se conservan.

La prueba digital no certifica precisión analógica, ruido o ancho de banda.
La prueba Qt offscreen comprueba recepción, procesamiento, llamadas de dibujo
y CSV; no mide los FPS reales de la pantalla del usuario.
