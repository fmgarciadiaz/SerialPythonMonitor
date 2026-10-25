import socket
import unittest
from monitor.v18.io.socket_transport import SocketTransport
from monitor.v18.io.audio_pump import AudioPump
from monitor.v18.io.local_transport import LocalTransport
from monitor.v18.io.prototype import Audio
from monitor.v18.receiver.unoq_usb import ProtocolError


class SocketTests(unittest.TestCase):
    def pair(self,tcp=False,**kwargs):
        if tcp:
            listener=socket.socket();self.addCleanup(listener.close)
            listener.bind(('127.0.0.1',0));listener.listen(1)
            client=socket.create_connection(listener.getsockname(),timeout=.5)
            peer,_=listener.accept();peer.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        else:client,peer=socket.socketpair()
        self.addCleanup(peer.close);self.addCleanup(client.close)
        transport=SocketTransport(client,**kwargs);self.addCleanup(transport.close)
        return transport,peer

    def test_empty_socket_is_nonblocking_and_eof_is_distinct(self):
        transport,peer=self.pair()
        self.assertEqual(transport.socket.gettimeout(),0.)
        with self.assertRaises(BlockingIOError):transport.recv(992)
        peer.close();self.assertEqual(transport.recv(992),b'')
        transport.close();transport.close()
        with self.assertRaises(RuntimeError):transport.recv(992)

    def test_fragmented_receive_preserves_every_byte(self):
        transport,peer=self.pair();original=bytes(range(256))*7
        peer.sendall(original);received=bytearray()
        while len(received)<len(original):received.extend(transport.recv(137))
        self.assertEqual(received,original);self.assertEqual(transport.received_bytes,len(original))

    def test_tcp_disables_nagle_and_retains_nonblocking_mode(self):
        transport,peer=self.pair(tcp=True)
        self.assertNotEqual(transport.socket.getsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY),0)
        self.assertEqual(transport.socket.gettimeout(),0.)
        transport.send(b'abc');self.assertEqual(peer.recv(3),b'abc')

    def test_kernel_backpressure_returns_short_write_or_eagain_without_retry(self):
        transport,peer=self.pair();transport.socket.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,1024)
        payload=b'x'*(32*992);admitted=0;partial=False;blocked=False
        for _ in range(256):
            try:count=transport.send(payload)
            except BlockingIOError:blocked=True;break
            admitted+=count;partial|=count<len(payload)
        self.assertTrue(partial or blocked);self.assertGreater(admitted,0)
        peer.setblocking(False);received=bytearray()
        while len(received)<admitted:received.extend(peer.recv(min(32768,admitted-len(received))))
        self.assertEqual(received,b'x'*admitted)
        self.assertEqual(transport.sent_bytes,admitted)

    def test_stall_deadline_without_sleep_and_new_data_refreshes_it(self):
        now=[0.];transport,peer=self.pair(clock=lambda:now[0])
        now[0]=1.9
        with self.assertRaises(BlockingIOError):transport.recv(992)
        peer.sendall(b'a');self.assertEqual(transport.recv(992),b'a')
        now[0]=3.
        with self.assertRaises(BlockingIOError):transport.recv(992)
        now[0]=4.
        with self.assertRaises(TimeoutError):transport.recv(992)

    def test_bounds_and_unconnected_socket_are_rejected(self):
        transport,_=self.pair()
        for size in (0,True,32*992+1):
            with self.assertRaises(ValueError):transport.recv(size)
        for value in (b'',bytes(32*992+1)):
            with self.assertRaises(ValueError):transport.send(value)
        raw=socket.socket();self.addCleanup(raw.close)
        with self.assertRaises(OSError):SocketTransport(raw)

    def test_actual_loopback_tcp_runs_audio_pump_with_fragmented_peer(self):
        transport,peer=self.pair(tcp=True);peer.setblocking(False)
        model=LocalTransport();pump=AudioPump(transport);self.addCleanup(pump.close)
        now=0.
        def step():
            nonlocal now
            now+=.0001;pump.turn(now)
            try:data=peer.recv(19)
            except BlockingIOError:data=b''
            while data:
                consumed=model.send(data);data=data[consumed:]
            if model.incoming:
                try:count=peer.send(model.incoming[:23])
                except BlockingIOError:count=0
                del model.incoming[:count]
        def until(predicate):
            for _ in range(4000):
                step()
                if predicate():return
            self.fail('Loopback state not reached')
        until(lambda:pump.control.state=='ready')
        pump.begin(1,11,960,40000,now)
        pump.enqueue(Audio(1,11,0,bytes(960)));pump.enqueue(Audio(1,11,480,bytes(960)))
        until(lambda:pump.control.state=='playing')
        self.assertEqual(model.accepted,960)
        pump.stop(now);until(lambda:pump.control.state=='stopped')
        self.assertEqual(bytes(model.sent),b'');pump.close();self.assertTrue(transport.closed)

    def test_partial_frame_then_real_eof_fails_pump_without_restore_claim(self):
        transport,peer=self.pair();pump=AudioPump(transport);self.addCleanup(pump.close)
        peer.sendall(b'SCP1');pump.turn(0);peer.close()
        with self.assertRaises(ProtocolError):pump.turn(.001)
        self.assertTrue(pump.closed);self.assertEqual(pump.control.state,'fault')
        self.assertTrue(transport.closed)
