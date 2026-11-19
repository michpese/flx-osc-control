#!/usr/bin/env bash
# Baut die eigenständige Linux-Einzeldatei dist/flx-panel aus dem Repo-Wurzelverzeichnis.
# Bevorzugt automatisch ein System-Python (>= 3.11) mit installiertem python3-tk, damit
# libtk8.6 mit Xft/Fontconfig (kantengeglättete Systemschriften & volles UTF-8) gebündelt wird.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN=""
for candidate in /usr/bin/python3.12 /usr/bin/python3.11 /usr/bin/python3; do
    if [[ -x "$candidate" ]] && "$candidate" -c 'import sys, tkinter; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        PYTHON_BIN="$candidate"
        break
    fi
done

echo "==> Synchronisiere Workspace und PyInstaller ..."
if [[ -n "$PYTHON_BIN" ]]; then
    echo "    Verwende System-Python mit Xft-Tkinter: $PYTHON_BIN"
    uv sync --all-packages --extra build --python "$PYTHON_BIN"
else
    echo "    Hinweis: Kein System-Python (>=3.11) mit python3-tk gefunden; nutze uv-Python."
    uv sync --all-packages --extra build --python 3.12
fi

echo "==> Baue flx-panel ..."
uv run --no-sync --package playback-panel flx-panel-build "$@"

if [[ -x "dist/flx-panel" ]]; then
    echo "==> Prüfe gebautes Binary mit Beispiel-Konfiguration ..."
    ./dist/flx-panel --check shows/playbacks.example.yaml
    echo ""
    echo "Fertig! Die ausführbare Linux-Einzeldatei liegt unter:"
    echo "  $REPO_ROOT/dist/flx-panel"
fi
