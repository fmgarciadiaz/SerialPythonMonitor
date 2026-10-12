# CH1: perfiles aceptados e incorporación V16

| Bits | Máximo íntegro ensayado | Perfil con margen | Nodo máximo / margen |
|---|---:|---:|---:|
|8|1.221.374,046 Hz (131 ticks)|1.118.881,119 Hz (143 ticks)|6912 /8192|
|10|909.090,909 Hz (176 ticks)|909.090,909 Hz (176 ticks)|8192 /8192|
|14|747.663,551 Hz (214 ticks)|701.754,386 Hz (228 ticks)|7936 /7936|

Cada ganador completó60s, tres arranques independientes de120s y600s:
CRC, secuencia, época, índices, timestamps, valores ADC y propiedad DMA válidos;
dropped=0 y fatal=0. Margen: media del envío de nodo al menos10%, cola pico
menor4 y tiempo positivo hasta sobrescritura.

Son máximos entre los perfiles ensayados, no límites universales del ADC.
La integridad no certifica precisión analógica, asentamiento, ENOB ni FPS GUI.
Las suspensiones del Mac contaminaron una campaña previa, archivada aparte;
las aceptaciones usadas registran host despierto y deriva pared/monotónico menor2s.

Incorporados en V16: whitelist MCU y relay generada desde aceptaciones completas,
metadatos del monitor, contrato codificado por perfil, decodificador kind20 e interfaz.
Los formatos y perfiles anteriores se mantienen. Los nuevos son SPI/CH1.
La ventana de adquisición de los nuevos perfiles es5 ciclos ADC a54 MHz.

La integración inicial excedía RAM en316 bytes. Se reutilizó, exclusivamente
en UART, el espacio posterior a sus dos nodos de2048 timestamps para el paquete
DATA. El modo UART comprueba que no sea nativo/CH1 y conserva todos los campos.
La comparación binaria del constructor real UART incluye desborde del contador.
WAV conserva16 bloques de480 puntos. Compilación corregida:258.484 bytes globales,
3.660 libres; relay construido y firmware cargado con respaldo exacto.

Evidencia:
- sweep.json: aceptaciones completas y parámetros restaurados.
- finish_margin.log: afinamiento225..241 y aceptación final de228.
- production_compile_scratch.log /production_relay_build.log: compilaciones.
- production_deployment.json: respaldo y hashes del firmware.
- production_integration.json: verificación integrada, estado a consultar.
  El primer fallo de comparación ACK está preservado en archivos *_ack_failure.
- native_profiles.json y native_profiles.h se generan mediante incorporate.py.

La restauración de campos del perfil original (ADC8/333333, SPI, seno50kHz)
es distinta de su integridad: ese perfil ya mostraba pérdidas antes de la campaña.
No usarlo como referencia estable de pérdidas cero.
