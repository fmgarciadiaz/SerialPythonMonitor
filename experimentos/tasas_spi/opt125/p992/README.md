# Scope Opt125 P992

Pareja fija experimental SCP1 V3: firmware, relay y receptor de esta carpeta deben utilizarse juntos. Sin negociación ni compatibilidad V2. App Scope Opt125 P992; remoto /home/arduino/ArduinoApps/scope-opt125-p992; contenedor serialmonitor-opt125-p992; TCP 8766 (uso exclusivo con P512).

Contrato en manifest.json: 992 bytes, payload 972, CRC en 988, muestras desde 80, máximo 113 pares. Nodo 2048 = 18*113+14: 19 fragmentos. Padding cero de 4 bytes en completos y 796 en último. TSIZE992 respeta límite1023 y alineación32. SPI32MHz, cola4, coordinación/ADC/generador/ownership/semáforos/prioridades iguales a P512. A2/A3 entradas ADC, A0 salida DAC.

No se incluye diagnóstico en DATA. Variante instrumentada y medición física separadas. [Validación física del 4 de octubre](../README.md): margen medio >10 %, dos capturas de 120 s a 14 bits/125 kHz, transiciones y monitor con USB real aprobados. Sigue como candidato experimental independiente.

Pruebas reproducibles desde cualquier cwd: `python3 /ruta/al/repo/tests/test_opt125_p992.py`. Compilan ejecutables host C++/C temporales y cruzan golden con Python, fragmentación TCP, nodo completo, comandos/control y rechazo de corrupción. Firmware y relay ARM compilados; evidencia de placa enlazada arriba. [Comparación analógica de ambos canales aprobada](../ANALOGICO.md) a 14 bits con seno ~2 kHz; calibración absoluta y otros estímulos no evaluados.
