#pragma once
#include <cstdint>

namespace scope_batch2 {
enum class Source : uint8_t { Idle, Reply, Normal, Pipelined, Word };
struct Half {
    Source source=Source::Idle;
    bool final_node=false;
};
constexpr Source select_source(bool reply,bool samples,bool word,bool pipelined) {
    return reply ? Source::Reply : !samples ? Source::Idle : word ? Source::Word :
           pipelined ? Source::Pipelined : Source::Normal;
}
constexpr bool early_slot_release(Half h) { return h.source==Source::Word; }
constexpr bool frame_release_after_physical_success(Half h) {
    return h.source==Source::Normal || h.source==Source::Pipelined;
}
constexpr bool node_release_after_physical_success(Half h) {
    return h.source==Source::Word && h.final_node;
}
struct Credits { unsigned frames, nodes; };
constexpr Credits credits_after_physical(const Half (&halves)[2],bool success) {
    return success ? Credits{
        unsigned(frame_release_after_physical_success(halves[0]))+
        unsigned(frame_release_after_physical_success(halves[1])),
        unsigned(node_release_after_physical_success(halves[0]))+
        unsigned(node_release_after_physical_success(halves[1]))} : Credits{0U,0U};
}
static_assert(early_slot_release({Source::Word,true}) &&
              !frame_release_after_physical_success({Source::Word,true}) &&
              node_release_after_physical_success({Source::Word,true}),
              "Word scratch may be reused after copy; node waits for DMA");
static_assert(frame_release_after_physical_success({Source::Normal,false}) &&
              frame_release_after_physical_success({Source::Pipelined,false}) &&
              !early_slot_release({Source::Pipelined,false}),
              "Ordinary and pipelined frames wait for physical completion");
static_assert(select_source(false,false,true,true)==Source::Idle &&
              select_source(true,true,true,true)==Source::Reply &&
              select_source(false,true,true,true)==Source::Word,
              "Priority and idle fallback never wait for another sample");
constexpr Half normal_and_idle[2]={{Source::Normal,false},{Source::Idle,false}};
constexpr Half word_final_and_idle[2]={{Source::Word,true},{Source::Idle,false}};
static_assert(credits_after_physical(normal_and_idle,true).frames==1U &&
              credits_after_physical(normal_and_idle,false).frames==0U &&
              credits_after_physical(word_final_and_idle,true).nodes==1U &&
              credits_after_physical(word_final_and_idle,false).nodes==0U,
              "Only a complete physical batch returns frame or node ownership");
}
