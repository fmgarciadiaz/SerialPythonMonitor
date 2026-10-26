# Segundo sondeo con métodos constantes · 25/10/2026

Base: pareja V18 aceptada545c/3c66, máximos CH1 8/86,10/120,12/146,14/170.
App independiente Scope V18 Rate Probe RateOnly2. V17 y producción intactas.

Candidatos:
-8 bits:85ticks,1.882.352,941S/s,bloque3488,cola8,IPCcompacto.
-10 bits:119/118ticks,1.344.537,815/1.355.932,203S/s,bloque5568,cola4.
-12 bits:145ticks,1.103.448,276S/s,bloque7488,cola4.
-14 bits:168/166/164/162/160ticks,hasta1.000.000S/s,bloque5952,cola4.

Solo listas y condiciones explícitas privadas. Se conservan relojes ADC/SPI,
resolución, sobremuestreo, DMA, packing y algoritmos. Políticas C comparadas
con producción para perfiles actuales y geometría de nuevos candidatos.

Primero15s por perfil,detención al primerfallo yrestauración exacta. Después
GUI120/RADIO/A0/ScanUS/WAV/Synth en candidatos que cumplan integridad yholgura.
La GUIhereda auxiliares actuales sinmodificar lógica producción. Las tasas
8/84,10/116y12/144ya fallaronconaudio yno se presentan como aceptadas.
No promover perfiles públicos por sondeos; requieren60+3×120s yGUI completa,
restauración,prebuild yrollback propios antesdeincorporaciónpareada.
