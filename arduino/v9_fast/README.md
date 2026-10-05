# V9 Fast SPI · firmware experimental

Derivado de V8 config, con app independiente, relay a **32 MHz** y
[monitor V11](../../monitor/v11/README.md). **100 kHz por canal** pasó dos minutos
continuos a 14 bits con DAC activo, sin huecos, nodos perdidos ni error DMA.
16 bits con oversampling siguen hasta 50 kHz; UART hasta 31,25 kHz.
Pines conservados: A0 DAC, A2 entrada, A3 salida del circuito.

100 kHz usa 68 ciclos de adquisición (1,7 µs), igual que 62,5 kHz.
El par ADC cabe sin acortar esa ventana. El trabajo redujo el cálculo del CRC,
el sellado duplicado de cada trama y aumentó el caudal del enlace SPI.
No cambia el formato ni las validaciones de integridad.

125 kHz perdió nodos con esta implementación. 200/250 kHz quedan como candidatos
CLI de diagnóstico; no están ofrecidos en V11 ni validados físicamente.
La exactitud analógica de ambos canales a las nuevas tasas sigue pendiente:
A3 recibió señal muy pequeña en el ensayo, compatible con circuito intermedio.

Python V10 + V8 config siguen siendo el conjunto estable y conservan sus fuentes.
[Resultados, estudio técnico, respaldo y restauración](../../experimentos/tasas_spi/README.md).

```sh
python3 tools/unoq.py compile --version v9_fast
python3 tools/usb_stream.py build --firmware v9_fast
```

App Lab: **Scope Fast SPI V9 Experimental**, importada, compilada y ensayada
físicamente sin reemplazar la app estable. La última compilación ocupa
101 776 bytes de programa y 156 224 bytes estáticos, con 105 920 bytes de RAM
restantes según Arduino CLI.
