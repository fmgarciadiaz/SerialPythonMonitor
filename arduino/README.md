# Adquisición y generación en Arduino UNO Q

[Arquitectura completa: partes, flujos y carga del Q](../docs/ARQUITECTURA.md)

El MCU ejecuta el sketch STM32 que adquiere A2/A3 y genera por A0 con
temporizadores y DMA. El MPU ejecuta Linux: App Lab mantiene la aplicación
y un relay nativo separado lleva muestras y comandos por SPI y USB/ADB.

Preparar Q en el monitor instala o actualiza ambos componentes. Conectar
usa lo instalado y comprueba/inicia app y relay cuando el enlace no responde.
Para administrar manualmente el conjunto de audio:

```sh
python tools/unoq.py status --version v17
python tools/unoq.py compile --version v17
python tools/usb_stream.py start --firmware v17
```

Compile valida sin cargar. Antes de cambiar firmware, cerrar el monitor y
detener la pareja anterior. [Instalación y respaldo](historico/v12_audio/README.md).

[MCU y cableado](../docs/UNO_Q_TECNICO.md) · [Relay](../docs/TRANSPORTE_TECNICO.md)

## Versiones

- [V17](v17/README.md): pareja activa, RADIO AM y Radio Test F1/F2.
- [V16](v16/README.md): respaldo local, retirado del Q y exportado el 19/10/2026.

- [V12 Audio](historico/v12_audio/README.md): variante anterior de audio, conservada para selección explícita.
- [V11 P992](historico/v11_p992/README.md): archivada con Monitor V12; selección explícita de consola.
- [Histórico](historico/README.md) y [catálogo de apps](apps_catalogo.json).
- [Puente R4 V5](historico/v5/r4_bridge_v5/README.md): transporte UART opcional.

[V13 Pulse](historico/v13_pulse/README.md): firmware histórico de Monitor V15, con audio y pulsos desde 100 µs.
