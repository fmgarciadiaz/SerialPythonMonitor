# Diagnóstico del atraso a 125 kHz

Instrumentación independiente de V9 Fast y V11. No optimiza aún el transporte:
primero mide para distinguir déficit sostenido de pausas ocasionales.
App MCU: [V10 diagnóstico](../../arduino/v10_diag/README.md).

## Qué se mide

MCU: separación entre sondeos del productor, validación/copia de nodo ADC,
tiempo desde take hasta release, construcción de fragmentos, espera entre
hilos por fragmento, preparación, verificación PING/control, armado DMA/SPI,
espera desde READY hasta completar intercambio, limpieza y separación entre
llamadas a loop. Cada métrica lleva cantidad, suma en microsegundos y máximo.
Los intervalos de handoff y envío de nodo incluyen las otras etapas: **no se
suman entre sí**. Los tiempos son de pared, incluyen preempciones y no separan
CPU activa de espera del planificador.

Cola: cantidad de slots ocupados (incluye el nodo prestado) y máximo, de 0 a 4.
Se conserva la propiedad de los slots hasta terminar la transferencia física.

Linux: espera READY, ioctl SPI, cola temporal de la iteración y envío TCP, con
cantidad, suma y máximo. Se imprimen resúmenes cada segundo y al abortar; no se
imprime por muestra ni por trama. Los primeros intervalos de arranque/configuración
pueden contaminar máximos: analizar régimen y progresión de la cola además del pico.

Python: captura los bytes originales del enlace y cada snapshot por nodo.
No dibuja ni graba CSV durante el diagnóstico. No atribuir al monitor un cuello
de botella que también aparezca en esta captura sin interfaz.

## Telemetría y efecto de medir

SCP1 de 512 bytes, DATA de hasta 53 pares. El último fragmento del nodo tiene
34 pares; su padding desde offset 352 admite **152 bytes** TDG1:
marca 4 bytes, 11 métricas de 12 bytes, cola actual/máxima y dropped/fatal.
Offsets 504–507 siguen en cero. No se agregan tramas ni se altera ningún dato ADC.
CRC original se comprueba antes de interpretar o normalizar el padding.

El receptor/relay exclusivos verifican límites de cola y contadores de estado;
normalizan sólo ese padding para reutilizar las validaciones de muestras.
Se rechazan CRC, padding, índices, timestamps, epochs, dropped y fatal igual que
antes. Las fuentes V9/V11 están referenciadas por SHA-256 en
[fuentes_referencia.json](fuentes_referencia.json).

Medir agrega instrucciones y una copia pequeña por nodo: hay efecto sobre el
caudal. Comparar con V9 sin instrumentación, no promover un máximo sólo por
esta app. Sumas y contadores MCU son uint32: los ensayos cortos evitan desborde
acumulativo; no interpretar una sesión indefinida sin manejar ese wrap.

## Ejecutar

Con el monitor desconectado:

```sh
python3 tools/usb_stream.py stop --firmware v9_fast
python3 tools/unoq.py stop --version v9_fast
python3 tools/usb_stream.py start --firmware v10_diag
python experimentos/timing_spi/medir.py --rates 100000 125000 --seconds 30
```

El rechazo a 125 kHz puede cerrar el relay; se guarda la última instantánea
válida y el log completo del rechazo antes de reiniciar. No se permite pérdida
silenciosa para prolongar el ensayo. La restauración dentro del script puede
fallar al cerrar el enlace y queda registrada.

## Volver a V11 + V9 Fast

```sh
python3 tools/usb_stream.py stop --firmware v10_diag
python3 tools/unoq.py stop --version v10_diag
python3 tools/usb_stream.py start --firmware v9_fast
python monitor/v11/app.py
```
