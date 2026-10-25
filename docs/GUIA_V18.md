# Monitor V18: uso y límites

V18 reúne osciloscopio, FFT, heatmap, Bode, FILTER, RADIO, generador, WAV y
Synth de veinte voces. [Presentación e imágenes](../README.md).

## Inicio y Preparar Q

Ejecutar `python -m monitor.v18 --gui`. Seleccionar el Q por USB.
«Preparar Q» verifica la pareja aceptada y diez segundos de adquisición. Si ya
coincide, no vuelve a instalarla. Puede recuperar una pareja aceptada detenida
y actualizar una instalación existente mediante respaldo completo y rollback.
No actúa mientras el monitor adquiere ni reemplaza otras apps activas.
Una placa sin Scope V18 requiere instalación inicial; el botón lo indica y no
sobrescribe aplicaciones desconocidas. «Conectar» sólo abre la pareja instalada.

El soporte del botón vive en `monitor/v18/q_support`, con recibo, binarios y
verificadores propios. No usa herramientas ni módulos de versiones anteriores.
Su firmware fuente está en la pareja `arduino/v18`.

## Adquisición y análisis

CH1 utiliza A2; dual utiliza A2/A3. ADC8 CH1 alcanza 1.818.181,818 S/s reales
(88 ticks), con IPC compacto automático. Los máximos públicos restantes son
10 bits: 1,25 MS/s; 12 bits: 1,066667 MS/s; 14 bits: 851,064 kS/s.
ADC16 por oversampling alcanza 76,227 kS/s por canal en dual. Las tasas son
muestras, no ancho de banda analógico ni precisión efectiva garantizada.
V(t) conserva trigger/SINGLE; FFT y heatmap analizan los canales seleccionados.
Bode compara referencia y respuesta: conectar la referencia real del circuito.

## RADIO y FILTER

La sintonía se limita según Fs. US extiende el dial y calcula el alias; su tramo
extendido tiene color distinto. Scan pausa las salidas necesarias y restituye
la configuración. El ancho AM inicial es 8 kHz. El gain manual/auto alcanza
80×; el ajuste automático es gradual salvo clipping extremo. Valores iniciales:
gain 10× y volumen A0 60%. FILTER tiene su propia entrada, band reject y presets.
Generador Radio puede tomar RADIO o FILTER y mantiene detector de realimentación.

## Generador, WAV y Synth

Salida A0 nominal de 0–3,3 V, con amplitud y offset dentro de ese rango.
Seno hasta 150 kHz y cuadrada hasta 200 kHz; frecuencias intermedias disponibles.
WAV reproduce archivos de entrada; los audios de ejemplo están en `audios/`.
Las grabaciones nuevas del monitor se guardan en `capturas/v18/`.
Synth admite veinte voces, MIDI, FM y modelos físicos.

## Evidencia y estabilidad

[Validación V18](VALIDACION_V18.md) distingue pruebas locales, transporte,
ensayos conjuntos, dibujo y restauración. Los últimos tres recorridos instalados
de 120 s aprobaron RADIO/A0, Scan, WAV y Synth20 a ADC8/1,818 MS/s. Los cortes
anteriores permanecen registrados; no es una garantía universal o analógica.
[Organización y limpieza](ORGANIZACION_V18.md).

## Cursores

La solapa Cursor permite medir con A/B en V(t), FFT, heatmap y Bode.
Ver [controles, unidades y uso con mouse](CURSORES_V18.md).
