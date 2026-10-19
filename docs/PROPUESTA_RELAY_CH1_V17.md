# Validación CH1 por formato y fronteras — autorizada el 14/10/2026

El usuario autorizó explícitamente avanzar con esta propuesta el 14/10/2026.
Instalada y aceptada físicamente en producción: los seis perfiles pasaron
60 s + tres arranques independientes de 120 s, sin pérdidas ni fatal.
Informe: `diagnosticos/resultados_v17/optimized_integration_20261014_095040/report.json`.
La revisión automática había rechazado
la instalación de la variante porque interpretó eliminar la reconstrucción
por muestra como una reducción de salvaguardas tras un fallo de integridad.
La variante anterior con reconstrucción por muestra se conserva en
`diagnosticos/referencias/v17_relay_before_proposal/config_relay_protocol.h`.
Los seis perfiles están habilitados en el selector V17. Los tres máximos
de integridad se distinguen de los tres perfiles con holgura medida.
El arranque de estos perfiles hace cinco segundos de adquisición a 40 kHz
antes de aplicar el máximo, conforme al procedimiento físico aceptado.

Cambio concreto propuesto en `arduino/v17/relay/config_relay_protocol.h`:
extender a los seis perfiles CH1 optimizados el camino por fronteras que
ya existe para ADC8. No cambia ADC/DMA, geometría, SPI, colas, firmware del
generador ni los perfiles duales.

El payload codifica exactamente N bits por valor; no transporta palabras
con bits sobrantes ni timestamps/índices individuales. Los grupos completos
de cuatro valores ocupan 4/5/6/7 bytes a ADC8/10/12/14. Por construcción,
todo valor decodificado está entre cero y 2^N−1. Un primer timestamp/índice
y el paso fijo definen los restantes; verificar la frontera siguiente tiene
el mismo significado que reconstruir todos los valores intermedios.

Antes de esa rama se mantienen CRC de toda la trama, secuencia, epoch,
perfil/bits/canales/ticks/tamaño de nodo, límites/alineación de count,
padding cero, índices dentro del nodo, dropped/fatal y métricas de cola.
La rama verifica el primer índice/timestamp contra el último anterior,
y calcula el último por aritmética uint32. MCU continúa validando cada
muestra ADC real y cada timestamp DMA antes de copiarla al nodo.

Pruebas C/Python de `tests/v17/test_optimized_profiles.py` verifican los
seis perfiles, extremos/packing, wrap uint32, CRC, padding y nueve campos
de metadata alterados con CRC recalculado. La instalación autorizada cumplió
la campaña integrada, con respaldo y restauración exacta de ADC10/909090 SPI
y generador apagado. El firmware nuevo permanece instalado; no se atribuye
holgura por equivalencia lógica.

Diff propuesto:

```diff
--- a/arduino/v17/relay/config_relay_protocol.h
+++ b/arduino/v17/relay/config_relay_protocol.h
@@
-    if(d->bits==8 && scope_high_rate(d->bits,native->channels,ticks,n)) {
-        // Existing ADC8 byte-wide path; unchanged validation scope.
+    if(scope_high_rate(d->bits,native->channels,ticks,n)) {
+        // Whole N-bit groups bound each ADC value; interior timestamps
+        // and indices have a fixed encoded step. Check both boundaries.
+        // MCU retains every raw ADC/timestamp DMA check.
```
