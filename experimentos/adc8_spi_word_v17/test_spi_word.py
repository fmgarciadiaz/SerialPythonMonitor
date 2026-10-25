"""Host checks of BYTE/WORD register fields and unchanged frame geometry."""
from pathlib import Path
import subprocess
import tempfile
import unittest

EXP=Path(__file__).resolve().parent
SKETCH=EXP/'arduino/historico/v16/oscilloscope/sketch'


class SpiWordTests(unittest.TestCase):
    def test_both_variants_preserve_byte_frames_and_erratum_field(self):
        header=(SKETCH/'spi_word_experiment.h').read_text().replace('SPI_DMA_BYTES = 4;', 'SPI_DMA_BYTES = 1;')
        for width in (1,4):
            with self.subTest(width=width),tempfile.TemporaryDirectory() as folder:
                source=Path(folder)/'config.cpp'
                code=('#include <cstdint>\n#define DMA_CTR1_SDW_LOG2_Pos 0\n'
                      '#define DMA_CTR1_DDW_LOG2_Pos 16\n'
                      '#define SPI_CFG1_CRCSIZE_Pos 16\n#define SPI_CFG1_FTHLV_Pos 5\n')
                code+=header.replace('SPI_DMA_BYTES = 1;',f'SPI_DMA_BYTES = {width};')
                code+='\nstatic_assert((SPI_FRAME_CONFIG & 31)==7);\n'
                code+='static_assert(((SPI_FRAME_CONFIG >> 16)&31)==7);\n'
                code+=f'static_assert(((SPI_FRAME_CONFIG >> 5)&15)=={3 if width==4 else 0});\n'
                code+=f'static_assert((SPI_DMA_WIDTH & 3)=={2 if width==4 else 0});\n'
                code+=f'static_assert(((SPI_DMA_WIDTH >> 16)&3)=={2 if width==4 else 0});\n'
                code+='static_assert(992 % SPI_DMA_BYTES == 0);\nint main(){}\n'
                source.write_text(code)
                subprocess.run(['c++','-std=c++17',str(source),'-o',str(Path(folder)/'check')],check=True,capture_output=True)
                subprocess.run([str(Path(folder)/'check')],check=True)
        sketch=(SKETCH/'sketch.ino').read_text()
        cfg_lines=[line for line in sketch.splitlines() if 'SPI3->CFG1 =' in line]
        self.assertTrue(cfg_lines)
        self.assertTrue(all('SPI_FRAME_CONFIG' in line for line in cfg_lines))
        self.assertIn('channel->CTR1 = SPI_DMA_WIDTH |',sketch)
        self.assertIn('SPI3->CR2 = BLOCK_BYTES;',sketch)
        self.assertIn('config.source_burst_length = config.dest_burst_length = SPI_DMA_BYTES;',sketch)


if __name__=='__main__':unittest.main()
