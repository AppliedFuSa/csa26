/*
 * csa26-testfixture — Beispiel 02 (medium): Sensor-Implementation.
 *
 * Bewusst MISRA-verletzend. Findings-Erwartungen siehe
 * `02-medium/expectations.md`.
 */

#include "sensor.h"

/* Verstoß 8.7 — externer Linkage für ein Symbol, das nur intern
 * verwendet wird. Sollte `static` sein. */
int16_t calibration_offset = 100;

void sensor_calibrate(sensor_reading_t *reading)
{
    /* Rule-14-Gruppe — implizite NULL-Prüfung statt expliziter
     * Vergleich. Hier bewusst „lax", csa26 darf das markieren. */
    if (reading != NULL) {
        reading->calibrated = (int16_t)(reading->raw) - calibration_offset;
    }
}

/* Verstoß 8.13 — `samples` wird nur gelesen, sollte const sein. */
uint16_t sensor_smooth(uint16_t *samples, size_t count)
{
    uint32_t sum = 0U;
    for (size_t i = 0U; i < count; ++i) {
        sum += (uint32_t)samples[i];
    }
    /* Verstoß-Cluster: Division ohne Null-Check (count==0),
     * implizite Konvertierung uint32_t → uint16_t. */
    return (uint16_t)(sum / count);
}
