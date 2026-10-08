"""V15 SCP1 V3/992: commands and replies for selecting SPI/UART output."""
from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib
from monitor.v15.receiver.unoq_usb import ProtocolError


class Mode(IntEnum):
    SPI = 0
    UART = 1


class Phase(IntEnum):
    ACCEPTED = 1
    APPLIED = 2
    REJECTED = 3


class Reason(IntEnum):
    OK = 0
    UNSUPPORTED = 1
    BUSY = 2
    ID_CONFLICT = 3
    HARDWARE = 4


def switch_request(request_id, mode):
    if not 0x80000000 <= request_id < 0xffffffff:
        raise ValueError('Identificador de solicitud inválido')
    mode = Mode(mode)
    packet = bytearray(992)
    struct.pack_into('<4sHHII', packet, 0, b'SCP1', 3, 4, request_id, 972)
    packet[16] = mode
    struct.pack_into('<I', packet, 988, zlib.crc32(packet[:988]))
    return bytes(packet)


@dataclass(frozen=True)
class TransportReply:
    sequence: int
    request_id: int
    requested: int
    active: Mode
    phase: Phase
    reason: Reason
    boundary: int


def switch_reply(packet, request_id, requested):
    if len(packet) != 992:
        raise ProtocolError('Respuesta de transporte incompleta')
    magic, version, kind, sequence, length = struct.unpack_from('<4sHHII', packet)
    if (magic, version, kind, length) != (b'SCP1', 3, 5, 972):
        raise ProtocolError('Cabecera de control inválida')
    if zlib.crc32(packet[:988]) != struct.unpack_from('<I', packet, 988)[0]:
        raise ProtocolError('CRC de control incorrecto')
    rid, target, active, phase, reason, boundary = struct.unpack_from('<IBBBBI', packet, 16)
    if not 0x80000000 <= rid < 0xffffffff or rid != request_id or target != requested:
        raise ProtocolError('Respuesta para otra solicitud')
    if any(packet[28:988]):
        raise ProtocolError('Padding de control inválido')
    try:
        active, phase, reason = Mode(active), Phase(phase), Reason(reason)
    except ValueError as exc:
        raise ProtocolError('Estado de control desconocido') from exc
    if ((phase == Phase.REJECTED) != (reason != Reason.OK)
            or (phase != Phase.REJECTED and target not in (Mode.SPI, Mode.UART))
            or (phase == Phase.ACCEPTED and boundary != 0)
            or boundary % 2048
            or (phase == Phase.APPLIED and active != target)):
        raise ProtocolError('Estado de control contradictorio')
    return TransportReply(sequence, rid, target, active, phase, reason, boundary)
