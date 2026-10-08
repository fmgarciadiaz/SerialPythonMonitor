# Adquisición y generación en Arduino UNO Q

El MCU ejecuta el sketch STM32 que adquiere A2/A3 y genera por A0 con
temporizadores y DMA. El MPU ejecuta Linux: App Lab mantiene la aplicación
y un relay nativo separado lleva muestras y comandos por SPI y USB/ADB.

Preparar Q en el monitor instala o actualiza ambos componentes. Conectar
usa lo instalado y comprueba/inicia app y relay cuando el enlace no responde.
Para administrar manualmente el conjunto de audio:

```sh
python tools/unoq.py status --version v12_audio
python tools/unoq.py compile --version v12_audio
python tools/usb_stream.py start --firmware v12_audio
```

Compile valida sin cargar. Antes de cambiar firmware, cerrar el monitor y
detener la pareja anterior. [Instalación y respaldo](v12_audio/README.md).

[MCU y cableado](../docs/UNO_Q_TECNICO.md) · [Relay](../docs/TRANSPORTE_TECNICO.md)

## Versiones

- [V12 Audio](v12_audio/README.md): MCU y relay usados con Monitor V13; añade WAV por A0.
- [V11 P992](v11_p992/README.md): pareja anterior con Monitor V12; predeterminado de las herramientas de consola.
- [Histórico](historico/README.md) y [catálogo de apps](apps_catalogo.json).
- [Puente R4 V5](historico/v5/r4_bridge_v5/README.md): transporte UART opcional.

[V13 Pulse experimental](v13_pulse/README.md).
