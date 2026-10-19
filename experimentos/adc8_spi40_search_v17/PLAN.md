# Buscar tasas ADC8/CH1 mayores que ticks112 con SPI40

El usuario eligió buscar una tasa mayor, antes de incorporar el perfil.
Fuentes MCU/relay idénticas al perfil40 sostenido. Formato original kind20,
864 muestras/frame,N3456,WORDDMA,READY50us yTCPporframe. Sincompactación.

Referencia112/10s (ya cualificada previamente60+3×120s), luego111/10s,
110/10s,108/10s,106/10s... hasta primer fallo o límite de firmware78.
Primer fallo se repite una vez con reinicio, sólo para caracterizarlo;
una repetición favorable no borra el fallo ni habilita ese perfil.
Se sondea el tick impar inmediatamente más lento que el primer fallo grueso.
No supone monotonicidad universal ni acredita un máximo absoluto.

Candidatos que pasaron pantalla se validan del más rápido al más lento:
60s +3×120s independientes. Corte inmediato ante fallo de integridad y
seguir con candidato más lento. El primero que completa las cuatro corridas
queda como mejor integridad observada. Si no cumple holgura, validar un
candidato más lento con holgura de pantalla, hasta encontrar uno o agotarlos.
Mantener resultados por perfil;ningún reintento selectivo para aceptar.
No600s. No subir SPIporencima40 ni cambiar nodo/protocolo en esta búsqueda.

Integridad:CRC/secuencia/epoch/índices/timestamps/rango/DMA,dropped/fatal0.
Holgura adicional:margenmedio>=10%,cola<4inclstartup,slackpositivo enlas4.
Cada caso reiniciaMCU/relay yconfirma clock_srcNOCACHE120M/DFS6/div3=40M
mediante lecturas fijasRO fuera deventana.No medicióneléctricaSCK ni garantía
eléctrica universal. No GUI/DSP/analogía/dual/UART ni producción.

Snapshotvivo/backup,un dueñoQ. Finally restaura firmware/relay/entorno/ADC/
generador exactos,hashfirmware,10scontinuidad yrelectura de reloj original.
