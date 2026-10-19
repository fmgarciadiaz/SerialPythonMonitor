# Plan vigente · V17 · 19/10/2026

[Estado actual](docs/ESTADO_ACTUAL_V17.md) · [Registro acumulado anterior](docs/historico/PLAN_ACUMULADO_20261019.md).

## Pendientes funcionales y de estabilidad

1. **Bode:** validar Tonos/Pulso con referencia del generador; repetir los tres métodos con cableado de circuito. Sweep CH2/CH2 ya dibuja. Validar físicamente el rango ampliado: seno 150 kHz, análisis de Pulso hasta 200 kHz según Fs. No usar CH1/antena como referencia del estímulo.
2. **RADIO/Scan:** capturar la pila GUI instrumentada cuando vuelva «GUI atrasada», especialmente ADC8/1,6 MS/s y US ADC10/1,25 MS/s. Los ensayos sin reproducción del fallo no cierran la incidencia.
3. **RADIO→A0:** completar estabilidad sostenida en los perfiles relevantes. Mantener seguimiento del underrun intermitente ADC14/851 kS/s y distinguir transporte ADC de alimentación DAC.
4. **WAV:** investigar las pausas de transporte/refill y calificar a largo plazo el candidato aislado de servicio por tramas. Ventana de dos bloques y buffer ampliado no calificaron por sí solos; no promoverlos.
5. **Etapa IV RADIO:** escucha y recepción selectiva US con antena real; mejorar confianza de banda sugerida; información de emisora si es inferible. A0 a 48 kHz requiere resolver reloj efectivo y validación; hoy no está implementado.
6. **Tasas por bits:** no aumentar ni declarar calificadas nuevas tasas sin evidencia física y restauración. Los ajustes de UI no sustituyen esa aceptación.

## Cambios incorporados recientes

- Generador: seno 150 kHz y cuadrada 200 kHz, frecuencias intermedias; host/relay/MCU instalados. [Evidencia](docs/GENERADOR_200K_V17.md).
- Bode: selectores por método y detección de inicio usando la referencia elegida. [Diagnóstico](docs/DIAGNOSTICO_BODE_SIN_CURVAS_V17.md).
- RADIO: gain hasta ×80, continuidad visual al cambiar auto gain y volumen reflejado en temporal bajo Generador Radio.
- Selector WAV no modal, entrada en `audios/`; instrumentación de errores de entrega GUI/DSP.
- Documentación separada en estado vigente e historial; Q con V17 únicamente, apps anteriores exportadas.

## Criterios de trabajo

Un propietario del Q; monitor cerrado para ensayos exclusivos. Guardar configuración y restaurar tras cada campaña. No compilar durante validación física. Separar integridad, holgura, respuesta analógica y dibujo visible. Para nuevas calificaciones usar 60 s + tres arranques de 120 s, sin convertir pruebas cortas en aceptación sostenida. UART permanece fuera de la campaña actual.
