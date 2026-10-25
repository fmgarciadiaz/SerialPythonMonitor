"""Independent local TCP emulator for process tests. No Q/ADB/Qt.

Only binds loopback in the parent fixture; server runs in its own spawn child
so holding the GUI/parent GIL cannot also freeze the emulated device.
"""
from dataclasses import asdict
import multiprocessing as mp
import socket
import time
from experimentos.radio_io_process_v17.local_transport import LocalTransport


def _serve(listener,commands,result):
    peer=None;model=None;error=None;termination=None;connection_error=None
    try:
        listener.settimeout(3);peer,_=listener.accept();listener.close()
        peer.setblocking(False);peer.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        model=LocalTransport(realtime=True,rf_enabled=False);stream_started=False
        while True:
            if commands.poll():
                command=commands.recv()
                if command=='disconnect':termination='disconnect_requested';break
                if command=='drop_acks':model.drop=True
                elif command!='disconnect':raise ValueError('Unknown fixture command')
            model.advance(time.monotonic())
            try:data=peer.recv(4096)
            except BlockingIOError:data=None
            if data==b'':termination='peer_eof';break
            if data:
                if not stream_started:
                    stream_started=True;model.rf_enabled=True;model.next_rf=time.monotonic()
                    model.advance(time.monotonic())
                while data:
                    consumed=model.send(data);data=data[consumed:]
            if model.incoming:
                try:count=peer.send(model.incoming[:619])
                except BlockingIOError:count=0
                del model.incoming[:count]
            time.sleep(.0002)
    except ConnectionResetError as exc:
        termination='peer_reset';connection_error=repr(exc)
    except BaseException as exc:error=repr(exc)
    finally:
        if peer is not None:peer.close()
        listener.close();commands.close()
        result.send(dict(error=error,termination=termination,connection_error=connection_error,state=int(model.state) if model is not None else None,
                         bits=model.config.bits if model is not None else None,
                         rate=model.config.rate if model is not None else None,
                         accepted=model.accepted if model is not None else 0,
                         played=model.played if model is not None else 0,
                         requests=model.frame_count if model is not None else 0,
                         generator=asdict(model.generator_config) if model is not None else None))
        result.close()


class TcpModelServer:
    def __init__(self):
        ctx=mp.get_context('spawn');listener=socket.socket()
        listener.bind(('127.0.0.1',0));listener.listen(1);self.address=listener.getsockname()
        reader,self.commands=ctx.Pipe(duplex=False);self.result,writer=ctx.Pipe(duplex=False)
        self.process=ctx.Process(target=_serve,args=(listener,reader,writer))
        self.process.start();listener.close();reader.close();writer.close();self.closed=None

    def connect(self):return socket.create_connection(self.address,timeout=1)

    def close(self):
        if self.closed is not None:return self.closed
        if not self.result.poll():
            try:self.commands.send('disconnect')
            except (BrokenPipeError,OSError):pass
        if not self.result.poll(3):
            self.process.terminate();self.process.join(2)
            raise RuntimeError('TCP fixture did not terminate')
        self.closed=self.result.recv();self.process.join(3)
        if self.process.is_alive():
            self.process.terminate();self.process.join(2)
            raise RuntimeError('TCP fixture exit not observed')
        self.commands.close();self.result.close();self.process.close();return self.closed
