# ADC16 CH1: soporte de formato aislado antes de la búsqueda física

El formato publicado de16bits usa dos canales y sobremuestreo16 de ADC14,
con desplazamiento2. La comparación CPU mostró margen de envío77,5→80%,
por lo que el transporte no está cerca de saturarse a76226muestras/s/canal.

El pack CH1 de producción no tiene rama16bits: la rama genérica restante
codifica14bits. No se debe agregar un perfil16bitsCH1 en tablas sin corregir
primero ese empaquetado. Esta carpeta conserva una copia del header con
rama16bits explícita little-endian; no cambia archivos de producción.

Test local con AddressSanitizer/UndefinedBehaviorSanitizer: un nodo3456,
capacidad436 muestras/frame y cola final404; valores0/65535/1/32768 y patrón
no trivial. El C real empaqueta, Python comprueba los valores y alimenta el
decoder estricto V17 en modo numérico y modo stdlib con timestamps que
cruzan uint32. Padding corrupto conCRC recalculado es rechazado.
El stride1050ticks es un dato sintético del test, no una tasa aceptada ni
una propuesta física validada. No se modificó Q para estos tests.

Siguiente bloque: copiar firmware/relay completos a un proyecto aislado,
agregar esta rama y tablas de ensayo, probar primero CH1 a una tasa
conservadora manteniendo sobremuestreo16. Registrar validación de nodo,
conversión, continuidad y salida analógica por separado. No reducir
sobremuestreo para anunciar mayor tasa16bits. Mantener DMA,CRC y timestamps.
