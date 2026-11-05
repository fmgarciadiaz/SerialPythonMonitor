import json,tempfile,unittest
from pathlib import Path
from monitor.v20.synth_start_journal import SynthStartJournal


class JournalTests(unittest.TestCase):
    def test_bounded_deduplicated_scalar_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            journal=SynthStartJournal(folder)
            for _ in range(100):journal.event('waiting',reason='ADC pending',audio=[1,2,3])
            for index in range(100):journal.event('state',state=index)
            rows=[json.loads(line) for line in journal.path.read_text().splitlines()]
            self.assertEqual(len(rows),64)
            self.assertEqual(rows[0]['reason'],'ADC pending')
            self.assertNotIn('audio',rows[0])
            self.assertTrue(all(row['elapsed']>=0 for row in rows))
    def test_recording_failure_cannot_prevent_playback(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'file';file.write_text('not a directory')
            SynthStartJournal(file).event('click')


if __name__=='__main__':unittest.main()
