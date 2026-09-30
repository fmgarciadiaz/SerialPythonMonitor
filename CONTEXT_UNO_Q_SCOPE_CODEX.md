# UNO Q Oscilloscope --- Context for Codex

## Goal

This repository contains the **current known-good version** of a
high-speed oscilloscope/acquisition project using the Arduino UNO Q /
STM32U585.

The current baseline acquires **two ADC channels at 32 ksample-pairs/s**
and successfully sends the data through an **UNO R4 WiFi bridge** to the
PC.

The next goal is to replace only the transport path with the UNO Q
internal SPI3 link:

``` text
STM32U585
  TIM/ADC -> GPDMA -> ping-pong RAM
                         |
                         v
                       SPI3
                         |
                         v
                  QRB2210 / Linux
                         |
                        USB
                         |
                         v
                    Python / PC
```

The final link should also be bidirectional:

``` text
Acquisition: STM32 -> SPI3 -> Linux -> USB -> Python
Control:     Python -> USB -> Linux -> SPI3 -> STM32
```

**Linux transports data and commands. The STM32 remains responsible for
every deterministic timing operation.**

## Baseline: do not break it

The code currently present in this repository is authoritative.

Important current status:

-   32 ksample-pairs/s works through the R4 bridge.
-   The timestamp problems from older versions have already been solved.
-   **Do not investigate, redesign, reconstruct, or "fix" timestamps.**
-   Do not revert ADC/DMA/timer/cache changes to older versions.
-   Preserve the R4 path as a known-good fallback until SPI3 passes
    independent integrity and throughput tests.
-   Inspect the repository before assuming exact buffer sizes, baud
    rates, timer values, cache operations, protocol layout, or current
    APIs.

The first SPI work should change as little as possible.

## Acquisition architecture

Historically the project uses:

``` text
A0 = PA4 = ADC1_IN9
A1 = PA5 = ADC1_IN10

hardware timer
     |
     v
ADC1 sequence: A0 + A1
     |
     v
GPDMA
     |
     v
ping-pong RAM buffers
```

Acquisition is hardware-triggered; it does not use `analogRead()` in the
acquisition loop.

Historically a sample pair has been:

``` cpp
struct __attribute__((packed)) Sample {
    uint32_t timestamp;
    uint16_t adc_in;
    uint16_t adc_out;
};
```

That is 8 bytes/pair. At 32,000 pairs/s this would be about 256,000
bytes/s raw payload, plus framing. **Verify the current repository
format before relying on this number.**

## Current transport

Known-good path:

``` text
STM32U585
   |
Serial1 / UART
   |
UNO R4 WiFi bridge
   |
ESP32-S3 / USB path
   |
PC / Python
```

The purpose of the new work is initially to replace only this transport.

## What not to redesign during the first SPI work

Do not redesign:

-   ADC setup
-   acquisition timer
-   ADC trigger chain
-   GPDMA acquisition
-   timestamp generation
-   analog channel order
-   working DMA/cache coherency
-   waveform generation
-   the working Python decoder except where an isolated transport test
    requires it

First answer one question:

> Can the STM32 stream deterministic binary blocks to Linux through the
> UNO Q internal SPI3 link, reliably and with comfortable margin above
> the current \~256 kB/s payload?

## Internal UNO Q SPI3 starting points

Relevant upstream sources:

ArduinoCore-Zephyr: https://github.com/arduino/ArduinoCore-zephyr

UNO Q overlay:
https://github.com/arduino/ArduinoCore-zephyr/blob/main/variants/arduino_uno_q_stm32u585xx/arduino_uno_q_stm32u585xx.overlay

UNO Q config:
https://github.com/arduino/ArduinoCore-zephyr/blob/main/variants/arduino_uno_q_stm32u585xx/arduino_uno_q_stm32u585xx.conf

Current upstream sources expose UNO Q SPI3 peripheral/slave support. The
variant configuration includes:

``` text
CONFIG_DMA=y
CONFIG_SPI_ASYNC=y
CONFIG_SPI_STM32_INTERRUPT=y
CONFIG_SPI_SLAVE=y
```

The UNO Q overlay declares `spi3` with a `zephyr,spi-slave` device.
ArduinoCore-Zephyr release history also contains PR #383,
`unoq: enable spi peripheral interface`.

**Do not assume upstream `main` and the installed core are identical.**
Inspect the actual headers/core used by this project before choosing
APIs. Never invent Arduino/Zephyr APIs.

## Existing SPI3 proof of concept

Reference project:

https://github.com/philippe86220/uno-q-spi3-app-lab-poc

It demonstrates:

``` text
STM32U585
   |
 SPI3
   |
QRB2210 Linux
   |
/dev/spidev0.0
   |
Python service
```

The PoC demonstrates MCU -\> MPU transfer and Linux access to the
internal SPI3 device. Its documentation explicitly describes it as
experimental and notes minimal synchronization and no CRC/integrity
checking.

Use it to understand SPI3 bring-up. Do **not** blindly copy its HTTP/App
Lab architecture; this project needs sustained binary streaming.

Expected SPI roles are:

``` text
QRB2210/Linux = controller/master
STM32U585     = peripheral/slave
```

Study the actual interface and PoC before inventing any additional
handshake wire.

## Timing rule

Linux may have millisecond-scale latency/jitter. That is fine for
configuration.

Correct:

``` text
Python: SET_SAMPLE_RATE 50000
 -> USB
 -> Linux
 -> SPI command
 -> STM32
 -> STM32 configures hardware timer
 -> timer triggers ADC deterministically
```

Incorrect:

``` text
Linux: sample now
wait
Linux: sample now
...
```

Sampling, trigger timing, waveform timing and synchronized starts belong
on the STM32.

## Phase 1: synthetic SPI benchmark FIRST

Do not connect SPI3 to the ADC yet.

Create an isolated deterministic binary benchmark.

Suggested frame:

``` text
4 bytes   magic ("SCP1" or similar)
2 bytes   protocol version
2 bytes   flags
4 bytes   sequence
4 bytes   payload length
N bytes   deterministic payload
4 bytes   CRC32
```

The exact frame may be changed for a good engineering reason.

The payload must be deterministic enough to verify every byte.

Linux receiver requirements:

1.  Open the actual UNO Q internal SPI3 device.
2.  Receive complete blocks.
3.  Validate header/magic.
4.  Validate sequence number.
5.  Validate payload.
6.  Validate CRC.
7.  Count missing and out-of-order blocks.
8.  Measure sustained throughput.
9.  Run long enough to expose rare failures.

Desired report:

``` text
SPI clock:          ...
Transferred:        ...
Elapsed:            ...
Throughput:         ... MB/s
Blocks received:    ...
Missing blocks:     0
Out-of-order:       0
Bad headers:        0
Bad payloads:       0
CRC errors:         0
```

Increase SPI clock progressively and measure actual throughput. Do not
infer throughput only from configured clock.

Acceptance goal: sustained error-free throughput with comfortable margin
over the current acquisition payload. Several times the required payload
rate is preferable before replacing the R4.

## Phase 2: connect the current acquisition

Only after Phase 1 is stable:

``` text
current DMA completed buffer
          |
          v
      SPI transport
          |
          v
        Linux
```

Preserve ping-pong ownership:

``` text
time ------------------------------------------>

ADC DMA: [fill A][fill B][fill A][fill B]
SPI:             [send A][send B][send A]
```

The implementation must prevent:

-   SPI reading a buffer while DMA writes it
-   DMA overwriting data not yet consumed
-   stale CPU cache data
-   silent block loss

Use explicit/provably safe buffer ownership. If transport cannot keep
up, detect and count overruns. Never silently overwrite data.

## Phase 3: Linux -\> PC over USB

Desired end-to-end path:

``` text
STM32 -> SPI3 -> QRB2210/Linux -> USB-C -> PC
```

Do not assume a particular Linux USB interface before checking the
actual UNO Q Linux image.

Investigate available USB gadget/device paths. Possible development
paths include:

1.  existing ADB/USB transport or port forwarding for initial tests
2.  existing CDC ACM gadget, if actually present and suitable
3.  dedicated USB bulk/function interface if higher performance is
    needed

Prefer the least invasive method first. Do not break
ADB/recovery/development access just to gain throughput.

The final integrity test must validate sequence and CRC at the **PC**,
not only on Linux.

## Bidirectional protocol

Eventually Python must send commands back to the STM32:

``` text
Python -> USB -> Linux -> SPI3 -> STM32
```

Future commands may include:

``` text
START
STOP
SET_SAMPLE_RATE
SET_WAVE_FREQUENCY
SET_WAVE_TYPE
SET_AMPLITUDE
SET_TRIGGER
GET_STATUS
```

Do not implement all of these in Phase 1, but design framing so commands
can be added cleanly.

Commands should receive ACK/status responses. Python must not assume a
requested setting was applied.

For synchronized operations, send configuration first, then let the
STM32 arm/start hardware locally.

## Future waveform/frequency-response work

Long term, Python will control acquisition and waveform generation, for
example:

``` text
set waveform = sine
set generator frequency = 1 kHz
set sample rate = 100 ksample/s
arm
start
```

The STM32 performs deterministic generation/acquisition and streams
results.

This can later support automated transfer-function measurements:

``` text
H(f) = Y(f) / X(f)
```

This is future scope. Do not let it complicate SPI bring-up.

## Engineering rules

1.  Inspect before editing.
2.  Preserve the known-good 32 ksample-pairs/s acquisition.
3.  Do not revisit solved timestamp issues.
4.  Do not replace working low-level STM32 code for stylistic reasons.
5.  Do not invent APIs; find declarations/implementations in the
    installed core.
6.  Make small, independently testable changes.
7.  Keep the R4 path buildable until SPI3 is proven.
8.  Add counters for detectable failure modes.
9.  Never silently drop blocks.
10. Keep Linux/USB latency out of deterministic acquisition timing.
11. Benchmark layers separately before combining them.
12. Be explicit about endianness, packing, lengths, sequence numbers and
    CRC.
13. Preserve all DMA/cache coherency requirements.
14. Measure actual sustained throughput.

## FIRST TASK FOR CODEX

**Start with analysis only. Do not modify the working acquisition yet.**

Inspect the complete current repository and report:

### A. Current architecture

Describe what the current code actually does at 32 ksample-pairs/s.

### B. Exact files/functions

Identify code responsible for:

-   timer/ADC triggering
-   ADC DMA
-   ping-pong buffering
-   cache management
-   current UART/R4 transport
-   binary protocol
-   Python receive/decode

### C. Current data rate

Confirm the actual sample structure, bytes/sample, framing overhead and
sustained required throughput.

### D. Installed SPI3 APIs

Determine the ArduinoCore-Zephyr version actually used by this project
and locate the real SPI peripheral/slave APIs available in that
installed version.

### E. Compare with the public PoC

Identify which pieces of the SPI3 PoC can be reused and which should not
be used for sustained oscilloscope streaming.

### F. Synthetic benchmark design

Propose the smallest implementation for:

``` text
STM32 synthetic generator -> SPI3 -> Linux verifier
```

with sequence checking, deterministic payload verification, CRC and
throughput measurement.

### G. Files to add/change

List exact files that would be created or modified.

### H. Risks/unknowns

List only concrete unknowns that require measurement or source
inspection.

After presenting this analysis, wait before making invasive changes to
the working acquisition.

## Success condition

The R4 can be removed only after:

``` text
STM32 acquisition
      |
     SPI3
      |
    Linux
      |
     USB
      |
      PC
```

demonstrates:

-   sustained throughput comfortably above the current 32
    ksample-pairs/s requirement
-   no missing sequence numbers
-   no CRC failures
-   no silent buffer overruns
-   stable long-duration operation
-   clean path for bidirectional commands
-   STM32 retains all deterministic timing

Until then, the current 32 ksample-pairs/s R4 version is the reference
implementation.
