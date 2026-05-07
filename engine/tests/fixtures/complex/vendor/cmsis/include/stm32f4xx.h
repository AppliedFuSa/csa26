/*
 * csa26-testfixture — STARK vereinfachter STM32F4xx-Stub.
 *
 * NICHT der echte CMSIS-Header. Nur so viel, dass die Beispiel-Module
 * gegen ein typisches Vendor-Header-Layout kompilierbar sind und die
 * `defines: STM32F407xx` / `USE_HAL_DRIVER`-Mechanik des csa26-Inputs
 * realistisch demonstriert wird.
 */

#ifndef STM32F4XX_H
#define STM32F4XX_H

#include <stdint.h>

#if !defined(STM32F407xx)
#error "STM32F407xx must be defined in defines: input"
#endif

typedef struct {
    volatile uint32_t MODER;
    volatile uint32_t OTYPER;
    volatile uint32_t OSPEEDR;
    volatile uint32_t PUPDR;
    volatile uint32_t IDR;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;
    volatile uint32_t LCKR;
    volatile uint32_t AFR[2];
} GPIO_TypeDef;

#define GPIOA ((GPIO_TypeDef *) 0x40020000U)
#define GPIOB ((GPIO_TypeDef *) 0x40020400U)
#define GPIOC ((GPIO_TypeDef *) 0x40020800U)

#endif /* STM32F4XX_H */
