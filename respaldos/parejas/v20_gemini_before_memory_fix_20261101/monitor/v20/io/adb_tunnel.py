"""Explicit ADB forward lease; injectable I/O, no implicit device operation.

Identity/exclusivity probes and an expected identity are mandatory. No sketch
installation, reset, ADC/generator changes, snapshot or hardware restoration.
Call from the future owner startup/teardown, never its sample-service loop.
"""
from copy import deepcopy
import re
import socket


class AdbTunnel:
    def __init__(self,serial,expected_identity,*,adb,identity,exclusive,connect=socket.create_connection):
        if not isinstance(serial,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]+',serial):
            raise ValueError('Invalid device serial')
        if (not isinstance(expected_identity,dict) or expected_identity.get('board_serial')!=serial or
                not isinstance(expected_identity.get('app'),str) or not expected_identity['app'] or
                not re.fullmatch('[0-9a-f]{64}',expected_identity.get('firmware_sha256',''))):
            raise ValueError('Complete expected identity required')
        self.serial=serial;self.expected=deepcopy(expected_identity)
        self.adb=adb;self.identity=identity;self.exclusive=exclusive;self.connect=connect
        self.socket=None;self.port=None;self.started=False;self.closed=False;self.errors=[]
        self.identity_before=None;self.identity_after=None
        self.unresolved=False;self.transferred=False;self.owner_exited=False

    def _identity(self):
        if self.exclusive() is not True:raise RuntimeError('Device exclusivity not established')
        found=self.identity(self.serial)
        if found!=self.expected:raise RuntimeError('Device identity mismatch or unavailable')
        return deepcopy(found)

    def _forwards(self):
        rows=set()
        for line in self.adb('forward','--list').splitlines():
            fields=line.split()
            if len(fields)!=3:raise RuntimeError('Malformed ADB forward list')
            rows.add(tuple(fields))
        return rows

    def _remove_owned(self):
        if self.port is None:return
        target=(self.serial,f'tcp:{self.port}','tcp:8766')
        rows=self._forwards()
        if target in rows:
            self.adb('-s',self.serial,'forward','--remove',f'tcp:{self.port}')
            if target in self._forwards():raise RuntimeError('ADB forward removal not confirmed')
        elif any(row[1]==target[1] for row in rows):
            raise RuntimeError('Forward mapping changed; replacement left untouched')
        self.port=None

    def open(self):
        if self.started or self.closed:raise RuntimeError('Tunnel lease cannot be reopened')
        self.started=True;before=None
        try:
            self.identity_before=self._identity()
            devices=self.adb('devices','-l').splitlines()[1:]
            if not any(len(f:=line.split())>=2 and f[:2]==[self.serial,'device'] and
                       any(field.startswith('usb:') for field in f[2:]) for line in devices):
                raise RuntimeError('Selected device is not available by USB/ADB')
            before=self._forwards()
            raw=self.adb('-s',self.serial,'forward','tcp:0','tcp:8766')
            if not re.fullmatch('[0-9]+',raw.strip()) or not 1<=int(raw)<=65535:
                raise RuntimeError('ADB returned an invalid allocated port')
            allocated=int(raw)
            target=(self.serial,f'tcp:{allocated}','tcp:8766')
            if target in before:raise RuntimeError('Allocated forward was already present')
            self.port=allocated
            if target not in self._forwards():raise RuntimeError('Allocated forward not confirmed')
            self.socket=self.connect(('127.0.0.1',self.port),timeout=1)
            return self
        except Exception:
            if self.port is None and before is not None:
                # A bad allocation reply gives no trustworthy ownership token.
                # Even a unique new mapping might belong to another client.
                try:
                    new=[row for row in self._forwards()-before
                         if row[0]==self.serial and row[2]=='tcp:8766']
                    if new:
                        self.unresolved=True;self.errors.append('Unattributed new forwards; none removed')
                except Exception as exc:
                    self.unresolved=True;self.errors.append(repr(exc))
            self.close();raise

    def take_socket(self):
        if self.socket is None or self.closed:raise RuntimeError('No connected socket to transfer')
        connected,self.socket=self.socket,None
        self.transferred=True
        return connected # Receiver now owns socket; lease still owns its forward.

    def confirm_owner_exit(self,exit_observed):
        if exit_observed is not True or not self.transferred:raise RuntimeError('Observed owner exit required')
        self.owner_exited=True

    def close(self):
        if self.socket is not None:
            connected,self.socket=self.socket,None
            try:connected.close()
            except Exception as exc:self.errors.append(repr(exc))
        pending_owner=self.transferred and not self.owner_exited
        if self.port is not None and not pending_owner:
            try:self._remove_owned()
            except Exception as exc:self.errors.append(repr(exc))
        self.closed=True
        return dict(forward_released=self.port is None and not self.unresolved,pending_owner=pending_owner,errors=list(self.errors),hardware_restored=False)

    def verify_identity_after(self):
        if not self.closed or self.port is not None or self.unresolved:raise RuntimeError('Close the owned forward before final identity check')
        self.identity_after=self._identity()
        return self.identity_after==self.identity_before # Identity only, not ADC/generator state.
