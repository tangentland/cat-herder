#!/usr/bin/env bash
# Lint the project's GMD graph with the correct scope.
#
# CLAUDE.md is the root agent-rules doc; its `id` is the resolution target for
# `[[claude#...]]` references elsewhere. Linting docs/ alone would surface
# dangling-anchor errors that resolve cleanly once CLAUDE.md is included.
# Exit non-zero on errors; warnings (e.g. `no-gmd-version` on prose plan files)
# are informational and do NOT fail.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# The linter is bundled under tools/gmd/.
LINTER="$ROOT/tools/gmd/lint.py"

if [[ ! -f "$LINTER" ]]; then
  echo "gmd lint not found at $LINTER" >&2
  echo "The bundled tools/gmd/lint.py is missing — restore it from the template." >&2
  exit 2
fi

cd "$ROOT"
exec python3 "$LINTER" CLAUDE.md SETUP.md docs/ "$@"
