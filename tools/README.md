# Arduscopio Q · herramientas del proyecto

La aplicación activa se inicia con `python -m monitor.v19 --gui` o `./tools/run_v19.sh`.
Las herramientas de esta carpeta conservan rutas estables porque también
se importan desde pruebas y campañas.

| Uso | Entrada |
|---|---|
| Abrir Arduscopio Q | `run_v19.sh` o `python -m monitor.v19 --gui` |
| Regresión offline | `python -m monitor.v19 --self-test` |
| Comparación visual V18/PySide | `compare_v19_visual.py` |
| Verificación GUI y RADIO/A0 | `gui_live_smoke_v19.py`, `probe_radio_rate_v19.py` |
| Matriz de tasas V19 instalada | `validate_v19.py --serial NUMERO_ADB --output RUTA --run`; usa sólo V19 |
| Build privado del relay y restauración | `build_relay_candidate_v19.py --serial NUMERO_ADB --output RUTA_NUEVA`; detiene la pareja antes de compilar |
| Sondeo de transporte con relay candidato | `probe_relay_transport_v19.py --serial NUMERO_ADB --build-report RUTA/report.json --output RUTA_NUEVA --seconds 60`; carga temporal y rollback exacto |
| GUI/RADIO/A0 con relay privado | `probe_relay_gui_v19.py --serial NUMERO_ADB --build-report RUTA/report.json --output RUTA_NUEVA --hold 60`; conexión exacta, lock del receptor hijo y restauración |
| Métricas RADIO/A0 con pareja aceptada | `gui_accepted_metrics_v19.py --metrics-output RUTA/wire_metrics.json --serial NUMERO_ADB --output RUTA/gui.json`; observador opt-in con restauración. Flags privados excluyentes: `--private-ack-refresh`, `--private-ack-sham`, `--private-ack-burst2`; [alcance y límites](../docs/RADIO_QUERY_V19_20261028.md) |
| Resumir costos SPI existentes | `python tools/summarize_spi_costs_v19.py RUTA/wire_metrics.json`; separa batch/nodo, cobertura y fronteras; [método](../docs/RADIO_SPI_COSTES_V19_20261028.md) |
| A/B de compilador Os/O2 sin desplegar | `compare_prepare_compiler_v19.py --output RUTA_NUEVA` (Mac) o `compare_prepare_compiler_q_v19.py --serial NUMERO_ADB --output RUTA_NUEVA` (Q detenido con respaldo/restauración); [versiones reales de GCC y límites](../docs/PREPARE_COMPILADOR_V19_20261028.md) |
| Verificación y Preparar Q | integrado en `monitor/v19/q_support`; verifica la pareja instalada y usa respaldo/recuperación para actualizar |
| Estado de parejas App/relay del Q | `python tools/unoq.py inventory --version v19` (sólo lectura; reporta V17, V18 y V19) |
| Compilar juntos firmware STM32 + relay V19 | `python tools/unoq.py compile-pair --version v19 --artifacts RUTA` (solo artefactos locales; no instala ni activa) |
| Ensayo RAM V19 sin USART3 | Agregar `--omit-serial3` a `compile-pair`; override aislado, experimental y pendiente de validación física |
| Compilar lector de margen de pilas V19 | `compile-pair --version v19 --artifacts RUTA --stack-diagnostic`; variante estándar, SCP1 tipo 21, sólo artefactos |
| Compilar margen de pilas con ahorro UART | Agregar `--omit-serial3` a `--stack-diagnostic`; variante temporal USART3-off, sólo artefactos |
| Capturar margen de pilas | `python tools/read_stack_diag_v19.py --serial NUMERO_ADB --duration 120 --output RUTA`; configura temporalmente el perfil nativo, restaura el original y requiere conexión exclusiva |
| Administración del Q | `unoq.py` (V19 predeterminado; usar `--version` explícito para históricos) |
| Calibración Bode | `calibrate_bode.py`, `calibrate_bode_matrix.py` |
| Capturas de presentación, sin Q | `capture_landing_v18.py` (generador sintético heredado) |

El inventario del 27/10/2026 confirmó Scope V19, `scope-v19-main-1` y
`serialmonitor-usb-stream-v19` como la única pareja activa. Los scripts que
conservan nombres de la pareja anterior se mantienen por
compatibilidad; no indican que el host activo use ese monitor. Las pruebas
físicas requieren un único propietario del Q y restauración verificada. Las
capturas animadas son demos sintéticas y no constituyen medición de rendimiento.

`run_stack_diag_v19.py` y `probe_v19_normal_pair.py` son herramientas históricas
retiradas: sus entradas operativas rechazan la ejecución porque restauraban
V17. Se conservan los helpers para leer y reproducir informes anteriores.

[Guía del monitor](../monitor/v19/README.md) · [Versiones](../docs/VERSIONES.md)

### Perfilado WAV privado de V19

`compare_wav_timing_q_v19.py` compila el control aceptado y el diagnóstico
`wav-chunk-cycles-v1`, con parada, respaldo y restauración verificada.
`wav_timing_candidate_v19.py` define la transformación exacta; el decoder está en
`wav_timing_metrics_v19.py`. Requiere binding privado: no activar la marca del
protocolo sobre una conexión de producción. Sus campos40/44 reemplazan
prepare/check sólo en DATA20; invalidan métricas ordinarias del relay y cualquier
aceptación de rendimiento. [Contrato y resultados](../docs/PERFILADO_WAV_V19_20261031.md).

`compare_wav_copy_q_v19.py` compila control, copia PCM con memcpy y su variante
instrumentada. Los informes seleccionados verifican el hash de su informe padre;
no relajan las reglas de conexión de producción ni permiten fuentes arbitrarias.
La copia mantiene validación, caché, descriptores y barrera de publicación.

### V20: ensayo privado de monitor y audio

`probe_v20_gui.py --serial ... --proof .../sram3_sustained_integrity_20261031/report.json
--output <directorio nuevo> --hold 60 --wav --fm --voices 20` verifica la pareja
V20 medida y entrega el lock al receptor hijo. `private_v20_pair.py` comprueba
fuentes, BIN, relay, placa y hashes del informe; nunca cambia el recibo público.
`gui_private_v20.py` usa exclusivamente el monitor V20 y guarda medidas de
exposición/paint y progreso. La transacción restablece V19 y verifica10s de
integridad al terminar. No ejecutar otra instancia durante un ensayo.

[Resultados y límites](../docs/V20_GUI_RADIO_20261101.md). Los campos opcionales
del smoke son válidos como pruebas de WAV/FM sólo cuando esos flags se pidieron.
El screen privado de reserva V20 no equivale a aceptación pública.

### V20: reparación privada del mapa SRAM3

`probe_v20_sram3.py --install-memory-fix` respalda la app candidata completa antes de reemplazar únicamente `acquisition.h` y añadir `acquisition_memory.h`. Verifica el BSP fijado por hashes, mide con el receptor V20 y restaura V19. Si falla el sondeo, restaura además las fuentes/caché anteriores de V20. No habilita tasas públicas. [Auditoría y límites](../docs/V20_MEMORIA_20261101.md).

El lanzador `probe_v20_gui.py` permite `--us` (Scan antes de A0), `--us --scan-during-a0` (pausa/Scan/reanudación) y `--analysis-mode vt|fft|heatmap|bode --bits B --rate R` (sin audio). US exige tres capturas y restauración explícita; heatmap dual exige datos en ambos paneles. Bode es sólo dibujo con curvas sintéticas. No combinar análisis crudo con audio/Scan. Se activa PYTHONFAULTHANDLER para conservar caídas nativas; una salida sin gui.json es un fallo, aunque la restauración administrativa pase. Ver [resultados y caída intermitente](../docs/V20_US_ANALISIS_20261101.md).

`gui_private_v20.py` instala la traza privada `qt_single_shot.jsonl`: registra la pila Python antes de entrar en la llamada nativa y su retorno. Se usa sólo en ensayos privados y puede alterar timing. Los informes nuevos guardan hashes del monitor y las herramientas; no convertir ausencia de caída en prueba de causa raíz. [Mitigación del cierre](../docs/V20_CIERRE_TIMER_20261101.md).

Para V(t), `probe_v20_gui.py --analysis-mode vt --window-seconds 2 --detail-percent 100` exige ventana y detalle realmente aplicados. Los informes separan función de `visible_gui_ok` (incluye piso de pintura); un caso puede adquirir/dibujar/cerrar correctamente y fallar rendimiento. La reserva usa queue_slots del perfil, no la capacidad máxima del arena ADC8. [Resultados](../docs/V20_VENTANAS_BITS_20261101.md).

Experimento privado: `probe_v20_gui.py --window-seconds 2 --detail-percent 100 --raster-workers 4` usa franjas sólo en el receptor GUI privado, sin cambiar el monitor por defecto. Con `--analysis-mode vt` no reproduce audio; sin esa opción prueba RADIO/A0 en V(t). Suave y X no ordenado/no finito usan el worker original. Requiere revisar coste y equivalencia antes de incorporar. [Resultados](../docs/V20_RASTER_PARALELO_20261101.md).

El ensayo privado acepta `--raster-nice 10` sólo con franjas2/4; baja prioridad exclusivamente dentro de hijos gráficos propios y registra su valor real. No cambia el producto normal. El observador `process_resources_v20.py` usa psutil del entorno habitual para GUI+descendientes; CPU muestreada y RSS sumada tienen límites explícitos. [Fallo de audio y coste medido: no incorporar paralelo por defecto](../docs/V20_RASTER_RECURSOS_20261101.md).

V20: `probe_v20_sram3.py --install-storage-fix --baseline-proof <informe restaurado> --storage-cycle` aplica sólo el parche acotado a acquisition/Storage y verifica16→4CH1→dual→16. Respalda fuentes/cache antes de escribir y compara inventario completo al rollback. `rehearse_v20_cache_restore.py` ensaya restauración del mismo candidato detenido. `probe_v20_gui.py --raw-ack-latency` captura el receptor V20 real y etapas existentes; requiere escenario con audio y ACK efectivamente observados. [Revisión y límites](../docs/V20_REVISION_ASTRA_IMPLEMENTADA_20261101.md).
