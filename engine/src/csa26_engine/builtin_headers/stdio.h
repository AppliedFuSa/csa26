/* csa26-engine builtin stub for <stdio.h>. */
#ifndef _CSA26_STDIO_H
#define _CSA26_STDIO_H

#include <stddef.h>

typedef struct _csa26_FILE FILE;

extern FILE *stdin;
extern FILE *stdout;
extern FILE *stderr;

int printf(const char *fmt, ...);
int fprintf(FILE *stream, const char *fmt, ...);
int sprintf(char *str, const char *fmt, ...);
int snprintf(char *str, size_t size, const char *fmt, ...);

int puts(const char *s);
int fputs(const char *s, FILE *stream);

#endif /* _CSA26_STDIO_H */
