# Integridad larga a1,6000MS/s permitiendo cola4

Autorización explícita: probar1600largo aunque llegue a4. Ejecutar60s+3x120s independientes. ADC8/CH1,100ticks,N3456,SPI40,CPU2/performance,READY50us,productor1ms,liberaciónoriginal,IRQoriginales,warm112/2s bombeando. Fuentes idénticas al respaldo validado106. No nuevos cambios firmware/relay.

Permitir pico4 para evaluar integridad, conservar definición/contador yCRC,sequence,epoch,índice/timestamp,rango,DMA,dropped/fatal. Cortar primerfallo de integridad; no reintentosselectivos. Holgura exige todavía margen>=10%,pico<4desdearranque,slackpositivo yse reporta separada. No600s.

Restaurar governor,firmware/relay/entorno/config/generador,reloj ycontinuidad10s. No producción. Perfil106protegido.
