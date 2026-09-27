import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from diagnosticos.analizar_captura import read_file


class CaptureFormatTests(unittest.TestCase):
    def test_comma_tab_and_legacy_decimal_comma(self):
        for content in (
            'Muestra,Tiempo_us,ADC_IN,V_IN,ADC_OUT,V_OUT\n0,100,20,0.25,40,0.5\n',
            'Muestra, Tiempo_us, ADC_IN, V_IN, ADC_OUT, V_OUT\n0, 100, 20, 0.25, 40, 0.5\n',
            'Muestra\tTiempo_us\tADC_IN\tV_IN\tADC_OUT\tV_OUT\n0\t100\t20\t0.25\t40\t0.5\n',
            '0 100 20 0,25 40 0,5\n',
        ):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'capture.csv'
                path.write_text(content, encoding='utf-8-sig')
                rows, bad = read_file(path)
                self.assertEqual(bad, [])
                self.assertEqual(len(rows), 1)
                self.assertEqual((rows[0]['idx'], rows[0]['ts'], rows[0]['vin'], rows[0]['vout']),
                                 (0, 100, .25, .5))


if __name__ == '__main__':
    unittest.main()
