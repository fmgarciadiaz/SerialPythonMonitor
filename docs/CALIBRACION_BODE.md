# Calibración instrumental de Bode

La referencia se mide conectando A0 directamente a A2 y A3, con masa común.
Corrige la diferencia de ganancia y fase entre los dos canales del instrumento;
no reemplaza una medición del circuito bajo prueba ni aumenta el ancho de banda
que permite el muestreo.

## Perfiles y banda

El monitor admite resoluciones de 8, 10, 12, 14 y 16 bits. La resolución de
16 bits admite tasas hasta 62,5 kHz; las otras tienen opciones en la interfaz
hasta 125 kHz. Hay 78 combinaciones en la interfaz actual. El contrato del
receptor incluye también opciones experimentales de 200 y 250 kHz (86
combinaciones), que no aparecen en el selector del monitor.
Que un perfil aparezca en ese contrato no garantiza que su calibración pase
la prueba física de repetibilidad.

La tanda priorizada utiliza únicamente **14 y 16 bits**, desde 40 kHz:
40/50/62,5/100/125 kHz en 14 bits y 40/50/62,5 kHz en 16 bits. Son ocho
perfiles y cuatro métodos por perfil. La opción anterior es 31,25 kHz.

Para la tanda completa se usa la banda de 20 Hz a `min(5000, 0,4 × Fs)` Hz.
Así, por ejemplo, una referencia a 1 kHz de muestreo cubre hasta 400 Hz.
El monitor no extrapola fuera de la banda medida.

Se ensayan Tonos, Sweep, Chirp y Pulso H1. En Pulso se conserva el estímulo
predeterminado de 100 µs y el promedio de ocho disparos. Por debajo de 20 kHz
el estímulo ocupa menos de dos muestras y no se habilita una referencia de
Pulso. La calibración no puede recuperar un estímulo que el ADC no resuelve.

## Validación independiente

Cada método y perfil usa tres mediciones sin corrección previa. Las dos
primeras forman la referencia, promediando ganancia y fase desenvuelta sobre
frecuencias comunes. La tercera queda fuera del cálculo y permite comprobar
la corrección contra el resultado de loopback esperado: 0 dB y 0°.

Para aceptar la referencia se exige:

- Ganancia y fase válidas en al menos el 90 % de los puntos de cada captura.
- Percentil 95 del error de ganancia ≤ 0,5 dB y del error de fase ≤ 2°.
- Error máximo de ganancia ≤ 1 dB y de fase ≤ 5°.

Los fallos de captura, referencias insuficientes y resultados que no cumplen
estos límites se registran en el reporte y no generan una referencia activa.
Las referencias anteriores se conservan.

## Identidad y uso

Una referencia corresponde a un número de serie, app activa, hash del binario
MCU instalado en App Lab, resolución ADC, tasa y método. El monitor habilita
Calibración solamente cuando encuentra una referencia aceptada que coincide.
El hash identifica la instalación gestionada por App Lab, no una lectura de
la memoria flash: una programación externa requiere invalidar la referencia.

## Herramienta

[calibrate_bode.py](../tools/calibrate_bode.py) ejecuta la tanda física. El
monitor debe estar desconectado para que exista un único dueño del relay.

```sh
python tools/calibrate_bode.py --serial NUMERO_DE_SERIE --loopback-confirmed
```

Para inventariar perfiles sin conectar al Q:

```sh
python tools/calibrate_bode.py --loopback-confirmed --list
```

Un reporte interrumpido se puede continuar con `--resume-report RUTA`.
`--bits` y `--rates` permiten limitar la tanda. Los resultados se guardan
después de cada método en `diagnosticos/resultados_bode/`, y las referencias
aceptadas en `monitor/v13/calibraciones/`. Al finalizar se solicita restaurar
ADC14/40 kHz y se confirma la salida apagada durante el cierre del receptor.

[calibrate_bode_matrix.py](../tools/calibrate_bode_matrix.py) continúa un
reporte con conexiones aisladas por perfil. Usa las opciones de la interfaz
actual; ante un cierre del flujo guarda el log, registra los métodos que no
pudo completar y reinicia la misma variante instalada para seguir.

```sh
python tools/calibrate_bode_matrix.py --loopback-confirmed --report RUTA \
  --bits 14 16 --rates 40000 50000 62500 100000 125000
```

## Resultados del 7 de octubre de 2026

Tanda priorizada completada: ocho perfiles, cuatro métodos por perfil y tres
mediciones independientes por método. Se aceptaron **16 referencias nuevas**,
además de conservar las 27 aceptadas en la tanda anterior de esta sesión.

| Bits | Muestreo (kHz) | Tonos | Sweep | Chirp | Pulso H1 |
| --- | --- | --- | --- | --- | --- |
| 14 | 40 | Sí | Sí | No pasó | No pasó |
| 14 | 50 | Sí | Sí | No pasó | No pasó |
| 14 | 62,5 | Sí | No pasó | No pasó | No pasó |
| 14 | 100 | Sí | Sí | No pasó | No pasó |
| 14 | 125 | Sí | No pasó | No pasó | No pasó |
| 16 | 40 | Sí | Sí | No pasó | Sí |
| 16 | 50 | Sí | Sí | No pasó | Sí |
| 16 | 62,5 | Sí | Sí | No pasó | No pasó |

La tabla describe la aceptación de referencias nuevas en esta tanda. Se
conserva también la referencia anterior de Chirp a 14 bits / 100 kHz; no se
generó una nueva para ese caso. Las referencias anteriores siguen sujetas
a la comprobación de identidad y perfil.

[Reporte completo y métricas de validación](../diagnosticos/resultados_bode/20261007_002031_calibracion_completa.json) ·
[Restauración y progreso final](../diagnosticos/resultados_bode/20261007_foco_y_restauracion.log).

Los intentos iniciales de 8 bits / 200 y 250 kHz cerraron el flujo y no
generaron referencias. Son opciones experimentales del receptor, fuera de
la interfaz actual. Los resultados previos de 8 bits y los perfiles de
10 bits ya completados se conservaron. El Q terminó con ADC14/40 kHz
y salida apagada.
