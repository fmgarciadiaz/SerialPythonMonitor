# Política de frecuencia CPU para el candidato106

Hipótesis, no causa probada: escalado dinámico contribuye a latencia de las llamadas del relay. Inventario Q: CPUs0-3 comparten policy0; schedutil original; frecuencia observada1305600kHz,min300000,max2016000. Comparar schedutil(F) contra performance(R), FRRF30s independientes. Mismo CPU2,N3456,106ticks,SPI40,preparación112/2s. MCU/relay originales sin instrumentación nueva. Performance afecta toda la política0: no se afirmará efecto exclusivo deCPU2.

AmbosR deben cumplir integridad,margen>=10%,pico<4desdearranque,slackpositivo. Si pasan:60+3x120 independientes,cortar primerfallo,sinreintentosselectivos. Cambiar sólo governor, conservar min/max/IRQ/prioridad. Snapshot y restauración verificada del governor original en finally, antes de restaurar app/relay/perfil/generador; continuidad10s y reloj original. Diagnóstico120 previo no sustituye aceptación.
