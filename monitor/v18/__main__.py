"""Arduscopio Q V18 entrypoint; never opens Q automatically."""
import argparse
import json
import unittest


def main():
    parser=argparse.ArgumentParser(description='Arduscopio Q V18: adquisición en un proceso separado')
    parser.add_argument('--self-test',action='store_true',help='Run offline tests, including localhost TCP')
    parser.add_argument('--gui',action='store_true',help='Abrir Arduscopio Q V18; conecta sólo por acción del usuario')
    args=parser.parse_args()
    if args.gui:
        from monitor.v18.app import main as gui_main
        return gui_main()
    if args.self_test:
        modules=['tests.v18.io.test_acquisition_process', 'tests.v18.io.test_adb_tunnel', 'tests.v18.io.test_audio_control', 'tests.v18.io.test_audio_pump', 'tests.v18.io.test_board_owner', 'tests.v18.io.test_device_snapshot', 'tests.v18.io.test_generator_barrier', 'tests.v18.io.test_generator_path', 'tests.v18.io.test_occupied_startup', 'tests.v18.io.test_process_audio', 'tests.v18.io.test_prototype', 'tests.v18.io.test_rf_numeric', 'tests.v18.io.test_socket_process', 'tests.v18.io.test_socket_transport', 'tests.v18.io.test_wire_adapter', 'tests.v18.io.test_layout', 'tests.v18.io.test_live_connection', 'tests.v18.io.test_receiver_process', 'tests.v18.io.test_receiver_lifecycle', 'tests.v18.io.test_rf_batch', 'tests.v18.test_synth_polyphony', 'tests.v18.test_synth_process']
        suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
        return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1
    print(json.dumps(dict(version=18,stage='functional_integration',gui_integrated=True,
                          physical_q_enabled=True,firmware_changes=False),indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
