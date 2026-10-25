# Carga conjunta GUI/RADIO/FILTER/A0

Usar el mismo binario privado de la calificación ADC, sin cambiar perfiles públicos. Candidatos8/10/14/16;12 queda excluido por dropped1. Un dueñoQ, respaldo, snapshot y restauración completa al terminar.

Primera matriz:8 casos de60s (cada resolución con IN=RADIO y con IN=FILTER/rechazo50Hz), salida40kHz y FFT65536. CH1 permanece en FFT junto a RADIO/FILTER. Se mide exposición y eventos Paint reales en los viewports; no se generan capturas de pantalla. Cada caso corre en proceso separado y restaura ADC14/40k antes de nuevas operaciones administrativasQ.

Incidencias del diagnóstico, a conservar:

- La fuente RADIO tiene dos comprobaciones de adquisición: panel y feed. La primera versión privada extendió sólo la del panel. En8 y14 el feed conserva los máximos públicos y bloquea antes de reproducir. Esos casos no son aceptación ni fallo de estabilidad. La repetición corregida deberá extender ambas referencias únicamente para el perfil privado exacto.
- FFT y temporal comparten un stack y no se muestran simultáneamente. Exigir Paint en ambos con FFT seleccionada es una compuerta incorrecta del diagnóstico. Conservar resultados crudos y evaluar los repintados de la vista efectivamente visible. Probar temporal por separado.

Tras restaurar el primer intento, repetir únicamente los casos bloqueados por las guardas privadas incompletas; no repetir fallos reales de transporte/audio. Agregar30s temporales por resolución con CH1+RADIO+FILTER y salidaFILTER, manteniendo30s como exploración, no aceptación larga.

Reportar por separado ADC,dropped/fatal, audio/underrun, DSP/GUI, Paint/exposición, margen de envío/cola/slack y restauración. Los umbrales de transporte y los controles de datos no se relajan. La aceptación analógica y de escucha permanece separada.
