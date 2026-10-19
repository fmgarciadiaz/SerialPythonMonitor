# accept cada16tramas — A/B descartado

**Decisión:conservar accept por vuelta.** Consultarlo cada16tramas con lector
activo aumentó el tiempo medio de envío por nodo **2,744% a ticks114** y
**4,609% a ticks112** en esta serieABBA. Los cuatro casos B quedaron bajo
10% de margen medio,con cola pico2 y slack positivo. No califica holgura;
no se continúa60+3×120s ni se incorpora a producción.

El rechazo de lectores adicionales funciona en ambas variantes,pero B añade
retardo visible al cierre de esas conexiones. No se demuestra una causa
específica de la regresión temporal;no hubo perfilador por etapas en este A/B.
Reducir una syscall no garantiza acortar una cadena con etapas solapadas.

## Condiciones y evidencia

[Reporte completo](probe_1400_20261015_233605/report.json):
`ok/restored/restore_integrity_ok/policy_ok=true`. `ok` significa ensayo
completado,no ganancia ni aceptación productiva. `winners` vacío.

Un mismo binario de relay,A=intervalo1,B=16,seleccionado al arrancar por
SCOPE_ACCEPT_INTERVAL. Launcher y logs por caso verificaron el valor. Sin
lector,se conserva consulta por vuelta y guard previo de ACK abandonados.
El MCU es idéntico en todos los casos:WORD corregido,PING de referencia.
Sin optimización PING,perfilador MCU o cambios de recv/send/backpressure.
No combinar este resultado con ganancias previas como si fueran aditivas.

ABBA:30s ticks114/112 por bloque,ADC8CH1,N3456,arranques independientes.
Total 339,660,864 muestras en las ocho ventanas de rendimiento,
CRC,secuencia,epoch,índice/timestamps,rango y propiedad DMA íntegros,
dropped/fatal0. Mismas tasas de adquisición en A/B;empeoró tiempo de envío,
no se afirma menor tasa ADC recibida.

| Bloque | Variante | Ticks | Muestras | Envío µs/nodo | Margen medio | Cola pico |
|---:|---|---:|---:|---:|---:|---:|
| 1 | A | 114 | 42,081,984 | 2195.631 | 10.834% | 3 |
| 1 | A | 112 | 42,832,800 | 2138.463 | 11.605% | 3 |
| 2 | B | 114 | 42,081,984 | 2257.960 | 8.302% | 2 |
| 2 | B | 112 | 42,833,664 | 2237.340 | 7.517% | 2 |
| 3 | B | 114 | 42,081,984 | 2247.414 | 8.731% | 2 |
| 3 | B | 112 | 42,832,800 | 2223.940 | 8.071% | 2 |
| 4 | A | 114 | 42,082,848 | 2189.430 | 11.086% | 3 |
| 4 | A | 112 | 42,832,800 | 2126.250 | 12.109% | 2 |

Gate definido antes de medir:ambos B por tasa íntegros y con holgura,mejora
media>=2% en ambas tasas,sin solapamiento de medias A/B. Falla en ambas.
Dos repeticiones no caracterizan toda variabilidad ni permiten atribuir la
regresión a un mecanismo de planificación específico. No se repiten sólo
los casos desfavorables para aceptar.

## Pruebas físicas de política,fuera de ventanas de rendimiento

Se abrió un primario por bloque y tres secundarios controlados por el mismo
runner sobre su túnelADB. Se bombeó continuamente el primario y se exigió
cierre del secundario en1s,sin datos y sin interrupción del primario.
Los12 secundarios fueron rechazados;ninguno recibió datos. El primario
mantuvo continuidad y completó APPLIED112 y muestras después de cada grupo.

| Variante | Rechazos correctos | Cierre secundario,ms | Primera muestra primario,ms |
|---|---:|---:|---:|
| A | 6 | 1.599–3.885 | 1.587–2.176 |
| B | 6 | 4.033–12.227 | 1.157–1.344 |

Latencias observadas desde el cliente,incluyen túnelADB,host y bombeo;
primera muestra se mide desde conexión TCP completada. No son medición
exclusiva de accept ni límites universales de admisión/rechazo. Cadencia
cada16tramas depende del ritmo de vueltas,especialmente fuera de estos
perfiles. Las sondas no compiten como dueños independientes deQ:son parte
del runner y nunca envían comandos por el secundario.

## Restauración y pruebas locales

Q restaurado exactamente aV17,relay original,ADC10/1167883SPI,generador
apagado y todos sus campos;11,675,400 muestras íntegras en10s. Firmafirmware
idéntica antes/después:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
App experimental detenida;ningún archivo o perfil productivo cambiado.

Prueba C local de política real pasó:lectores activos,inactivo,fd0,cadencia
1/16 y desborde uint32. MCU/relay compilaron y ejecutaron enQ;fuentes MCU y
configuración por caso verificadas al cierre. El gate conservador es el
mismo ya cubierto por test en el experimento PING. No aceptación analógica,
GUI,dual,UART,RADIO/FFT/FILTER ni nuevas tasas.
