# Local, reversible ADC8/2M preparation experiment

Hypothesis: the sample-frame preparation path compiled with `O2` is cheaper
than the current `Os` function. The current product uses `Os` for the complete
`prepare_batch_half`; its hot sample path copies 992 bytes, writes the unchanged
SCP1 metadata and seals the unchanged CRC. Both variants here emit identical
bytes for 256 sequences and verify the CRC. The benchmark omits queue access,
Zephyr, DMA, scheduling, and the SPI wire. It is a screening experiment, not a
firmware patch or physical performance claim. Rates other than the exact
ADC8/CH1/80 ticks/3488 pairs would not be switched to a future candidate.

Run `g++ -std=c++17 -O2 -I arduino/v20/oscilloscope/sketch
experiments/v20/adc8_2m_prepare_o2/prepare_microbench.cpp -o /tmp/v20-prepare-o2`
from the repository root, then `/tmp/v20-prepare-o2`. No Q is used. A future
firmware candidate requires ARM build/size, exact output and CRC checks, then
paired physical A/B with snapshot restoration before deciding whether to keep
it. Existing product sources and the installed pair are unchanged.
