# ADC14 a 851,063 kS/s con RADIO y A0

La mejora quedó instalada el 18/10/2026. Conserva la tasa efectiva de **851.063,83 muestras/s** (160 MHz / 188 ticks), con RADIO y A0 simultáneos. El límite temporal de 599,25 kS/s ya no bloquea esta combinación.

## Qué cambió

El perfil CH1 de 14 bits usa nodos de **5.952 muestras**, en lugar de 1.984. Cada nodo representa 6,9936 ms de adquisición, frente a 2,3312 ms. Esto aumenta la tolerancia a demoras sin reducir la tasa. Timestamp DMA y scratch ocupan 49.600 de los 65.536 bytes disponibles; ADC ocupa 23.808 de 32.768 bytes.

El relay aplica la política de CPU y envío a los perfiles exactos de ADC14. El host selecciona `HighRateRadioDacSource` solamente para **14 bits / 851063**: ráfaga máxima de 16 bloques, intervalo de 6 ms y ventana de 30 créditos, siempre limitada por los huecos confirmados. La correlación del detector de loops se calcula fuera del bloqueo de la fuente de audio; su historial de salida se copia bajo un bloqueo breve.

Los demás perfiles conservan `RadioDacSource` y su ráfaga de 8 bloques. No se relajaron CRC, continuidad ni contadores de pérdidas. El registro del perfil cambia de geometría, sin añadir una tasa nueva. MCU y relay conservan la geometría anterior para compatibilidad, pero el host selecciona N5952 para la tasa objetivo.

## Calificación conjunta

Informe: `experimentos/radio14_nodes_v17/probe_20261018_131346/report.json`. Campaña completa y restaurada, con RADIO y A0 a 40 kHz:

| Prueba | Margen medio de envío | Cola pico |
|---|---:|---:|
| 60 s | 19,48% | 2 |
| 120 s, repetición 1 | 19,39% | 2 |
| 120 s, repetición 2 | 19,41% | 2 |
| 120 s, repetición 3 | 19,41% | 3 |

Todas pasaron sin pérdidas, errores fatales ni underrun de A0 y con slack positivo. Cumplen el criterio de holgura conjunta: margen ≥10%, cola <4 y slack positivo. La calificación corresponde a esta configuración medida; no certifica calidad analógica, escucha prolongada ni FPS visibles.

## Instalación final

Informe: `experimentos/radio14_nodes_v17/installation_20261018_133339/report.json`: `ok=true`, `installed=true`, `restored=true`. Pasaron 36 pruebas locales y las siguientes comprobaciones físicas de 60 s:

| Adquisición | Entrada de A0 | Salida A0 | Resultado |
|---|---|---|---|
| ADC14 / 833,333 kS/s | RADIO | 40 kHz | Correcto |
| ADC14 / 851,063 kS/s | RADIO | 40 kHz | Correcto |
| ADC8 / 1.600 kS/s | RADIO | 40 kHz | Correcto |
| ADC10 / 1.250 kS/s | RADIO | 40 kHz | Correcto |
| ADC12 / 1.066,667 kS/s | RADIO | 40 kHz | Correcto |
| ADC14 / 851,063 kS/s | FILTER | 20 kHz | Correcto |

La repetición final de ADC14/851063 a 40 kHz dio margen 19,23% y cola pico 2. FILTER → A0 a 20 kHz dio 21,55% y cola pico 2. ADC8 pasó continuidad, pero su cola pico 6 sigue sin cumplir holgura completa; no se extiende la aceptación de ADC14 a ese perfil.

Firmware instalado: `f3cab6f48a0d6b45fb7c1329ceee7e485f6cf32baadac1c9578533d1f5090bf5`. Se restauraron los ajustes previos al ensayo: ADC14/599250, generador apagado. Recuperación final de 10 s: 5.989.884 muestras sin pérdidas ni errores fatales. Q quedó libre. Abrir de nuevo V17 y seleccionar 851,063 kS/s para usar la mejora.

## Antecedentes conservados

La sesión original cerró el relay por una pérdida de nodo a N1984, con CRC correcto. El candidato de CPU y envío solamente falló por underrun de A0 en la tercera repetición. El siguiente candidato de reposición, todavía con N1984, volvió a perder un nodo. Ambos se restauraron y no se incorporaron.

El primer piloto N5952 no midió: la interfaz de diagnóstico rechazó el perfil privado; se corrigió únicamente ese acceso y se restauró Q. La primera instalación con reposición nueva para todos los bits se revirtió por un underrun en ADC8. La instalación final aplica esa ruta sólo a ADC14/851063 y pasó la matriz descrita arriba. Los respaldos, fuentes congeladas e informes permanecen junto a cada campaña.
