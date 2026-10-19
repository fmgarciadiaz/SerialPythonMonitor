# Separar USB de SPI: no resuelve la cola a1,6000MS/s

Único cambio: IRQ99USB efectivaCPU1, manteniendoSPI/READY yrelayCPU2,performance,N3456,SPI40,warm112/2s. Fuentes MCU/relay idénticas. ABBA,30s yreiniciosindependientes.

|Caso|IRQUSBefectiva|Margenmedio|Colapico|
|---|---:|---:|---:|
|A|0|11.976%|2|
|B|1|12.472%|4|
|B|1|12.533%|3|
|A|0|12.068%|4|

Todos íntegros. B no es elegible: primerpiloto alcanzó4. No ejecutarcalificaciónlarga ni repetirfallo. La pequeña mejora del promedio no demuestra reducción de excursiones raras. El segundo control A también alcanzó4.

Restauración verificada de IRQsolicitada0-3 yefectiva0,governorschedutil,firmware/relay/entorno/ADC/generadororiginales,reloj33,333MHz ycontinuidad10s. Verclosure_audit.json. Respaldo106intacto.

Esta prueba descarta mover sóloUSB aCPU1 como solución suficiente; no descarta otros efectos de planificación/IRQ. Siguiente alternativa acotada: probar afinidad deSPI cerca delrelay, sin modificar simultáneamenteUSB/READY. Todavía no realizada.
