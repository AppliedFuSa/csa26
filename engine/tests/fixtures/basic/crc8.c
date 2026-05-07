/*
 * csa26-testfixture — Beispiel 01 (basic).
 *
 * Eine einzelne C-Datei mit absichtlich eingebauten MISRA-C:2012-
 * Verstoss-Mustern. Selbstständig kompilierbar gegen <stdint.h> /
 * <stddef.h>, keine Vendor-Header, keine Build-Defines.
 *
 * NICHT als Lehrbeispiel für „guten" Code geeignet — die Datei
 * existiert ausschließlich, um csa26 Findings produzieren zu lassen.
 */

#include <stdint.h>
#include <stddef.h>

/* Verstoß-Andeutung (Rule 8.13 — const-correctness):
 * `data` wird nur gelesen, der Pointer-Typ sollte const-qualifiziert sein. */
uint8_t compute_crc8(uint8_t *data, size_t len)
{
    uint8_t crc = 0xFFU;
    for (size_t i = 0U; i < len; ++i) {
        crc ^= data[i];
        /* Magic-Number 8 (Schleifen-Limit) — Rule 12-Gruppe.            */
        for (int bit = 0; bit < 8; ++bit) {
            /* Rule 14.4 — kontrollierender Ausdruck soll vom Typ bool sein. */
            if (crc & 0x80U) {
                /* Magic-Number 0x07 — typisches CRC-Polynom-Konstanten-Muster. */
                crc = (uint8_t)((crc << 1) ^ 0x07U);
            } else {
                crc = (uint8_t)(crc << 1);
            }
        }
    }
    return crc;
}

/* Verstoß 8.4 — keine vorherige Deklaration von `main` mit externer Linkage.
 * Demonstriert das gleiche Muster wie unsere interne Smoketest-Fixture. */
int main(void)
{
    uint8_t buf[4] = {1U, 2U, 3U, 4U};
    /* Implizite Konvertierung uint8_t → int beim Return — Rule-10-Gruppe. */
    return compute_crc8(buf, 4U);
}
