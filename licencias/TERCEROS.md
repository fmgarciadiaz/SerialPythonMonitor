# Dependencias y materiales de terceros

La licencia no comercial de Arduscopio Q sólo cubre material original de su
autor. No cambia las licencias del software o material de terceros.

## PyQt y distribución del conjunto

V18 utiliza PyQt6. Riverbank publica PyQt bajo GPLv3 o licencia comercial:

- [Licencias de PyQt](https://www.riverbankcomputing.com/software/pyqt/intro).
- [Preguntas de licenciamiento](https://www.riverbankcomputing.com/commercial/license-faq).

No se ha acreditado en este repositorio una licencia comercial de Riverbank
ni una revisión de compatibilidad de la distribución conjunta con las
condiciones no comerciales elegidas para Arduscopio Q. Por tanto, añadir la
licencia del proyecto no certifica que se pueda redistribuir el conjunto bajo
esas condiciones. La GPL no debe interpretarse como una licencia que prohíba
por sí misma el uso comercial.

Antes de distribuir el conjunto se debe resolver la compatibilidad con PyQt:
usar una licencia de aplicación compatible con GPL o acreditar la licencia
comercial que corresponda. No se han cambiado dependencias para resolverlo
automáticamente.

Qt tiene condiciones propias, distintas de las de PyQt. También deben
conservarse y cumplirse sus avisos y las licencias de las demás dependencias
de [requirements.txt de V18](../monitor/v18/requirements.txt).
Este aviso no es un inventario completo de licencias transitivas.

## Referencias de audio

Los audios de referencia del piano mantienen su licencia independiente:
[Creative Commons Attribution 3.0](../diagnosticos/referencias_piano/LICENSE).
No se incluyen bajo la licencia no comercial del material original.

## Firmware, herramientas y bibliotecas

Arduino, Zephyr y las herramientas de la placa conservan sus licencias.
Los respaldos y las versiones congeladas se conservan sin reescribir avisos
de terceros ni atribuciones históricas.
