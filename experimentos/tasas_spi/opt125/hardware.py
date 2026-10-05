#!/usr/bin/env python3
"""Build and operate only explicitly named opt125 resources. Run by the coordinator."""
import argparse,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from unoq import Board
from spi_benchmark import BUILD_IMAGE,IMAGE

def board_for(variant):return Board(json.loads((HERE/variant/'unoq.json').read_text()))
def sources_digest(board):
    sources=board.check_sources()
    digest=hashlib.sha256(b''.join(str(p.relative_to(board.local)).encode()+p.read_bytes() for p in sources)).hexdigest()[:20]
    return sources,'/home/arduino/.cache/serialmonitor/opt125/fw-'+digest

def compile_firmware(board):
    sources,folder=sources_digest(board);board.push_sources(sources,folder+'/source')
    result=board.shell('arduino-cli','compile','--fqbn',board.config['fqbn'],'--build-path',folder+'/build',folder+'/source/sketch',capture=True)
    print(result.stdout)
    (HERE/'resultados').mkdir(exist_ok=True)
    (HERE/'resultados'/('compile_'+board.config['name'].replace(' ','_')+'.txt')).write_text(result.stdout)
    print(folder)
    return folder

def relay_binary(board,variant,build=False):
    local=HERE/variant/'relay'
    sources=sorted(local.glob('*.[ch]'));digest=hashlib.sha256(b''.join(p.name.encode()+p.read_bytes() for p in sources)).hexdigest()[:20]
    folder='/home/arduino/.cache/serialmonitor/opt125/relay-'+digest
    if build:
        for p in sources:
            board.shell('mkdir','-p',folder);board.run('push',str(p),folder+'/'+p.name)
        board.shell('docker','run','--rm','--user','0:0','--security-opt','no-new-privileges','--mount',f'type=bind,src={folder},dst=/build','--entrypoint','sh',BUILD_IMAGE,'-c','apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && cc -O2 -std=c11 -Wall -Wextra -Werror /build/unoq_config_stream.c -lm -o /build/unoq_stream')
    board.shell('test','-x',folder+'/unoq_stream');return folder+'/unoq_stream'
def stop_relay(board):
    names=board.shell('docker','ps','-a','--format','{{.Names}}',capture=True).stdout.splitlines();name=board.config['container']
    if name in names:board.shell('docker','stop','--time','3',name);board.shell('docker','rm',name)
def start(board,variant):
    target=relay_binary(board,variant);stop_relay(board);board.start()
    board.shell('docker','run','-d','--name',board.config['container'],'--network','host','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','0:0','--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw','--mount',f'type=bind,src={target},dst=/work/unoq_stream,readonly','--entrypoint','/work/unoq_stream',IMAGE)
    time.sleep(1)
    state=json.loads(board.shell('docker','inspect','--format','{{json .State}}',board.config['container'],capture=True).stdout)
    if not state['Running']:raise RuntimeError('Relay no quedo activo: '+board.shell('docker','logs',board.config['container'],capture=True).stdout)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('compile','build','create','start','stop','logs','status'));parser.add_argument('--variant',choices=('p512','p992','p512_timing','p992_timing'),required=True);args=parser.parse_args();board=board_for(args.variant)
    if args.command=='compile':compile_firmware(board)
    elif args.command=='build':print(relay_binary(board,args.variant,True))
    elif args.command=='create':board.create()
    elif args.command=='start':start(board,args.variant)
    elif args.command=='stop':stop_relay(board);board.stop()
    elif args.command=='logs':board.shell('docker','logs',board.config['container'])
    else:board.shell('docker','inspect','--format','{{json .State}}',board.config['container'])
if __name__=='__main__':main()
