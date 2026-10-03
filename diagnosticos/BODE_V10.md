# Bode V10 — validación física del 3 de octubre de 2026

El ensayo [verificar_bode_qt_v10.py](verificar_bode_qt_v10.py) usa el monitor
Qt real, la conexión USB/SPI del Q y el circuito conectado a A0/A2/A3. Lee el
estado inicial antes de abrir el monitor, mantiene el perfil ADC y guarda CSV
sin alterar el firmware ni reiniciar el relay.

## Resultado

- Q `1060031107`, ADC 16 bits OS ×16, 31 250 pares/s.
- Barrido de seno de 2 a 100 Hz, 8 puntos logarítmicos, asentamiento de 300 ms
  como mínimo; en frecuencias bajas se esperan tres ciclos y se miden ocho.
- 462 901 pares recibidos por Qt; 461 470 filas grabadas, cero discontinuidades.
- Todos los puntos medidos; CSV permaneció abierto durante el barrido.
- Ganancia de −2,349 dB / fase −37,732° a 2 Hz; −30,831 dB / −80,661° a 100 Hz.
  La forma de la respuesta es compatible con un pasa bajos; no se conocen aquí
  los valores de los componentes, por lo que no se valida contra una curva
  teórica del circuito ni se infiere calibración instrumental.
- Restauración exacta comprobada por una segunda consulta al Q: cuadrada de
  79 Hz, habilitada, modo continuo, DAC códigos 310/4033, frecuencia final
  guardada de 20 kHz y duración guardada de 10 s. ADC sin cambios.
- Relay siguió ejecutándose con PID 20963; no se compiló/cargó firmware.

## Evidencia

- [Informe JSON](resultados_usb/20261003_021228_178271_bode_qt_v10.json).
- [Muestras originales](../capturas/bode_v10/20261003_021228_178271/muestras.csv).
- [Puntos Bode](../capturas/bode_v10/20261003_021228_178271/bode.csv).
- [Captura del monitor](../capturas/bode_v10/20261003_021228_178271/bode.png).

Para repetir, cerrar otras sesiones del monitor y ejecutar desde el repo con
el Python que tiene NumPy/PyQt5:

```sh
QT_QPA_PLATFORM=offscreen python diagnosticos/verificar_bode_qt_v10.py
```

Se preserva el perfil SPI encontrado y la configuración original del generador.
El ensayo requiere muestras SPI existentes; no cambia el destino UART a SPI.
La restauración se consulta al terminar, incluso si falla el ensayo.

## Corrección de restauración

Bode ahora conserva la configuración binaria confirmada del Q. Antes se
reconstruía desde valores de amplitud/offset redondeados en los controles, que
podían producir un código DAC distinto. Los niveles del estímulo se toman de
los controles; la restauración usa los códigos originales. También se espera
la primera consulta de estado del generador antes de iniciar Bode.

Pruebas locales: 142 casos, incluidas restauración exacta con códigos 310/4033
y prevención del barrido antes de conocer el estado del Q.

## Pendiente

Calibración de fase instrumental: conectar temporalmente A2 y A3 al mismo nodo
de A0 y repetir un barrido de referencia. El ensayo actual corresponde al
circuito conectado y no puede usarse como esa referencia. Falta ampliar la
validación física de Bode por encima de 100 Hz y con otros perfiles ADC.

## Rango elegido y puntos por década

Ensayo adicional [20261003_022037_325268](resultados_usb/20261003_022037_325268_bode_qt_v10.json):
2–1000 Hz, dos puntos por década, siete tonos, ADC 16 bits / 50 kHz,
528 755 filas CSV sin saltos. Se midieron seis puntos hasta 632,456 Hz; a 1 kHz
la salida no superó el criterio de ruido/asentamiento y el punto es inválido.
El recorrido llegó al extremo solicitado y restauró todos los ajustes
originales del generador (79 Hz, códigos 310/4033) y del ADC (16 bits / 50 kHz).
Esto valida el recorrido hasta 1 kHz, no una medición válida de transferencia
en el último punto.

Los puntos sin señal válida ya no abortan el recorrido; se guardan como huecos
y se informa el total. Discontinuidades, rechazo del Q o timeout sí abortan.
El eje X queda fijado al rango pedido. Pruebas locales ampliadas: 145 casos.
El ensayo puede repetirse con `--end 1000 --points-per-decade 2`.

### Cambio posterior del criterio de salida

Los resultados anteriores describen el criterio vigente durante esos ensayos.
Actualmente se conserva la ganancia de salidas muy atenuadas o constantes; el
ruido puede volver indeterminada la fase, sin descartar la ganancia. La nueva
regla está probada localmente con salida cero, DC constante y salida de 1 µV.
El ensayo de 1 kHz anterior no se recalculó ni se repitió con esta regla.

### Referencia anterior invalidada por cableado incorrecto (3 de octubre)

El usuario informó posteriormente que el cableado de este ensayo era incorrecto.
Esta referencia fue retirada y sus resultados no deben usarse como calibración.
El ensayo registró 31 frecuencias, diez puntos
por década, ADC de 16 bits a 50 kHz, 200 ms de asentamiento y 16 ciclos por tono.
Todos los puntos tuvieron ganancia y fase válidas. El ensayo completo guardó
583 434 filas CSV sin discontinuidades y restauró exactamente el generador y
el perfil ADC. [Informe](resultados_usb/20261003_123118_712918_bode_qt_v10.json).

La referencia guardada en [bode_v10.json](../calibraciones/bode_v10.json) muestra
una ganancia próxima a 0 dB y fase instrumental de +63,34° a 20 kHz. Es una
referencia relativa entre canales; no calibra la amplitud absoluta del DAC.
El monitor puede restarla en ganancia y fase sólo para ese perfil y rango.

Se comparó una captura independiente anterior con esta referencia: diferencia
máxima corregida de 0,0445 dB y 0,2313°, RMS de 0,0085 dB y 0,0523°.
[Comprobación](resultados_usb/bode_calibration_crosscheck.json). Esto comprueba
repetibilidad en esos puntos, no incertidumbre absoluta ni interpolación entre
puntos. La primera captura se completó, pero su informe falló por serialización
de un booleano NumPy; se corrigió el diagnóstico antes del segundo ensayo.

### Nueva referencia con cableado corregido

El usuario confirmó A0 conectado directamente a A2 y A3 y el monitor
desconectado. Se repitió el ensayo completo: 20 Hz–20 kHz, 31/31 puntos válidos,
ADC 16 bits / 50 kHz, 200 ms de asentamiento y 16 ciclos por tono. Se guardaron
581 579 filas CSV sin discontinuidades y se restauró la configuración inicial.
[Informe](resultados_usb/20261003_123522_633848_bode_qt_v10.json).

La nueva referencia sustituye a la anterior en `calibraciones/bode_v10.json`;
la referencia invalidada se conserva en `calibraciones/historico/`. La ganancia
medida va de −0,0072 a +0,0134 dB y la fase llega a +63,54° a 20 kHz. La
comprobación de repetibilidad anterior también queda invalidada: no se ha
realizado un segundo barrido independiente con el cableado corregido.
