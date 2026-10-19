# 1,6000MS/s: sondeo DMA más frecuente

Hipótesis: reducir la espera entre comprobaciones del productor suaviza la disponibilidad de nodos. Único cambio MCU acquisition.h: para ADC8/period100 k_usleep(750) en vez de k_sleep(1ms); conservar demás perfiles, validación y cuatro slots. No suponer exactitud750us: medir poll_max existente. CPU2/performance/N3456/SPI40,warm112/2s. Dos pilotos30s independientes ->60+3x120 sólo ambos íntegros,margen>=10%,pico<4incluidoarranque,slackpositivo. Cortar calificación al primer fallo,sin reintentosselectivos. Restauración exacta governor/firmware/relay/config/generador/reloj ycontinuidad10s. Compilar sólo antes de medir. Perfil106 intacto.

Derivado del500us: cola2 ypollmáximo~897us, pero margen~8%;750us prueba compromiso entre menor sondeo y costo envío. No afirmar mejora sin evidencia.
