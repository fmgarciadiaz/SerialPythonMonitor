# Receptor V18

El proceso receptor conecta únicamente con Scope V18 y su relay instalado.
Valida CRC, secuencia, épocas y continuidad de SCP1 antes de entregar muestras.
Los cambios de configuración conservan el orden de datos y confirmaciones.

ADC8 CH1 a 1,818 MS/s utiliza lotes compactos entre procesos. La reconstrucción
en el host conserva valores, timestamps e índices. El audio PCM dispone de un
canal de pedidos independiente y conserva créditos y límites del DAC.

«Conectar» no instala ni reinicia firmware. «Preparar Q» utiliza exclusivamente
`monitor.v18.q_support`, con recibo aceptado, respaldo y recuperación.

[Guía actual](../../../docs/GUIA_V18.md) ·
[Arquitectura](../../../docs/ARQUITECTURA_V18.md).
