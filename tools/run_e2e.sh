#!/usr/bin/env bash
# Avvio rapido del harness E2E dBX. Passa tutte le opzioni a e2e_harness.py.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 tools/e2e_harness.py "$@"
