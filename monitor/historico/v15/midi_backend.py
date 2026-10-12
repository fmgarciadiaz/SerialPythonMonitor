"""Isolated CoreMIDI access; stdout is a bounded JSON message stream."""
import argparse
import json
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--port')
    parser.add_argument('--virtual',action='store_true')
    args=parser.parse_args()
    try:
        import mido
        backend=mido.Backend('mido.backends.rtmidi')
        if args.list:
            print(json.dumps({'ports':backend.get_input_names()}),flush=True)
            return 0
        with backend.open_input(args.port,virtual=args.virtual) as port:
            print(json.dumps({'ready':True}),flush=True)
            for message in port:
                if message.type in ('note_on','note_off','control_change'):
                    print(json.dumps({'message':message.dict()}),flush=True)
    except Exception as error:
        print(json.dumps({'error':str(error)}),flush=True)
        return 1
    return 0


if __name__=='__main__':sys.exit(main())
