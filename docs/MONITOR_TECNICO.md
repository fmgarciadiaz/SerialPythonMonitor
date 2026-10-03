# Monitor Python · funcionamiento técnico

[Proyecto](../README.md) · [Uso de V10](../monitor/v10/README.md)

## Flujo de datos

```mermaid
flowchart LR
 Q[UNO Q por USB / ADB] --> W[Worker de transporte]
 R[UNO R4 por USB serial] --> W
 W --> P[Decodificación DATA y control]
 P --> H[Historial circular: muestras y timestamps]
 P --> CSV[Registro CSV original]
 P --> B[Bode: medición de tono por pasos]
 H --> T[Trigger y ventana temporal]
 T --> D[Reducción visual según zoom y detalle]
 D --> V[Gráfica V/t]
 H --> F[FFT NumPy y normalización de ventana]
 F --> S[Espectro de hasta dos canales]
 F --> M[Heatmap con historia limitada]
 B --> C[Referencia instrumental por perfil ADC]
 C --> G[Ganancia y fase: hasta cinco barridos]
```

La interfaz y sus temporizadores pertenecen a Qt; la recepción se realiza en el
worker. Los registros incluyen índice, timestamp, ADC_IN y ADC_OUT, convertidos
a V_IN/V_OUT según el perfil confirmado. El CSV conserva muestras originales.
La frecuencia real se deriva de timestamps; FPS describe dibujo, no adquisición.

## Componentes del monitor

| Archivo | Responsabilidad |
|---|---|
| [app.py](../monitor/v10/app.py) | Ventana, recepción, historial, trigger, controles, CSV y generador |
| [spectrum.py](../monitor/v10/spectrum.py) | FFT, heatmap, ejes y escalas estables |
| [bode.py](../monitor/v10/bode.py) | Barrido, asentamiento, ajuste de tono, comparación y restauración |
| [bode_calibration.py](../monitor/v10/bode_calibration.py) | Lectura de referencia y corrección sin extrapolar |
| [transport](../transport/) | Protocolos, decodificadores y conexión |

## Bode y calibración

```mermaid
sequenceDiagram
 participant UI as Monitor
 participant Q as MCU UNO Q
 UI->>Q: Solicitar seno a frecuencia f
 Q-->>UI: APPLIED del generador
 UI->>UI: Esperar asentamiento en timestamps
 Q-->>UI: Pares A2/A3 con timestamps
 UI->>UI: Capturar ciclos elegidos y ajustar seno/coseno/DC
 UI->>UI: H = V_OUT / V_IN, siguiente frecuencia
 UI->>Q: Restaurar configuración previa al terminar o cancelar
```

El ajuste usa las dos entradas adquiridas y sus tiempos. La salida nula es
válida: ganancia −∞ dB y fase indeterminada. Una referencia A2 inválida impide
formar el cociente. La fase también puede quedar indeterminada por incertidumbre.
Las curvas tienen marcadores y relleno translúcido, sin modificar resultados.

La calibración resta ganancia en dB y fase de la referencia medida conectando
A0 a ambas entradas. Interpola en log(f), sólo dentro de su rango y con los
mismos bits/tasa. Los datos internos permanecen originales; la corrección es
visual. Cada curva añadida conserva el perfil con el que fue adquirida.

## FFT, heatmap y dibujo

FFT unilateral con amplitud pico normalizada por ganancia coherente de la
ventana; DC y Nyquist no se duplican. Se puede mostrar dBV o voltios pico.
El heatmap limita historia y trabajo por cuadro; las discontinuidades dejan
huecos. FFT puede enlazar escalas y usa margen e histéresis para evitar saltos.
El relleno llega al límite inferior de amplitud en dBV o a cero en voltios.

[Opciones y criterios completos](FFT_V10.md) ·
[Pruebas](../tests/) · [Evidencia de Bode](../diagnosticos/BODE_V10.md)
