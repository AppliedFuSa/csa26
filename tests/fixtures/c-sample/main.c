/*
 * csa26 — interne Smoketest-Fixture.
 *
 * Dieser Code ist ABSICHTLICH so geschrieben, dass das Cppcheck-MISRA-
 * Addon mehrere Regel-Befunde meldet. Die Fixture ist klein und
 * repräsentiert KEINEN realistischen embedded-Code — sie existiert
 * nur, damit die Action im CI lebendige Findings parsen kann.
 *
 * Eine ausführlichere Test-Fixture (für externe Smoketests gegen
 * gepushte Images) lebt im separaten Repo AppliedFuSa/csa26-testfixture.
 */

#include <stdint.h>
#include <stddef.h>

/* Pointer-Parameter wird nur gelesen, ist aber nicht const-qualifiziert.
 * Erwartet u.a. einen Hinweis in Richtung Rule 8.13. */
uint32_t checksum(uint8_t *data, size_t len)
{
    uint32_t sum = 0;
    for (size_t i = 0; i < len; ++i) {
        sum += data[i];
    }
    return sum;
}

/* Funktion mit unbenutztem Parameter — Hinweis Richtung Rule 2.7. */
int handle_event(int code, int unused_flag)
{
    return code * 2;
}

/* Bewusst kompakte main mit Magic Number und impliziter Konvertierung. */
int main(void)
{
    uint8_t buffer[16];
    for (int i = 0; i < 16; ++i) {
        buffer[i] = (uint8_t)i;
    }
    uint32_t s = checksum(buffer, 16);
    return (int)s;
}
