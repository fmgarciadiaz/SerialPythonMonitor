# Pulsos DAC temporizados por hardware

Variante experimental independiente de adquisición y audio. V12 Audio conserva
sus fuentes y su app instalada. La variante usa TIM6 en modo one-pulse para
volver al nivel bajo sin esperar el supervisor de 2 kHz. DMA4 se detiene y
no se usa para este pulso; vuelve a estar disponible para ondas y WAV.

Rango inicial: 100–65535 µs enteros. El selector inicia en 1000 µs (1 ms).
La duración breve se programa con TIM6 a 1 MHz; hay una pequeña latencia de
armado entre el flanco inicial y el arranque del contador, pendiente de medir
con osciloscopio externo. No se promete precisión de 1 µs por las pruebas ADC.

## Protocolo y compatibilidad

El byte de configuración reservado 3 indica duración en µs sólo en Pulso.
Cero conserva el contrato de ms. El estado anuncia capacidad en byte 23;
Monitor V13 habilita µs únicamente cuando la recibe. El firmware/relay anterior
rechaza esa extensión. Relay y MCU deben provenir de esta misma carpeta.

```sh
python tools/unoq.py compile --version v13_pulse
python tools/usb_stream.py build --firmware v13_pulse
```

Para cambiar de app, cerrar el monitor, detener el relay y la app activa antes
de arrancar otra. El Q ejecuta una sola app MCU de adquisición a la vez.
Preparar Q del monitor sigue instalando V12 Audio, no esta variante.

## Referencia técnica

[Manual STM32U5: TIM6 y DAC](https://www.st.com/resource/en/reference_manual/rm0456-stm32u575585-armbased-32bit-mcus-stmicroelectronics.pdf) ·
[Implementación](oscilloscope/sketch/generator_dma.h) ·
[Arquitectura y DMA](../../docs/UNO_Q_TECNICO.md).

## Comprobación física · 6 de octubre de 2026

MCU y relay compilados. 18 pulsos (seis de 100, 200 y 1000 µs), ADC14/100 kHz:
los anchos detectados en A2 coincidieron con el valor configurado dentro de la
resolución ADC de 10 µs. No aparecieron pulsos adicionales tras drenar el historial
del arranque. La primera tentativa incluyó muestras anteriores al ensayo y se
excluyó, sin atribuirlas al motor nuevo. Pruebas nativas verifican unidades y
finalización por hardware; pruebas de compatibilidad Qt/WAV/conexión: 27 OK.

Wav50 completó una pasada de un segundo tras pulsos y seno, con salida apagada
al terminar. La variante quedó activa en el Q, con ADC14/40 kHz y salida apagada.
V12 Audio está instalada y detenida; sus fuentes no se cambiaron.
[Informe ADC](../../diagnosticos/resultados_pulsos/20261006_pulso_us.json).
La exactitud y los flancos del pulso requieren comprobación con osciloscopio externo.

Para volver a la pareja conservada, cerrar el monitor y ejecutar:

```sh
python tools/usb_stream.py stop
python tools/unoq.py stop --version v13_pulse
python tools/usb_stream.py start --firmware v12_audio
```

## Versiones

- Esta carpeta: V13 Pulse, experimento para [Monitor V13](../../monitor/historico/v13/README.md).
- [V12 Audio](../v12_audio/README.md): pareja conservada.
