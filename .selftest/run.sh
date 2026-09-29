#!/usr/bin/env bash
# Run the template's self-tests (template-only; excluded from scaffolds by .scaffoldignore).
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" -m unittest discover -s .selftest -p 'test_*.py' "$@"
