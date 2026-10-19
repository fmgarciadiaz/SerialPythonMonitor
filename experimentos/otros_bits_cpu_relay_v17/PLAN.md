# Candidato de relay CPU2/performance para CH1 10/12/14

Derivado de la comparación ABBA de otros_bits_cpu_v17. Copia aislada del
relay V17; sin editar tablas públicas ni firmware MCU. Activa política CPU
sólo para (10,137,5568), (12,163,4608), (14,188,1984), además del ADC8 SPI40
existente. SPI solicitado sigue38MHz y cola MCU4 para10/12/14. Se usa la
cola TCP parcial acotada ya existente para estos perfiles también.

Entrada desde ADC14/40000 para cambiar CPU sin drenar una cola de tasa alta.
CPU se prepara antes de transmitir SET_ACQUISITION y se conserva hasta el
APPLIED o REJECTED; al salir restaura governor y afinidad originales. No se
habilita aún esta receta en GUI de producción ni se prueban tasas nuevas.

Cada resolución:60s +3 arranques independientes de120s, normal40k/3s tras
cada corrida y verificación de política normal. Integridad estricta mediante
receptor V17 y NumericBatch. Holgura:media>=10%, pico<4 desdearranque yslack>0.
Cualquier fallo queda registrado y detiene la promoción; no se sustituye
por una repetición silenciosa. No ensayos600s ni compilaciónQ durante medición.

Snapshot, fuente/hash de relay, respaldo app previa, firmware SHA antes/después,
restauración de relay original (montajes/caps/entorno), ADC/generador exactos y
10s de continuidad. Un solo dueño deQ. ADC16 queda fuera de este candidato.

## Revisión del protocolo tras el primer intento

qualification_20261017_014639: ADC10 completó sus4 etapas y4 controles de
regreso3s, con margen14,31–14,37%. ADC12 pasó60s, pero su control normal3s
falló la compuerta de tasa/reloj del host. El runner anterior no guardó las
medidas antes de esa compuerta; no se atribuye a una causa específica ni se
cuenta esa etapa como aceptación completa. Reporte y logs permanecen.

La restauración inicial falló después de la ventana10s de verificación:
el relay de producción registró dropped1 durante la consulta Docker de
scheduler. Se recuperó con un nuevo arranque original, identidad comprobada
a baja carga y10s de continuidad sin procesos administrativosQ; recuperación
posterior registrada en el mismo informe. No se altera el criterio de1,6MHz.

Revisión nueva: controles normales10s, medidas siempre guardadas antes del
umbral (mismo2% de tolerancia y mismo límite de deriva), host mantenido
despierto con caffeinate y administraciónQ únicamente a baja carga en snapshot
/restauración. No se reintenta silenciosamente una corrida fallida. ADC10
se hereda explícitamente sólo tras verificar sus8 casos, hashesC, identidad
y restauración; ADC12 vuelve a empezar desde60s, seguido de3×120s, y luego
ADC14. La recetaC y las tasas no cambian entre ambos informes.

## Interferencia de segunda instancia y exclusión local

qualification_20261017_020027: ADC10 heredado tras verificar hashes e identidad.
ADC12 completó60s y dos corridas120s con holgura; el control posterior a la
segunda120s recibióEOF sin fallo de integridad en log del candidato. Durante
la recuperación OpenOCD falló al pedirGPIO swdio. Se detectó monitor local
PID5754 y app/relay de nuevo activos. No se fuerza otra recuperación mientras
esa instancia siga abierta; restauración exacta pendiente de acceso exclusivo.
La detección se registra como interferencia, no como aceptación ni límiteADC.

El autoinicio V17 y esta campaña ahora comparten board_owner: bloqueo local
por serial obtenido antes de ensure_scope y sostenido durante toda la sesión.
Si existe otro dueño, no se crea Connection ni se ejecuta autoinicio. Se
libera ante error y al salir; no se borra el archivo para evitar dos inodos
bloqueados de forma independiente. Pruebas locales cubren competencia,
liberación, placas distintas y duración de la sesión. Instancias antiguas
ya ejecutándose requieren cerrarse para que la nueva protección tenga efecto.
