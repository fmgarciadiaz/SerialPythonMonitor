# Scope Opt125 P512

Copia independiente de V9Fast: SCP1 versión 2, tramas de 512 bytes, SPI 32 MHz, 53 pares por fragmento y cola ADC de 4 slots. App `Scope Opt125 P512`, remoto `/home/arduino/ArduinoApps/scope-opt125-p512`, contenedor `serialmonitor-opt125-p512`, TCP 8766.

Cableado adoptado: A2/A3 entradas ADC, A0 salida DAC. Antes de cargar firmware confirmar compatibilidad del cableado. Ownership, semáforos, prioridades, ADC y generador conservan la implementación V9Fast. No se cambia el protocolo ni se agrega información al padding DATA.

Cambios: `valid_ping` calcula una vez la semilla y verifica grupos de cuatro bytes; todos los bytes de payload siguen verificados, además de cabecera y CRC. Helpers locales y preparación de metadata/muestras usan O2 bajo GCC. El CRC tabulado/O2 y el sellado único ya estaban en V9Fast.

`benchmark_protocol_baseline.h` conserva el código anterior para comparación. Desde cualquier cwd: `python3 /ruta/al/repo/tests/test_opt125_p512.py`. El ejecutable C++ diferencial compara PING, DATA, cabecera, CRC, padding, corrupción en cada posición y secuencias de frontera. La inspección ARM del ensamblado y las mediciones físicas se realizan en Q por separado; el ensamblado host no acredita el código ARM.

La telemetría RAM y snapshot después de detener adquisición se gestionan en variante instrumentada separada por el runner común Opt125. Este firmware no contiene diagnósticos en DATA. No hay validación física de 125 kHz todavía.
