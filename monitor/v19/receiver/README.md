# Receptor de Arduscopio Q

El proceso receptor conecta únicamente con **Scope V19** y su relay instalado.
Valida CRC, secuencia, épocas y continuidad de SCP1 antes de entregar muestras.
Los cambios de configuración conservan el orden de datos y confirmaciones.

ADC8 CH1 a 1,818 MS/s utiliza lotes compactos entre procesos. La reconstrucción
en el host conserva valores, timestamps e índices. El audio PCM dispone de un
canal de pedidos independiente y conserva créditos y límites del DAC.

«Conectar» no instala ni reinicia firmware. «Preparar Q» usa exclusivamente
`monitor.v19.q_support`; para V19 queda protegido hasta completar su recibo de
aceptación física.

[Guía del monitor](../../../docs/README.md) ·
[Arquitectura](../../../docs/ARQUITECTURA_V19.md).
