# Tanda de períodos menores · 25/10/2026

Copia experimental de la pareja V18 aceptada. No modificar monitor/arduino
V18 de producción, V17 ni Scope V17. App independiente Scope V18 Rate Probe
RateOnly. Restauración de app, relay, política CPU e identidad de producción
por runner transaccional. Sin publicación automática de tasas.

Método constante por formato: misma ventana/reloj ADC, resolución,
packing/CRC/validación, tamaño de bloque, arena DMA, colas y reloj SPI.
Solo ampliar listas explícitas para nuevos períodos; las rutas existentes
conservan todas sus condiciones. Heredar CPU y modo IPC del perfil de partida.

| Bits | Bloque | Períodos candidatos | Tasas (MS/s aprox.) |
|---|---:|---|---|
| 8 | 3488 | 87 / 86 / 84 | 1,839 / 1,860 / 1,905 |
| 10 | 5568 | 120 / 118 / 116 | 1,333 / 1,356 / 1,379 |
| 12 | 7488 | 144 / 142 / 140 | 1,111 / 1,127 / 1,143 |
| 14 | 5952 | 174 / 172 / 170 | 0,920 / 0,930 / 0,941 |

Primero sondeo 15 s del menor incremento de cada formato. Fallo implica
parar esa escalera y restaurar; no omitir un fallo ni subir todavía más.
Integridad no equivale a holgura: margen medio >=10%, cola pico <4 y slack
positivo se registran por separado. Candidato viable requiere luego
60 + 3×120 s, GUI visible/RADIO/A0/Scan US/WAV y restauración verificadas.
16 conserva x16 sobremuestreo: la escalera anterior ya encontró fallos
por encima de los máximos aceptados. No se reduce resolución para ganar FS.
