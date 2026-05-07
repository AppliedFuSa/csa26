/*
 * csa26-testfixture — Beispiel 02 (medium): Verwendung des Sensor-Moduls.
 */

#include "sensor.h"

/* Verstoß 8.4 — keine vorherige Deklaration. */
int main(void)
{
    sensor_reading_t r = { .raw = 1024U, .calibrated = 0 };
    sensor_calibrate(&r);

    uint16_t buf[3] = { 100U, 200U, 300U };
    /* Implizite Konvertierung uint16_t → int. */
    return (int)sensor_smooth(buf, 3U);
}
