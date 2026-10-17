#!/usr/bin/env bash
set -euo pipefail
TASK_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
exec python3 "$TASK_DIR/hidden/score.py" "$@"
