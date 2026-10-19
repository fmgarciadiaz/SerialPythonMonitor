# Comprobación del siguiente reloj — 16/10/2026

## Decisión tras encontrar el setup Qualcomm: no promover 40 MHz

La [hoja oficial QRB2210, 80-30843-1 Rev AD, sección 3.10.9,
tabla 3-26, página impresa 67](https://docs.qualcomm.com/doc/80-30843-1/80-30843-1.pdf)
especifica setup de entrada MISO mínimo de **5 ns**. El límite de reloj
del maestro es50MHz, pero no elimina este requisito del enlace.

[ST DS13086 Rev10, tabla150, página303](https://www.st.com/resource/en/datasheet/stm32u585ai.pdf)
especifica tv(SO) máximo12ns para el grupo de pines aplicable a1,71–2,7V,
voltage range1. El límite41,5MHz del esclavo asume setup maestro0 y duty50%.
No es un límite garantizado para el enlace con QRB2210.

Presupuesto ideal MISO (duty50%, sin retardos de placa):

| SPI MHz | Semiperíodo ns | tv(SO) máx ns | setup maestro ns | Saldo ns |
|---:|---:|---:|---:|---:|
| 33,333333 | 15 | 12 | 5 | -2 |
| 40 | 12,5 | 12 | 5 | -4,5 |

Incluso con10ns típicos de ST,40M deja -2,5ns. Son cálculos con límites
publicados y captura convencional en el flanco opuesto; no una medición
eléctrica ni evidencia de errores reales. Duty no ideal y propagación
requieren más presupuesto. El techo ideal con12+5ns es29,411765MHz,
sin margen de placa. Tampoco constituye recomendación de una tasa nueva.

La integridad física ya observada a33,333M sigue siendo evidencia de esas
campañas concretas; no demuestra margen eléctrico garantizado en todas
las condiciones. No se cambia retroactivamente su resultado.

No se ejecuta el piloto40M con esta configuración. Para justificarlo se
necesita demostrar otro punto de captura/retardo GENI compatible con ambos
extremos o caracterización eléctrica suficiente; pasar CRC sólo probaría
integridad durante el ensayo. La alternativa inmediata de rendimiento es
investigar el coste por transacción ya medido, conservando READY por trama.
No se cambió firmware, relay ni reloj durante esta revisión documental.

## Discrepancia resuelta con lectura física de DFS

`clock_levels_live.json` conserva tres snapshots idénticos de registros
fijos del RCG S5 en 0x0141f738, abiertos O_RDONLY y mmap PROT_READ.
Contenedor sin red, rootfs y montajes RO, /dev/mem:r y única capacidad
adicional SYS_RAWIO. No se escribieron registros ni se reinició la app.

DFS control=0x2b: bit enable=1, nivel activo=5. Debugfs del origen muestra
CLK_GET_RATE_NOCACHE, coherente con DFS. Los niveles decodificados son:

| Índice | Fuente MHz |
|---:|---:|
| 0 | 19,2 |
| 1 | 32 |
| 2 | 48 |
| 3 | 64 |
| 4 | 96 |
| 5 | 100 |
| 6 | 120 |
| 7 | 19,2 (slot repetido, CFG/M/N cero) |

`decode_clock_levels.py` usa los campos HID/M/N de RCG2 y tasas de padres
leídas en debugfs. El modelo de selección upstream con esos niveles reproduce
exactamente el resultado anterior: request38MHz, índice5, fuente100M/div3.
No hay fuente75/80M en esta tabla. Requests38,5 y39M conservan33,333M;
el siguiente punto representable es40M, fuente120M/div3, índice6.
Esto resuelve la discrepancia de representabilidad, no certifica timing ni
mide SCK eléctrico. La tabla efectiva no es la tabla estática upstream.

Se mantuvo el reloj fuente100M y no se ejecutó piloto40M. Sigue pendiente el
presupuesto temporal del maestro indicado abajo. La ganancia ideal de bits
por992B sería39,68us (238,08 a198,40us), sin garantía de igual ganancia global.
No hay un paso intermedio37,5M disponible mediante la tabla actual.

## Análisis previo conservado

Lecturas por ADB, sin detener aplicaciones ni modificar firmware, relay o
reloj: compatible raíz `arduino,imola`, `qcom,qrb2210`, `qcom,qcm2290`.
Proveedor real `/sys/bus/platform/devices/1400000.clock-controller`,
compatible `qcom,gcc-qcm2290`, driver `gcc-qcm2290`. SPI usa `qcom,geni-spi`.

La [tabla upstream QCM2290](https://raw.githubusercontent.com/torvalds/linux/master/drivers/clk/qcom/gcc-qcm2290.c)
incluye fuentes 75, 80 y 120 MHz, compartidas por S5. Por tanto, el modelo
upstream permite representar 37,5 MHz (75/2) y 40 MHz (80/2 o 120/3).
Esto no prueba que el kernel instalado exponga esos niveles.

Hay una discrepancia que impide tomar esa tabla como evidencia del sistema
actual: con toda la tabla upstream y el algoritmo de selección GENI,
pedir 38 MHz elegiría 75/2 = 37,5 MHz. La campaña física anterior
leyó fuente 100 MHz, índice 5 y divisor 3 = 33,333333 MHz. No atribuir la
diferencia a una causa todavía no verificada.

El [selector GENI](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux.git/+/75eab749e7aec0b7b515d7c50ed429ef4e1c5f3f/drivers/soc/qcom/qcom-geni-se.c)
obtiene niveles mediante clk_round_rate y elige el menor error por debajo
de lo solicitado; el [driver SPI](https://raw.githubusercontent.com/torvalds/linux/master/drivers/spi/spi-geni-qcom.c)
aplica divisor entero redondeado hacia arriba. Son fuentes upstream,
no el commit exacto 122c2c22d838 instalado.

Antes del piloto falta identificar la tabla efectiva del kernel/firmware
actual. No basta con la tabla estática de otro árbol. El código común
[RCG2](https://raw.githubusercontent.com/torvalds/linux/master/drivers/clk/qcom/clk-rcg2.c)
también contempla niveles DFS cargados desde registros cuando se habilita
ese mecanismo; no se comprobó que esté activo aquí.

Además sigue pendiente el setup del maestro Qualcomm: el límite ST de
41,5 MHz no garantiza por sí solo 40 MHz full-duplex. A 40 MHz el semiperíodo
ideal es 12,5 ns; con tvSO máximo de 12 ns, quedarían sólo 0,5 ns antes de
descontar setup, propagación y duty. Consultar condiciones completas en
RESULTADOS.md. No se ejecutó un piloto a mayor reloj ni se certificó timing.

Siguiente trabajo concreto: obtener el fuente exacto o los niveles efectivos
del proveedor instalado mediante lectura; resolver la discrepancia 38 MHz.
Sólo después seleccionar un piloto corto con CRC/continuidad y restauración.
