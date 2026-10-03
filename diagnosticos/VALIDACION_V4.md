# Validación física V4 — 29/09/2026

Configuración final cargada:

- Q: Osciloscopio DMA_TXRX V4, arduino:zephyr 1.0.0, 20 kHz por canal.
- Q–R4: 3.000.000 baudios, DATA/512, timestamps uint32 + dos ADC uint16.
- R4 WiFi: renesas_uno 1.6.0; RX SCI2 con ISR propia, cola 8 KiB;
  TX SCI9 por TDRE sin interrupción TX por byte.
- USB/monitor: 2.000.000 baudios, monitor/historico/v6/app.py.

## Resultados

| Prueba | Resultado |
|---|---|
| Verificador sin gráficos, 15 s | 585 paquetes, 299.520 pares, 19.967,7 pares/s |
| Saltos/repeticiones de timestamp | 0 |
| ADC fuera de rango | 0 |
| Bytes descartados después de sincronizar | 0 |
| Monitor V6 real, Qt fuera de pantalla + CSV, ~20 s | 400.896 filas; Fs=20.000 Hz |
| Saltos de timestamp en el CSV del monitor | 0 |

El verificador comenzó a mitad de un paquete (2022 bytes iniciales descartados)
y terminó con 2093 bytes de un paquete incompleto. No son pérdidas en régimen.
La captura del monitor se guardó temporalmente en `/private/tmp/v4_gui_20khz.csv`.

## Por qué no bastaba cambiar el baudrate

Con el puente basado en Serial1.read y Serial.write a 2 Mbps no se recibían
paquetes válidos. Una ISR RX reducida mejoró la recepción, pero persistió corrupción.
Al quitar también la ISR TX por byte, los paquetes llegaron íntegros, aunque
el caudal era ~18.091 pares/s y aparecían saltos de timestamp de ±204.800 µs:
el Q alcanzaba a sobrescribir dos nodos DMA antes de transmitirlos.
Subir sólo Q–R4 a 3 Mbps, manteniendo USB a 2 Mbps, eliminó esos errores
en las pruebas indicadas. No se cambió el formato binario ni la resolución ADC.

El protocolo no lleva CRC, por lo que la continuidad/rango no detecta todas las
alteraciones posibles de amplitud. Estas pruebas no equivalen a una prueba de
larga duración ni certifican otros cables/equipos. V3 y su puente se conservan
para restaurar la configuración anterior a 1,1 Mbps si hiciera falta.
