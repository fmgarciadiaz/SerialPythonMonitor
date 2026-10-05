# Firmware aislado de tiempos MCU

Copia de V9 Fast para localizar el atraso de 125 kHz. No es un firmware de uso
normal y no debe abrirse con el monitor V11.

`preparar_firmware_diagnostico.py` genera esta app desde las fuentes V9 Fast.
Los únicos cambios funcionales son la instrumentación y la detención al detectar
un nodo perdido: detiene TIM2 y los hilos productor/consumidor, conserva los
contadores en RAM y entrega una trama diagnóstica SCP1 tipo 11 con CRC. El DAC
queda en su estado actual hasta detener la app. No agrega salida Serial ni texto
al flujo DATA. La trama se lee con el relay diagnóstico de este experimento.

## Métricas

Se acumulan ciclos de CPU de 160 MHz, número de observaciones y máximo:

1. Preparación de trama, incluyendo CRC.
2. Armado de intercambio: reset/configuración DMA, caché y habilitación SPI.
3. Desde armado hasta callback final DMA: incluye espera al maestro y reloj SPI.
4. Desde callback final hasta retorno: incluye despertar del hilo y limpieza.
5. Validación y comandos recibidos.
6. Preparación/handoff de fragmento completo en el consumidor.
7. Duración completa del envío de un nodo.
8. Intervalo entre recorridos del productor ADC.
9. Validación/copia del nodo ADC a la cola.

Se mide ocupación máxima de los cuatro espacios, incluyendo el nodo prestado.
Los contadores se reinician al cambiar resolución/tasa. Los sumatorios son de
64 bits; los intervalos individuales usan resta modular de 32 bits.

La captura se congela antes de emitir la instantánea. No hay logging durante
adquisición. Los tiempos de espera se superponen con el trabajo de otros hilos:
**no sumar todas las métricas como si fueran costos independientes**. La propia
instrumentación tiene costo; comparar con el fallo previo sin instrumentación.

## Decodificación de evidencia

```sh
python3 experimentos/tasas_spi/leer_snapshot_mcu.py RUTA_DEL_LOG
```

El lector exige tipo, longitud, CRC, cantidad de métricas y padding correctos,
y convierte los ciclos a microsegundos según el reloj guardado en la instantánea.
Para volver al firmware normal, detener el relay y esta app antes de iniciar
`tools/usb_stream.py start --firmware v9_fast`. La app normal se conserva en su
carpeta independiente; no se reemplazan sus fuentes.
