## Estado actual: integrado e instalado

Ver [resultado final](../../docs/GENERADOR_200K_V17.md). El texto inferior conserva la preparación histórica del prototipo.

# Candidato de temporización del generador V17

Alcance: generador normal; seno hasta150kHz y cuadrada hasta200kHz.
No afecta RADIO/WAV/Radio Test. Producción y Q intactos.

Prototipo aislado de protocolo MCU y selección de puntos; no es una versión
completa instalable. Host, relay y UI todavía conservan50kHz. No desplegar estos
headers solos: validadores deben coincidir antes de un ensayo físico.

Verificación local:

```
c++ -std=c++17 -I experimentos/generador_200k_v17/include experimentos/generador_200k_v17/timing_probe.cpp -o /tmp/generador_200k_timing
/tmp/generador_200k_timing
```

Resultado: cuadrada50%100/200kHz exactos,150kHzreal150093.809Hz.
Seno100kHz10puntos exactos;150kHz6puntos,real149812.734Hz(-0.124844%).
PresupuestoDAC<=1Mactualizaciones/s; tablas<=50kHz conservan selección previa.
Triángulo/rampa/pulso quedan50kHz. Los números son temporización ideal, no
calidad analógica ni prueba DMA conjunta. Cuadrada con duty variable pendiente.

Siguientes pasos: candidato completo host/relay/UI aislado con límites por onda,
pruebas de validación y sweep, compilación MCU, respaldo/identidad Q y ensayo
A0→entrada con captura suficiente. Medir amplitud/THD/alias y adquisición conjunta;
restaurar firmware/configuración después. No promover seno150kHz sin medirlo.

Medición física completada: [resultados](probe_20261019_144937/RESULTADOS.md), [ondas capturadas](probe_20261019_144937/waveforms.png). Q restaurado; candidato no incorporado a interfaz.
