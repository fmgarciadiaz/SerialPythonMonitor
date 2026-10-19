# Liberación después de copiar: no resuelve1600

Cambio aislado ADC8/100ticks: liberar slot de muestras tras construir/enlistar último frame, antes de esperar transmisión. Los framesSPI mantienen propiedad hastaDMA/EOT. finish_send conserva medición take->finfísico. Cuatro slots,formatoyCRC intactos. Prueba localASAN/UBSAN confirma independencia de copias y tiempo de envío.

|Etapa|Muestras|Margenmedio|Pico|
|---|---:|---:|---:|
|screen|47972736|12.130%|3|
|screen|47971872|12.152%|2|
|finalist|95944608|12.026%|2|
|acceptance_1|191890080|11.992%|4|

Primeraobservaciónpico4a38,296sdesdeprimerframe100,enprimer120s. Integridad preservada,pero noholgura. Cortócalificación, sinreintento selectivo. No incorporación: conservar cambio sólo como experimento rechazado paraesteobjetivo. La reducción de retención no bastó para eliminar las excursiones.

Q restaurado/verificado, firmware/relay/entorno/config/generador/governor/reloj originales ycontinuidad10s. Perfil106aceptado intacto.
