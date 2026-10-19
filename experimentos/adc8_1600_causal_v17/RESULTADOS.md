# Congestión capturada a 1,6000 MS/s

Una corrida diagnóstica de120s a100ticks/N3456/CPU2/performance/SPI40, con productor original1ms y preparación112/2s. 191.889.216 muestras íntegras, margen12,014%,cola pico4,slackmínimo822,419us. Esto es diagnóstico instrumentado, no aceptación.

El primer pico4 capturado pertenece a la ventana medida: nodo44574/producidos44577, antes del estado final del receptor. La cola se acumuló durante varios nodos consecutivos, no por un único bloqueo extremo. En el contexto previo, el envío MCU anterior subió de1801us a2435/2720/2802/3020/2818/2756us, frente a2160us de presupuesto por nodo.

En ese tramo, ioctlSPI frecuentemente pasó de~280us a350–390us; accept de~20us a60–110us y send de~40–70us a130–295us. READY fue habitualmente corto, con algunas esperas adicionales. Varias etapas Linux se ralentizaron a la vez. No basta atribuir el fallo aTCP, READY,ADC o una sola syscall. Los tiempos son transcurridos inclusivos y no aíslan CPU, IRQ ni planificación.

Medias del epoch100 completo hasta parada: READY166,3us, SPI281,2us, validación6,15us, recv2,65us, accept20,79us, send53,88us. Agregados incluyen preparación/asentamiento y tramo posterior al cierre del receptor; no son exclusivamente120s. La correlación usa secuencias/metadatos, sin restar relojes MCU/Linux. La copia del anillo ocurre después de observar el pico; el intervalo entre iteraciones posterior incluye esa perturbación.

Siguiente ensayo fundamentado: inventariar actividad IRQ por núcleo durante las ráfagas y comparar una única afinidad de IRQ con restauración exacta, manteniendo prioridad, governor, formato y nodo. Las observaciones actuales no prueban la causa de la ralentización simultánea. No modificarCRC ni aumentar slots para aprobar.

Q restaurado y verificado: firmware/relay/entorno/configuración/generador originales, governor schedutil, reloj33,333MHz y continuidad10s. Perfil106/1,5094MS/s intacto. Ver closure_audit.json, report.json, causal_relay.log y analysis.json.
