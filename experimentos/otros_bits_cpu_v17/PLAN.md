# 10/12/14/16 bits: primer bloque de mejoras equivalentes

A/B/B/A a tasas ya admitidas, 10 s por caso, mismo firmware y transporte.
A: governor/afinidad normales capturados después de salir del perfil ADC8
SPI40. B: governor performance y afinidad del relay CPU2. La prioridad y
SPI de cada perfil siguen bajo su política de producción.

10 bits: CH1 ticks137 N5568; 12 bits: CH1 ticks163 N4608;
14 bits: CH1 ticks188 N1984; 16 bits: dos canales ticks2099 N3456,
sobremuestreo16. No extrapolar el resultado ADC16 a CH1 ni resolución efectiva.

Registrar CRC/secuencia/epoch/timestamps mediante decoder estricto, pérdidas,
cola, envío y slack desde APPLIED. Separar integridad y margen. Cambios de
política sólo en etapa ADC14/40000, con bombeo continuo del receptor.
No compilar, flashear ni cambiar perfiles públicos. Snapshot, respaldo,
identidad y configuración exacta; verificar restauración y10s de continuidad.
Un único dueño de Q. Cualquier fallo detiene este bloque y queda archivado.
Esto es screening comparativo, no aceptación prolongada de nuevas tasas.
