"""Combine batch2 with single-pass command decoding, retaining atomic prevalidation."""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent;OUT=EXP/'batchfast'
HEADER='''#pragma once
namespace scope_batch_command {
enum class Kind { Invalid, Ping, Wav, Generator, Acquisition, Control };
struct Command {
    Kind kind=Kind::Invalid;
    uint32_t ping=0;
    scope_wav::Request wav{};
    scope_gen::Request generator{};
    scope_acq::Request acquisition{};
    scope_control::Request control{};
};
inline bool decode(const uint8_t *p,Command &out) {
    out=Command{};
    // Dispatch by kind before invoking its full unchanged protocol decoder.
    // This removes redundant CRC work while retaining every field check.
    const unsigned kind=scope_bench::get16(p+6);
    if(kind==2 && scope_bench::valid_ping(p)) {out.kind=Kind::Ping;out.ping=scope_bench::get32(p+8);}
    else if((kind==11 || kind==13) && scope_wav::decode(p,992,out.wav))out.kind=Kind::Wav;
    else if((kind==8 || kind==10) && scope_gen::decode(p,992,out.generator))out.kind=Kind::Generator;
    else if(kind==6 && scope_acq::decode(p,992,out.acquisition))out.kind=Kind::Acquisition;
    else if(kind==4 && scope_control::decode(p,992,out.control))out.kind=Kind::Control;
    return out.kind!=Kind::Invalid;
}
inline bool decode_pair(const uint8_t *p,Command (&out)[2]) {
    return decode(p,out[0]) && decode(p+992,out[1]);
}
}
'''
def prepare():
 for name in ('oscilloscope','relay'):shutil.copytree(EXP/'batch2'/name,OUT/name,dirs_exist_ok=True)
 shutil.copyfile(EXP/'batch2/candidate_profiles.json',OUT/'candidate_profiles.json')
 p=OUT/'oscilloscope/sketch/sketch.ino';s=p.read_text()
 a=s.index('static bool valid_batch_command(');b=s.index('static void process_batch_command',a)
 s=s[:a]+s[b:]
 s=s.replace('#include "frame_buffer.h"','#include "frame_buffer.h"\n#include "generator_protocol.h"\n#include "wav_protocol.h"\n#include "batch_command.h"',1)
 s=s.replace('static void process_batch_command(const uint8_t *packet) {','static void process_batch_command(const scope_batch_command::Command &command) {')
 s=s.replace('    if (valid_ping(packet)) { last_ping=get32(packet+8); return; }','    using scope_batch_command::Kind;\n    if(command.kind==Kind::Ping) {last_ping=command.ping;return;}')
 s=s.replace('    scope_control::Request request{};\n    scope_acq::Request config_request{};\n    scope_gen::Request generator_request{};\n    scope_wav::Request wav_request{};', '    const auto &request=command.control;\n    const auto &config_request=command.acquisition;\n    const auto &generator_request=command.generator;\n    const auto &wav_request=command.wav;')
 for old,new in [('scope_wav::decode(packet,BLOCK_BYTES,wav_request)','command.kind==Kind::Wav'),('scope_gen::decode(packet,BLOCK_BYTES,generator_request)','command.kind==Kind::Generator'),('scope_acq::decode(packet,BLOCK_BYTES,config_request)','command.kind==Kind::Acquisition'),('scope_control::decode(packet,BLOCK_BYTES,request)','command.kind==Kind::Control')]:s=s.replace(old,new)
 s=s.replace('    const int physical_result=exchange();','    scope_batch_command::Command commands[2];\n    const int physical_result=exchange();')
 s=s.replace('!valid_batch_command(rx_batch) ||\n              !valid_batch_command(rx_batch+BLOCK_BYTES)','!scope_batch_command::decode_pair(rx_batch,commands)')
 s=s.replace('process_batch_command(rx_batch+i*BLOCK_BYTES);','process_batch_command(commands[i]);')
 p.write_text(s);(p.parent/'batch_command.h').write_text(HEADER)
 p=OUT/'oscilloscope/app.yaml';p.write_text(p.read_text().replace('Scope V18 Rate Probe Batch2','Scope V18 Rate Probe BatchFast'))
 p=OUT/'oscilloscope/python/main.py';p.write_text(p.read_text().replace('Scope V18 Rate Probe Batch2','Scope V18 Rate Probe BatchFast'))
if __name__=='__main__':prepare()
