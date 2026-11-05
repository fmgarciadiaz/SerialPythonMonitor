# Arduscopio Q · documentación técnica

[Presentación del proyecto, funciones e imágenes](../README.md) ·
[Versiones y respaldos](VERSIONES.md).

| Tema | Documento |
|---|---|
| V20 estabilidad de tasas | [2 MS/s con RADIO/A0 y candidatos ADC10/12](V20_ESTABILIDAD_TASAS_20261103.md) |
| V20 recuperación frente a V19 | [Synth con un Play, detalle y vista mixta](V20_RECUPERACION_20261103.md) |
| V20 envolvente retirada | [Evidencia histórica del experimento](V20_ENVOLVENTE_20261102.md) |
| V20 pausas y raster | [Pruebas visibles y límite de dibujo](V20_GUI_PAUSAS_20261102.md) |
| V20 DX Piano | [Caché por nota: medición y validación](V20_DX_PIANO_CACHE_20261102.md) |
| V20 Synth sostenido | [Controles FM y fallos abiertos](V20_SYNTH_SOSTENIDO_20261102.md) |
| V20 TCP y servicio RADIO | [Campañas, fallo de entrega y corrección host](V20_TCP_AUDIO_SEGUIMIENTO_20261101.md) |
| V20 revisión Astra implementada | [Memoria, ACK fresco y rollback completo validados](V20_REVISION_ASTRA_IMPLEMENTADA_20261101.md) |
| V20 coste del raster y audio | [CPU/RSS, UNDERRUN y decisión de mantener worker único](V20_RASTER_RECURSOS_20261101.md) |
| V20 raster paralelo privado | [Benchmark, ensayos y límites antes de incorporar](V20_RASTER_PARALELO_20261101.md) |
| V20 ventanas y bits | [Comparación de detalle y límites de reserva](V20_VENTANAS_BITS_20261101.md) |
| V20 cierre | [Timer persistente, pruebas y límite de la mitigación](V20_CIERRE_TIMER_20261101.md) |
| V20 US y análisis | [Casos ejecutados y fallo de cierre abierto](V20_US_ANALISIS_20261101.md) |
| V20 RADIO/A0 sostenido | [60s + tres corridas120s, V20 reparada](V20_RADIO_SOSTENIDO_20261101.md) |
| V20 memoria: solapamiento y reparación | [Mapa del BSP y pruebas](V20_MEMORIA_20261101.md) |
| V20 GUI, RADIO/A0, WAV y Synth | [Pruebas visibles y artefactos](V20_GUI_RADIO_20261101.md) |
| V20 SRAM3 y tasas de 2 MS/s | [Revisión y pruebas físicas](V20_SRAM3_VALIDACION_20261031.md) |
| Uso, conexión y dependencias del monitor activo | [Guía de inicio](../monitor/v19/README.md) |
| Componentes y flujo de datos | [Arquitectura](ARQUITECTURA_V19.md) |
| Comparación visual, pruebas y límites | [Validación del host](PYSIDE_V19_COMPARACION.md) |
| Copia PCM: ensayo memcpy descartado | [Medición comparada](COPIA_PCM_V19_20261031.md) |
| Propuesta ACK de audio combinado con RF | [Diseño con Astra, sin implementar](DISENO_ACK_RF_V19_20261031.md) |
| Tiempos reales de validación, copia y bloqueo WAV | [Perfilado privado con Astra](PERFILADO_WAV_V19_20261031.md) |
| Combinaciones de validación PCM y prellenado A0 | [Dos ensayos y comparación PLAY](COMBO_VALIDACION_PRELLENADO_V19_20261031.md) |
| Validación PCM y pérdida de nodo previa al ensayo | [Candidato privado y pruebas](VALIDACION_WAV_IRQ_V19_20261031.md) |
| Salida A0, DMA y procesamiento de bloques | [Mediciones CHUNK/QUERY](DMA_SALIDA_RPC_V19_20261031.md) |
| Controles RF/RADIO/A0 con ventana visible | [Comparación sobre pareja aceptada](CONTROLES_VISIBLES_V19_20261031.md) |
| Reposición PLAY y contexto de picos | [Sondeos privados 1/2 y límites](REPOSICION_PLAY_V19_20261031.md) |
| Prellenado uniforme y picos durante PLAY | [Sondeos y combinación privada](PRELLENADO_UNIFORME_V19_20261031.md) |
| Ciclo completo del relay y picos del prellenado | [Mediciones y corrección de instrumentación](CICLO_RELAY_V19_20261031.md) |
| Combinación IPC500, O2 y READY250 | [Dos sondeos y límites](COMBO_IPC_O2_READY_V19_20261031.md) |
| IPC500: Scan/US, audio y cierre en todos los bits | [Matriz funcional y limitaciones](IPC_TRANSICIONES_V19_20261031.md) |
| Eficiencia de colas IPC y candidato privado | [Mediciones del 31/10](IPC_RADIO_V19_20261031.md) |
| Corte RADIO y pausas del receptor | [Diagnóstico e hipótesis IPC](PAUSAS_RECEPTOR_V19_20261030.md) |
| Combinaciones O2, READY y cadencia RADIO/A0 | [Ocho ensayos y restauración](COMBINACIONES_RADIO_V19_20261030.md) |
| Costos SPI y pausas del lector | [Latencias medidas y candidatos descartados](LATENCIAS_RELAY_V19_20261030.md) |
| Holgura combinada y ensayos de ráfaga/IRQ | [Resultados del 30/10](HOLGURA_RADIO_V19_20261030.md) |
| Apertura lenta y conexión bloqueada | [Diagnóstico y corrección de recursos Qt/Synth](ARRANQUE_V19_20261030.md) |
| Dibujo de detalle completo sin bloquear recepción | [Raster y validación](RASTER_TEMPORAL_V19_20261029.md) |
| Cierre aislado de flujo V(t) | [Diagnóstico y plan de captura](DIAGNOSTICO_CIERRE_FLUJO_VT_V19.md) |
| Revisión global V19 y correcciones | [Auditoría Astra](REVISION_ASTRA_V19_20261027.md), [correcciones y pruebas](CORRECCIONES_REVISION_V19_20261028.md) |
| Relay privado: build y transporte | [Ensayo y límites](RELAY_CANDIDATO_V19_20261028.md) |
| Relay privado con GUI y audio | [Propiedad del Q y controles](RELAY_GUI_V19_20261028.md) |
| Consultas y picos de cola RADIO/A0 | [Diagnóstico host privado](RADIO_QUERY_V19_20261028.md) |
| Intercalado SPI de audio y adquisición | [Revisión y medición por batch](RADIO_SPI_V19_20261028.md) |
| Preparación y validación por batch | [Costos medidos y cobertura](RADIO_SPI_COSTES_V19_20261028.md) |
| A/B de compilación de preparación SPI | [GCC12.2/14.3, memoria y pilas](PREPARE_COMPILADOR_V19_20261028.md) |
| Ensayo relay de admisión CHUNK | [Diseño y controles privados](RELAY_CHUNK_PACING_V19_20261028.md) |
| Plan y continuidad | [Plan de trabajo](../Plan%20de%20trabajo.md) |
| Ensayos de señal y tasas | [Validación histórica](VALIDACION_V18.md), [WAV](WAV_TASAS.md), [catálogo](CATALOGO_TASAS_V18_PLAN_20261025.md) |
| ADC, perfiles y formatos | [Configuración de adquisición](CONFIGURACION_ADQUISICION.md) |
| FFT y cursores | [Análisis FFT](FFT_ANALISIS.md), [cursores](CURSORES_V18.md) |
| Preparación del Q | [Guía integrada](../monitor/v19/README.md) |
| Cableado, MCU, relay y transporte | [UNO Q](UNO_Q_TECNICO.md), [transporte](TRANSPORTE_TECNICO.md) |
| Synth y MIDI | [Guía Synth](SYNTH.md) |
| Historia del proyecto | [Historia](HISTORIA.md) · [fuentes anteriores](../monitor/historico/README.md) |

Los informes fechados describen las condiciones y límites de cada campaña;
no deben leerse como afirmación de que todas las tasas funcionan bajo cualquier
carga concurrente.
