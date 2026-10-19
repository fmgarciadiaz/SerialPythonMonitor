import unittest

from experimentos.adc8_spi40_search_v17.run import ClockSearch


class SimulatedSearch(ClockSearch):
    def __init__(self, failures=(), margins=()):
        self.screens={};self.qualified={};self.calls=[]
        self.failures=set(failures);self.margins=set(margins)
        self.report={'cases':[],'winners':{}}

    def save(self):pass

    def measure(self,ticks,seconds,stage):
        self.calls.append((ticks,seconds,stage))
        row=dict(ticks=ticks,requested_seconds=seconds,stage=stage,
                 ok=(ticks,stage) not in self.failures,
                 headroom_ok=(ticks,stage) not in self.margins,samples=1000)
        self.report['cases'].append(row)
        return row


class SearchAcceptanceTests(unittest.TestCase):
    def test_passing_retry_never_erases_original_failure(self):
        search=SimulatedSearch(failures=[(110,'screen')])
        search.search()
        self.assertTrue(search.screens[110]['failure_repeat_ok'])
        self.assertNotIn(110,search.report['eligible_ticks'])
        winner=search.report['winners']['8']['best_integrity_above_reference']
        self.assertEqual(winner['ticks'],111)
        self.assertEqual([n for t,n,s in search.calls if s.startswith('acceptance') or s=='finalist'],[60,120,120,120])

    def test_integrity_and_headroom_can_select_different_profiles(self):
        search=SimulatedSearch(failures=[(108,'screen'),(108,'repeat_failure')],
            margins=[(109,stage) for stage in ('screen','finalist','acceptance_1','acceptance_2','acceptance_3')])
        search.search()
        winners=search.report['winners']['8']
        self.assertEqual(winners['best_integrity_above_reference']['ticks'],109)
        self.assertFalse(winners['best_integrity_above_reference']['headroom_accepted'])
        self.assertEqual(winners['best_headroom_above_reference']['ticks'],110)
        self.assertTrue(winners['best_headroom_above_reference']['headroom_accepted'])

    def test_failed_long_run_stops_profile_and_uses_slower_candidate(self):
        search=SimulatedSearch(failures=[(108,'screen'),(108,'repeat_failure'),(109,'finalist')])
        search.search()
        self.assertEqual([stage for tick,_,stage in search.calls if tick==109],['screen','finalist'])
        self.assertEqual(search.report['winners']['8']['best_integrity_above_reference']['ticks'],110)
        self.assertLessEqual(max(seconds for _,seconds,_ in search.calls),120)


if __name__=='__main__':unittest.main()
