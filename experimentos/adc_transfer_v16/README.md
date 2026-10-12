# Transferencia V16: medición y ADC14 empaquetado

Ensayo independiente autorizado el 10 de octubre de 2026. La aplicación estable Scope V16 y sus fuentes permanecen sin cambios. Scope V16 Transfer Experimental quedó detenida al terminar.

## Resultado físico

| Variante | Vaciado medio por nodo a ADC333 | Resultado |
| --- | ---: | --- |
| Original instrumentado | 7,518 ms | Cola llena; flujo cerrado a 0,115 s |
| CRC de cuatro bytes | 6,816 ms | Cola llena; flujo cerrado a 0,193 s |
| CRC de ocho bytes, padding y bucle O2 | 6,510 ms | Cola llena; flujo cerrado a 0,330 s |
| ADC14 empaquetado + optimizaciones anteriores | 5,548 ms | 120,000 s sin pérdidas ni errores fatales |

La última variante recibió **39.981.814 pares** a ADC333 en la prueba de 120 s, además de una prueba inicial de 10 s con 3.329.290 pares. La tasa observada larga fue 333.181,316 pares/s frente a 333.333,333 nominales. El contador MCU y el relay conservaron `dropped=0`, `fatal=0`, CRC, secuencia, índices, época y validación original de timestamps TIM5 por muestra.

La reducción del tiempo medio frente al original instrumentado fue de aproximadamente **26.2 %**. La comparación original tiene una ventana corta porque el perfil pierde nodos rápidamente; no es una estimación estadística de rendimiento a largo plazo.

La ocupación observada una vez por nodo fue 1/4 en 16.073 registros y 2/4 en 3.450. Los promedios por cuartos del ensayo fueron 1,173 / 1,184 / 1,174 / 1,176 slots, sin tendencia de crecimiento. Se observaron 19.522 nodos completos entre los extremos de telemetría. El nodo más lento observado tardó 7,794 ms; la cola absorbió esos picos.

A 333,3 kHz llegan nodos cada 6,144 ms: el margen **medio** del ensayo es de aproximadamente 9,7 %, y no equivale a margen mínimo garantizado. Se conserva como experimento; faltan interfaz real, precisión analógica con fuente confirmada, ensayo prolongado y concurrencia con generador/synth.

## Implementación

Se mantuvieron SPI solicitado a 32 MHz, tramas de 992 bytes, cuatro slots, la ventana ADC de 36 ciclos / 0,72 µs y DMA/validación por muestra. No se aumentó la cola ni se eliminó ningún control de integridad.

* CRC-32/ISO-HDLC equivalente mediante tablas de ocho bytes: se usa para datos y control. La tabla ocupa 8 KiB.
* Preparación de muestras: sólo se pone a cero el padding; metadatos y muestras se sobrescriben completamente. Se verificó equivalencia de las tramas de la variante sin empaquetar.
* Compilación O2 de `loop()` y `exchange()`; el hook del core quedó igual.
* Tipo de datos experimental **15** para ADC14: dos pares CH1/CH2 de 14 bits se guardan exactamente en siete bytes. El resto de resoluciones conserva tipo 3. Cada trama admite 258 pares, y cada nodo de 2048 pares requiere **8 tramas**, con 242 pares en la última, frente a 10 tramas anteriores. No cambia resolución, escala ni orden de las muestras.
* Telemetría TDG2 en el padding de la última trama: 13 palabras desde offset 931. Se valida el CRC original antes de extraerla. El decoder y relay siguen rechazando padding no reservado, recortes de nodo y discontinuidades.

No se subió SPI: sus límites eléctricos dependen de tensión, pines y tiempos del receptor; véase la tabla 150 de la [hoja de datos STM32U585 de ST](https://www.st.com/resource/en/datasheet/stm32u585ri.pdf). El ensayo conserva el reloj del perfil anterior.

## Evidencia y restauración

* `baseline_results.json`, `crc4_results.json`, `fast8_results.json`: variantes previas, todas restauradas.
* `packed_results.json`: prueba completa y restauración; `packed_case_summary.json`: resumen de tiempos y distribución de cola.
* `packed_relay_trial.log`: registro del relay. `baseline_sketch`, `crc4_sketch`, `fast8_sketch`: fuentes MCU archivadas de cada etapa anterior.
* `prior_profile.json`: perfil guardado antes del primer ensayo. Las exportaciones App Lab están indicadas en los reportes y en `respaldos/unoq/`.
* `manifest.json`: formato de esta variante experimental, incompatible con receptores que no admiten tipo 15.

Cada ensayo recargó el MCU y relay estables, restauró ADC14/250 kHz, generador apagado y WAV IDLE, y verificó otros 10 s de captura. La última verificación recibió 2,498,546 pares sin pérdidas ni errores fatales. El menú y firmware habituales siguen en su estado previo.

Pasaron **27 pruebas**: CRC de referencia con longitudes y alineación variadas, comparación de padding, empaquetador C++ real del MCU contra valores originales, interop C/Python, continuidad y rechazo de formatos inválidos, además de pruebas del protocolo estable.

```sh
python -m unittest experimentos.adc_transfer_v16.test_packed experimentos.adc_transfer_v16.test_decoder experimentos.adc_transfer_v16.test_crc experimentos.adc_transfer_v16.test_frames tests.v16.test_compact_protocol tests.v16.test_spi_emit_boundary
```

`run.py` compila/instala la app independiente, mide ADC250/333/250 y siempre recarga V16. Antes de ejecutarlo otra vez debe guardarse un perfil actual del Q; el perfil archivado no debe asumirse vigente. Se requiere un único dueño de la placa, monitor cerrado y salidas apagadas. La captura headless no valida precisión analógica ni interacción con la GUI.
