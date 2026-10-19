# RADIO: antena CH1 y US — 18/10/2026

Captura pasiva real en CH1, sin generador ni A0: 5 s de adquisición por perfil
ADC8/1,6 MS/s, ADC10/1,25 MS/s y ADC14/851063. Se guardaron aproximadamente
786 mil muestras iniciales por perfil y tres ventanas Scan. No hubo dropped,
fatal ni códigos saturados. Esto no califica estabilidad prolongada ni escucha.

Evidencia: `diagnosticos/resultados_v17/antena_am/20261018_190744/report.json`,
NPZ originales y `demodulation.json`; WAV cortos normalizados para inspección.
Se restauró ADC12/1066666, generador OFF; recuperación 10 s, 10664640 muestras
sin pérdidas/fatales. Firmware f3cab6f4 sin cambios.

Un candidato en 710,44 kHz con FS1,6 MHz aparece cerca de 539,56 kHz con
FS1,25 MHz y 140,62 kHz con FS851063, compatible con la misma señal y su alias.
Otro candidato 630,385 kHz corresponde aproximadamente a 619,614 y220,679 kHz.
Hay interferencias fuertes cerca de 8,26/16,27 kHz y otros picos: Scan detecta
candidatos espectrales, no confirma emisoras ni identifica sus nombres.

## US

Botón US, inicialmente OFF, limitado explícitamente a zona Nyquist2.
RF entre FS/2+B/2 y FS−B/2, con extremos estrictos; alias=FS−RF.
Dial muestra RF; DSP usa alias; estado muestra ambas frecuencias; FFT Radio
mantiene eje de alias y Scan convierte candidatos a RF de la zona seleccionada.
Al cambiar US se invalidan candidatos y continuidad DSP. El rango del dial se
recalcula como en recepción directa y recorta la selección fuera de rango.

Ejemplo FS1,6MHz: RF1MHz → alias600kHz. La misma captura no permite distinguir
RF600kHz de RF1MHz. US no aumenta el ancho de banda analógico ni elimina señales
de otras zonas: la recepción selectiva requiere un filtro de entrada adecuado.
Inversión espectral zona2 no cambia AM por envolvente; no generalizar a SSB/IQ.

## Propuestas de Astra y próximos pasos

1. Límites compartidos completos para evitar aceptar f≤B/2: corregido en Scan,
   procesamiento, dial y validación A0, junto con implementación US zona2.
2. Contrastar candidatos a dos FS y añadir confianza/persistencia entre Scans;
   mostrar RF/alias sin asignar identidad física automáticamente.
3. Mejorar sugerencia de banda: ruido externo robusto, energía integrada por
   subbandas y confianza. El estimador actual puede devolver indeterminado con
   voz/música ancha o vecinos; mantener aplicación manual. No está resuelto.
4. Ensayo de escucha con capturas más largas y filtro de entrada, luego comparar
   recepción directa/US de la misma emisora. WAV actuales son demasiado cortos
   para aceptación de inteligibilidad.
5. Evaluar blanker para impulsos y demodulación síncrona con medición comparativa.
   Mantener A0/48k y estabilidad máxima ADC8 como trabajos separados pendientes.


## Dial combinado y Scan multitasa — cierre posterior 18/10

US ON ahora incluye zona directa y zona2; mínimo según banda, máximo FS−B/2.
Se rechazan canales que cruzan Nyquist. US OFF mantiene mapeo1:1 y conserva
candidatos alias tal como aparecen. Arco superior azul suave.

Scan US usa tres perfiles realmente admitidos para los mismos bits/canales,
una captura fresca continua de3×65536 porperfil tras descartar transitorios.
Busca hipótesis directa y FSoriginal−alias y contrasta plegado modular contra
las otras tasas reales. Tolerancia dosbins de la FS mayor más100ppm de RF;
no equivale a calibración del reloj. Candidatos muestran RF estimada/ambigua,
con número de perfiles concordantes. No se identifican emisoras por nombre.

No arranca con A0 activo, registro o Bode. Se pausa RADIO; al terminar restaura
configuración original, sintonía y Play previo. Pulsar Scan durante la campaña
solicita cancelación con restauración. Cerrar espera restauración; desconexión
física puede impedirla y se informa. Sin cambios de firmware.

Prueba GUI/Q real: `diagnosticos/resultados_v17/us_multiscan_20261018_193808/report.json`.
FS1.6M→1.40350877M→1.11888112M→1.6M;18hipótesis, incluyendo870.532kHz
porencimadeNyquist. No prueba identidad/escucha. Restauración deScan yfrecuencia
correctas. Restauraciónexternafinal ADC12/1066666 genOFF, recuperación10662336
muestras10s sindropped/fatal,firmwaref3cab6f4inalterado. Qlibre.

Primerintento193738noinicióporselecciónauxiliarinválida;restauradocorrectamente.
Se corrigió selecciónapartirdelregistrodeperfiles; sólo193808eséxitoGUI.
