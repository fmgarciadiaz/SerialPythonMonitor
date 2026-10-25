"""Scoped NSProcessInfo activity for diagnosis; no preferences or system changes.

Constants verified in the installed NSProcessInfo.h. Activity is ended and its
retained token released explicitly; idle system/display sleep remain permitted.
"""
import ctypes
import sys

class MacActivity:
    def __init__(self,mode='user'):
        if mode not in ('user','critical'):raise ValueError('Unknown activity mode')
        self.mode=mode;self.token=None
        if sys.platform!='darwin':return
        self.foundation=ctypes.CDLL('/System/Library/Frameworks/Foundation.framework/Foundation')
        self.objc=ctypes.CDLL('/usr/lib/libobjc.A.dylib')
        self.objc.objc_getClass.argtypes=[ctypes.c_char_p];self.objc.objc_getClass.restype=ctypes.c_void_p
        self.objc.sel_registerName.argtypes=[ctypes.c_char_p];self.objc.sel_registerName.restype=ctypes.c_void_p
        ptr=ctypes.c_void_p
        self.send=ctypes.CFUNCTYPE(ptr,ptr,ptr)(('objc_msgSend',self.objc))
        self.send_void=ctypes.CFUNCTYPE(None,ptr,ptr)(('objc_msgSend',self.objc))
        self.end=ctypes.CFUNCTYPE(None,ptr,ptr,ptr)(('objc_msgSend',self.objc))
        string=ctypes.CFUNCTYPE(ptr,ptr,ptr,ctypes.c_char_p)(('objc_msgSend',self.objc))
        begin=ctypes.CFUNCTYPE(ptr,ptr,ptr,ctypes.c_uint64,ptr)(('objc_msgSend',self.objc))
        pool=self.send(self.objc.objc_getClass(b'NSAutoreleasePool'),self.sel(b'alloc'))
        pool=self.send(pool,self.sel(b'init'))
        try:
            self.process=self.send(self.objc.objc_getClass(b'NSProcessInfo'),self.sel(b'processInfo'))
            reason=string(self.objc.objc_getClass(b'NSString'),self.sel(b'stringWithUTF8String:'),
                          b'Monitor V18 bounded acquisition diagnostic')
            options=0x00FFFFFF & ~(1<<20)  # UserInitiatedAllowingIdleSystemSleep
            if mode=='critical':options|=0xFF00000000
            token=begin(self.process,self.sel(b'beginActivityWithOptions:reason:'),options,reason)
            if not token:raise RuntimeError('NSProcessInfo activity returned no token')
            self.token=self.send(token,self.sel(b'retain'))
        finally:self.send_void(pool,self.sel(b'drain'))
    def sel(self,name):return self.objc.sel_registerName(name)
    @property
    def active(self):return self.token is not None
    def close(self):
        if self.token is not None:
            token,self.token=self.token,None
            self.end(self.process,self.sel(b'endActivity:'),token)
            self.send_void(token,self.sel(b'release'))
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
