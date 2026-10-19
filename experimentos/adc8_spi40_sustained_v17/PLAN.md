# SPI40 sostenido — ADC8CH1 original, sin compactar

Continuación autorizada de piloto40. FuentesMCU/relay idénticas alpiloto;
único cambio frente referencia:relojSPI solicitado40 en lugar38MHz.
Kind20/864muestras,N3456,WORDDMA,READYfresco/spin50us,TCPporframe intactos.
No mezclar formato compacto niotras optimizaciones.

PreflightA640/10s a33,333M yB640/10s a40M,despuésB112 (1.428.571,429S/s):
60s +tres120s independientes.Máximo120s,no600s.ReinicioMCU/relay porcaso.
Corte primerfallo de integridad;sin reintentosselectivos ni salto detasas.
Si falta holgura pero integridad continúa,completar serie yclasificar aparte.

Cada caso confirmafuente clk_srcNOCACHE,GCCDFSactivo=GENIindex ydivisor:
A100M/5/3=>33,333M,B120M/6/3=>40M.Lecturas fijasRO fuera deventana de medida.
No mide SCKeléctrico.Gateintegridad:todos4casoslongs correctosCRC/secuencia/
epoch/index/timestamp/rango/DMA,dropped/fatal0.Gateholgura adicional:
margenmedio>=10%,cola pico<4 inclstartup,slackmínimopositivo enlos4casos.

Snapshotvivo/backup,un dueñoQ.Finally restaura firmware/relay/entorno/ADC/
generador exactos,identidadfirmware,10scontinuidad yrelecturarelojoriginal.
No modificarproducción niaceptacióneléctrica/analógica/GUI/dual/UART/RADIO.
Éxito sostenido sóloacredita las condiciones ensayadas;persiste la limitación
documentada delpresupuestoMISO publicado yno garantiza temperatura/tensión.
