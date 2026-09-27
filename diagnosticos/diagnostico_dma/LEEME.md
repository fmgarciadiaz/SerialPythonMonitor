# Prueba de nodos DMA

El firmware normal esta en `../../sketch.ino`; esta prueba usa una copia separada. Cargar `diagnostico_dma.ino` en el Q.
Mantener el puente R4 y el cableado actuales. UART Q–R4: 1 Mbaud.
La copia toma la firma de LL_DMA_CreateLinkNode del header instalado: admite
el parametro mutable de Zephyr 0.90.0 y el parametro const de 1.0.0.
Mantener la version de core con la que se obtuvo la captura original.

1. Cerrar V5 y cualquier monitor serial que use el R4.
2. Compilar y cargar este sketch en el Q con el entorno que compila el original.
3. En una terminal, desde la raiz del proyecto y con el entorno Python habitual:
   `python3 diagnosticos/recibir_diagnostico.py`
   Esto lista los puertos. Elegir el del R4.
4. Ejecutar `python3 diagnosticos/recibir_diagnostico.py /dev/cu.usbmodemXXXX`.
5. Cuando diga "Receptor listo", reiniciar el Q. No reiniciar el R4.
6. Esperar el mensaje "Listo". Los archivos `diagnostico_*.txt` y `.bin` se guardan
   automaticamente en `capturas/diagnosticos/`, dentro del proyecto.

Si Python informa `No module named serial`, activar el entorno usado para V5
o instalar `pyserial` en el entorno elegido con `python3 -m pip install pyserial`.

No abrir V5 simultaneamente. El receptor guarda el stream binario y extrae el
texto que el Q emite solamente despues de detener TIM2. El protocolo normal se
mantiene durante la adquisicion; el volcado posterior es exclusivo de esta prueba.
El primer bloque con un dt fuera de 97–103 us no se envia como DATA: aparece
completo en el volcado de texto. La resta de timestamps tolera el wrap de uint32.

La prueba termina al detectar un timestamp anomalo, una escritura corta o al
cumplir unos 15 segundos, siempre que el hilo no este bloqueado dentro de write.
Un timeout del receptor puede indicar bloqueo, desconexion o perdida del volcado;
no demuestra ausencia de errores. A2 sigue alternando despues de detener TIM2.
Para repetir, volver a abrir el receptor y reiniciar el Q.
Para volver al funcionamiento normal, cargar el sketch original.

Revision `startup_sync_v2`: espera observar ambos DMA dentro del nodo 0, limpia
las TC iniciales y espera que ambos pasen al nodo 1 con nuevas TC antes de
consumir el nodo 0. `first_ready_us` conserva el tiempo TIM5 de esa primera
entrega, incluso si el registro circular ya descarto los eventos de arranque.
Deberia rondar 205000 us (incluye el tiempo de inicializacion desde TIM5).

Fases: S = nodo 0 activo al arrancar; F = primera entrega validada;
T = ambas TC antes de limpiarlas; B = antes de copiar; C = despues de
copiar; W = despues de enviar; X = inmediatamente despues de detener TIM2.
`elapsed_us` mide copia en C y llamadas de envio en W, no necesariamente el ultimo
bit fisico de UART. `written` debe ser 4103 en W.
Flags: bit 0 TC ADC, bit 1 TC timestamp, bit 2 DTE ADC, bit 3 DTE timestamp,
bit 4 overrun ADC. Direcciones expresadas en decimal; cada nodo ocupa 8192 bytes
en ambos buffers. Las lecturas de registros son consecutivas, no atomicas:
interpretar transiciones con el contexto anterior y posterior.
Solo las filas C incluyen las dos primeras muestras del bloque copiado.
`bad_pair` es el indice dentro del nodo seleccionado, no un contador global.

La instrumentacion agrega trabajo y puede alterar una carrera temporal. Comparar
el patron con la captura original; una corrida limpia no descarta el problema.
Solo se corrigio la sincronizacion inicial. El consumo posterior, los
descriptores y las funciones cache se preservan para aislar este cambio.
Una finalizacion por `timeout_wait` con `first_ready_us` distinto de cero puede
ser simplemente el limite de 15 segundos mientras se esperaba el siguiente nodo.
No implica por si sola un bloqueo DMA ni ausencia de picos ADC.
