#!/usr/bin/env bash
# Avvia dBX senza attivare alcun virtualenv.
# Sceglie l'interprete giusto (venv locale se presente, altrimenti python3 di sistema)
# e lancia `python -m dbx` passando tutti gli argomenti ricevuti.
#
#   ./start.sh                 apre dBX
#   ./start.sh --demo          apre il progetto dimostrativo
#   ./start.sh /percorso/prog  apre un progetto esistente
#
# Variabili opzionali:
#   DBX_PYTHON   interprete da usare (bypassa la ricerca automatica)
#   DBX_THEME    light | dark
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

find_python() {
    if [[ -n "${DBX_PYTHON:-}" ]]; then
        echo "$DBX_PYTHON"
        return 0
    fi
    # Preferisce il venv del progetto (usato direttamente, senza attivarlo).
    local candidate
    for candidate in .venv/bin/python venv/bin/python; do
        if [[ -x "$candidate" ]] && "$candidate" -c "import PyQt6" >/dev/null 2>&1; then
            echo "$candidate"
            return 0
        fi
    done
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import PyQt6" >/dev/null 2>&1; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

if ! PYTHON="$(find_python)"; then
    cat >&2 <<'EOF'
dBX: nessun interprete Python con PyQt6 trovato.

Installa la dipendenza con uno dei seguenti comandi:

  python3 -m pip install --user PyQt6          # installazione utente, nessun venv
  python3 -m venv .venv && .venv/bin/pip install -e .   # venv locale (start.sh lo usa da solo)

Oppure indica l'interprete da usare:

  DBX_PYTHON=/percorso/al/python ./start.sh
EOF
    exit 1
fi

exec "$PYTHON" -m dbx "$@"
