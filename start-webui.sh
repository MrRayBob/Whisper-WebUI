#!/bin/bash

set -euo pipefail

source venv/bin/activate

if [ "${1:-}" = "--legacy" ]; then
    shift
    exec python3 app.py "$@"
fi

HOST="0.0.0.0"
PORT="7860"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --host|--server_name)
            HOST="${2:-}"
            shift 2
            ;;
        --port|--server_port)
            PORT="${2:-}"
            shift 2
            ;;
        *)
            echo "Unsupported flag for FastAPI mode: $1" >&2
            echo "Use --legacy to launch the Gradio UI with legacy arguments." >&2
            exit 1
            ;;
    esac
done

exec uvicorn backend.main:app --host "$HOST" --port "$PORT"
