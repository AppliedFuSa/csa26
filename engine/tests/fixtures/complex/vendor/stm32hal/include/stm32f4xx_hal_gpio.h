/*
 * csa26-testfixture — STARK vereinfachter STM32 HAL-Stub für GPIO.
 *
 * NICHT der echte ST HAL-Header. Demonstriert das `defines:
 * USE_HAL_DRIVER`-Setup gegenüber csa26.
 */

#ifndef STM32F4XX_HAL_GPIO_H
#define STM32F4XX_HAL_GPIO_H

#include "stm32f4xx.h"

#if !defined(USE_HAL_DRIVER)
#error "USE_HAL_DRIVER must be defined in defines: input"
#endif

typedef enum {
    HAL_OK    = 0,
    HAL_ERROR = 1
} HAL_StatusTypeDef;

typedef enum {
    GPIO_PIN_RESET = 0,
    GPIO_PIN_SET   = 1
} GPIO_PinState;

HAL_StatusTypeDef HAL_GPIO_Init(GPIO_TypeDef *port, uint32_t pin);
void              HAL_GPIO_WritePin(GPIO_TypeDef *port, uint32_t pin,
                                    GPIO_PinState state);

#endif /* STM32F4XX_HAL_GPIO_H */
