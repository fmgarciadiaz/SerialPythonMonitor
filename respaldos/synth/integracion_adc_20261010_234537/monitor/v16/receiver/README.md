# Receptor V16

Receptor propio para SCP1 V4/992: CH1 y CH2, uint16 little-endian desde byte 84, timestamp inicial en byte 80. Reconstruye el tiempo usando el período confirmado y valida secuencia, índice, época, CRC, padding, rangos y fronteras de nodos. El monitor usa ConfigurationDecoder y OutputReceiver; los otros decoders son compatibilidad interna del mismo V4.

El Q conserva el control; UART/R4 recibe DATA heredado de ocho bytes por par mediante expansión explícita en el MCU. La reducción de tráfico de V16 se aplica a SPI/USB, no a UART. No conecta con un relay V3: se requiere la pareja arduino/v16.
