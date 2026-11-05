"""Private-process diagnostic: persist Python call sites before native singleShot."""
import json
import time
import traceback


def install(path):
    from PySide6 import QtCore
    import PySide6
    with open(path,'a') as stream:stream.write(json.dumps(dict(phase='installed',qt=QtCore.qVersion(),pyside=PySide6.__version__))+'\n')
    original=QtCore.QTimer.singleShot
    sequence=0
    def traced(*args,**kwargs):
        nonlocal sequence
        sequence+=1
        event=dict(id=sequence,time=time.monotonic(),stack=traceback.format_stack(limit=8),
                   callbacks=[getattr(value,'__qualname__',type(value).__name__) for value in args])
        with open(path,'a') as stream:
            stream.write(json.dumps(dict(event,phase='enter'))+'\n');stream.flush()
        result=original(*args,**kwargs)
        with open(path,'a') as stream:stream.write(json.dumps(dict(id=event['id'],phase='returned'))+'\n')
        return result
    QtCore.QTimer.singleShot=staticmethod(traced)
    return original
