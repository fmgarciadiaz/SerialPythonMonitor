# Bode sin curvas — 2026-10-19

El usuario confirmó perfil dual y CH1 conectado a antena. El par predeterminado de Bode es referencia CH1, respuesta CH2: una antena no proporciona la referencia del estímulo del generador. No se debe representar como transferencia válida una medición sin referencia coherente.

Se corrigió un defecto independiente en `bode_pulse.py`: la detección de inicio de Pulso/Sweep leía CH1 fijo en lugar de la referencia elegida. El mensaje de estímulo ausente ahora identifica el canal seleccionado.

Prueba física en ADC14/40 kHz, CH2 como referencia y respuesta, sin cambiar cableado:
- `diagnosticos/resultados_bode/gui_v17_20261019_153515/report.json`: antes de corregir, ningún método produjo puntos válidos.
- `diagnosticos/resultados_bode/gui_v17_20261019_153746/report.json`: después, Sweep produjo 2545 ganancias válidas y ambas curvas visibles con datos finitos.
- `diagnosticos/resultados_bode/gui_v17_20261019_153820/report.json`: repetición, Sweep produjo 2546 ganancias válidas. Tonos con asentamiento reducido de 20 ms siguió rechazando todas las referencias; Pulso no detectó el estímulo. Estos dos métodos no quedan validados físicamente por estas pruebas. Se conservaron capturas de tonos para análisis; no se atribuye todavía su rechazo a una causa única.
- Todas las ejecuciones restauraron la configuración previa y conservaron el firmware SHA256 96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9. Recuperación sin drops/fatales.

Regresiones: detección con referencia CH2, arranque de los tres métodos con FILTER OFF y fase de loopback: 3 tests correctos. Suite completa en Qt minimal: 10/11, fallo de dimensiones de controles (no de cálculo). Cocoa sin escalación no pudo abrir pantalla; no se declara esa suite completa aprobada.

Para medir un circuito: A0 a su entrada y CH1; salida a CH2, masa común. CH2/CH2 sirve como autocomprobación de transferencia unitaria, no mide la respuesta del circuito. Mientras CH1 se use como antena no utilizarlo como referencia de Bode.

## Ampliación posterior de selectores

Tonos y Sweep/Chirp permiten hasta 150 kHz; Pulso hasta 200 kHz. Se mantiene el límite final <0,45×Fs. Se comprobó localmente cada máximo y una frecuencia intermedia de 123456,7 Hz. Esto no agrega aceptación física del rango ampliado ni resuelve por sí solo la referencia del montaje.
