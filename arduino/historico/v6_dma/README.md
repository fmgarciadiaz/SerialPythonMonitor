# V6 DMA: SPI3 con GPDMA TX/RX

Ensayo sintético independiente, sin ADC ni transporte USB al monitor.
Conserva SCP1/v2: 512 bytes por bloque, 460 bytes de patrón útil, CRC32,
secuencia y confirmación PING en la trama siguiente.

[Resultados de las pruebas físicas](../../../diagnosticos/DMA_SPI_V6.md):
20 MHz, pausa solicitada 150 µs, 212.221 bloques en dos minutos sin errores,
813.510 B/s útiles. Supera el umbral de 750.000 B/s en el ensayo sintético.

La [variante posterior IRQ + READY](../v6_irq/README.md) reemplaza la espera
activa y la pausa fija: validada dos minutos sin errores a 824.169 B/s.

GPDMA1 canal 2 transmite RAM → SPI3 TXDR (request 11); canal 3 recibe
SPI3 RXDR → RAM (request 10). Cada acceso es de un byte, con direcciones
incrementales sólo en RAM y sin listas enlazadas. Los canales 0/1 quedan
libres para la futura adquisición; no se reinicia el controlador DMA completo.
Se comprueba que 2/3 estén deshabilitados antes de usarlos. Esta asignación
corresponde al core 1.0.0; debe revisarse si cambia el core o se agregan periféricos.

Los buffers están alineados a la línea de caché y su longitud es múltiplo
de ella. Se limpia/invalida antes de armar y se invalida RX después de
confirmar que DMA terminó. La configuración usa registros y constantes
LL del core instalado, sin modificar Zephyr ni activar CONFIG_SPI_STM32_DMA.

**Esta etapa mueve los bytes con DMA, pero todavía espera el fin/error por
polling.** No demuestra aún una API asíncrona ni reducción medida de uso de CPU.
Las interrupciones ajenas a SPI3 y los dos canales dedicados siguen activas,
salvo la sección crítica breve de mantenimiento de caché. Una transacción
activa tiene timeout de 50 ms; esperar al maestro no consume secuencias.
Ante un fallo se detienen ambos DMA antes de reutilizar RAM; si no se logra,
el ensayo queda detenido hasta reiniciarlo.

## Ejecutar

```sh
python3 tools/unoq.py compile --version v6_dma
python3 tools/unoq.py create --version v6_dma  # una vez
python3 tools/unoq.py stop --version v5      # o la variante que esté activa
python3 tools/unoq.py start --version v6_dma
python3 tools/spi_benchmark.py --firmware v6_dma --implementation c --hz 1000000 --seconds 5 --gap-us 1000
python3 tools/spi_benchmark.py --firmware v6_dma --implementation c --hz 8000000 --seconds 10 --gap-us 250
```

Esperar que `start` termine antes de medir. Si falta el verificador nativo,
compilarlo con `python3 tools/spi_benchmark.py --build-native`.
No ejecutar simultáneamente otra aplicación MCU. El umbral se mantiene en
750.000 B/s de patrón verificado; integridad correcta con caudal inferior
igualmente devuelve código 1.

## Diagnóstico

El campo retenido `last_driver_error` codifica los errores SPI como en
[V6 polling](../v6_polling/README.md). Para DMA se usa un rango independiente:
`-(0x02000000 | ((TX_CSR & DMA_ERRORS) >> 8) | ((RX_CSR & DMA_ERRORS) << 8))`.
`DMA_ERRORS` contiene DTEF/ULEF/USEF/TOF. Primero distinguir este rango
antes de interpretar un valor como SR de SPI. La diferencia de contadores
indica errores nuevos; el último error puede provenir de un ensayo anterior.

La variante queda cargada al finalizar las pruebas, según lo pedido.
Para volver manualmente a adquisición: detener `v6_dma` e iniciar `v5`.
