# V6 IRQ + READY: DMA con espera por eventos

Aplicación independiente `Scope SPI IRQ READY V6`, protocolo SCP1/v2 idéntico
al ensayo DMA. Sin ADC ni transporte USB al monitor.

[Resultados y validación física](../../../diagnosticos/IRQ_READY_SPI_V6.md).
20 MHz, pausa fija cero: 215.002 bloques en dos minutos sin errores,
824.169 B/s útiles. El umbral de caudal e integridad pasó.

## Cómo se reemplaza la pausa fija

1. El MCU prepara DATA, limpia/invalida caché y arma DMA RX/TX.
2. Sube READY (PG13); Linux recibe el evento por GPIO70 y autoriza un bloque.
3. DMA mueve los bytes mientras el hilo MCU espera un semáforo.
4. Las IRQ de GPDMA1 canales 2/3 bajan READY y sus callbacks despiertan
   el hilo cuando terminaron ambos canales, o ante error. El hilo comprueba EOT.
5. El hilo comprueba PING y prepara el siguiente bloque; vuelve a subir READY.

Linux usa GPIO character-device v2 y `poll()`, con un segundo de timeout.
El primer nivel alto permite el primer bloque. Luego exige un nuevo flanco
ascendente por bloque: no reutiliza el nivel alto de la transferencia anterior.
Se comprueba la secuencia de eventos y se descartan eventos iniciales tardíos
anteriores al inicio del intercambio precedente. El descriptor GPIO permanece
reservado durante toda la medición. No hay `nanosleep` entre bloques: `--gap-us 0`.

Esto elimina la pausa fija, **no el tiempo real necesario para rearmar**.
Preparación, comprobación y caché todavía ocurren entre bloques. Los buffers
alternados y la adquisición real serán otra etapa. Tampoco se ha medido aún
el porcentaje de CPU: el hilo duerme mediante `k_sem_take`, pero hay trabajo
por bloque e interrupciones. La espera ociosa despierta cada 50 ms para
comprobar transferencias truncadas; éstas se detectan en aproximadamente
50–100 ms. Las IRQ ajenas a SPI3 permanecen habilitadas salvo las secciones críticas breves
de caché heredadas de V5.

## READY también interviene en el arranque

El [esquema oficial](https://docs.arduino.cc/resources/schematics/ABX00162-schematics.pdf)
conecta PG13 del MCU con GPIO70 del MPU a 1,8 V. No hace falta un cable.
Pero Arduino Router también usa GPIO70 como salida de autorización de
arranque. El loader del core 1.0.0 espera PG13 alto antes de ejecutar el sketch.
Por eso no se puede cambiar el MPU a entrada antes de arrancar el MCU.

`tools/unoq.py start --version v6_irq` utiliza `ready_boot` de `unoq.json`:
primero detiene la aplicación, mantiene el MCU en reset (GPIO38 bajo), pone
GPIO70 alto y libera reset. Luego inicia la app. El sketch mantiene PG13 como
entrada hasta que el receptor reserva GPIO70 como entrada con pull-down;
entonces toma PG13 como salida y publica el primer bloque listo.

No iniciar esta variante directamente desde App Lab después de haber usado
READY como entrada: usar el comando anterior para repetir correctamente el
arranque. No ejecutar otro consumidor de GPIO70 durante la medición. No se
modifican los servicios de Arduino Router ni el loader. Si el servicio/router
o el MCU se reinician, detener la medición y repetir el arranque completo.

Para cambiar de variante, usar `python3 tools/unoq.py stop --version v6_irq`:
además de detener la app, devuelve GPIO70 al nivel de arranque bajo reset,
para que V5 u otra variante puedan iniciar normalmente después.

## Comandos

```sh
python3 tools/unoq.py compile --version v6_irq
python3 tools/unoq.py create --version v6_irq  # sólo primera instalación
python3 tools/unoq.py stop --version v6_dma  # o la aplicación que esté activa
python3 tools/unoq.py start --version v6_irq
python3 tools/spi_benchmark.py --build-native
python3 tools/spi_benchmark.py --firmware v6_irq --implementation c --hz 1000000 --seconds 5 --gap-us 0
python3 tools/spi_benchmark.py --firmware v6_irq --implementation c --hz 20000000 --seconds 120 --gap-us 0
```

El receptor C compilado se conserva por hash en
`/home/arduino/.cache/serialmonitor/` para sobrevivir a reinicios; los paquetes
de compilación sólo se instalan dentro del contenedor temporal. En esta
variante se requieren C y pausa cero; el script agrega el dispositivo GPIO
además de spidev al contenedor. Los resultados se guardan en
`diagnosticos/resultados_spi/` y mantienen el umbral de 750.000 B/s.

SPI mantiene la codificación de [V6 DMA](../v6_dma/README.md).
En esta variante los errores DMA llegan como errno del callback del core:
`last_driver_error = -(0x02000000 | abs(errno_TX) | (abs(errno_RX) << 16))`.
No interpretar ese rango como una captura CSR: el driver limpia sus banderas
antes de llamar al callback. El último error queda retenido entre ensayos.
`ready_wait_s` mide la espera Linux por READY, separada de `timing_s.exchange`.
Un timeout de READY devuelve error y no emite un bloque especulativo.

## IRQ compartidas del core

El core 1.0.0 tiene `CONFIG_SHARED_INTERRUPTS=1`: `irq_connect_dynamic()`
agrega un cliente, no reemplaza automáticamente al driver ya conectado.
El primer intento con ISR propia observó un bloque válido y luego timeout,
porque el driver DMA limpiaba TC antes de nuestra lectura. La implementación
actual configura los callbacks mediante la API DMA del core; mantiene SPI3
por registros con su IRQ deshabilitada. Hay dos notificaciones por bloque,
no una interrupción por byte. No se modifica la tabla ISR con direcciones fijas.
