# Filtros digitales · V16

**Filtro digital** está en una solapa junto a **Trigger**, en la columna derecha. Fuente elige CH1/A2 o CH2/A3; FILTER se calcula en Python, sin modificar entradas, firmware o DAC.

- Paso bajo, paso alto, paso banda y Directo (bypass).
- Butterworth de orden 1 a 8. En banda, el orden indicado es el del prototipo: el filtro completo tiene el doble.
- RC: sección digital de primer orden mediante transformación bilineal con prewarping; banda encadena paso alto y paso bajo. La respuesta de banda RC no equivale a un Butterworth.
- Low y High, con diales logarítmicos planos de 54 px y valores no editables debajo. Band pass habilita ambos; Low pass usa sólo High y High pass usa sólo Low. Directo deshabilita ambos. Los límites siguen la tasa confirmada y quedan por debajo de Nyquist.

El filtro usa `sosfilt` con estado conservado entre bloques. La inicialización usa el equilibrio de la primera muestra para evitar un salto artificial ante un nivel DC constante. Se reinicia al cambiar fuente, parámetros, tasa o adquisición; los cambios de filtro vacían el historial visible. Es causal: conserva su fase y retardo, no usa filtrado hacia atrás ni compensa automáticamente el retardo.

La leyenda de canales de arriba a la izquierda en V(t) permite mostrar u ocultar CH1, CH2 y FILTER haciendo clic directamente en la línea/ojito o en el nombre. No hay botón adicional ni selectores de trazas en el panel. La elección persiste entre refrescos. Los selectores de los gráficos FFT y heatmap incluyen FILTER; las mediciones y trigger también. CSV agrega FILTER junto con los canales originales e índice/tiempo. WAV conserva CH1/CH2 originales.

**Bode y FFT Transfer permiten seleccionar referencia X y respuesta Y entre CH1, CH2 y FILTER.** La relación mostrada es Y/X. No se aplican calibraciones físicas de CH2/CH1 a otros pares ni a un filtro digital. Cambiar el par borra las comparaciones anteriores; cambiar el filtro borra los resultados Bode que lo usan. El retardo causal del filtro permanece en fase y retardo de grupo. En Bode por pulso/sweep, el flanco de CH1 detecta el inicio del estímulo: CH1 debe recibir A0, aunque el par analizado sea otro. Los parámetros de FILTER no se guardan todavía como cabecera CSV, por lo que deben anotarse al comparar archivos.

Pruebas: equivalencia bloque completo/fragmentado, rechazo de huecos, DC sin salto, separación de tonos, límites Nyquist, Demo, historial, selección y regresiones del monitor. La inspección visual manual del panel sigue siendo necesaria.

## Familias adicionales

Bessel (corte normalizado en magnitud a −3 dB), Chebyshev I y II y elíptico. Chebyshev I y elíptico usan ripple de banda pasante de 1 dB; Chebyshev II y elíptico, rechazo de 40 dB. Son parámetros fijos de esta revisión, indicados en el tooltip de Tipo. El corte de Chebyshev II corresponde al límite de rechazo, no al punto −3 dB de Butterworth. El banco usa secciones de segundo orden y conserva estado entre bloques para todas las familias. Diseño mediante [SciPy iirfilter](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.iirfilter.html) y Bessel con normalización de magnitud.

El panel comparte el gris #21252f de las tarjetas de Trigger, con títulos centrados. 149 pruebas locales pasan, incluidas persistencia de clics en la leyenda, iconos, valores no editables, estabilidad y equivalencia por bloques de las nuevas familias. No se modificó firmware ni se operó el Q.

Trigger y Filtro comparten un alto fijo calculado con el tamaño mínimo de ambas páginas. El panel inferior desaparece y devuelve espacio vertical al gráfico. El dial plano conserva la interacción nativa de QDial; el arco cyan indica su posición. 150 pruebas locales pasan.
