# V20: Play de Synth, diagnóstico local

No se reprodujo el Play inerte en este bloque local. Quince pruebas pasaron
en5,401s, incluyendo un clic en el botón real, recepción de estados mediante
`owner._wav_confirmed` y conservación de la petición ante IDLE previo al PLAY.
La interfaz muestra `Synth · cargando` mientras prepara y `Synth · Activo`
tras la confirmación de reproducción. Un fallo de solicitud BEGIN se conserva
visible en el estado del generador. No se modificó código de producto.

Preparación real en un proceso separado con parámetros predeterminados del
panel DX Piano/20k:1,164s; primer bloque480PCM entre842 y3279, no plano.
Otra corrida anterior con FMSource genérica tardó12,020s y produjo480PCM
entre807 y3288. Son perfiles y estados de caché distintos: no es comparación
cold/warm controlada ni mide la espera de la sesión del usuario.

La segunda captura conservó `processes_closed=false` en el límite de2s del
cierre del pool; el helper terminó después. Una inspección de procesos
posterior confirmó que no quedaba ningún Python de prueba o monitor activo.
No se accedió al Q. [Evidencia y comandos](../diagnosticos/resultados_v20/synth_play_local_20261104/tests.txt),
[PCM del panel](../diagnosticos/resultados_v20/synth_play_local_20261104/prepare_panel_defaults.json).

Falta el estado concreto de la corrida que no reproduce: si espera capacidad
o configuración, si continúa `cargando`, si hubo error del Future y si llegó
un PLAY de sesión nueva. La ausencia de señal física no permite distinguir
esas fases. No se atribuye el fallo al hardware ni se declara resuelto.

## Registro persistente de Play y un smoke físico normal

Los registros de la sesión real anterior no conservaban la intención Play ni
el motivo de espera. Se incorporó un journal por solicitud en
`diagnosticos/resultados_v20/synth_start/play_*.jsonl`: máximo64eventos
distintos, sin PCM, notas ni parámetros. Guarda clic/guards, preparación del
Future, BEGIN enviado, primer PCM y estados A0. El estado visible distingue
configuración ADC pendiente, ADC>40k, capacidad A0 no confirmada o STOP de
audio anterior. Se informa también una cancelación por conexión/modo cambiado.
No se cambiaron créditos, guards de audio, firmware ni tiempos de preparación.
Backup SHA: `respaldos/host/v20_before_synth_start_journal_20261104/manifest.json`.
Diecisiete pruebas focalizadas pasaron en5,870s.

Q estaba libre y la lectura confirmó snapshot14/32dual/SPI/genOFF/WAVIDLE e
identidad exacta V20. Un [smoke normal instalado](../diagnosticos/resultados_v20/normal_synth_journal20_20261104/report.json)
seleccionó ADC14/40k dual, Synth con DX Piano/20k predeterminado y un solo
Play. El [journal físico](../diagnosticos/resultados_v20/normal_synth_journal20_20261104/synth_start.jsonl)
registró preparación2,935s, BEGIN, primer PCM480 y ACKPLAY2,990s tras el clic.
Sostuvo20,103s desde PLAY y avanzó402.240muestras DAC; confirmó STOP de la
misma sesión3687399445. No hubo errores ni AUDIO UNDERRUN en lo observado.
No se midió salida analógica ni audición.

Al cerrar restauró exactamente el snapshot durante10,018s,313.344muestras,
cero pérdidas/fatales, actividad del receptor liberada y SHA MCU/relay iguales
antes/después. Q quedó V20 restaurada sin monitor de prueba. Esta ejecución
sí recorrió el Play real, pero no reproduce ni resuelve la inercia intermitente
del usuario; el journal permitirá localizar su siguiente caso en una fase
concreta. No hubo despliegue ni cambios de versiones anteriores.
