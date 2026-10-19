import unittest
import numpy as np
from monitor.v17.history import SampleHistory

class HistorySearchTests(unittest.TestCase):
    def test_search_matches_numpy_after_wrap_and_duplicates(self):
        for capacity in (1,7,100):
            history=SampleHistory(capacity)
            for offset in range(0,300,13):
                history.extend(np.arange(offset,offset+13)//3)
                logical=history.window(0,len(history))
                for side in ('left','right'):
                    for value in (logical[0]-1,logical[0],logical[-1],logical[-1]+1,float(np.mean(logical))):
                        self.assertEqual(history.searchsorted(value,side),np.searchsorted(logical,value,side))
        history.clear();self.assertEqual(history.searchsorted(0),0)
