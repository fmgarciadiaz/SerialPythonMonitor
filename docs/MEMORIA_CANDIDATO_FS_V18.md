# Revisión de memoria del candidato FS V18

Astra revisó las fuentes y el core Arduino/Zephyr instalado, sin operar Q.
Compilación inicial:257948/262144bytes informados,4196bytes de margen.
Ese margen corresponde a la arena del sketch, no a toda la pila disponible.

El `autoconf.h` del core UNOQ/Zephyr1.0.0 confirma:

- `CONFIG_MAIN_STACK_SIZE=32768`.
- Heap general32768bytes y arena LLEXT256KiB.
- `CONFIG_THREAD_STACK_INFO=1`; sin evidencia de watermark inicializado.

Adquisición y salida reservan estáticamente4096bytes de stack cada una.
SingleMemory usa163840bytes:ADC32768,timestamps65536,samples65536. Ocho
nodos de3456muestras y descriptores caben en el mismo arena de samples,
comprobado por static_assert. DAC ocupa28800bytes (30×480×uint16).
Dos frames SPI se alojan en la parte libre de timestamps con comprobación de
no solapamiento. La escalera de ticks no agranda esos buffers.

El bucle principal usa TX/RX1984bytes y puede añadir992bytes idle; la tabla
local de temporización del generador añade516bytes. Son tamaños de objetos,
no una medición del máximo stack de todas las llamadas.

No se justifica reducir buffers o alterar DMA por el warning genérico. Se
mantiene el diseño y se solicita ELF/map para revisar secciones, alineación y
los símbolos grandes antes del sondeo. No atribuir aceptación física al mero
hecho de que compile ni aumentar colas para ocultar demoras.

Las tablas `native_profiles.h` y `high_rate_profile.h` coinciden entre MCU y
relay. ADC8ticks88–98 conserva SPI40/WORD, DSIZE8/CRCSIZE7 y ocho nodos.
La whitelist permite los perfiles, pero no prueba conversión/precisión ADC.

## Artefactos obtenidos

Segunda compilación aislada y restauración verificadas. `artifacts/` contiene
ELF/map y salidas reproducibles size/nm. `.bss=213400`, `.text=42688`,
`.data=124`; storage adquisición con metadatos163936bytes, memoriaDAC28800,
pilasproducer/output4096cadauna. TablaCRC8192 está en `.rodata`, no `.bss`.
El análisis no muestra un crecimiento de nodos ni una necesidad de cambiar
buffers para el sondeo. Falta medir stack máximo real y estabilidad física.
