import unittest
from experimentos.radio_io_process_v17.adb_tunnel import AdbTunnel


IDENTITY=dict(board_serial='test-board',app='scope-v17-main-1',firmware_sha256='a'*64)


class DummySocket:
    def __init__(self):self.closes=0
    def close(self):self.closes+=1


class FakeAdb:
    def __init__(self):
        self.rows={('other-board','tcp:4500','tcp:8766'),('test-board','tcp:4600','tcp:8766')}
        self.calls=[];self.output='48000';self.usb=True
    def __call__(self,*args):
        self.calls.append(args)
        if args==('devices','-l'):
            return 'List of devices attached\ntest-board device '+('usb:1-1' if self.usb else 'transport_id:1')
        if args==('forward','--list'):return '\n'.join(' '.join(row) for row in sorted(self.rows))
        if args==('-s','test-board','forward','tcp:0','tcp:8766'):
            self.rows.add(('test-board','tcp:48000','tcp:8766'));return self.output
        if args==('-s','test-board','forward','--remove','tcp:48000'):
            self.rows.discard(('test-board','tcp:48000','tcp:8766'));return ''
        raise AssertionError('Unexpected ADB call '+repr(args))


class TunnelTests(unittest.TestCase):
    def tunnel(self,adb=None,**changes):
        adb=adb or FakeAdb();sock=DummySocket()
        def connect(address,timeout):
            self.assertEqual(address,('127.0.0.1',48000));self.assertEqual(timeout,1)
            return sock
        kwargs=dict(adb=adb,identity=lambda _:dict(IDENTITY),exclusive=lambda:True,connect=connect)
        kwargs.update(changes)
        lease=AdbTunnel('test-board',IDENTITY,**kwargs)
        return lease,adb,sock

    def test_open_close_owns_only_new_forward_and_identity_check_is_separate(self):
        lease,adb,sock=self.tunnel();before=set(adb.rows)
        lease.open();self.assertEqual(sock.closes,0)
        result=lease.close();lease.close()
        self.assertEqual(sock.closes,1);self.assertEqual(adb.rows,before)
        self.assertTrue(result['forward_released']);self.assertFalse(result['hardware_restored'])
        self.assertTrue(lease.verify_identity_after())
        with self.assertRaises(RuntimeError):lease.open()

    def test_busy_or_wrong_identity_performs_no_adb_or_connection(self):
        for changes in ({'exclusive':lambda:False},{'identity':lambda _:None},
                        {'identity':lambda _:{**IDENTITY,'firmware_sha256':'b'*64}}):
            lease,adb,sock=self.tunnel(**changes)
            with self.assertRaises(RuntimeError):lease.open()
            self.assertEqual(adb.calls,[]);self.assertEqual(sock.closes,0)

    def test_network_device_without_usb_cannot_open_forward(self):
        adb=FakeAdb();adb.usb=False;lease,_,_=self.tunnel(adb)
        with self.assertRaises(RuntimeError):lease.open()
        self.assertFalse(any('tcp:0' in row for row in adb.calls))

    def test_connect_failure_removes_only_owned_forward(self):
        def failed(*args,**kwargs):raise OSError('connect failed')
        lease,adb,_=self.tunnel(connect=failed);before=set(adb.rows)
        with self.assertRaises(OSError):lease.open()
        self.assertEqual(adb.rows,before);self.assertIsNone(lease.port)

    def test_invalid_port_output_does_not_guess_ownership_of_new_mapping(self):
        adb=FakeAdb();adb.output='bad port';lease,_,_=self.tunnel(adb);before=set(adb.rows)
        with self.assertRaises(RuntimeError):lease.open()
        self.assertTrue(before.issubset(adb.rows))
        self.assertIn(('test-board','tcp:48000','tcp:8766'),adb.rows)
        self.assertFalse(lease.close()['forward_released'])
        with self.assertRaises(RuntimeError):lease.verify_identity_after()

    def test_changed_mapping_is_never_removed_as_ours(self):
        lease,adb,_=self.tunnel();lease.open()
        adb.rows.remove(('test-board','tcp:48000','tcp:8766'))
        adb.rows.add(('other-board','tcp:48000','tcp:9999'))
        result=lease.close()
        self.assertFalse(result['forward_released']);self.assertTrue(result['errors'])
        self.assertIn(('other-board','tcp:48000','tcp:9999'),adb.rows)
        with self.assertRaises(RuntimeError):lease.verify_identity_after()

    def test_socket_transfer_keeps_forward_lease_until_owner_has_closed(self):
        lease,adb,sock=self.tunnel();lease.open();transferred=lease.take_socket()
        result=lease.close();self.assertEqual(sock.closes,0)
        self.assertTrue(result['pending_owner']);self.assertIsNotNone(lease.port)
        transferred.close();self.assertEqual(sock.closes,1)
        lease.confirm_owner_exit(True)
        self.assertTrue(lease.close()['forward_released'])
        with self.assertRaises(RuntimeError):lease.take_socket()

    def test_identity_change_after_close_is_not_restoration_success(self):
        current=[dict(IDENTITY)]
        lease,_,_=self.tunnel(identity=lambda _:current[0]);lease.open();lease.close()
        current[0]={**IDENTITY,'app':'different-app'}
        with self.assertRaises(RuntimeError):lease.verify_identity_after()

    def test_existing_forward_is_never_adopted_when_allocation_output_is_wrong(self):
        adb=FakeAdb();adb.output='4600';lease,_,_=self.tunnel(adb)
        with self.assertRaises(RuntimeError):lease.open()
        self.assertIn(('test-board','tcp:4600','tcp:8766'),adb.rows)
        self.assertFalse(any('--remove' in row for row in adb.calls))

    def test_transferred_owner_must_have_observed_exit_before_release(self):
        lease,adb,_=self.tunnel();lease.open();lease.take_socket()
        with self.assertRaises(RuntimeError):lease.confirm_owner_exit(False)
        self.assertFalse(lease.close()['forward_released'])
        lease.confirm_owner_exit(True);self.assertTrue(lease.close()['forward_released'])
