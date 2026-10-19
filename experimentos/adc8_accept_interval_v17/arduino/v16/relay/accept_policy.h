#pragma once
#include <stdint.h>
#include <stdbool.h>
// The launcher permits only1 or16. No-client admission is checked every loop.
static inline bool accept_due(int client, uint32_t command, unsigned interval) {
    return client < 0 || (command & (interval - 1U)) == 0;
}
