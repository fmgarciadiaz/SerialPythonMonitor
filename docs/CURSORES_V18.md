# Cursores A y B · V18

La primera solapa **Cursor**, antes de Trigger, Filtro y Radio, reúne los controles.
El LED junto a **A** y a **B** apaga o enciende su cursor de forma
independiente. Los iconos de las cuatro solapas siguen los recursos SVG del monitor.

1. Elegir la fuente de A o B y encenderlo. Mover el mouse dentro del gráfico
   de esa fuente: la línea del gráfico lleva sólo la etiqueta A o B. Las lecturas están en
   una única pantalla al pie de esta solapa: filas A, B y B−A,
   diferenciadas por color y con las lecturas alineadas. Las diferencias son B menos A.
2. Hacer clic para fijar. Clic en su línea/etiqueta lo selecciona
   otra vez. **Esc** cancela el movimiento y recupera la posición previa.
3. El selector **Seguir / Libre** a la derecha del canal es independiente para cada cursor.
   **Seguir** busca la muestra/bin visible más cercano, sin usar la
   reducción de puntos de dibujo. **Libre** permite marcar una posición
   arbitraria. La posición se controla exclusivamente con el mouse; las coordenadas
   se leen en los pantalla de la solapa Cursor.
4. **Vincular A/B** conserva el desplazamiento horizontal entre A y B al
   mover uno. **Centrar** los devuelve a la zona visible; Cada LED apaga su cursor.

| Análisis | Fuente | Lecturas |
| --- | --- | --- |
| V(t) | CH1, CH2, FILTER o RADIO | Tiempo relativo del cuadro en µs y voltaje; Δt, ΔV y 1/\|Δt\| |
| FFT | Canal mostrado; ganancia/fase en Transfer | Frecuencia y ordenada con las unidades del gráfico; Δf y ΔY |
| Heatmap | Canal del panel | Tiempo relativo en s, frecuencia en Hz y nivel de la celda; Δt, Δf y ΔNivel |
| Bode | Ganancia o Fase de la medición actual | Frecuencia y dB o grados; Δf, y ΔY sólo entre unidades iguales |

En FFT y heatmap, seleccionar una fuente que no se muestra la asigna al panel
correspondiente al activar. CH2 no se habilita en perfiles de un
canal. Bode usa el par referencia/respuesta configurado para ese barrido, no
inventa voltajes a partir de la transferencia. La lectura de Bode corresponde
a la medición actual, no a las curvas históricas superpuestas.

Los cursores funcionan también sobre el cuadro detenido. No interpolan a través
de huecos ni convierten ausencia de muestras en cero. Las escalas logarítmicas
se leen en Hz físicos. Cada análisis guarda su propio juego: posiciones, fuentes, Seguir/Libre,
encendidos y vínculo A/B se recuperan al volver. Las posiciones son relativas a los ejes del cuadro,
no marcadores absolutos de una grabación. 1/|Δt| es el inverso del intervalo
marcado: representa frecuencia de una señal si el intervalo elegido es su período.

Referencia funcional: [Tektronix TDS5000B, Waveform/Screen Cursors](https://download.tek.com/manual/PHP023702.pdf).
La implementación agrega fuentes independientes, coordenadas, diferencias y
posicionamiento sobre el gráfico; no modifica adquisición, firmware ni relay.
