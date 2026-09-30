#include <Arduino.h>

#if !defined(ARDUINO_UNOR4_WIFI)
#error "Este puente requiere UNO R4 WiFi / renesas_uno 1.6.0"
#endif
// Serial: UART al ESP32/USB. Serial1: SCI2, RX D0/P301, TX D1/P302.
constexpr uint32_t LINK_BAUD = 3000000;
// 31.25 kpares/s, DATA/512: ~2.503 Mbps 8N1. Ambos UART deben usar 3 Mbps.
constexpr uint32_t SAMPLE_RATE_CEILING_HZ = 31250;
static_assert(uint64_t(SAMPLE_RATE_CEILING_HZ) * 4103U * 10U <
              uint64_t(LINK_BAUD) * 512U, "Caudal insuficiente para DATA/512");
constexpr uint32_t QUEUE_SIZE = 8192;
constexpr uint32_t QUEUE_MASK = QUEUE_SIZE - 1;
static volatile uint8_t queue[QUEUE_SIZE];
static volatile uint32_t head = 0, tail = 0, droppedBytes = 0;
static IRQn_Type rxIRQ = FSP_INVALID_VECTOR;

// Un productor (ISR) y un consumidor (loop). Evita la capa SafeRingBuffer
// y sus secciones críticas por cada consulta/read del core.
static void fast_receive() {
  const uint8_t value = R_SCI2->RDR;
  R_BSP_IrqStatusClear(rxIRQ);
  const uint32_t next = (head + 1) & QUEUE_MASK;
  if (next == tail) ++droppedBytes;
  else {
    queue[head] = value;
    __DMB();
    head = next;
  }
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(LINK_BAUD); // UART hacia ESP32/USB; baud del monitor.
  Serial1.begin(LINK_BAUD);
  R_SCI9->SCR_b.TIE = 0;
  R_SCI9->SCR_b.TEIE = 0;
  R_SCI9->SCR_b.TE = 1;
  for (unsigned i = 0; i < BSP_ICU_VECTOR_MAX_ENTRIES; ++i) {
    if ((R_ICU->IELSR[i] & 0x1ffU) == ELC_EVENT_SCI2_RXI) {
      rxIRQ = static_cast<IRQn_Type>(i);
      R_BSP_IrqDisable(rxIRQ);
      // El core mantiene su tabla de vectores en RAM (IRQManager).
      auto vectors = reinterpret_cast<volatile uint32_t *>(SCB->VTOR);
      vectors[16 + i] = reinterpret_cast<uint32_t>(fast_receive);
      __DSB(); __ISB();
      R_BSP_IrqEnable(rxIRQ);
      break;
    }
  }
  if (rxIRQ == FSP_INVALID_VECTOR) {
    digitalWrite(LED_BUILTIN, HIGH);
    while (true) {}
  }
}

void loop() {
  // SCI9 alimenta el ESP32/USB. Sin una ISR TX adicional por byte.
  if (tail != head && R_SCI9->SSR_b.TDRE) {
    R_SCI9->TDR = queue[tail];
    tail = (tail + 1) & QUEUE_MASK;
  }
  if (droppedBytes) digitalWrite(LED_BUILTIN, HIGH);
  // No usar Serial.write ni Serial1.read/available con esta ruta exclusiva.
}
