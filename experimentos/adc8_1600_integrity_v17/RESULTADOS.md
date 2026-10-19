# 1,6000 MS/s: integridad sostenida aceptada, holgura no aceptada

El usuario autorizó explícitamente continuar aunque la cola alcanzara4. Se ejecutaron60s+3x120s con reinicios independientes, sin repetir selectivamente. ADC8/CH1,100ticks,N3456,SPI40,CPU2/performance/FIFO10,READY50us,productor1ms,liberaciónoriginal,IRQoriginales ygeneradorOFF. Preparación112ticks/2s bombeando/validando yesperandoAPPLIED antesde100ticks. Fuentes MCU/relay idénticas al perfil106 aceptado.

|Corrida|Muestras|Margenmedio|Colapico|Slackmínimoµs|Framesobservadoscola3/4|
|---|---:|---:|---:|---:|---|
|finalist|95944608|12.113%|3|822.869|0/0|
|acceptance_1|191889216|11.955%|4|822.344|32/0|
|acceptance_2|191889216|12.120%|4|822.587|200/2|
|acceptance_3|191890080|12.045%|4|818.212|51/0|

Total:671613120 muestras íntegras. CRC,secuencia,epoch,índices/timestamps,rango ypropiedadDMA válidos; dropped/fatal0. Los histogramas cuentan observaciones porframe; no son duración física exacta del pico. Pico incluye arranque yno se reinicia para aprobar.

Aceptación:integrity_accepted=true,headroom_accepted=false. Los tres120s alcanzaron4slots; no se garantiza reserva frente auna demora adicional. El perfil106/1,5094MS/s conserva aceptación completa de integridad yholgura. Esta campaña no borra el fallo previo del experimento READY150us ni lo mezcla: aquíREADYoriginal50us.

Q restaurado/verificado: firmware/relay/entorno/ADC8/1403508SPI/generadorOFF originales,governorschedutil,reloj33,333MHz ycontinuidad10s. Verclosure_audit.json yreport.json. Sinincorporaciónaproducción. Noaceptaciónanalógica,GUI/DSP/RADIOconjunto,dual/UARTni margeneléctricouniversalSPI40. Relojconfiguradoverificado,noSCKeléctricamente.
