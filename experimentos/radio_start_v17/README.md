# Revisión de Radio Test: arranque CH1 y margen dual

## Evidencia física · 14/10/2026

No se modificó firmware ni relay en esta ronda. Se mantuvo el relay que conserva SPI38/FIFO10 para el dual exacto ADC10/519480 Hz.

`baseline.json`: ADC10 CH1 a 1142857 Hz, 140 ticks, 2784 muestras/nodo. Cinco segundos con generador apagado llegaron a cola 2/4. Cinco arranques/Stop con portadoras de 20 a 20,1 kHz en pasos de 25 Hz, segunda portadora 40 kHz, tono 1 kHz y aproximadamente 2 Vpp/offset 1,65 V pasaron sin pérdida. ACK de Play: 4,35–5,25 ms; cola al reproducir: 3/4.

Cada nodo dura 2,436 ms; cuatro slots representan 9,744 ms de almacenamiento bruto. La capacidad libre instantánea depende del estado de la cola. Los tiempos de ACK incluyen transporte, preparación y respuesta; **no son una medición exclusiva del tiempo de fill**. El fallo previo de Play en CH1 máximo sigue sin resolución: cinco pruebas sanas no descartan un fallo intermitente.

`dual_margin_60s.json`: 60 segundos en ADC10 dual 519480 Hz con Radio Test activo; 31.146.696 pares, dropped=fatal=0, cola pico 2/4. Margen medio observado de envío 8,57 %, mínimo −11,22 %. La cola absorbió los picos, pero no se acredita el objetivo de margen medio ≥10 %. El promedio usa observaciones de métricas con cambios de `(produced, send_ticks)`; no es un promedio certificado por identificador único de nodo. El perfil mantiene headroom=false.

## Código y conclusiones

En `generator.h::apply`, la tabla de 5120 muestras se prepara síncronamente; `sketch.ino::loop` llama a `generator::submit` en el mismo hilo que sirve SPI. Durante esa preparación el hilo no avanza al siguiente intercambio SPI. Es una causa plausible del aumento de ocupación al dar Play, consistente con la observación; falta medir su duración interna para atribuir el fallo previo de forma concluyente. Los cambios de frecuencia también requieren preparación, no sólo Play.

En dual, el relay ya utiliza SPI38/FIFO10, pero `sketch.ino::high_rate_transport` sigue limitado a perfiles CH1. Por eso el MCU aún espera confirmación por cada fragmento dual y reconfigura su DMA mediante la ruta general. Es una oportunidad concreta para medir un pipeline dual separado del selector de validación CH1. No se propone ampliar scope_high_rate ni retirar chequeos.

## Próximas correcciones a verificar

1. Preparación incremental de Radio Test con un trabajo acotado entre intercambios SPI. Mantener DMA detenido mientras se escribe la tabla compartida, impedir conflictos con WAV/cambios concurrentes, responder APPLIED sólo al finalizar y controlar Stop/errores. Evitar otro buffer de tabla y reservar cuidadosamente RAM/stack.
2. Pipeline MCU únicamente para ADC10 dual (308 ticks, 4176 pares), conservando todos los validadores de ADC y timestamps. Verificar caché DMA, propiedad de slots, drenaje antes de APPLIED, cambios CH1/dual/UART y retorno a perfiles normales.
3. Probar por separado ambos cambios: ciclos Play/Stop y cambios de frecuencia desde CH1 máximo, ruido/ráfagas, 60 s y corridas independientes de 120 s; registrar integridad y margen por separado y restaurar el Q.

## Estado final

Ambos ensayos restauraron ADC14/31250 Hz, SPI y el generador apagado con sus campos originales. Recuperación de 10 s íntegra, mismo firmware SHA256 `3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`. Ver summary.json. No se midieron aceptación analógica ni FPS visibles.
