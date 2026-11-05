# Arduscopio Q · especificaciones y capacidades

[Presentación del proyecto](../README.md) · [Guía de funciones](GUIA_FUNCIONES.md) · [Índice técnico](README.md)

## Entradas y salida

- Dos entradas analógicas, A2/CH1 y A3/CH2; rango nominal de 0 a 3,3 V.
- Salida A0 mediante DAC de 12 bits; rango nominal de 0 a 3,3 V.
- La resolución seleccionable depende del perfil. El modo de 16 bits usa
  oversampling y no implica 16 bits de precisión efectiva.

## Referencias de muestreo

| Modo ADC8 | Tasa de referencia |
|---|---:|
| CH1 | 1,860465 MS/s |
| Dual, por canal | 632,411 kS/s |

La tasa de 2 MS/s en CH1 es **experimental**. Los ensayos observan menor margen
de envío que a 1,860465 MS/s y no constituyen una calificación general ni una
autorización para presentarla como estable. Consultá el [análisis de margen y
límites](V20_MARGEN_ADC8_2M_20261104.md) y la [evidencia de tasas](V20_ESTABILIDAD_TASAS_20261103.md).

Las tasas de muestreo no especifican el ancho de banda analógico ni la precisión
medible. Los resultados dependen del modo, el transporte y la carga activa.

## Funciones de señal y audio

El generador ofrece seno, cuadrada, triángulo y rampa, además de modos Sweep,
Chirp y Pulso. WAV registra A2/A3 en estéreo y permite reproducir audio mono por
A0; Synth y Radio también pueden usar A0. Las tasas de DAC y combinaciones
válidas se describen en sus documentos de ensayo, no se infieren de una prueba
local aislada.

[Perfiles de adquisición](CONFIGURACION_ADQUISICION.md) · [Generador](../monitor/v20/README.md) · [Ensayos WAV](WAV_TASAS.md) · [Synth](SYNTH.md)
