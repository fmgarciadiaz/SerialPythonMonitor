import unittest
import numpy as np
from monitor.v10.plot_fill import area_polygons


class AreaTests(unittest.TestCase):
    def test_missing_reading_closes_both_areas_vertically(self):
        x,y=area_polygons([1,2,3,4,5],[10,20,np.nan,40,50],0)
        np.testing.assert_allclose(x,[1,1,2,2,1,np.nan,4,4,5,5,4,np.nan],equal_nan=True)
        np.testing.assert_allclose(y,[0,10,20,0,0,np.nan,0,40,50,0,0,np.nan],equal_nan=True)

    def test_no_readings_or_isolated_points_have_no_area(self):
        for y in ([np.nan,np.nan],[1,np.nan,2]):
            xfill,yfill=area_polygons(np.arange(len(y)),y,0)
            self.assertEqual(len(xfill),0)
            self.assertEqual(len(yfill),0)
