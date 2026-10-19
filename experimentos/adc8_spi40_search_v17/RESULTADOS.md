# Búsqueda SPI40 — interrumpida por cambio de objetivo, Q restaurado

El usuario eligió sondear cómo llegar a1,5MS/s,en lugar de continuar con
perfiles inferiores. Se envió SIGINT al único runner;finally restauróQ.
[Reporte original](probe_1400_20261016_084742/report.json) conserva `ok=false` y
`error=signal2`:no convertir la búsqueda interrumpida en campaña completa.

Antes de la interrupción sí quedó completa la aceptación de integridad de
ADC8/CH1ticks108=1.481.481,481S/s:60+3×120s,621.870.912muestras íntegras,
dropped/fatal0. No cumple holgura:cola pico4 enparte de la serie. Los datos
yaceptación porperfil están enqualified_profiles delreporte,aunque no se
completó la selección final de winners.

Tasas superiores:

- 104ticks=1.538.461,538S/s:dos fallos independientes durante asentamiento,
  dropped1,cola4,fatal0 yslackpositivo.
- 105ticks=1.523.809,524S/s:10s y60s correctos,fallo tras reinicio al comenzar
  el primer120s,dropped1,cola4. No aceptado.
- 106ticks=1.509.433,962S/s:10s y60s correctos,mismo fallo de arranque al
  comenzar primer120s,dropped1,cola4. No aceptado.
- 111/110/108/106 pasaron sondeos10s conholgura;no confundir pantallas con
  aceptación sostenida. La corrida larga110 se interrumpió yno se acredita.

Nuevo sondeoautorizado:../adc8_target1500_probe_v17,arranque directo frente
apasar112durante2s antes de106,y nodos3456/6912,sin cambiosMCU/relay.
Busca reproducir/aislar el fallo temprano de106,en lugar de seguir bajando tasa.

Restauración exactaADC8/1403508SPI,generadorOFF ytodos sus campos,relay/
entorno,firmwareSHAidéntico:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
14,031,360muestras íntegras/10s yreloj33,333M al cierre.
App experimental detenida antes delnuevo sondeo. No cambiosproductivos.
