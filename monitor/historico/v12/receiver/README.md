# Receptor de adquisición y control

Este código corre en el PC y utiliza SCP1 V3 de 992 bytes. Procede de versiones
anteriores, pero sus imports y contrato están adaptados a V12.

La aplicación usa `unoq_config_receiver.py` y `unoq_config_decoder.py` para
recibir muestras, validar continuidad y controlar adquisición y generador.
`unoq_usb.py` proporciona la conexión USB/ADB y las utilidades binarias;
`unoq_switch.py`, `unoq_acquisition.py`, `unoq_generator.py` y `unoq_control.py`
definen los comandos y respuestas.

`unoq_receiver.py` y `unoq_dual.py` son módulos auxiliares de compatibilidad
para recepción con perfil fijo; no constituyen el camino de recepción de la
aplicación. La prueba de compatibilidad UART importa el parser del primero.
No confundirlos con versiones completas V7/V9 ni con el relay del MPU, ubicado
en `arduino/historico/v11_p992/relay/` desde la raíz del proyecto.
