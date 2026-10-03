# V9: selectores de control y destino, Qt y CSV

Validación del 2 de octubre de 2026 con **Scope Output Select V7**, relay dual,
Q por USB/ADB y R4 con puente V5 a 3 Mbps. Adquisición fija: 14 bits,
31.250 pares/s y período de 32 µs.

## Resultado físico

Se ejecutó la interfaz Qt de V9 en modo offscreen, con el gráfico activo y una
grabación CSV durante los cambios en vivo. Secuencia:

1. Conectar al Q con destino SPI.
2. Cambiar a UART y elegir el R4.
3. Volver a SPI, conservando la grabación.
4. Desconectar y reconectar con destino UART.
5. Desconectar y reconectar con destino SPI.

Resultado aprobado:

| Comprobación | Resultado |
|---|---:|
| Pares entregados a Qt | 712.192 |
| Filas del CSV del primer tramo | 475.136 |
| Saltos de timestamp en CSV | 0 |
| Saltos de índice en CSV | 0 |
| Errores de recepción o continuidad en Qt | 0 |
| Llamadas de renderizado | 1.554 |
| Duración de la prueba completa | 27,344 s |
| Frecuencia estimada por el monitor | 31.250 Hz |

Cada sesión nueva empieza una captura independiente; no se exige continuidad
entre desconexiones. Dentro de la sesión que cambió SPI → UART → SPI, tanto
índices como timestamps permanecieron continuos. Se comprobaron los dos
selectores de destino y el puerto USB específico del R4, separado del Q.
El control permanece por Q; el receptor exige PING confirmado periódicamente.

[Informe completo aprobado](resultados_usb/20261002_103210_025238_monitor_v9.json).

## Código y regresiones

- [Monitor V9](../monitor/historico/v9/app.py): interfaz independiente basada en V8,
  selectores y cambio en vivo, CSV en `capturas/experimental_v9/`.
- [Receptor](../transport/unoq_receiver.py): lector R4 paralelo, confirmación del
  Q y continuidad común; retiene muestras SPI si queda una cola UART de frontera.
- [Diagnóstico reproducible](verificar_monitor_v9.py): usa los controles Qt,
  cuenta todas las muestras y relee el CSV temporal antes de eliminarlo.
- [Pruebas del receptor](../tests/test_output_receiver.py): fragmentación DATA,
  corrupción, llegada UART anterior/posterior al ACK, índices, reconexión,
  rechazo de hardware y heartbeat durante una transición.
- [Pruebas de sesiones](../tests/test_v9_session.py): las señales encoladas de
  un hilo cerrado no modifican datos, estado o errores de una sesión nueva.

Pasaron **91 pruebas automáticas** del proyecto.

V9 mantiene trigger, mediciones, estilos de trazo, RUN/STOP, Demo y CSV de V8.
También se inspeccionó visualmente la ventana y se comprobó Demo, cierre y
exclusión del puerto de servicio del Q de la lista R4.

## Alcance y estado final

La prueba usa un Q y un R4 físicos. La lista permite elegir otros dispositivos,
pero no se probó un segundo Q/R4 ni una sesión prolongada de horas. Las llamadas
de renderizado no son una medición de FPS presentados en una pantalla real.
UART conserva DATA sin CRC; sus comprobaciones no detectan toda corrupción de
amplitud. SPI conserva CRC y secuencia global SCP1.

El Q quedó con la app dual y el relay activos, listo para `python monitor/historico/v9/app.py`.
Los verificadores terminaron y sus puertos quedaron libres. V8 conserva su app
V6 ADC y debe iniciarse con su relay correspondiente para volver a esa versión.

Este avance completa la integración del **paso dos** del
[plan](../Plan%20de%20trabajo.md). El paso tres configurará adquisición según
el transmisor; el panel del generador corresponde al paso cuatro.
