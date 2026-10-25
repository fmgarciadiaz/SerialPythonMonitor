# Parejas V17 y V18

Por instrucción del usuario, V17 se conserva congelada y el desarrollo pasa
completamente a V18, tanto en el monitor como en el Q.

## V17 congelada

[Respaldo pareado](../respaldos/parejas/v17_20261023_000325/manifest.json):
fuentes del monitor/firmware/relay y herramientas, app exportada del Q,
firmware binario, relay binario e inspección de sus contenedores. Cada artefacto
y fuente tiene SHA256. No se editaron `monitor/v17` ni `arduino/v17`.

Al descubrir el dispositivo, Scope V17 estaba activo y su relay ya estaba
detenido. El respaldo fue de sólo lectura; no se inventó un snapshot de
adquisición que no podía consultarse. La app V17 se conserva instalada y se
detiene para permitir activar la pareja independiente V18.

## V18 de trabajo

Monitor: `monitor/v18`. Q: `arduino/v18`, app `Scope V18` y contenedor relay
`serialmonitor-usb-stream-v18`. Las fuentes del Q parten de la base validada;
los candidatos de 1,818MS/s y demás incrementos permanecen experimentales.
La app activa del Q ya es Scope V18; la app V17 y sus respaldos se conservan.

La GUI verifica app V18 y SHA de firmware/relay antes de abrir su túnel,
no instala ni reinicia programas automáticamente. El protocolo continúa SCP1V4.
Abrir: `python -m monitor.v18 --gui`.

La landing raíz conserva badges, imágenes y explicación de módulos. Los
informes de activación y validación van en `diagnosticos/resultados_v18/`.

## Activación realizada

`diagnosticos/resultados_v18/activation_20261023_000458/report.json` registra
la creación y el primer frame verificado. V17 permanece instalada y detenida.
El relay V18 usa el mismo binario validado cuando las fuentes son idénticas,
pero tiene contenedor e identidad de app propios. El cambio de nombre del host
no se usa como evidencia de nuevas tasas ni de un protocolo distinto.

Las herramientas de los próximos sondeos V18 ya toman `arduino/v18` como base
y restauran la pareja V18. Los informes de campañas anteriores conservan sus
identidades V17 históricas; no se reescriben sus resultados.

## Incidencias de validación preservadas

Las primeras pruebas de la nueva pareja detectaron sobrecarga de RF/GUI a
8bits/1,6MS/s. Se corrigió el cierre para diferir errores hasta completar los
eventos de una lectura, y el snapshot inicial espera evidencia del transporte.
También se acotaron notificaciones de progreso WAV a20Hz; todos los ACK
internos siguen procesándose. Los informes fallidos permanecen en resultados.

La activación de la pareja independiente no se presenta como una nueva
calificación de alta carga. Las tasas públicas no se incrementaron. RADIO/WAV/
Synth y restauración se verifican también a carga moderada por separado.
