# ADC8 CH1 cerca de 1,4 MHz · 13/10/2026

Las seis combinaciones fallaron antes de completar el segundo de estabilización.
No se inició aceptación prolongada ni se modificó el selector de producción.

| Tasa real (Hz) | Nodo | Cola pico | dropped / fatal | Presupuesto nodo (µs) | Último envío (µs) |
|---:|---:|---:|---:|---:|---:|
| 1391304.348 | 3456 | 4 | 1 / 0 | 2484.000 | 2572.806 |
| 1403508.772 | 3456 | 4 | 1 / 0 | 2462.400 | 3844.331 |
| 1391304.348 | 6912 | 4 | 1 / 0 | 4968.000 | 6082.538 |
| 1403508.772 | 6912 | 4 | 1 / 0 | 4924.800 | 5758.750 |
| 1391304.348 | 8192 | 4 | 1 / 0 | 5888.000 | 8038.706 |
| 1403508.772 | 8192 | 4 | 1 / 0 | 5836.800 | 7584.137 |

Los tiempos son instantáneas de fallo, no medias sostenidas. Cola llena y envío mayor
al presupuesto señalan saturación del consumidor/transporte; no demuestran un límite
de conversión ADC. Firmware experimental existente, fuentes remotas contrastadas con
hashes locales, generador apagado, host con caffeinate y continuidad estricta.

Q restaurado: ADC14/363636, SPI, todos los campos del generador originales (apagado).
Firmware y relay originales restaurados; hash firmware idéntico. Diez segundos de
continuidad: 3634440 pares sin error del decodificador.

Dos intentos preliminares fallaron por red Docker y quedaron archivados aparte.
Se creó la red exclusiva experimental 10.203.140.0/24 tras verificar rutas/subredes,
y se recreó sólo su contenedor detenido, sin borrar fuentes ni volúmenes.

[Reporte completo](report.json).
