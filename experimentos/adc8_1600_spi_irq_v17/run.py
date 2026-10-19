"""Isolated SPI40 sustained integrity/headroom validation; no electrical qualification."""
import errno
import hashlib
import json
from pathlib import Path
import signal
import select
import socket
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.adc8_ping_word_v17.run import PingProbe,optimized,TimingDecoder
import experimentos.maxfreq_v16.contract as original_contract
import struct
from experimentos.maxfreq_v16.contract import Session
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_generator import GeneratorConfig
from tools.unoq import Board
from spi_benchmark import IMAGE

EXP=Path(__file__).resolve().parent
optimized.EXP=EXP
optimized.send.EXP=EXP


class StartupDecoder(TimingDecoder):
    target_ticks=106
    enabled=True
    latest=None
    def __init__(self):
        super().__init__();self.trace_buffer=bytearray();self.trace=[];self.trace_started=None;self.last_peak=None;self.last_queue=None;self.settle_status=None
        StartupDecoder.latest=self
    def feed(self,data):
        self.trace_buffer.extend(data)
        while len(self.trace_buffer)>=992:
            p=bytes(self.trace_buffer[:992]);del self.trace_buffer[:992]
            super().feed(p)
            if self.enabled and struct.unpack_from('<H',p,6)[0]==20 and self.status and self.status['ticks']==self.target_ticks:
                stamp=time.monotonic()
                peak=self.status['queue_peak'];queue=self.status['queue']
                if self.last_peak==peak and not (queue>=3 and self.last_queue!=queue):
                    self.last_queue=queue
                    continue
                self.last_peak=peak;self.last_queue=queue
                if self.trace_started is None:self.trace_started=stamp
                self.trace.append([round((stamp-self.trace_started)*1e6,3),
                    struct.unpack_from('<I',p,8)[0],struct.unpack_from('<I',p,52)[0],
                    struct.unpack_from('<I',p,72)[0],self.status['queue'],self.status['queue_peak'],
                    self.status['dropped'],self.status['fatal'],self.status['send_ticks'],
                    self.status['slack_ticks'],struct.unpack_from('<I',p,112)[0]])

    def reset_metrics(self):
        if hasattr(self,'trace') and self.status and self.status.get('ticks')==self.target_ticks:
            self.settle_status=dict(self.status)
        super().reset_metrics()

class StartupSession(Session):
    warm=False
    latest=None
    def __init__(self,connection):
        super().__init__(connection);self.warm_steps=[];StartupSession.latest=self
    def configure(self,bits,ticks,n):
        if self.warm and ticks in (106,104,102,100):
            step=dict(profile=[bits,112,n],phase='configure',samples=0);self.warm_steps.append(step)
            super().configure(bits,112,n);step['phase']='settle'
            before=self.decoder.pairs;end=time.monotonic()+2
            while time.monotonic()<end:self.pump()
            step.update(profile=list(self.decoder.profile),samples=self.decoder.pairs-before,phase='ready')
        return super().configure(bits,ticks,n)

original_contract.Decoder=StartupDecoder
optimized.send.sweep_module.Session=StartupSession

def start_relay(board,target):
    interval=board.config.get('experiment_spi_hz',38000000)
    optimized.send.usb_stream.stop(board)
    board.shell('docker','run','-d','--name',optimized.send.usb_stream.CONTAINER,
        *(['--cpuset-cpus',str(board.config['experiment_cpu'])] if board.config.get('experiment_cpu') is not None else []),
        '--network','host','--read-only','--cap-drop','ALL','--cap-add','SYS_NICE',
        '--env','SCOPE_EXPERIMENT_RT=1','--env',f'SCOPE_SPI_HZ={interval}',
        '--security-opt','no-new-privileges','--user','0:0',
        '--device','/dev/spidev0.0:/dev/spidev0.0:rw',
        '--device','/dev/gpiochip1:/dev/gpiochip1:rw',
        '--mount',f'type=bind,src={target},dst=/work/unoq_stream,readonly',
        '--entrypoint','/work/unoq_stream',IMAGE)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        log=board.run('shell','docker logs '+optimized.send.usb_stream.CONTAINER+' 2>&1',capture=True).stdout
        if ('SPI ready: first verified frame' in log and 'SCHED_FIFO priority 10' in log
            and f'Experimental SPI requested={interval} Hz' in log):
            info=board.shell('docker','exec',optimized.send.usb_stream.CONTAINER,'cat','/proc/1/status','/proc/1/sched',capture=True).stdout
            allowed=next(line.split(':',1)[1].strip() for line in info.splitlines() if line.startswith('Cpus_allowed_list:'))
            cpu=board.config.get('experiment_cpu')
            if allowed != ('0-3' if cpu is None else str(cpu)):raise RuntimeError(f'Unexpected effective CPU affinity {allowed}')
            board.config['_affinity_start']=dict(allowed=allowed,process=info,
                interrupts=board.shell('cat','/proc/interrupts',capture=True).stdout)
            return
        time.sleep(.2)
    raise RuntimeError('Relay did not confirm interval, scheduler and first frame')


optimized.send.sweep_module.start_relay=start_relay
optimized.send.probe_module.start_relay=start_relay


class Target1500Probe(PingProbe):
    def __init__(self):
        super().__init__()
        cfg=dict(self.candidate.config)
        cfg.update(local_app='experimentos/adc8_1600_spi_irq_v17/arduino/v16/oscilloscope',
                   experiment_spi_hz=40000000)
        self.candidate=Board(cfg)
        self.report['runner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.report['changes']=['Only SPI requested clock38/40MHz; source/DFS verification without cache','Original kind20 payload864 and WORD DMA; no compact format or TCP batching']
        self.variant='B'
        self.report.update(revision='adc8_1600_spi_irq_v17',
            changes=['Only SPI IRQ123 affinity original vsCPU2; MCU/relay identical to validated106',
                     'Fixed100ticks N3456 CPU2 performance SPI40 warm112/2s'],
            schemes={'A':dict(warm=True,node=3456,cpu=2,governor='performance',ticks=100,spi_irq='original'),
                     'B':dict(warm=True,node=3456,cpu=2,governor='performance',ticks=100,spi_irq='2')},
            plan=dict(order=list('ABBA'),screen_seconds=30,qualification_seconds=[60,120,120,120],electrical_acceptance=False))

    governor_path='/sys/devices/system/cpu/cpufreq/policy0/scaling_governor'

    def governor(self):
        return self.stable.shell('cat',self.governor_path,capture=True).stdout.strip()

    def set_governor(self,value):
        if value not in ('schedutil','performance'):raise ValueError('Unexpected governor')
        self.stable.shell('docker','run','--rm','--read-only','--network','none',
            '--cap-drop','ALL','--user','0:0','--mount',
            f'type=bind,src={self.governor_path},dst=/governor',
            '--entrypoint','sh',IMAGE,'-c',f'printf %s {value} > /governor')
        if self.governor()!=value:raise RuntimeError('Governor did not apply')

    def cpu_snapshot(self):
        return self.stable.run('shell',"for f in /sys/devices/system/cpu/cpufreq/policy0/affected_cpus /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq /sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq /sys/devices/system/cpu/cpufreq/policy0/stats/time_in_state /sys/class/thermal/thermal_zone*/temp; do echo \"$f\"; cat \"$f\" 2>/dev/null || true; done",capture=True).stdout

    irq_path='/proc/irq/123/smp_affinity_list'

    def irq_affinity(self):
        return self.stable.shell('cat',self.irq_path,capture=True).stdout.strip()

    def set_irq(self,value):
        if value not in ('0-3','0','2'):raise ValueError('Unexpected SPI IRQ affinity')
        self.stable.shell('docker','run','--rm','--read-only','--network','none',
            '--cap-drop','ALL','--cap-add','SYS_NICE','--user','0:0','--mount',
            f'type=bind,src={self.irq_path},dst=/affinity',
            '--entrypoint','sh',IMAGE,'-c',f'printf %s {value} > /affinity')
        if self.irq_affinity()!=value:raise RuntimeError('SPI affinity did not apply')

    def trial(self,*args,**kwargs):
        row=super().trial(*args,**kwargs)
        row['affinity_start']=self.candidate.config.get('_affinity_start')
        row['interrupts_after']=self.candidate.shell('cat','/proc/interrupts',capture=True).stdout
        row['spi_requested_hz']=self.candidate.config['experiment_spi_hz']
        self.logs(f"case_{len(self.report['cases'])-1:02d}_relay.log")
        self.save()
        return row

    def load(self,variant):
        self.variant=variant
        self.candidate.config['experiment_spi_hz']=self.report['relay_spi_hz'][variant]
        self.fast_reset()

    def configuration(self,name):
        out=self.stable.shell('docker','run','--rm','--read-only','--network','none',
            '--cap-drop','ALL','--cap-add','SYS_RAWIO','--security-opt','no-new-privileges',
            '--user','0:0','--device','/dev/mem:/dev/mem:r',
            '--mount','type=bind,src=/tmp/serialmonitor-spi-read-config.py,dst=/reader.py,readonly',
            '--mount','type=bind,src=/sys/kernel/debug/clk/gcc_qupv3_wrap0_s5_clk_src/clk_rate,dst=/clock_rate,readonly',
            '--mount','type=bind,src=/sys/kernel/debug/clk/gcc_qupv3_wrap0_s5_clk/clk_rate,dst=/branch_rate,readonly',
            '--entrypoint','python3',IMAGE,'/reader.py',capture=True).stdout
        (self.folder/name).write_text(out)
        data=json.loads(out)
        snapshots=data['snapshots']
        if not all(x==snapshots[0] for x in snapshots):raise RuntimeError('Unstable SPI clock snapshot')
        div=(snapshots[0]['serial_clock_config']>>4)&4095
        if not div or data['source_hz_before']!=data['source_hz_after']:raise RuntimeError('Unstable source clock')
        data['configured_hz']=data['source_hz_before']/div
        data['gcc_active_level']=(data['gcc_dfs_control']>>1)&15
        if data['gcc_active_level']!=snapshots[0]['clock_select']:raise RuntimeError('GENI/GCC DFS levels disagree')
        return data

    def measure(self,scheme,seconds,stage):
        spec=self.report['schemes'][scheme]
        self.set_governor(spec['governor'])
        self.set_irq(self.report['original_spi_irq_affinity'] if spec['spi_irq']=='original' else spec['spi_irq'])
        cpu_before=self.cpu_snapshot()
        self.candidate.config['experiment_cpu']=spec['cpu']
        StartupSession.warm=spec['warm'];StartupDecoder.enabled=True;StartupDecoder.target_ticks=spec['ticks']
        row=self.trial(8,spec['ticks'],spec['node'],seconds,stage,restart=True)
        row['cpu_before']=cpu_before;row['cpu_after']=self.cpu_snapshot()
        row['spi_irq_affinity']=self.irq_affinity()
        row['spi_irq_effective']=self.stable.shell('cat','/proc/irq/123/effective_affinity_list',capture=True).stdout.strip()
        if spec['spi_irq']=='2' and row['spi_irq_effective']!='2':raise RuntimeError('SPI effective CPU mismatch')
        row['governor']=self.governor();row['scheme']=scheme;row['warm']=spec['warm'];row['cpu']=spec['cpu']
        row['warm_steps']=StartupSession.latest.warm_steps if StartupSession.latest else []
        if StartupDecoder.latest:
            name=f"case_{len(self.report['cases'])-1:02d}_startup_trace.json"
            (self.folder/name).write_text(json.dumps(dict(columns=['host_us','sequence','index','node',
                'queue','peak','dropped','fatal','send_ticks','slack_ticks','produced'],
                rows=StartupDecoder.latest.trace,settle_status=StartupDecoder.latest.settle_status),indent=2))
            row['startup_trace']=name
        row['configuration']=self.configuration(f"case_{len(self.report['cases'])-1:02d}_configuration.json")
        row['clock_matches']=abs(row['configuration']['configured_hz']-40000000)<1
        self.save()
        if not row['clock_matches']:raise RuntimeError('SPI40 configuration mismatch')
        return row

    def run_probe(self):
        self.save()
        try:
            self.report['original_spi_irq_affinity']=self.irq_affinity()
            self.report['original_spi_irq_effective']=self.stable.shell('cat','/proc/irq/123/effective_affinity_list',capture=True).stdout.strip()
            self.report['original_governor']=self.governor()
            if self.report['original_governor']!='schedutil':raise RuntimeError('Unexpected initial CPU governor')
            self.save()
            self.stable.run('push',str(EXP/'read_config.py'),'/tmp/serialmonitor-spi-read-config.py')
            self.report['initial_configuration']=self.configuration('initial_configuration.json')
            self.prepare();self.candidate.start()
            start_relay(self.candidate,self.deployment['candidate_relay'])
            for scheme in self.report['plan']['order']:
                self.measure(scheme,30,'irq_pilot')
            pilots=[r for r in self.report['cases'] if r['scheme']=='B']
            eligible=len(pilots)==2 and all(r['ok'] and r.get('headroom_ok',False) for r in pilots)
            self.report['pilot_eligible']=eligible;self.save()
            if eligible:
                rows=[]
                for stage,seconds in [('finalist',60),('acceptance_1',120),('acceptance_2',120),('acceptance_3',120)]:
                    row=self.measure('B',seconds,stage);rows.append(row)
                    if not row['ok'] or not row.get('headroom_ok',False):break
                result=dict(governor='performance',cpu=2,spi_irq_cpu=2,ticks=100,rate=1600000,node=3456,warm=True,
                    integrity_accepted=len(rows)==4 and all(r['ok'] for r in rows),
                    headroom_accepted=len(rows)==4 and all(r['ok'] and r.get('headroom_ok',False) for r in rows))
                self.report['qualification_results']=[result];self.save()
                if result['headroom_accepted']:self.report['target_qualified']=result
            self.report['ok']=True
        except BaseException as exc:
            self.report['error']=str(exc) or type(exc).__name__
            print('EXPERIMENT ERROR',repr(exc),flush=True)
        finally:
            try:
                original=self.report.get('original_spi_irq_affinity')
                if original is not None:self.set_irq(original)
                self.report['restored_spi_irq_affinity']=self.irq_affinity()
                self.report['irq_restored']=self.report['restored_spi_irq_affinity']==original
                self.report['restored_spi_irq_effective']=self.stable.shell('cat','/proc/irq/123/effective_affinity_list',capture=True).stdout.strip()
            except BaseException as exc:self.report['irq_restore_error']=str(exc)
            try:
                if self.report.get('original_governor')=='schedutil':self.set_governor('schedutil')
                self.report['restored_governor']=self.governor()
                self.report['governor_restored']=self.report.get('original_governor')==self.report['restored_governor']
            except BaseException as exc:self.report['governor_restore_error']=str(exc)
            if self.switched:
                try:
                    self.restore()
                    self.report['restored_configuration']=self.configuration('restored_configuration.json')
                except BaseException as exc:self.report['restore_error']=str(exc)
            else:self.report['restored']=True
            self.save()
        print('REPORT',self.folder/'report.json','OK',self.report['ok'],'RESTORED',self.report['restored'],flush=True)
        return 0 if self.report['ok'] and self.report['restored'] and self.report.get('governor_restored') and self.report.get('irq_restored') else 1


def interrupted(signum,frame):raise KeyboardInterrupt(f'signal {signum}')


if __name__=='__main__':
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    raise SystemExit(Target1500Probe().run_probe())
