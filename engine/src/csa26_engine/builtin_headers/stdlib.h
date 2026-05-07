/* csa26-engine builtin stub for <stdlib.h>. */
#ifndef _CSA26_STDLIB_H
#define _CSA26_STDLIB_H

#include <stddef.h>

void *malloc(size_t size);
void *calloc(size_t nmemb, size_t size);
void *realloc(void *ptr, size_t size);
void  free(void *ptr);

void  abort(void);
void  exit(int status);

int   atoi(const char *nptr);
long  atol(const char *nptr);

#endif /* _CSA26_STDLIB_H */
