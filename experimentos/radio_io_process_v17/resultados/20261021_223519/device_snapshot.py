"""Immutable state/restore contract, not a physical Q driver.

Injected backend methods must be bounded. No ADB, socket, firmware operation
or physical claim is performed by this module. Running audio/generator is not
accepted as an initial experiment baseline; live waveform phase is not saved.
"""
from dataclasses import asdict,dataclass
import re
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.unoq_wav import State


@dataclass(frozen=True)
class DeviceIdentity:
    board_serial:str
    app:str
    firmware_sha256:str
    relay_sha256:str

    def __post_init__(self):
        if (not isinstance(self.board_serial,str) or not self.board_serial or
                not isinstance(self.app,str) or not self.app or
                any(not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value)
                    for value in (self.firmware_sha256,self.relay_sha256))):
            raise ValueError('Full MCU and relay identity required')


@dataclass(frozen=True)
class Observation:
    identity:DeviceIdentity
    acquisition:Configuration
    generator:GeneratorConfig
    running:bool
    wav_state:State
    transport:Mode=Mode.SPI


@dataclass(frozen=True)
class DeviceSnapshot:
    identity:DeviceIdentity
    adc_bits:int
    adc_period:int
    generator:GeneratorConfig

    def __post_init__(self):
        if not isinstance(self.identity,DeviceIdentity) or not isinstance(self.generator,GeneratorConfig):
            raise ValueError('Typed snapshot required')
        if type(self.adc_bits) is not int or type(self.adc_period) is not int:
            raise ValueError('Exact ADC wire profile required')
        Configuration.from_wire(self.adc_bits,self.adc_period)
        if self.generator.enabled:raise ValueError('Snapshot baseline requires generator OFF')

    @property
    def acquisition(self):return Configuration.from_wire(self.adc_bits,self.adc_period)

    @classmethod
    def capture(cls,observed):
        if (observed.transport!=Mode.SPI or observed.running is not False or
                observed.wav_state not in (State.IDLE,State.DONE)):
            raise ValueError('Snapshot requires SPI, stopped audio and generator')
        return cls(observed.identity,observed.acquisition.bits,observed.acquisition.request_period,
                   GeneratorConfig(**asdict(observed.generator)))

    def to_dict(self):
        return dict(schema=1,identity=asdict(self.identity),adc_bits=self.adc_bits,
                    adc_period=self.adc_period,generator=asdict(self.generator))

    @classmethod
    def from_dict(cls,data):
        if set(data)!= {'schema','identity','adc_bits','adc_period','generator'} or type(data['schema']) is not int or data['schema']!=1:
            raise ValueError('Unsupported snapshot schema')
        return cls(DeviceIdentity(**data['identity']),data['adc_bits'],data['adc_period'],
                   GeneratorConfig(**data['generator']))

    def matches(self,observed):
        return (observed.identity==self.identity and observed.transport==Mode.SPI and
                observed.acquisition==self.acquisition and observed.generator==self.generator and
                observed.running is False and observed.wav_state in (State.IDLE,State.DONE))


def restore_contract(snapshot,backend):
    """Exercise exact restore/readback/recovery through an injected interface.

    Contract success is not physical acceptance; no live backend exists here.
    Firmware/relay must already match: this never installs or reflashes them.
    """
    result=dict(restore_contract_ok=False,hardware_restored=False,errors=[],recovery=None)
    try:
        if backend.exclusive() is not True:raise RuntimeError('Exclusive owner not established')
        before=backend.observe()
        if before.identity!=snapshot.identity:raise RuntimeError('Identity changed; no restore writes attempted')
        backend.stop_audio()
        stopped=backend.observe()
        if (stopped.identity!=snapshot.identity or stopped.wav_state!=State.IDLE or stopped.running is not False):
            raise RuntimeError('STOP not confirmed; no ADC/generator restore attempted')
        try:backend.apply_acquisition(snapshot.acquisition)
        except Exception as exc:result['errors'].append('ADC: '+repr(exc))
        # Preserve exact OFF parameters even if the ADC operation failed.
        try:backend.apply_generator(snapshot.generator)
        except Exception as exc:result['errors'].append('Generator: '+repr(exc))
        final=backend.observe()
        if not snapshot.matches(final):raise RuntimeError('Final state does not match snapshot')
        recovery=backend.recover(10)
        if (set(recovery)!= {'seconds','samples','dropped','fatal','continuous','configuration'} or
                type(recovery['seconds']) not in (int,float) or not 10<=recovery['seconds']<float('inf') or
                type(recovery['samples']) is not int or recovery['samples']<max(1,
                    snapshot.acquisition.actual_rate*recovery['seconds']-snapshot.acquisition.node_pairs-904) or
                type(recovery['dropped']) is not int or recovery['dropped']!=0 or
                type(recovery['fatal']) is not int or recovery['fatal']!=0 or
                recovery['continuous'] is not True or recovery['configuration']!=snapshot.acquisition):
            raise RuntimeError('Recovery evidence incomplete or failed')
        result['recovery']={key:value for key,value in recovery.items() if key!='configuration'}
        result['recovery']['configuration']=dict(bits=recovery['configuration'].bits,
                                               wire_period=recovery['configuration'].request_period)
        if not snapshot.matches(backend.observe()):raise RuntimeError('State changed during recovery')
        result['restore_contract_ok']=not result['errors']
    except Exception as exc:result['errors'].append(repr(exc))
    return result
