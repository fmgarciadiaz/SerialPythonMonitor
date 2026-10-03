# Capturas Bode V10

[20261003_021228_178271](20261003_021228_178271/): circuito real, barrido 2–100 Hz,
8 puntos; ADC 16 bits / 31,25 kHz, CSV continuo sin saltos. Incluye muestras,
puntos de ganancia/fase y captura de Qt.

[Informe y procedimiento](../../diagnosticos/BODE_V10.md). La captura no es una
calibración de fase instrumental.

[20261003_022037_325268](20261003_022037_325268/): recorrido 2–1000 Hz,
dos puntos por década, ADC 16 bits / 50 kHz; seis puntos válidos, uno inválido
por ruido en salida a 1 kHz; 528 755 filas sin saltos y restauración exacta.

[20261003_123041_538000](20261003_123041_538000/): primera referencia A0 → A2 y A3,
20 Hz–20 kHz, 31 puntos. Conserva CSV y captura; el informe JSON falló al
serializar un booleano NumPy. Usada para comparar repetibilidad.

[20261003_123118_712918](20261003_123118_712918/): referencia repetida y guardada,
31/31 puntos válidos, ADC 16 bits / 50 kHz, 583 434 filas CSV sin saltos y
restauración exacta. Calibración válida entre 20 Hz y 20 kHz para ese perfil.

Las capturas 20261003_123041_538000 y 20261003_123118_712918 fueron
**invalidadas como calibración**: el usuario informó cableado incorrecto.
Se conservan sólo como evidencia histórica.

[20261003_123522_633848](20261003_123522_633848/): nueva referencia con cableado
corregido confirmado por el usuario. 31/31 puntos entre 20 Hz y 20 kHz,
ADC 16 bits / 50 kHz, 581 579 filas CSV sin saltos y restauración exacta.
Sustituye a las referencias invalidadas.
