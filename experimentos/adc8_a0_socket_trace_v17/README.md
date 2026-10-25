# Recepción host y entrega completa de ACK al socket

Copia experimental de command_tails y host_timing; sin cambios de producción,
créditos, protocolo ni política de colas. El runner verifica las fuentes
heredadas y permite diferencias sólo en cmd_trace.h, frame_send_queue.h y
unoq_config_stream.c. Requiere el SHA256 revisado del binario Linux antes
de la campaña; no reutilizar el hash del relay anterior.

El host obtiene FIONREAD antes y después de cada lectura original. Conserva
128 lecturas recientes y las ocho más lentas. No consume bytes para medir;
registra errores y vuelve a lanzar la excepción original. Dos ioctl por
lectura agregan sobrecarga experimental que debe considerarse al comparar.
El hijo aplica y restaura el parche Connection.read con un context manager;
guarda socket_trace en su resultado incluso al fallar.

El relay registra por RID ack_socket_complete_ns cuando send acepta el
último byte de la trama, tanto en camino directo como tras envíos parciales.
EAGAIN no produce una falsa finalización. La traza congelada admite esta
anotación posterior para los ACK ya pendientes. Nueva etapa acotada top8:
ack_rx_to_socket_complete. No imprime durante alta adquisición.

Esto mide aceptación por el socket local, NO llegada física al host. FIONREAD
no identifica qué bytes son ACK ni reconstruye su historial de llegada.
No restar timestamps absolutos de host y Q.

```sh
.venv-v13/bin/python -m unittest experimentos.adc8_a0_socket_trace_v17.test_socket_trace experimentos.adc8_a0_socket_trace_v17.test_relay_trace -v
```

Validación local: tres tests pasan, incluido parcial+EAGAIN, finalización
posterior al freeze, preservación de bytes/excepciones y memoria acotada.
Compilación Linux completa aprobada (-Wall/-Wextra/-Werror), binario
4aa0b54e9f64ed61f3a4da42e0a51833eb4501edb4a61d14e0884ee85a34d421.
Ensayos físicos y sus límites se registran en
[el diagnóstico](../../docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md). Ninguna tasa
ni relay nuevos fueron promovidos.

ReadyRead (`--fast-read`) se probó de forma aislada: pasa120s de audio, pero
no demuestra holgura. El duplicado se cierra con su conexión original; se
canceló un prototipo previo que no cumplía ese contrato, conservando su nota.

GuiTrace separa callbacks de render, entrega de lotes y etapas FFT, con
tiempo de pared/CPU, top8 y128 eventos lentos. GcTrace observa colecciones
sin cambiar su política. Esos relojes requieren el Python3.13 real del
proyecto; el Python3.10 local carece de time.thread_time en este equipo.

`--fft-workspace` fue el candidato matemáticamente equivalente incorporado
luego de pruebas numéricas y físicas; evita un temporal de4×65536 doubles
al quitar DC. Su benchmark mide preparación FFT, no toda la aplicación.
