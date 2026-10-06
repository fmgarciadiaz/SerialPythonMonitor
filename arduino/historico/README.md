# Versiones anteriores de Arduino

Estas carpetas conservan las fuentes anteriores sin cambiar su funcionamiento.
La adquisición actual está en [V11 P992](../v11_p992/README.md).

- [V8 config](v8_config/README.md): pareja histórica del monitor V10.
- [V9 Fast](v9_fast/README.md): pareja histórica del monitor V11.
- [V10 diagnóstico](v10_diag/README.md): instrumentación experimental.

- [V5](v5/README.md): respaldo Q + R4 por UART a 3 Mbps, 31,25 kHz; monitor V7.
- [Q V4](v4/oscilloscope/README.md) y [R4 V4](v4/r4_bridge_v4/README.md): UART a 2 Mbps, 20 kHz; monitor V6.
- [V6](v6/README.md): primer ensayo de SPI con datos sintéticos.
- [V6 polling](v6_polling/README.md): acceso a registros SPI.
- [V6 DMA](v6_dma/README.md): DMA TX/RX con espera por polling.
- [V6 IRQ + READY](v6_irq/README.md): DMA por interrupciones y handshake, antes de integrar ADC.

Las herramientas siguen aceptando `--version v4`, `v5`, `v6`, `v6_polling`,
`v6_dma` y `v6_irq`; encuentran aquí sus configuraciones. Mover estas carpetas
no mueve ni elimina las apps instaladas en el Q.

## Versiones archivadas al consolidar V10

- [V7 dual](v7_dual/README.md): firmware del monitor V9.
- [V6 ADC](v6_adc/README.md): firmware del monitor V8.

El firmware actual es [V8 config](v8_config/README.md). Las apps del Q
conservan sus nombres y destinos remotos; esta consolidación organiza los archivos locales.
