#pragma once
#include <cstddef>
#include <cstdint>

namespace scope_validation {
// Keep every timestamp check. Unsigned arithmetic intentionally wraps at 2^32.
// Separate instantiations move the queue-ownership branch outside the sample loop.
template<bool Copy, typename Pair>
inline bool validate_node(const uint16_t *adc, const uint32_t *timestamps,
                          std::size_t count, uint8_t bits, uint32_t period,
                          bool have_previous, uint32_t previous, Pair *output) {
    if (!count || !period || !bits || bits > 16) return false;
    uint32_t expected = timestamps[0];
    uint32_t errors = have_previous ? expected - previous - period : 0U;
    const uint32_t forbidden = ~((1U << bits) - 1U);
    for (std::size_t i = 0; i < count; ++i) {
        const uint16_t a = adc[2*i], b = adc[2*i+1];
        errors |= timestamps[i] ^ expected;
        errors |= (uint32_t(a) | uint32_t(b)) & forbidden;
        if constexpr (Copy) output[i] = {a, b};
        expected += period;
    }
    return errors == 0U;
}
}
