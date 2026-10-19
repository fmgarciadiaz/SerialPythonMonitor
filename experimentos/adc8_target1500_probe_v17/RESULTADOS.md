# Llegar a 1,5 MS/s: arranque escalonado validado para integridad

**La vía observada es preparar ADC8/CH1 a 1.428.571,429 S/s durante 2 segundos,
bombeando y validando continuamente, y luego aplicar 1.509.433,962 S/s.**
Mantener nodo3456 y SPI40MHz, formato original kind20/864, WORDDMA,
READY fresco con spin50us y un frame por envío TCP.

El perfil escalonado completó60s +3×120s independientes con 633,597,120
muestras íntegras,dropped/fatal0. Queda aceptado para integridad en estas
condiciones, **no para holgura**:una corrida llegó a cola pico4. No se
incorporó a producción. No requiere cambios del código MCU/relay.

[Reporte completo](probe_1400_20261016_090731/report.json) y
[receta experimental](target1500_integrity_profile.json).

## Receta ensayada

1. Arrancar el relay experimental a40MHz y confirmar fuente120M/DFS6/div3.
2. Usar un único receptor, con el generador apagado.
3. Aplicar ADC8/CH1,ticks112,N3456 y esperar su APPLIED.
4. Durante al menos2s,bombear y validar todos los frames;no dormir sin leer.
5. Aplicar ticks106,N3456,esperar APPLIED y continuar leyendo/validando.

Es una secuencia de preparación del host, no una modificación del reloj ADC
ni un descarte de muestras oculto. El cambio explícito deepoch/configuración
mantiene las comprobaciones de continuidad correspondientes a cada perfil.
Se verifica reloj configurado,no SCK medido eléctricamente. Con160M yperíodo
fijo entero,106ticks es el punto superior más próximo a1,5M;107ticks daría
1.495.327,103S/s. No se introdujo jitter deperíodo para simular tasaexacta.

## Sondeo comparativo de arranque

Tres reinicios independientes de10s por esquema,en ordenABCDBCDACDAB.
Todo a106ticks/40MHz,con fuentes MCU/relay idénticas ymisma validación.

| Esquema | Preparación | Nodo | Integridad | Holgura |
|---|---|---:|---:|---:|
|A|Directo|3456|1/3|1/3|
|B|112ticks durante2s,luego106|3456|3/3|3/3|
|C|Directo|6912|2/3|0/3|
|D|112ticks durante2s,luego106|6912|3/3|0/3|

A es control diagnóstico:nuevas pantallas favorables no borran sus fallos
previos. SóloB fue elegible para validación larga. Los nodos grandes no
aportaron holgura yel arranque directo siguió siendo intermitente.
La comparación muestra viabilidad de la secuencia en estas corridas;no
prueba cuál función,frecuenciaCPU oestado interno causa la diferencia.

Se guardaron hasta512frames válidos iniciales de106 porsondeo,con recepción
host,secuencia,index,node,cola,pico,errores,send yslack. La traza cubre sólo
ese tramo,no todo el asentamiento ni tiempo exclusivo deCPU. Los frames
rechazados por elrelay se conservan enlogs ymetadatos de fallo. La traza
adicional se desactivó para las corridas largas;CRC/continuidad nunca.

## Validación sostenida del esquemaB

Cada caso reinicióMCU/relay yrepitió la preparación112/2s antes de106.
Todas las ventanas siguientes corresponden a106ticks,no a la preparación.

| Corrida | Segundos | Muestras | Margen medio envío | Cola pico | Slack mínimo µs |
|---|---:|---:|---:|---:|---:|
| finalist | 60 | 90,514,368 | 11.615% | 3 | 942.431 |
| acceptance_1 | 120 | 181,027,872 | 11.723% | 4 | 945.825 |
| acceptance_2 | 120 | 181,027,872 | 11.414% | 3 | 944.612 |
| acceptance_3 | 120 | 181,027,008 | 11.866% | 3 | 943.144 |

CRC,secuencia,epoch,índices/timestamps,rango ypropiedadDMA correctos;
no pérdidas ni erroresfatales. Los márgenes medios superan10% yslackpositivo,
pero acceptance_1 alcanzócola4. Por tanto:
`qualification_results.integrity_accepted=true`,
`qualification_results.headroom_accepted=false`;`target_qualified` no se
establece porque ese campo exige ambas cosas. No relajar el criterio decola
ni esconder el pico por ser transitorio. No600s ni reintentos selectivos.

Frente al perfil112,106 aumenta tasa nominal5,660%;frente114,7,547%.
Eso no certifica precisión analógica,GUI/DSP,dual/UART ni margen eléctrico
universal deSPI40. Es aceptación experimental de integridad condicionada
ala secuencia dearranque. No declarar resuelto todo arranque posible.

## Restauración

`ok/restored/restore_integrity_ok=true`. Se restauraron exactamente firmware,
relay/entorno,ADC8/1403508SPI ygeneradorOFF contodos sus campos originales.
14,031,360muestras íntegras en10s al cierre. Hashfirmware idéntico:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
Relojoriginal100M/DFS5/div3=33,333M confirmado. App experimental detenida.
Fuentes finales coinciden con40sostenido yhashdelrunner coincide coninicio.

La búsqueda anterior se interrumpió yrestauró al cambiar el usuario el
objetivo;su aceptación de108 ysu corrida110 parcial no se mezclan aquí.
Pendiente para robustecer este perfil:localizar yreducir el pico decola4,
sin bajar el objetivo de1,5MS/s ni afirmar que ya existe holgura suficiente.
