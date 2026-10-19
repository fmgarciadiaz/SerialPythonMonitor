# Piloto SPI 40 MHz — primero reloj, luego formato compacto

Autorizado por el usuario como experimento aun sin margen eléctrico
garantizado (QRB setup5ns +ST tvSOmax12ns >12,5ns). No certificar timing.
MCU WORD de referencia,READYspin50µs,TCP por frame,CRC yvalidación íntegros.
Un relay binario admite sólo SCOPE_SPI_HZ38000000/40000000.

Control38solicitados(33,333configurados):ADC8ticks640/114,10s cadauno.
Luego40solicitados:640/10s,114/30s,112/30s,110/10s,reinicios independientes.
Cortar primer fallo de integridad,sin reintentos selectivos. Releer fuente,
divisor ymodo después de cada caso fuera de ventana:expect100M/div3 o120M/div3.
No confundir relojconfigurado con medición eléctricaSCK. Si pasa,no equivale
a calificación larga ni margen universal. Medir integridad yholgura aparte.

Snapshot vivo/backup previos,un dueñoQ,restaurar siempre firmware/relay/ADC/
generador exactos,hashfirmware y10scontinuidad.Releer reloj al cierre.
Nada productivo.Siguiente tarea autorizada:formato compactoADC8alta velocidad,
aislado del ensayo de reloj para poder atribuir diferencias.
