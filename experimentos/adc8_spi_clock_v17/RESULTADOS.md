# SPI GENI: reloj configurado y ventana NSS — diagnóstico cerrado

**Hallazgo:**38MHz solicitados corresponden a **33,333MHz configurados** en
el controlador actual:fuente100MHz,divisor3. La ventana NSS medida mediante
callbacks del MCU es~253µs y el ioctl~339–342µs. El residual emparejado es
**86,5–88,8µs fuera deNSS**. No equivale a CPU puro del kernel.

No se cambió la frecuencia SPI,no se instaló otro kernel y no se calificó
una tasa nueva. Estas medidas descartan interpretar38MHz solicitado como
SCK medido y cuantifican dónde queda parte del tiempo de transacción.

## Configuración leída sin escrituras

GENI `4a94000.spi`,driver`geni_spi`,kernel`7.0.0-g122c2c22d838`.
[Lectura inicial](configuration_initial.json) y lecturas por caso/restauración:

- Fuente debugfs gcc_qupv3_wrap0_s5_clk=100.000.000Hz,antes y después de leer.
- GENI_SER_M_CLK_CFG0x31:enable1,divisor3.
- Wrapper0x30000000:versión3.0. El driver upstream usa oversampling1 para
  esta versión;derivaciónSCK=100.000.000/(3×1).
- GENI_DMA_MODE_EN1,GSI_EVENT_EN0,DMA_INTERFACE_ENABLE1:modoDMA GENI
  habilitado,distinto de una afirmación de FIFO puro o GPI-DMA.
- Tres snapshots iguales por lectura;configuración inicial,dos casos y
  restauración conservaron reloj/divisor/modo.

El lector`read_config.py` sólo abre /dev/mem O_RDONLY y mmap PROT_READ,
con direcciones fijas de configuración,no FIFOs ni clear-on-read. Contenedor
sin red,rootfsRO,device:r,capacidad SYS_RAWIO como única capacidad adicional.
No escribe registros. Los offsets y bits se interpretan según los
[registros oficiales Linux GENI](https://github.com/torvalds/linux/blob/master/include/linux/soc/qcom/geni-se.h)
y el [driver SPI GENI](https://github.com/torvalds/linux/blob/master/drivers/spi/spi-geni-qcom.c).
Se consultó código upstream;no se obtuvo el fuente exacto del commit del
kernel instalado. La cifra33,333MHz es derivada de configuración,**no una
medición eléctrica deSCK**.

El kernel instalado tiene ftrace,kprobes y dynamicdebug desactivados,según
/boot/config. No se pudo trazar cada función interna con esas interfaces.
Debugfs permitió leer el reloj fuente;no expone una lista utilizable de
frecuencias OPP para este SPI (directorio vacío). No asumir que pedir40MHz
configure40MHz ni que pedir50MHz sea compatible con el receptor.

## Medición emparejada de la misma transacción

Firmware aislado WORD de referencia agrega callbackGPIO EXTI en ambos flancos
dePG12NSS. No llama gpio_pin_configure;verifica MODER yAFR intactos. PG13READY
conserva su función. Callback captura reloj de ciclos MCU y secuencia SPI.
Campos40/44 de DATA experimental llevan duración y secuencia de esa captura,
con CRC32 íntegro. El relay primero valida toda la trama y luego empareja la
captura deN con el ioctl deN,que se guardó al recibir la trama anterior.
No confunde el ioctl deN+1 con el intervalo reportado deN.

Dos casos30s,N3456,ADC8CH1,ticks114/112,arranques independientes. Las medias
usan las dos últimas ventanas10s completas,descartando startup (unos20s
seleccionados por caso). Cada ventana conserva cuentas,máximos y residual
con signo,incluidos los negativos si los hubiera.

| Ticks | Muestras en30s | Pares alineados | NSS medio,µs | ioctl pareado,µs | Residual medio,µs |
|---:|---:|---:|---:|---:|---:|
| 114 | 42,081,984 | 32,470 | 252.710 | 341.544 | 88.834 |
| 112 | 42,832,800 | 33,050 | 252.734 | 339.277 | 86.543 |

Total65.520 pares,100% alineados por secuencia,0mismatch y0residuales negativos.
Los dos sondeos pasaron integridad,dropped/fatal0. Total de muestras en las
ventanas30s: 84,914,784. CRC,secuencia,epoch,índices/timestamps,
rango ADC y propiedad DMA intactos. El caso112 no cumple holgura diagnóstica;
ninguno constituye aceptación de tasa por tener IRQ/perfilado adicionales.

A33,333MHz,992×8bits requieren238,080µs ideales. Los~253µs deNSS incluyen
además fases deCS/posibles pausas y latencia diferencial deISR;no se atribuye
su diferencia de~15µs a un mecanismo único. El residual fuera deNSS incluye
preparación/finalización del controlador,copias,DMA,IRQ y planificación;
no está desglosado por función ni es coste exclusivo del kernel.

NSS usa callbacks software,no captura de timer hardware ni analizador lógico.
Sus marcas tienen latencia de interrupción. Relojes MCU/Linux independientes;
se convierte MCU con160MHz nominal. No restar este residual de benchmarks
anteriores ni extrapolarlo como ganancia garantizada.

## Límites eléctricos y siguiente decisión

[ST DS13086 Rev10,tabla150](https://www.st.com/resource/en/datasheet/stm32u585ai.pdf)
separa maestro,receptor esclavo y transmisor/full-duplex esclavo. Para este
último cita41,5/25,5MHz a1,71–2,7V según pines y38,5MHz a2,7–3,6V,bajo sus
condiciones. Su nota3 condiciona el máximo al tiempo de salida del esclavo,
setup del maestro y dutycycle. No usar el máximo de maestro o receptor para
justificar50MHz en full-duplex. El [esquemático UNOQ](https://docs.arduino.cc/resources/schematics/ABX00162-schematics.pdf)
identifica PG2:15/VDDIO2 con alimentación nominal1,8V;no se midió esa tensión.

Antes de subir SCK,hay que verificar un punto de reloj representable y el
presupuesto temporal de ambos extremos. Esta campaña no demuestra que40MHz
sea alcanzable ni aceptable. La otra vía es reducir overhead por transacción,
pero agrupar ioctls exigiría conservar una autorización READY fresca para
cada tramo:la medición no autoriza saltar ese handshake. No se elige un
cambio de driver/kernel sin identificar su coste y revisar ese contrato.

## Restauración y pruebas

[Reporte completo](probe_1400_20261015_235911/report.json):
`ok/restored/restore_integrity_ok=true`. V17,relay y ADC10/1167883SPI,
generadorapagado y todos sus campos restaurados exactamente.
11,675,400 muestras íntegras en10s al cierre. Firmwareoriginal antes/después:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
App experimental detenida y relectura SPI original idéntica. Sin cambios
productivos,clockwrites ni aceptación analógica,GUI,dual,UART,RADIO/DSP.

Dos pruebas locales pasan:contadorC real conserva residuales negativos y
lector selecciona únicamente ventanas alineadas. MCU/relay compilaron y
corrieron físicamente. Hashes de fuentes MCU verificados al cierre y auditoría
incluye scripts,relay y lector fijo de registros.
