# Estado vigente · V17 · 19/10/2026

V17 es la pareja activa: `monitor/v17`, `arduino/v17` y `tests/v17`. V16 se conserva como respaldo local; versiones anteriores en `monitor/historico` y `arduino/historico`. Los informes fechados describen lo probado entonces y no reemplazan este estado.

## Funciones y límites

| Área | Estado actual |
|---|---|
| Adquisición | A2/CH1 y A3/CH2, 8/10/12/14 bits y 16 por oversampling. Perfiles CH1 y dual según resolución. ADC8 CH1 llega a 1,6 MS/s; integridad sostenida no implica holgura ni ancho de banda analógico. |
| Generador A0 | Seno hasta 150 kHz; cuadrada hasta 200 kHz; triángulo/rampa hasta 50 kHz. Frecuencias intermedias, amplitud y offset. La frecuencia efectiva depende del timer. |
| RADIO | Recepción AM, banda RF predeterminada 8 kHz, gain manual/automático hasta ×80. US con dial extendido, alias y Scan multitasa; sin US, mapeo directo. |
| Generador Radio | Entrada RADIO o FILTER, volumen y offset en generador; salida de la señal procesada hacia A0. Protección de lazo. Estabilidad global todavía en seguimiento. |
| FILTER | Selector propio de entrada; OFF sin procesamiento de filtro. Incluye rechazo de banda y presets. |
| Análisis | Temporal, FFT, heatmap y Bode. CH1 puede permanecer visible junto a RADIO. |
| Bode | Tonos y Sweep/Chirp hasta 150 kHz; Pulso hasta 200 kHz. Final menor que 0,45 × Fs. Necesita una referencia coherente del estímulo. |
| WAV | Selector no modal que abre en `audios/`. A0 a 20/40/50 kHz con restricciones de adquisición; cortes variables siguen abiertos. |

El volumen modifica la amplitud visual de RADIO en temporal cuando se usa Generador Radio. Auto gain conserva la continuidad visual al ajustar la ganancia. El rótulo «s/holg.» se retiró de la interfaz; la limitación física sigue documentada.

## Cableado para Bode

A0 a la entrada del circuito y CH1/A2; salida del circuito a CH2/A3, masa común. CH1 conectado a antena no sirve como referencia del estímulo. CH2/CH2 permite una autocomprobación unitaria si A0 llega a CH2.

Pulso/Sweep ahora detectan el inicio usando la referencia seleccionada. Sweep dibujó 2545 y 2546 puntos válidos en pruebas físicas CH2/CH2. Tonos y Pulso no quedaron validados por esos ensayos; la ampliación de selectores de frecuencia sólo tiene comprobación local, no aceptación física de Bode a 150/200 kHz.

## Q instalado

Sólo **Scope V17** queda como app de usuario, activa. Los ejemplos del catálogo Arduino se conservan. V16 y Send1400 se exportaron con verificación ZIP y SHA256 antes de retirarlos. No se recompiló ni reinició V17 durante la limpieza.

Firmware verificado antes/después:
`96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9`.

[Informe de limpieza](../diagnosticos/resultados_v17/cleanup_apps_20261019_160438.json) · [Respaldos exportados](../respaldos/unoq/apps_retiradas_20261019_160438) · [Apps](../arduino/APPS_APPLAB.md).

Las herramientas de consola conservan V16 como valor predeterminado por compatibilidad. Para operar la versión activa indicar siempre `--version v17` o `--firmware v17`. No ejecutar preparación V16 por omisión.

## Validación y pendientes

- [Corte real RADIO/A0 ADC8/1,6 MS/s](DIAGNOSTICO_RADIO_A0_ADC8_1600_V17.md): underrun confirmado; registro ampliado, causa abierta.

- [Generador ampliado](GENERADOR_200K_V17.md): evidencia física e instalación, con límites analógicos explícitos.
- [Bode sin curvas](DIAGNOSTICO_BODE_SIN_CURVAS_V17.md): referencia, corrección y alcance de pruebas.
- [Scan y GUI atrasada](DIAGNOSTICO_SCAN_GUI_V17.md): fallos reales todavía no reproducidos consistentemente; instrumentación conservada.
- [Cortes WAV](DIAGNOSTICO_CORTES_WAV_V17.md): candidatos aislados, sin promoción de variantes no calificadas.
- [RADIO/A0 sostenido](VALIDACION_DESACOPLE_RADIO_V17.md): resultados mixtos y controles posteriores; no declarar aceptación global.
- [RADIO y US](RADIO_ANTENA_US_V17.md): recepción selectiva y escucha real pendientes.

[Plan vigente](../Plan%20de%20trabajo.md) · [Continuidad](../%23%20Continuar%20desde%20donde%20quedaste.md).
