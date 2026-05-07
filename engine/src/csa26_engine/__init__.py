"""csa26-engine — eigenständige MISRA-C-Analyse-Engine.

Phase-2-Prototyp. Sieht den C-Quellcode roh und macht alle Analyse-
Schritte selbst: Lexer, Preprocessor, Parser, Symbol-Resolution,
Type-System, Rule-Engine. Cppcheck und externe Frontends sind
explizit nicht im Stack.
"""

__version__ = "0.0.1"
