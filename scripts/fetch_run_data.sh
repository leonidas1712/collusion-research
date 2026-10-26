#!/usr/bin/env bash
# Restore the checksum-pinned data-v1 release; gh authentication supports private drafts.
set -euo pipefail
exec python3 "$(dirname "$0")/fetch_run_data.py" "$@"
