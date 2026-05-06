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

# Cppcheck via apt. Das Addon-Skript misra.py ist im aktuellen Debian-
# trixie-Paket (cppcheck 2.17.1) NICHT mit ausgeliefert — wir holen es
# version-synchron aus dem Cppcheck-Upstream-Repo. Damit hängen Tool und
# Addon nicht an Debian-Paketier-Entscheidungen.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        cppcheck \
        ca-certificates \
        curl \
 && rm -rf /var/lib/apt/lists/*

# addons/-Verzeichnis passend zur installierten Cppcheck-Version laden.
# Wir nehmen das ganze Verzeichnis (statt nur misra.py), weil misra.py
# auf cppcheckdata.py und ggf. weitere Addon-Helper angewiesen ist.
# Tags im Upstream-Repo haben kein „v"-Prefix („2.17.1", nicht „v2.17.1").
RUN set -eu; \
    CPPCHECK_VERSION="$(cppcheck --version | awk '{print $2}')"; \
    echo "Cppcheck $CPPCHECK_VERSION → addons/ @ tag $CPPCHECK_VERSION"; \
    mkdir -p "${CSA26_CPPCHECK_ADDONS_DIR}"; \
    curl -sSfL \
        "https://codeload.github.com/danmar/cppcheck/tar.gz/refs/tags/${CPPCHECK_VERSION}" \
      | tar -xz --strip-components=2 -C "${CSA26_CPPCHECK_ADDONS_DIR}" \
            "cppcheck-${CPPCHECK_VERSION}/addons"; \
    test -s "${CSA26_CPPCHECK_ADDONS_DIR}/misra.py"; \
    test -s "${CSA26_CPPCHECK_ADDONS_DIR}/cppcheckdata.py"

# Wrapper-Code installieren
COPY pyproject.toml /opt/csa26/
COPY src/ /opt/csa26/src/
COPY rules/ /opt/csa26/rules/

RUN pip install --no-cache-dir /opt/csa26

# GitHub mountet den Repo-Inhalt unter /github/workspace und CD-t dorthin
# bevor ENTRYPOINT läuft. Kein WORKDIR nötig.

ENTRYPOINT ["csa26-action"]
