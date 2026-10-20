# Plan vigente · V17 · 19/10/2026

[Estado actual](docs/ESTADO_ACTUAL_V17.md) · [Registro acumulado anterior](docs/historico/PLAN_ACUMULADO_20261019.md).

## Pendientes funcionales y de estabilidad

Prioridad del usuario: [muestras perdidas RADIO/WAV, clic de sintonía y clics Sweep](docs/ESTABILIDAD_RADIO_WAV_CLICS_V17.md). Landing restaurada y regla permanente en `AGENTS.md`.

1. **Bode:** corregido el orden de confirmación respecto a muestras pendientes. Tonos CH2/CH2 pasó 20–1000 Hz con asentamiento normal de 200 ms; Sweep también dibuja. Pulso sigue sin detectar estímulo (ensayos 1 y 10 ms). Repetir con cableado de circuito y validar el resto del rango. Validar físicamente el rango ampliado: seno 150 kHz, análisis de Pulso hasta 200 kHz según Fs. No usar CH1/antena como referencia del estímulo.
2. **RADIO/Scan:** capturar la pila GUI instrumentada cuando vuelva «GUI atrasada», especialmente ADC8/1,6 MS/s y US ADC10/1,25 MS/s. Los ensayos sin reproducción del fallo no cierran la incidencia.
3. **RADIO→A0:** nuevo underrun real ADC8/1,6 MS/s con 11 resintonías; completar estabilidad sostenida en los perfiles relevantes. [Diagnóstico e instrumentación](docs/DIAGNOSTICO_RADIO_A0_ADC8_1600_V17.md). Mantener seguimiento del underrun intermitente ADC14/851 kS/s y distinguir transporte ADC de alimentación DAC.
4. **WAV:** incorporada la combinación de dos chunks PCM en vuelo, capacidad anunciada hasta 30 y servicio por tramas tras 3×120 s ADC16/76226→50 kHz. Seek/Stop/EOF/replay pasaron. ADC14/100000→50 kHz pasó 60 s, con fallo Qt/SIP posterior al finalizar Python. Mantener abiertas otras combinaciones y el cierre Qt. Las variantes parciales que fallaron siguen descartadas. [Evidencia](docs/ESTABILIDAD_RADIO_WAV_CLICS_V17.md).
5. **Etapa IV RADIO:** escucha y recepción selectiva US con antena real; mejorar confianza de banda sugerida; información de emisora si es inferible. A0 a 48 kHz requiere resolver reloj efectivo y validación; hoy no está implementado.
6. **Tasas por bits:** no aumentar ni declarar calificadas nuevas tasas sin evidencia física y restauración. Los ajustes de UI no sustituyen esa aceptación.

7. **Clics:** transición de emisoras suavizada y conservación explícita del tiempo de audio obsoleto dentro de la sesión; verificar escucha real. Sweep/Chirp tienen saltos medidos en inicio/fin; preparar un candidato aislado de firmware que no altere Bode ni los límites del generador.

## Cambios incorporados recientes

- Generador: seno 150 kHz y cuadrada 200 kHz, frecuencias intermedias; host/relay/MCU instalados. [Evidencia](docs/GENERADOR_200K_V17.md).
- Bode: selectores por método, detección de inicio usando la referencia elegida y confirmación del generador ordenada detrás de las muestras ya recibidas. [Diagnóstico](docs/DIAGNOSTICO_BODE_SIN_CURVAS_V17.md).
- RADIO: gain hasta ×80, continuidad visual al cambiar auto gain y volumen reflejado en temporal bajo Generador Radio.
- Selector WAV no modal, entrada en `audios/`; instrumentación de errores de entrega GUI/DSP y entrega PCM calificada con dos créditos.
- Suavizado de sintonía Radio A0 y compensación registrada de audio de sintonía anterior descartado.
- Landing recuperada con badges, imágenes y presentación de módulos; regla permanente en `AGENTS.md`.
- Documentación separada en estado vigente e historial; Q con V17 únicamente, apps anteriores exportadas.

## Criterios de trabajo

Un propietario del Q; monitor cerrado para ensayos exclusivos. Guardar configuración y restaurar tras cada campaña. No compilar durante validación física. Separar integridad, holgura, respuesta analógica y dibujo visible. Para nuevas calificaciones usar 60 s + tres arranques de 120 s, sin convertir pruebas cortas en aceptación sostenida. UART permanece fuera de la campaña actual.
