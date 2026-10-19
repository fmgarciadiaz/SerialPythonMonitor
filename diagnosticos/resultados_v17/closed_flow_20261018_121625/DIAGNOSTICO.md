# Cierre de flujo con RADIO —18/10/2026

Inspección sólolectura de últimos100logs relay,sin reinicios ni segundo cliente ADC. Frame67734 kind20 CRCcorrecto,anterior67733. ADC14 CH1,ticks188,N1984,851063Hz,epoch2: dropped1,fatal0,queue3,pico4,slack174530,send658745. native_feed rechaza dropped!=0(p+56); relay sale goto done y cierra TCP. Connection.read recibeEOF y muestra mensaje genérico. No hay evidencia de corrupciónUSB: CRCidéntico; no confundir con cortesA0porunderrun visibles enradio_a0_stops.jsonl aADC10/1250000.

Causa inmediata probada: pérdida de nodoADC14máximo. Desencadenante bajoRADIO/GUI aúnporaislar; no afirmar autogain/USB como causa.14/16 no tenían aceptaciónconjunta y siguenpospuestos. Probar conservadoramente14/599250 y reproducir matrizaislada con/sinRADIO,A0,autogain cuandoQestélibre,con unpropietario y restauración. No modificar verificador para tolerar pérdidas ni autoreconectar ocultando discontinuidad.
