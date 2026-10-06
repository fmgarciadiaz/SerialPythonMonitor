# Puente R4 WiFi V4

Para el Q V4 de 20 kHz. **Q → R4: 3.000.000 baudios. R4 → PC: 2.000.000.**
El monitor V6 conserva su baud predeterminado de 2 millones.

Abrir `r4_bridge_v4.ino` en Arduino IDE y seleccionar **Arduino UNO R4 WiFi**.
Core comprobado: `arduino:renesas_uno` 1.6.0. El sketch original del IDE no fue
modificado; no volver a cargarlo mientras el Q ejecute V4 porque usa 1,1 Mbps.

Compilar desde la raíz del repositorio:

```sh
arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi arduino/historico/v4/r4_bridge_v4
arduino-cli upload --fqbn arduino:renesas_uno:unor4wifi --port /dev/cu.PUERTO_R4 arduino/historico/v4/r4_bridge_v4
```

## Recursos exclusivos

- SCI2 recibe en D0/P301 desde TX del Q. Conservar GND común y cableado existente.
- SCI9 transmite al ESP32 que hace de puente USB (pines internos P109/P110).
- `Serial.begin` y `Serial1.begin` configuran reloj, pines y UART al arrancar.
- Se reemplaza en RAM el vector RX de SCI2 por una ISR breve que escribe en
  una cola circular de 8192 bytes (8191 útiles). Sólo ISR modifica head;
  sólo loop modifica tail. No se deshabilitan interrupciones por cada byte.
- TX consulta TDRE y escribe TDR directamente; no hay ISR TX por byte.
- No llamar Serial.write, Serial1.read/available ni compartir estos UART con
  otra biblioteca. La asociación de periféricos es específica del R4 WiFi.

LED encendido: cola desbordada o no se encontró el vector esperado.
No sustituye la comprobación de continuidad en el PC. El protocolo no tiene CRC.

## Prueba

Cerrar primero el monitor y ejecutar:

```sh
python3 diagnosticos/verificar_enlace.py /dev/cu.PUERTO_R4 --seconds 15
```

La validación física dio 299.520 pares en 15 s, cero anomalías de timestamp,
cero ADC fuera de rango y cero bytes perdidos después de sincronizar.
Los bytes anteriores a la primera cabecera y un fragmento final son esperables.

Para volver a V3: detener V4, restaurar en el R4
`respaldos/historico/DebuggerRtRx_1100000.ino.bak` como sketch del IDE y arrancar V3.
USB/PC sigue a 2 Mbps; sólo el enlace Q–R4 vuelve a 1,1 Mbps.
