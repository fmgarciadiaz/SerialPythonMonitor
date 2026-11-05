import unittest
from unittest.mock import Mock
from tools.probe_spi_irq_v19 import spi_irq,restore_affinity


class SpiIrqTests(unittest.TestCase):
    def test_failed_apply_needs_no_privileged_restore_if_already_unchanged(self):
        original=dict(requested='0-3',effective='0');write=Mock()
        self.assertEqual(restore_affinity(original,lambda:dict(original),write),original)
        write.assert_not_called()

    def test_controller_retaining_effective_cpu_is_restored_explicitly(self):
        original=dict(requested='0-3',effective='0');write=Mock()
        read=Mock(side_effect=[dict(requested='2',effective='2'),
                              dict(requested='0-3',effective='2'),original])
        self.assertEqual(restore_affinity(original,read,write),original)
        self.assertEqual([c.args[0] for c in write.call_args_list],['0-3','0','0-3'])

    def test_only_unique_dedicated_controller_is_selected(self):
        self.assertEqual(spi_irq(' 116: 10 0 0 0 GICv3 364 Level 4a94000.spi\n'),116)
        for value in ('116: 10 other.spi\n','116: 10 4a94000.spi-extra\n',
                      '116: 10 4a94000.spi\n117: 1 4a94000.spi\n'):
            with self.subTest(value=value),self.assertRaises(ValueError):spi_irq(value)
