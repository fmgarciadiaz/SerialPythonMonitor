# Receptor V16

Receptor propio para SCP1 V4/992: CH1 y CH2 desde byte 84, timestamp inicial en byte 80. Tipo 3 conserva uint16 little-endian (226 pares); tipo 15 empaqueta ADC14 sin pérdida en siete bytes por dos pares (258 pares). Acepta ambos formatos. Reconstruye el tiempo usando el período confirmado y valida secuencia, índice, época, CRC, padding, rangos y fronteras de nodos. El monitor usa ConfigurationDecoder y OutputReceiver; los otros decoders son compatibilidad interna del mismo V4.

El Q conserva el control; UART/R4 recibe DATA heredado de ocho bytes por par mediante expansión explícita en el MCU. La reducción de tráfico de V16 se aplica a SPI/USB, no a UART. No conecta con un relay V3: se requiere la pareja arduino/v17.

Tipo 16: CH1 rápido, ADC14, 516 muestras por trama, cuatro muestras en siete bytes.
Los perfiles nominales 599250 y 661157 usan período/timestamps en ticks de 160 MHz (267 y 242 ticks).
El resto mantiene timestamps en microsegundos. Las respuestas de adquisición
identifican el perfil por ese período reservado; el cambio confirmado de época
reinicia continuidad. La aplicación convierte los ticks validados a microsegundos
continuos antes de dibujar o exportar; no aplica una conversión anticipada al CRC
ni a las comprobaciones de continuidad. UART queda fuera de este perfil.
