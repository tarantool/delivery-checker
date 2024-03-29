#!/usr/bin/env bash

set -e

while [[ $# -gt 0 ]]; do
    case "$1" in
    -f)
        FILE_MODE=true
        shift
        ;;
    -l | --log_file)
        LOG_FILE="$2"
        shift
        shift
        ;;
    *)
        echo "Unknown argument: $1"
        exit
        ;;
    esac
done

if [ -n "${FILE_MODE}" ] && [ -z "${LOG_FILE}" ]; then
    LOG_FILE="archive/$(date +"%Y%m%d_%H%M%S").log"
fi

cd "$(dirname "$0")"
if [ -z "${LOG_FILE}" ]; then
    ./venv/bin/python check.py -v
else
    mkdir -p "$(dirname "${LOG_FILE}")"
    ./venv/bin/python check.py &>"${LOG_FILE}"
fi
