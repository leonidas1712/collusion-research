#!/usr/bin/env bash
# Restore checksum-verified release data. No release is assumed to exist yet.
set -euo pipefail
exec python3 "$(dirname "$0")/fetch_run_data.py" "$@"
