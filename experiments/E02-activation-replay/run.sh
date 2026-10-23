#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -x "$here/.venv/bin/python" ]]; then
  uv venv "$here/.venv" --python 3.11
  uv pip sync --python "$here/.venv/bin/python" "$here/requirements-lock.txt"
fi
command="${1:-help}"
if [[ $# -gt 0 ]]; then shift; fi
case "$command" in
  replay) exec "$here/.venv/bin/python" "$here/replay.py" "$@" ;;
  directions) exec "$here/.venv/bin/python" "$here/directions.py" "$@" ;;
  test) exec "$here/.venv/bin/python" -m unittest discover -s "$here" -p 'test_*.py' ;;
  *) echo "Usage: $0 {replay|directions|test} [arguments]"; exit 2 ;;
esac
