/*
 * csa26-testfixture — Beispiel 03 (complex): LED-Treiber-API.
 */

#ifndef LEDS_H
#define LEDS_H

#include <stdint.h>

#define LED_COUNT 3U

void leds_init(void);
void leds_set(uint8_t led_idx, uint8_t state);

#endif /* LEDS_H */
