# Radio Test · transición ADC10 CH1 → dual

Fallo observado y reproducido con el firmware V17 cuyo SHA256 es `3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`. El relay original `usb-stream-f25225079211ab351626` cambia SPI38/FIFO10/spin a SPI32/normal/poll al pasar a ADC10 dual (308 ticks, 4176 pares, 519480 Hz nominales). Tras algunos segundos, `dropped=1`, CRC correcto y cola 4/4; el relay cierra el flujo por integridad. También se reproduce con amplitud cero.

Cambio acotado: `arduino/v17/relay/transport_policy.h` conserva SPI38/FIFO10/spin únicamente para ese perfil dual exacto, además de los CH1 ya existentes. `scope_high_rate` permanece intacta en MCU y relay: dual conserva el validador completo. No se cambia firmware MCU, ADC, DAC ni perfiles publicados.

- `baseline.json`, `baseline_relay.log`, `baseline_container.json`: reproducción y binario anterior.
- `prior.json`: estado recuperado tras el fallo inicial, ADC14/31250, SPI, generador apagado. El estado anterior al cierre no pudo consultarse porque el relay ya estaba detenido.
- `fast_zero_screen.json`: comprobación preliminar de 15 segundos con amplitud cero y recuperación de 10 segundos.
- `fast_levels_transitions.json`: tres transiciones, Radio Test 20/40 kHz y tono 1 kHz, extremos DAC 807–3288 (aprox. 2 Vpp, offset 1,65 V).
- `run.py`: runner de un único dueño, captura persistente y restauración al finalizar una ejecución sana. Ante pérdida del flujo conserva el error; requiere recuperar el relay y ejecutar `--restore` con el mismo `--prior`.

Las métricas `send_ticks` se comparan con ticks ADC × pares/nodo para informar margen por nodo observado. Las pausas transitorias pueden dar margen negativo sin pérdida cuando hay cola disponible; esto no acredita margen mínimo sostenido del 10 %. Integridad, margen, aceptación analógica y FPS visibles son criterios separados.

20 pruebas locales de política, perfiles y protocolo aprobadas. El relay candidato compiló en ARM con `-Wall -Wextra -Werror`. La campaña física y la restauración final se resumen al cerrar los ensayos.

## Caso adicional encontrado

`fast_levels_initial_ch1_failure.json` y `.log` conservan un fallo separado: al arrancar Radio Test directamente en CH1 ADC10/1142857 Hz (140 ticks, 2784 pares), apareció `dropped=1` antes de entrar en dual. No se conoce todavía su causa exacta; ese perfil ya carece de margen acreditado. La excepción de transporte dual no corrige ese arranque.

Para aislar la transición original, el runner posterior activa Radio Test en ADC14/40 kHz y luego cambia a CH1 y dual manteniendo el generador activo. Los tres ciclos anteriores sí incluían solicitar Play desde CH1 y pasaron; no basta para declarar estable ese otro caso de arranque.

## Resultado final

La transición original quedó corregida en los casos medidos: tres ciclos de 20 segundos (31.138.692 pares duales) y una corrida independiente de 120 segundos (62.297.916 pares), todos con Radio Test a niveles normales, `dropped=fatal=0` y cola dual pico 2/4. También pasó el screening de 15 segundos con amplitud cero.

Restauración final verificada: ADC14/31250 Hz, SPI y generador apagado con sus campos originales; recuperación de 10 segundos íntegra, mismo SHA256 del firmware y relay corregido activo. Ver `summary.json`, `fast_levels_120s.json`, `final_container.json` y `final_relay.log`.

No se acredita margen mínimo del 10 %: hubo duraciones transitorias de envío superiores al período del nodo, absorbidas por la cola sin pérdida. El perfil conserva `headroom=false`. El arranque de Radio Test directamente en CH1 ADC10/1142857 sigue pendiente y no forma parte de la corrección dual. No se midieron calidad analógica ni FPS GUI.
