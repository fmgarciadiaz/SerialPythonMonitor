import os
os.environ.setdefault('PYQTGRAPH_QT_LIB','PySide6')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time,unittest,subprocess,sys
from multiprocessing import shared_memory
import numpy as np
from PySide6 import QtCore,QtGui
from monitor.v20.temporal_raster import RasterProcess,paint_traces
from tools.private_raster_tiles_v20 import TiledRasterProcess

class TileTests(unittest.TestCase):
    def frame(self,style='Rápido'):
        x=np.linspace(-.2,2.2,8001);y=1.65+.2*np.random.default_rng(3).normal(size=len(x));y[199:204]=np.nan;y[800:810]+=8
        return [(x,y,'#00e5ff'),(x,3.3-y,'#ffd166')],dict(step=True,gap_cut=True,time_mode=False,dt=1.,style=style,dpr=2.)
    def wait(self,worker):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            result=worker.poll()
            if result is not None:return result
            time.sleep(.01)
        self.fail('Raster child timeout')
    def test_real_workers_exact_pixels_metadata_and_smooth_fallback(self):
        worker=TiledRasterProcess(2,RasterProcess)
        try:
            for style in ('Rápido','Intenso','Suave'):
                traces,opts=self.frame(style);rect=(0,2,0,3.3);size=(960,480);frame=object()
                self.assertTrue(worker.submit(traces,rect,size,opts,('epoch',style),frame));self.assertTrue(worker.busy)
                self.assertFalse(worker.submit(traces,rect,size,opts,'later',None))
                result=self.wait(worker);self.assertIs(result['frame'],frame);self.assertEqual(result['token'],('epoch',style));self.assertFalse(worker.busy)
                image=QtGui.QImage(*size,QtGui.QImage.Format.Format_ARGB32_Premultiplied);image.fill(QtCore.Qt.GlobalColor.transparent);paint_traces(image,traces,rect,opts)
                self.assertEqual(bytes(image.constBits()),bytes(result['image'].constBits()))
                self.assertEqual(worker.mode,'fallback' if style=='Suave' else 'tiles')
        finally:worker.close()
        self.assertTrue(all(not process.is_alive() for _,process in worker.children))
    def test_close_inflight_unlinks_arenas_and_is_idempotent(self):
        worker=TiledRasterProcess(2,RasterProcess)
        traces,opts=self.frame();worker.submit(traces,(0,2,0,3.3),(960,480),opts,1,None)
        names=[worker.pending[key].name for key in ('inputs','output')]
        worker.close();worker.close();self.assertFalse(worker.busy)
        self.assertFalse(worker.submit(traces,(0,2,0,3.3),(960,480),opts,1,None))
        for name in names:
            with self.assertRaises(FileNotFoundError):shared_memory.SharedMemory(name=name)
        self.assertTrue(all(not process.is_alive() for _,process in worker.children))

    def test_import_does_not_force_hidden_platform_on_normal_gui(self):
        env=dict(os.environ);env.pop('QT_QPA_PLATFORM',None)
        subprocess.run([sys.executable,'-c',"import os;import tools.private_raster_tiles_v20;assert 'QT_QPA_PLATFORM' not in os.environ"],env=env,check=True,capture_output=True)

    def test_background_priority_is_lowered_only_for_owned_children(self):
        worker=TiledRasterProcess(2,RasterProcess,nice_increment=10)
        try:
            traces,opts=self.frame();worker.submit(traces,(0,2,0,3.3),(960,480),opts,1,None)
            self.wait(worker)
            self.assertEqual(len(worker.last_priorities),2)
            self.assertTrue(all(value>=10 for value in worker.last_priorities))
        finally:worker.close()
