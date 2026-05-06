# csa26 — MISRA-C:2012 Pre-Audit-Container
#
# Phase-1-Prototyp. Wrapper über Cppcheck + dessen MISRA-Addon.
# Wird von action.yml als Docker-Container-Action geladen.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CSA26_CPPCHECK_ADDONS_DIR=/usr/share/cppcheck/addons

# Cppcheck inklusive MISRA-Addon. Das Debian-Paket legt misra.py unter
# /usr/share/cppcheck/addons/ ab — der Wrapper sucht es genau dort.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        cppcheck \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Sanity-Check beim Build: Cppcheck-Binary und MISRA-Addon vorhanden?
RUN cppcheck --version \
 && test -f "${CSA26_CPPCHECK_ADDONS_DIR}/misra.py"

# Wrapper-Code installieren
COPY pyproject.toml /opt/csa26/
COPY src/ /opt/csa26/src/
COPY rules/ /opt/csa26/rules/

RUN pip install --no-cache-dir /opt/csa26

# GitHub mountet den Repo-Inhalt unter /github/workspace und CD-t dorthin
# bevor ENTRYPOINT läuft. Kein WORKDIR nötig.

ENTRYPOINT ["csa26-action"]
