"""Pinned BSP contract for the dedicated acquisition tail; no Q access on import."""
import json
from pathlib import Path
import re
import shlex

ROOT=Path(__file__).resolve().parents[2]
BSP_ROOT='/home/arduino/.arduino15/internal/arduino_zephyr_1.0.0_280fc2760e675f10/'
BSP_FILES=frozenset(BSP_ROOT+suffix for suffix in (
    'firmwares/zephyr-arduino_uno_q_stm32u585xx.config',
    'firmwares/zephyr-arduino_uno_q_stm32u585xx.dts',
    'firmwares/zephyr-arduino_uno_q_stm32u585xx.elf',
    'variants/_ldscripts/memory-static.ld','variants/_ldscripts/memory-check.ld',
    'variants/_ldscripts/build-dynamic.ld','variants/_ldscripts/build-static.ld',
    'variants/arduino_uno_q_stm32u585xx/syms-dynamic.ld',
    'variants/arduino_uno_q_stm32u585xx/syms-static.ld'))


def load_contract():
    contract=json.loads((ROOT/'arduino/v20/unoq.json').read_text()).get('memory_contract',{})
    if (contract.get('schema')!=1 or contract.get('begin')!=0x20060000 or
            contract.get('end')!=0x200c0000 or contract.get('kernel_image_end')!=0x20053890
            or set(contract.get('bsp_files',{}))!=BSP_FILES):
        raise ValueError('Exact V20 acquisition memory contract required')
    for path,digest in contract['bsp_files'].items():
        if not path.startswith('/home/arduino/.arduino15/internal/arduino_zephyr_1.0.0_280fc2760e675f10/') or not re.fullmatch('[0-9a-f]{64}',digest):
            raise ValueError('Invalid pinned V20 BSP file')
    return contract


def verify_output(text,contract):
    observed={}
    for line in text.splitlines():
        digest,path=line.split(maxsplit=1)
        if path in observed:raise RuntimeError('Duplicate BSP hash result')
        observed[path]=digest
    if observed!=contract['bsp_files']:
        raise RuntimeError('V20 BSP changed; re-audit SRAM3 before starting the MCU')
    return observed


def verify_board(board):
    contract=load_contract()
    verify_output(board.shell('sha256sum',*contract['bsp_files'],capture=True).stdout,contract)
    return contract


def verify_runner(serial,runner):
    contract=load_contract()
    command=shlex.join(['sha256sum',*contract['bsp_files']])
    verify_output(runner('-s',serial,'shell',command),contract)
    return contract
