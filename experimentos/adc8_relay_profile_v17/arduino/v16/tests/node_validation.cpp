#include "../oscilloscope/sketch/node_validation.h"
#include <array>
#include <cassert>
#include <limits>
struct Pair {uint16_t a,b;};
int main() {
    constexpr unsigned N=2048;
    std::array<uint16_t,2*N> adc{};
    std::array<uint32_t,N> timestamps{};
    std::array<Pair,N> output{};
    for (unsigned bits: {8U,10U,12U,14U,16U}) {
        for (unsigned period: {4U,5U,8U,16U,25U,1000U}) {
            const uint32_t first=std::numeric_limits<uint32_t>::max()-100U;
            for (unsigned i=0;i<N;++i) {timestamps[i]=first+i*period;adc[2*i]=(1U<<bits)-1U;adc[2*i+1]=0;}
            const auto check=[&](bool previous,uint32_t last) {
                return scope_validation::validate_node<true>(adc.data(),timestamps.data(),N,bits,period,previous,last,output.data());
            };
            assert(check(false,0));assert(check(true,first-period));
            assert(!check(true,first-period-1));
            for (unsigned i=0;i<N;++i) {
                timestamps[i]^=1;assert(!check(false,0));timestamps[i]^=1;
            }
            if(bits<16) {
                for(unsigned rank: {0U,1U}) {
                    const auto saved=adc[rank];adc[rank]=1U<<bits;
                    assert(!check(false,0));adc[rank]=saved;
                }
            }
            output[0]={123,456};
            assert(scope_validation::validate_node<false>(adc.data(),timestamps.data(),N,bits,period,false,0,output.data()));
            assert(output[0].a==123 && output[0].b==456);
            assert(check(false,0));
            for(unsigned i=0;i<N;++i) assert(output[i].a==adc[2*i] && output[i].b==adc[2*i+1]);
        }
    }
}
