/*
 * csa26-testfixture — Beispiel 02 (medium).
 *
 * Public-Header für ein Mini-Sensor-Modul. Wird von src/sensor.c
 * implementiert, von src/main.c benutzt. Demonstriert das
 * `include-paths`-Action-Input.
 */

#ifndef SENSOR_H
#define SENSOR_H

#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint16_t raw;
    int16_t  calibrated;
} sensor_reading_t;

void     sensor_calibrate(sensor_reading_t *reading);
uint16_t sensor_smooth(uint16_t *samples, size_t count);

#endif /* SENSOR_H */
