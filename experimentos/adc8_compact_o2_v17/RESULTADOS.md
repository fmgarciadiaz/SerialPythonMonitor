# Compactación O2 — íntegra, sin mejora; campaña cerrada

[Reporte](probe_1400_20261016_011533/report.json):8×30sABBA,339,661,888muestras íntegras,
dropped/fatal0. Mismoformatokind21 de908muestras/992B,conoptimize(O2) en
helpers GCCARM32,no cambios Linux/decoder niSPI. No redujo preparaciónMCU:
B~80µs frenteA~35µs,igual a primera versión. Envío normalizado empeoró
4,325%114 y6,124%112;cuatroB sinholgura. Gatefalse,sinprueba larga/promoción.

La revisión siguiente ../adc8_compact_direct_v17 construye header80 ypayload
enposición final paraeliminar memmove delpayload;misma representaciónbinaria.
Es otra campaña,con código yreportes separados.No reemplazar este fallo.

Cinco pruebasC/Python conASAN/UBSAN pasan,codec yvalidaciones intactos.
12lectores extra rechazados,primario/APPLIED/perfillento legacy correctos.
Restauración exactaADC8/1403508SPI,generadorOFF ytodos los campos,relay/entorno,
app experimental detenida;hashfirmwareidéntico:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
`ok/restored/restore_integrity_ok=true`,14,031,360muestras/10s.
Sinproducción ni aceptación eléctrica/analógica/GUI/dual/UART/RADIO.
