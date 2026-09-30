# R4 V5 experimental

Sketch `r4_bridge_v5.ino`, UNO R4 WiFi / renesas_uno 1.6.0.
Basado en el puente optimizado V4. **RX del Q: 3 Mbps; salida USB: 3 Mbps.**
Usar junto con Q V5 y monitor V7. Preparado, no validado físicamente.

Reserva SCI2 RX y SCI9 TX, cola 8 KiB y vector RX propio igual que V4.
No usar Serial.write ni Serial1.read con esta ruta. LED alto indica error local.

Compilar desde la raíz:
`arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi arduino/v5/r4_bridge_v5`

Ver [plan y restauración](../README.md).
