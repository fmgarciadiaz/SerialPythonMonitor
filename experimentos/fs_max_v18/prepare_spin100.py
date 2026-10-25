"""Relay-only READY wait comparison; MCU and data validation unchanged."""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent;OUT=EXP/'spin100'
def prepare():
    for name in ('oscilloscope','relay'):shutil.copytree(EXP/name,OUT/name,dirs_exist_ok=True)
    shutil.copyfile(EXP/'candidate_profiles.json',OUT/'candidate_profiles.json')
    p=OUT/'relay/base_verifier.c';s=p.read_text();old='const double spin_until=now()+0.000050;'
    assert s.count(old)==1;p.write_text(s.replace(old,'const double spin_until=now()+0.000100;'))
    p=OUT/'relay/unoq_config_stream.c';p.write_text(p.read_text().replace('spin50us','spin100us'))
if __name__=='__main__':prepare()
