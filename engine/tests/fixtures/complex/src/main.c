/*
 * csa26-testfixture — Beispiel 03 (complex): App-Entry.
 */

#include "leds.h"

/* Verstoß 8.4 — keine vorherige Deklaration. */
int main(void)
{
    leds_init();
    leds_set(0U, 1U);
    return 0;
}
