# Preparación SPI: comparación de compilador · 28/10/2026

Continúa la [medición de costos SPI](RADIO_SPI_COSTES_V19_20261028.md).
La única modificación de fuente en cada A/B es un carácter del atributo de
`prepare_batch_half`:Os→O2. Ambas variantes usan idéntico perfil y toolchain,
ruta temporal de fuente compartida y flags de metadatos
`-fstack-usage -fdump-ipa-cgraph`. No cambia ADC, protocolo ni propiedad DMA.

## Diferencia de toolchains encontrada

Aunque ambos paquetes internos se llaman `arm-zephyr-eabi 1.0.1`, el compilador
instalado en esta Mac Intel reporta SDK0.17.4/GCC12.2.0. El DWARF del respaldo
aceptado reporta GCC14.3.0. Los comandos y fuentes generadas (excluyendo#line)
coinciden en lo esencial, pero no corresponde transferir resultados entre GCC.

El A/B local `prepare_opt_ab_20261028` compiló, pero su control no coincide con
el binario aceptado. O2 allí aumentó `.text`336bytes y bajó la pila del wrapper
176→160. Se conserva como referencia secundaria, no evidencia para desplegar.

Para reproducir el toolchain aceptado se ejecutó otro A/B en el Q, con respaldo
pareado, app/relay detenidos, fuentes bajo `/tmp/` único y ninguna instalación
de candidatos. El control Os reprodujo **exactamente** el BIN aceptado:
`37f049fa029ad62a10767c56dc586b2c3697f8d250a0b8a7396570ce8e0c7060`.
Se verificó cierre de procesos compiladores antes de restaurar la pareja.

## Comparación relevante: GCC14.3

Evidencia `diagnosticos/resultados_v19/prepare_opt_ab_q_20261028/`:

| Magnitud | Os aceptado | O2 privado |
|---|---:|---:|
| Archivo ELF |126.588 B|126.728 B|
| `.text` |42.968 B|43.248 B|
| `.rodata` |1.496 B|1.496 B|
| `.llext.rodata.noreloc` |11.649 B|11.649 B|
| `.data` |124 B|124 B|
| `.bss` |213.400 B|213.400 B|
| Estimación RAM del checker |258.228 B|258.508 B|
| Libre estimado |3.916 B|3.636 B|
| Relocaciones `.rel.text` |1.413|1.418|
| Código `prepare_batch_half` |916 B|980 B|
| Pila propia estática `prepare_batch_half` |184 B|152 B|
| Pila propia `loop` |4.280 B|4.280 B|
| Pila propia `output_worker` |88 B|88 B|

Candidato BIN `4e56c37bffca36c6dc88779fb225b5d76f1c6a49f323ce7272a847fb260c29ce`,
no instalado ni habilitado por el recibo productivo.

El crecimiento de código se explica exactamente: el antiguo `build_samples`
de1.516bytes se divide en944+808+40 (+276); el wrapper agrega64; `data_frame`
externo de60bytes se incorpora por inlining:276+64−60=280. No usar el delta
del tamaño ELF140bytes como costo de carga del módulo.

## Revisión estática y límites

Astra pudo revisar el A/BGCC14.3 después de una interrupción previa por cuota.
Verificó el SHA del control y que las demás secciones desensambladas coinciden,
incluidos loop, output_worker, CRC y adquisición ADC. No es una aprobación física.
El wrapper `build_samples` restaura SP antes de su tailbranch; sus4bytes propios
no se suman simultáneamente a los40 del helper nativo. Los `.su` no prueban por
sí solos el máximo completo incluyendo llamadas importadas, interrupciones y heap.

El resultado es un candidato estático explicable, **no prueba de velocidad**.
Preparación145µs incluye lock/esperas/preempciones; no se promete una reducción
equivalente. El helper de empaquetado también cambia su generación de código:
una futura prueba debe vigilar servicio por nodo, copy/poll, colas, integridad,
audio y STOP, además de preparación media. El margen de carga LLEXT y pilas
en ejecución sigue pendiente. No se reducen pilas ni se cambia geometría.

La infraestructura privada actual del relay exige firmware aceptado. Probar
este BIN requeriría un mecanismo explícito para firmware privado con relay
aceptado, identidad exacta y rollback, sin relajar el recibo de producción.
No se implementó ni ejecutó ese despliegue en esta tanda.

Ambos buildsGCC14.3, análisis y restauración terminaronPASS. Fuentes originales
y runtime sin cambios; V17/V18 intactos. Ocho tests de build/rollback pasaron.
Herramientas: `compare_prepare_compiler_v19.py` (Mac) y
`compare_prepare_compiler_q_v19.py` (pareja detenida y restauración). Resumen
en `static_comparison.json`, ensamblado, relocaciones, símbolos, `.su` y cgraph.

## Actualizar GCC en la Mac

No se instaló ni actualizó ningún compilador. `brew install gcc` instala el
compilador host; no selecciona el toolchain de Arduino. Homebrew ofrece también
[`arm-none-eabi-gcc`](https://formulae.brew.sh/formula/arm-none-eabi-gcc), pero
es un toolchain distinto del Zephyr fijado por esta receta, no un reemplazo
automático. No modificar PATH ni los paquetes internos para equipararlos.

El [SDKZephyr1.0.1](https://github.com/zephyrproject-rtos/sdk-ng/releases/tag/v1.0.1)
incluye GCC14.3 y publica paquetes macOS paraAArch64, no para esta Mac Intel.
Para builds locales equivalentes conviene Linux aislado con el SDK fijado;
para el trabajo actual, el GCC14.3 ya instalado en Q reprodujo el control exacto.
