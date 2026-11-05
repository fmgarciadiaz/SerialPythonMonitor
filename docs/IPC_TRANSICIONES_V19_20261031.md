# Ajuste IPC500: transiciones y perfiles · 31/10/2026

Se completaron ocho intentos privados con la pareja aceptada y el ajuste
`empty_backoff(500)` del harness. No se modificaron runtime, firmware ni relay,
ni se habilitaron tasas públicas. Cada intento conservó su informe y restauró
el snapshot original. No hubo campañas de aceptación de holgura de 120 s.

## Matriz

| Perfil | Scan | Resultado funcional | Exposición periódica | Margen MCU / pico |
|---|---|---|---:|---|
| 10 bits · 1,36 MHz | US | PASS | 100 % | 6.55 % / 4 |
| 8 bits · 1,86 MHz | US | PASS | 9 % | 10.30 % / 6 |
| 12 bits · 1,10 MHz · 550 kHz | US | FAIL; ver explicación | 100 % | Sin PLAY |
| 12 bits · 1,10 MHz · 530 kHz | US | PASS | 100 % | 7.51 % / 2 |
| 14 bits · 1 MHz | US | PASS | 100 % | 9.75 % / 2 |
| 16 bits dual · 76,226 kHz | US | PASS | 100 % | 80.40 % / 1 |
| 16 bits CH1 · 150,943 kHz | US | FAIL; ver explicación | 100 % | 70.40 % / 1 |
| 16 bits CH1 · 150,943 kHz | normal | PASS | 36 % | 70.41 % / 1 |

Cada caso válido incluyó RADIO40k/A0, Stop/reinicio de A0, resintonía,
Scan durante reproducción y reanudación, WAV, Synth de 20 voces y cierre.
El tramo final de WAV/Synth usó adquisición de 40 kHz; no se debe atribuir
esa parte a la tasa máxima inicial. El audio RADIO retenido fue de al menos
20 s en los casos válidos, además de las pausas deliberadas de transición.

La exposición se midió con observaciones periódicas Cocoa. Las corridas de
8 bits y 16 bits CH1 normal fueron funcionales pero no acreditan FPS visibles
sostenidos: la ventana estuvo mayormente oculta. No convertir temporizadores
o frames preparados en una afirmación de dibujo visible.

## Dos intentos fallidos preservados

- **12 bits, 550 kHz:** a Fs=1.103.448 S/s y banda de 8 kHz, el borde superior
  cruza Nyquist. RADIO rechazó la configuración, A0 no arrancó y las
  aserciones de Scan/reproducción fallaron. Fue un error de selección del
  harness. Se repitió a 530 kHz sin errores; el informe inicial sigue intacto.
- **16 bits CH1 con US:** `scan_profiles(Configuration(16,150943))` devuelve
  una lista vacía. Sólo existe un perfil base CH1 elegible para ese selector;
  las otras tasas CH1 son perfiles de catálogo excluidos como auxiliares.
  No se inventaron auxiliares ni se ampliaron criterios de aceptación. El
  intento no confirmó Scan US/reanudación; cierre y restauración pasaron.
  Se repitió con Scan normal y pasó toda la secuencia. US en 16 bits dual
  sí completó con los auxiliares actualmente disponibles.

Estos fallos no se borraron ni se reclasificaron como PASS. La limitación
US de 16 bits CH1 sigue pendiente; la ausencia de auxiliares elegibles existe
con independencia del ajuste de sondeo.

## Verificación y límites

40 tests dirigidos PASS: colas reales FIFO tras pasar de vacío a disponible,
argumentos/lecturas bloqueantes, restauración ante excepciones, instrumentación
acotada, contadores, y un receptor real creado con spawn bajo el ajuste privado.
Este último verificó entrega PCM, créditos RF y cierre por cancelación. También
pasó la suite existente de ReceiverProcess, incluyendo sobrecarga y terminal.

La eficiencia medida antes (menos llamadas/CPU dentro de Queue.get) sigue
siendo evidencia del host. Los picos y márgenes de esta tabla mantienen
separada la holgura MCU; no justifican tasas superiores ni promoción del
candidato como solución del corte intermitente. El ajuste continúa privado.

Restauración final independiente: `final_verification.json`, 10 s de
continuidad, snapshot e identidad aceptados iguales. V17/V18 intactas.

## Siguiente bloque

Combinar el backoff privado con la preparación O2 y el relay READY acotado
ya compilados, en un sondeo aislado de 20 s a ADC8/1.860.465 con FFT/RADIO/A0.
Son candidatos conocidos, pero su combinación nueva requiere evidencia propia.
Mantener los criterios: media ≥10 %, pico acumulado <4 y slack positivo,
integridad, dibujo visible y restauración. Si no pasa, no extenderlo como
campaña de aceptación ni incorporar tasas. Antes de producción, reemplazar
el parche global de Queue del experimento por sondeo explícito de las entradas
del receptor y volver a validar ese código final.

[Resumen de ocho intentos](../diagnosticos/resultados_v19/ipc500_functional_20261031/summary.json)
· [Medición IPC previa](IPC_RADIO_V19_20261031.md).
