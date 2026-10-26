#pragma once
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
