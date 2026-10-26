import unittest
from experimentos.fs_max_v18.catalog_selection import build
class CatalogSelectionTests(unittest.TestCase):
 def test_audio_and_maxima_are_preserved_without_collisions(self):
  result=build()
  maxima={8:1860465,10:1355932,12:1103448,14:1000000,16:150943}
  for b in maxima:
   rows=result['bits'][str(b)]
   self.assertLessEqual(len(rows),18)
   self.assertEqual(len(rows),len({r['rate'] for r in rows}))
   self.assertEqual(rows[-1]['rate'],maxima[b])
   audio={r['nominal_rate'] for r in rows if r['kind']=='audio'}
   self.assertEqual(audio,{44100,48000,96000,192000} if b!=16 else {44100,48000,96000})
 def test_single_extension_is_approximately_uniform(self):
  result=build()
  for b in (8,10,12,14,16):
   rows=[r['actual_rate'] for r in result['bits'][str(b)] if r['kind'] in ('single_intermediate','single_maximum')]
   gaps=[v-u for u,v in zip(rows,rows[1:])]
   self.assertLess(max(gaps)/min(gaps),1.15)
