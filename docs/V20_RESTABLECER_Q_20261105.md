# Restablecer Q (V20)

Acción explícita junto a **Preparar Q**, sólo con adquisición desconectada.
Verifica el recibo privado `working_pair.json`, prueba original, BSP, fuentes
remotas y ambos SHA256, incluso si los contenedores están detenidos. Rechaza
otra Scope/App Lab activa y lectores TCP. Guarda inspect y logs antes de reset.

Reinicia la misma app con nombre fechado y el mismo contenedor relay. El comando
`arduino-app-cli app start <ruta verificada> --no-prepare` **compila/carga las
fuentes existentes**: no es un simple reinicio Linux ni una actualización. No
utiliza el destino canónico de Preparar Q ni cambia fuentes Arduino.

Una carga remota conserva UUID, PID, log y estado terminal en
`/tmp/serialmonitor-v20-recovery-<uuid>/`. El marcador local por serial bloquea
Conectar y Preparar hasta terminar. Una caída del proceso local se reconcilia
con **Restablecer**; no comienza otra carga mientras quede pendiente. Consultas
ADB agotadas no significan que terminó el uploader. Si no se obtiene estado
durante 15 s, se devuelve error conservando el marcador; un estado `running`
con proceso vivo mantiene el dueño local hasta terminar. Nunca mata herramientas
remotas. Un lock remoto adicional impide dos cargas de esta acción a la vez.

Después de verificar nuevamente los BIN, arranca el mismo relay, comprueba la
identidad completa y aplica un perfil seguro nuevo: ADC14, 40 kS/s dual, SPI,
generador OFF, WAV IDLE. Exige lectura confirmada, 10 s de continuidad, cero
CRC/drop/fatal y otra comprobación de identidad. No restaura el perfil que falló
ni conecta/reproduce automáticamente. Un fallo de verificación nunca informa
éxito. Los diagnósticos están en `diagnosticos/resultados_autoload_v20/`.

CLI equivalente:

```sh
python -m monitor.v20.q_support.recovery --serial 1060031107 --report diagnosticos/resultados_autoload_v20/restablecer_manual.json
```

## Resultado físico del 5/11

El relay había terminado con código 1 tras detectar un nodo perdido a
ADC8/2 MHz con RADIO/A0. La trama tenía CRC correcto, `dropped=1` y `fatal=0`;
Linux y la app Scope seguían activos. El rechazo de integridad se conserva:
no se ignoran pérdidas ni se reanuda reproducción automáticamente.

La recuperación real pasó: misma pareja y SHA256, ADC14/40 kS/s dual,
generador OFF, WAV IDLE, 10,028 s y 401.408 muestras continuas, sin CRC,
dropped ni fatal. La identidad se verificó nuevamente después de la lectura.
El Q quedó disponible para Conectar. Esto no acredita estabilidad sostenida
de 2 MHz con audio; esa combinación sigue siendo experimental.

[Reporte físico](../diagnosticos/resultados_autoload_v20/restablecer_manual_20261105.json) ·
[Fallo previo](../diagnosticos/resultados_v20/q_failure_20261105/report.json).

Las 23 pruebas focalizadas del motor, identidad e interfaz son offline;
complementan el ensayo físico, sin sustituirlo.
