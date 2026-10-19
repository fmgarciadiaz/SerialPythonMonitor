# Piloto SPI40 — integridad observada, sin calificación eléctrica ni sostenida

Sí fue posible configurar40MHz y completar los casos del piloto sin errores
de integridad. [Reporte válido](probe_1400_20261016_005838/report.json).
118,479,456 muestras íntegras;CRC/secuencia/epoch/índices/timestamps/DMA,
dropped/fatal0. El caso más rápido fueADC8/160M÷110=1.454.545,455S/s,
sólo10s,cola pico4:sinholgura global pese amargen medio15,25%.
No es nuevo perfilestable ni promoción de40MHz.

| Variante | SPIconfig MHz | Ticks | Segundos | Muestras | Cola pico | Margen medio envío | Holgura |
|---|---:|---:|---:|---:|---:|---:|---|
| A | 33.333333 | 640 | 10 | 2,498,688 | 1 | 83.745% | sí |
| A | 33.333333 | 114 | 10 | 14,028,768 | 2 | 9.401% | no |
| B | 40.000000 | 640 | 10 | 2,498,688 | 1 | 84.532% | sí |
| B | 40.000000 | 114 | 30 | 42,081,984 | 2 | 18.007% | sí |
| B | 40.000000 | 112 | 30 | 42,832,800 | 2 | 17.373% | sí |
| B | 40.000000 | 110 | 10 | 14,538,528 | 4 | 15.250% | no |

B114/B112 pasaron integridad yholgura en30s cadauno;no60+3×120s.
A114 sólo10s,distinta duración aB:no afirmar comparación ABBA ni ganancia
estable.A640/B640 controles10s.No caracterización analógica/GUI/dual/UART.

## Corrección de lectura de reloj

El primer intento [reporte conservado](probe_1400_20261016_005453/report.json)
se detuvo al verificar reloj:se leía la rama gcc_qupv3_wrap0_s5_clk,cuyo
clk_rate estaba cacheado100M aun conGENIseleccionando nivel6.No hubo fallo
de integridad;se restauróQ completo antes de repetir.Ese intento no valida
la frecuencia40M por sí mismo.

El lector propio ahora consulta gcc_qupv3_wrap0_s5_clk_src,marcado
CLK_GET_RATE_NOCACHE,y contrasta nivelDFS real enregistroGCC conGENI:

- A:origen100M,GENIindex5,GCCnivel5,divisor3=>33,333333M.
- B:origen120M,GENIindex6,GCCnivel6,divisor3=>40M.
- Wrapper3.0,DMAGENI1/GSI0;3snapshots iguales porlectura.

Leeconfiguración fijaO_RDONLY/PROT_READ,no FIFOs ni registrosclear-on-read.
ContenedorRO,sinred,capSYS_RAWIO,device:r.Las lecturas se hacen fuera de
ventanas de rendimiento.La frecuencia se deriva de configuración,noSCK
medido con instrumento.Las lecturas anteriores de33,333M siguen coherentes
conorigen100M yDFS5;no extrapolar valores cacheados al nivel6.

El presupuesto publicado (setupQualcomm5ns +tvSOmaxST12ns) sigue sin
respaldar40M con captura convencional.Las muestras intactas de este ensayo
no certifican margen frente atemperatura,tensión,carga ovariación de placa.
El usuario autorizó expresamente el piloto con esa limitación.

## Restauración ycontinuación

`ok/restored/restore_integrity_ok=true`. Estado originalADC8/1403508SPI y
generadorOFF con todos sus campos exactos,relay/entornooriginales.
14,032,224muestras íntegras en10s;firmwareantes/después:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
Relojrestaurado:origen100M,DFS5,divisor3;app experimental detenida.

Sin producción.El siguiente experimento autorizado escompactaciónADC8,
separado yconreloj33,333M para no mezclar cambios.
