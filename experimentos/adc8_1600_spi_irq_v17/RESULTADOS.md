# IRQ SPI en CPU2: no resuelve los picos a1,6000MS/s

CPU2 es el tercer núcleo del procesador Linux (numerados0–3). El relay ya corría allí; se trasladó únicamente IRQ123SPI aese núcleo. USB yREADY no se modificaron. Misma receta CPU2/performance/N3456/100ticks/SPI40,warm112/2s; fuentes MCU/relay intactas.

|Etapa|Caso|SPIefectiva|Margenmedio|Pico|
|---|---|---:|---:|---:|
|irq_pilot|A|0|12.014%|3|
|irq_pilot|B|2|12.054%|2|
|irq_pilot|B|2|12.029%|3|
|irq_pilot|A|0|11.906%|4|
|finalist|B|2|12.088%|3|
|acceptance_1|B|2|10.787%|4|

Ambos pilotosB pasaron y60s también, pero primer120s alcanzó4. Todos los intervalos preservaron integridad. Calificación detenida sin reintentosselectivos; noaceptaciónlarga completa. AfinidadSPI2 no es solución suficiente.

Restauración verificada: IRQsolicitada0-3/efectiva0 original,governorschedutil,firmware/relay/entorno/ADC/generador originales,reloj33,333MHz,continuidad10s. Verclosure_audit.json. Perfil106/1,5094MS/s protegido.
