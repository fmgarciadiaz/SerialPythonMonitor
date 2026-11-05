"""Arduscopio Q desktop entrypoint; never opens the Q automatically."""
import argparse
import json
import unittest


def main():
    parser=argparse.ArgumentParser(description='Arduscopio Q: adquisición en un proceso separado')
    parser.add_argument('--self-test',action='store_true',help='Run offline tests, including localhost TCP')
    parser.add_argument('--gui',action='store_true',help='Abrir Arduscopio Q; conecta sólo por acción del usuario')
    args=parser.parse_args()
    if args.gui:
        from monitor.v19.app import main as gui_main
        return gui_main()
    if args.self_test:
        suite=unittest.defaultTestLoader.discover('tests/v19',top_level_dir='.')
        return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1
    print(json.dumps(dict(version=19,binding='PySide6',stage='active',gui_integrated=True,
                          physical_q_enabled=True,firmware_changes=False),indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
