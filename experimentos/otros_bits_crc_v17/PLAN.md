# Tasas adicionales con CRC acelerado

Estado: preparación local; perfiles privados, sin aceptación física ni cambios en selectores públicos.

Primero cerrar RADIO 40 kHz con ADC8/1,6 MS/s: ensayo de 60 s, luego 120 s y transición PCM → Radio Test → PCM. Después verificar RADIO con las tasas actuales de 10/12/14/16 bits.

Candidatos independientes:

| Bits | Canales | Ticks | Muestras/s | Muestras/nodo |
|---|---|---|---|---|
| 10 | 1 | 128 | 1.250.000 | 5568 |
| 12 | 1 | 150 | 1.066.666,67 | 4608 |
| 14 | 1 | 176 | 909.090,91 | 3968 |
| 16 | 1 | 1050 | 152.380,95 | 3488 |

ADC16 conserva sobremuestreo 16; primero verificar formato CH1 a 80.000 muestras/s. La tasa dual existente no se reemplaza.

Cada candidato: pantalla de 60 s y tres arranques independientes de 120 s. Guardar continuidad numérica, CRC, secuencia, épocas, índices/timestamps, drops/fatals, cola y margen de envío. Integridad y holgura son resultados separados (holgura: media >=10%, cola pico <4 y slack mínimo positivo). No reutilizar aceptación de otro binario.

Un propietario Q; respaldo y captura antes de modificar; compilar con ADC detenido. Restaurar exactamente headers, firmware, relay y configuración previos, verificar identidad y 10 s de continuidad antes de cerrar. No promover tasas sin evidencia física. La aceptación analógica y de escucha requiere pruebas adicionales.

`prepare.py` prepara firmware/relay compatibles con DAC de 30 bloques y CRC verificado. `test_contract.py` comprueba empaquetado MCU → validador relay → decodificadores Python; no acredita velocidad física.

Ejecución preparada: `run.py --all` realiza sólo las pantallas de 60 s (más preparación de formato ADC16 CH1 a 80 kS/s). Cada perfil arranca por separado y vuelve a baja tasa para verificar política normal. `run.py --all --qualify --evidence <reporte>` exige que todas las pantallas de 60 s hayan pasado con holgura, hashes idénticos y restauración confirmada; recién entonces ejecuta tres pruebas de 120 s por resolución con el mismo binario. No se heredan resultados de un firmware distinto. Cada fase restaura la instalación original y comprueba 10 s de continuidad.

## Alcance vigente por instrucción del usuario

17/10: el usuario pidió dejar 14 y 16 bits para más adelante. `prepare()` genera por defecto únicamente ADC10/128 y ADC12/150; la campaña `--all` utiliza sólo los perfiles realmente preparados. ADC14/16 no se miden ni se incorporan en esta etapa. Las propuestas anteriores se conservan aquí para retomarlas, sin aceptación.

Candidato8064 (`qualification_20261017_130711`) falló CRC físico. Causa identificada por bytes de timestamps en frame: scratch SPI de2×992 al final del arena timestamps65536 comienza en63552;2×8064×4=64512 invade960bytes. No promover. Nuevo candidato ADC12 N7488 (13frames576,59904bytesDMA) deja5632bytes, superior a1984scratch. Conservar tasa ticks150 y verificar bound antes de medición física.

Candidato7488: pantalla`qualification_20261017_131439` pasó/restaurado. ADC10/1,25M19,28%cola3; ADC12/1,067M17,64%cola2, sin pérdidas. Aceptación larga se ejecuta sobre exactamente ese binario. La incorporación final además pruebaRADIO8/1,6M120s, FILTER50Hz→A0 en8/1,6M60s yFILTER→A0 en los nuevos10/12 durante60s; publicar integridad y holgura conjunta por separado.
