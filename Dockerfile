# csa26 v1.0 — eigenständige MISRA-C:2012-Analyse-Engine.
#
# Keine Drittanbieter-Static-Analyser im Stack. Lexer, Preprocessor,
# Parser, Symbol-/Type-System und Rule-Engine sind Apple-2.0-IP der
# Applied FuSa, vollständig im `engine/`-Subprojekt.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Engine-Package installieren. Kein cppcheck, kein addons-Tarball,
# keine ca-certificates für Net-Pulls — alles, was wir brauchen,
# kommt aus diesem Repo.
COPY engine /opt/csa26-engine
RUN pip install --no-cache-dir /opt/csa26-engine

ENTRYPOINT ["csa26-engine"]
