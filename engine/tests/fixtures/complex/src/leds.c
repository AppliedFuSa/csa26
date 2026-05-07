/*
 * csa26-testfixture — Beispiel 03 (complex): LED-Treiber-Implementation.
 *
 * Realistischer Vendor-SDK-Kontext: bindet CMSIS-Header und HAL-Header,
 * benötigt `STM32F407xx` und `USE_HAL_DRIVER` als Defines beim
 * cppcheck-Aufruf — sonst schlagen die `#error`-Direktiven in den
 * Stubs zu und cppcheck gibt auf, bevor das MISRA-Addon greift.
 *
 * Bewusst MISRA-verletzend. Findings-Erwartungen siehe expectations.md.
 */

#include "leds.h"
#include "stm32f4xx_hal_gpio.h"

/* Verstoß 8.7 — externer Linkage, intern verwendet. */
GPIO_TypeDef *led_port = GPIOC;

/* Magic-Pin-Nummer 13 — typisch fürs Onboard-LED-Pin auf einem
 * STM32F4-Discovery / Nucleo. Rule-Cluster 12.x. */
void leds_init(void)
{
    HAL_GPIO_Init(led_port, 13U);
    HAL_GPIO_Init(led_port, 14U);
    HAL_GPIO_Init(led_port, 15U);
}

void leds_set(uint8_t led_idx, uint8_t state)
{
    /* Rule 14.4 — kontrollierender Ausdruck nicht boolesch. */
    if (state) {
        HAL_GPIO_WritePin(led_port,
                          (uint32_t)(13U + led_idx),
                          GPIO_PIN_SET);
    } else {
        HAL_GPIO_WritePin(led_port,
                          (uint32_t)(13U + led_idx),
                          GPIO_PIN_RESET);
    }
}
