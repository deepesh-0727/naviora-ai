#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_command="${PYTHON:-python3}"
command -v "${python_command}" >/dev/null 2>&1 || { echo "Backup/restore failed: ${python_command} is unavailable." >&2; exit 1; }
"${python_command}" "${script_dir}/backup_restore.py" restore "$@"
