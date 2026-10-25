# Candidatos de tasas para V18

Fuentes privadas copiadas de producción y modificadas aquí. No instalar estas
tasas mediante los perfiles públicos. `source_manifest.json` registra origen
y hashes. `prepare.py` regenera la copia, no modifica el origen.

```sh
python experimentos/fs_max_v18/prepare.py
python -m unittest experimentos.fs_max_v18.test_contract -v
python experimentos/fs_max_v18/compile_only.py
```

La última orden requiere Q exclusivo: captura estado e identidad, pasa ADC a
40kS/s mientras compila en una carpeta temporal independiente, continúa
recibiendo y luego restaura el estado previo con diez segundos de recuperación.
**La compilación aislada no instala el candidato ni modifica fuentes del Q.**
El runner físico sí instala/activa una app experimental independiente y restaura
Scope V18 al cerrar; nunca modifica la pareja congelada V17.
`compile_report.json` guarda el resultado; compilar no acredita ninguna tasa.

La escalera ADC8 conserva SPI40/WORD y nodos3456: ticks98,96,94,92,90,89,88.
89t =1,797753MS/s y88t=1,818182MS/s. Otros perfiles en
`candidate_profiles.json`. ADC16CH1 conserva sobremuestreo y empaquetado16bits.
El relay selecciona SPI40 antes deCONFIG, no sólo despuésdeAPPLIED.

Antes de sondeos físicos de firmware: respaldo de la app instalada, identidad
MCU y binario relay, montajes/env/CPU y perfilADC/generador exactos; runner con
único dueño, salida de emergencia y restauración verificada incluso por fallo.
No reutilizar un runner anterior que escriba fuentes locales de V17. Los
sondeos por escalera no califican integridad sostenida ni holgura ni audio.


## Variantes privadas

`prepare_spi40.py` prepara `spi40_10_12/`: SPI40 y DMA WORD con frames de696/
576 muestras para10/12bits. Conserva cuatro slots y usa memoria libre de
 timestamps, sin buffers adicionales. App `Scope V18 Rate Probe SPI40`.

`prepare_wide8.py` prepara `wide8/`: ADC8/88ticks con nodos6912 y cuatro slots.
La capacidad total27648muestras coincide con8×3456 de la receta original.
Busca amortizar gestión por nodo; comparar ocupación en tiempo y proporción,
no sólo el número de nodos. App `Scope V18 Rate Probe Wide8`.

Ejemplos (Q exclusivo; --run activa y restaura el experimento):

```sh
python experimentos/fs_max_v18/run_probe.py --run --recipe spi40_10_12 --bits 10 12 --seconds 15
python experimentos/fs_max_v18/run_probe.py --run --recipe wide8 --bits 8 --seconds 60
python experimentos/fs_max_v18/run_probe.py --run --bits 8 --target-ticks 88 --seconds 120 --repeats 3
```

Adopción exige app detenida y fuentes idénticas; las identidades de variantes
son explícitas y no se sobrescribe una app con fuentes diferentes. El cierre
compara configuración de montajes independientemente de su orden y verifica
las políticas CPU normal y activa por separado. Los fallos detienen la campaña.

### CRC8: comparación aislada del costo CRC del relay

`prepare_crc8.py` genera Full8 con CRC32 slicing-by-eight portable. Conserva el firmware Full8 exacto y reutiliza sólo su app experimental verificada; el relay recibe una ruta independiente por digest. No cambia reloj, payload, buffers, validación ni protocolo.

Verificación sin Q: `python -m unittest experimentos.fs_max_v18.test_crc8`; benchmark local: `python experimentos/fs_max_v18/test_crc8.py --benchmark`. El benchmark mide únicamente CRC, no la cadena completa. Campaña privada: `python experimentos/fs_max_v18/run_probe.py --run --recipe crc8 --bits 8 --target-ticks 88 --seconds 60`. Aplican respaldo, dueño único y restauración del runner.

### Diagnóstico ADC8 con RADIO/A0

`trace8` y `trace8time` reutilizan el firmware y app WordPing exactos. Sólo el relay cambia: ring64 de metadatos ante fallo; timing añade esperaREADY/ioctl y resumen64frames cada10s. Esos resúmenes no representan medias de toda la corrida. `test_trace8.py` compila el ring y verifica wrap y tiempos. El arnésGUI captura candidate_relay.log antes de restaurar.

`alignedping` usa app independiente y cargas alineadas may_alias con fallback seguro. Falló el sondeo físico161220 y no se promueve. WordPing conserva evidencia60+3×120 de transporte, pero aún falla combinado con RADIO/A0. Ningún resultado habilita tasa pública.
