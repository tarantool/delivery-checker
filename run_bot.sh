#!/usr/bin/env bash

set -e

export LOG_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
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

source venv/bin/activate
if [ -z "${LOG_FILE}" ]; then
    python3 bot.py
else
    mkdir -p "$(dirname "${LOG_FILE}")"
    python3 bot.py >"${LOG_FILE}"
fi
