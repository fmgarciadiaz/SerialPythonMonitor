#pragma once
#include <cstddef>
#include <cstdint>
#include <new>

// UNO Q BSP 1.0.0: the kernel ELF, DTS and config are hash-pinned by the
// V20 launcher. Its mapped image (including both bounded heaps) ends here.
// This tail is exclusive to acquisition; never move it into the LLEXT heap.
namespace scope_acquisition_memory {
constexpr uintptr_t kernel_image_end=0x20053890U;
constexpr uintptr_t begin=0x20060000U;
constexpr uintptr_t end=0x200c0000U;
template<class T> constexpr bool fits() {
    return begin>=kernel_image_end && begin%alignof(T)==0 &&
           sizeof(T)<=end-begin && sizeof(T)%sizeof(uint32_t)==0;
}
template<class T> T &initialize_once(void *address,bool &initialized) {
    static_assert(sizeof(T)%sizeof(uint32_t)==0 && alignof(T)>=alignof(uint32_t), "Word-initialized arena");
    // Full-word writes seed the complete arena before any byte/halfword use,
    // including when SRAM ECC is enabled. Do not change flash option bytes.
    if(!initialized) {
        volatile uint32_t *words=static_cast<volatile uint32_t *>(address);
        for(std::size_t i=0;i<sizeof(T)/sizeof(uint32_t);++i) words[i]=0;
        new(address) T; // Begin Storage lifetime; bind() constructs its active union.
        initialized=true;
    }
    return *static_cast<T *>(address);
}
}
