# Arduscopio Q · parejas Arduino UNO Q

La pareja activa es **[Scope V19](v19/README.md)**, asociada a
`monitor/v19`. Sus hashes de firmware y relay están verificados contra el
recibo V19; la calificación física disponible cubre ADC8 CH1 a 1,860 MS/s y los
smokes descritos en la documentación. V18 y V17 se conservan intactas como
parejas anteriores.

Para comprobar la pareja activa y sus componentes (V19):

```sh
python tools/unoq.py inventory --version v19
python tools/unoq.py status --version v19
```

`inventory` es de solo lectura y muestra por separado las apps y relays activos.
Para preparar o actualizar V19 usar el botón «Preparar Q», que verifica el
recibo, respalda y conserva recuperación. No iniciar V18 junto con V19: ambos
usan ADC/SPI/READY. V17 permanece congelada y detenida; las versiones anteriores
están en `historico/`.

[Guía V19](../monitor/v19/README.md) · [Parejas y estado](../docs/VERSIONES.md) ·
[Histórico](historico/README.md) · [Catálogo](apps_catalogo.json).
