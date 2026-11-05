# Arduscopio Q · monitor de escritorio

Monitor de escritorio activo, basado en PySide6. Incluye
osciloscopio, generador, RADIO/FILTER, FFT, heatmap, Bode, WAV, Synth y cursores.

## Inicio

Desde la raíz del repositorio, con el entorno Python 3.13 del proyecto:

```sh
./tools/run_v20.sh
```

En VS Code, elegir **Arduscopio Q: abrir monitor**. También se puede ejecutar con el
intérprete habitual mediante `python -m monitor.v20 --gui` o abrir `app.py`
con **Run Python File**. El programa no conecta con el Q hasta pulsar Conectar.

## Dependencias

El runtime soportado es Python 3.13 con PySide6 6.11.2, pyqtgraph 0.14.0,
NumPy 2.3.1, SciPy 1.16.0, pyserial 3.5, Numba 0.62.1, mido 1.3.3 y
python-rtmidi 1.5.8. Las dependencias están enumeradas en
[`requirements.txt`](requirements.txt) y en el entorno reproducible
[`environment.yml`](environment.yml). No se cargan PyQt y PySide en un mismo
proceso.

El lanzador usa el Python 3.13 configurado para este equipo. En otra máquina,
crear el entorno del archivo YAML y definir `ARDUSCOPIO_PYTHON` con la ruta a
su ejecutable Python, o usar Run Python File con ese entorno.

## Pareja del UNO Q

V20 tiene ahora una pareja de firmware propia: **Scope V20**, con app, ruta y
relay independientes. Parte de las fuentes exactas de V18, salvo la identidad
de despliegue. El detalle y hashes están en [`arduino/v20`](../../arduino/v20/README.md).
V18 conserva su pareja **Scope V18** en `monitor/v18` y `arduino/v18`.

La pareja Scope V20 está instalada y usa un recibo propio; no depende del recibo
V18. La primera recuperación de 10,03 s y el smoke visible de adquisición/FFT
pasaron. Esto no califica todas las combinaciones ni la salida analógica.
«Preparar Q» verifica hashes y recuperación de la pareja instalada; las
actualizaciones usan respaldo y rollback. Los artefactos V18 se conservan en
`q_support/v18_reference` sólo como referencia. Una sola instancia puede
adquirir del Q a la vez.

El uso gratuito no comercial está permitido; el uso comercial requiere
contactar al autor y obtener autorización. Consultar la
[licencia](../../LICENSE.md).

## Tests y evidencia

Ejecutar la suite completa sin hardware:

```sh
python -m monitor.v20 --self-test
```

También se puede usar `python -m unittest discover -s tests/v20 -t . -v`. Los
diagnósticos nuevos se guardan bajo `diagnosticos/resultados_v20/` y las
capturas bajo `capturas/v20/`. La comparación visual y las pruebas realizadas,
junto con sus límites, se resumen en
[validación y comparación](../../docs/PYSIDE_V20_COMPARACION.md).

Los monitores anteriores siguen disponibles como respaldo desde
[Versiones](../../docs/VERSIONES.md); sus fuentes no se cargan al ejecutar V20.
