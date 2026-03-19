#!/bin/bash

set -euo pipefail

source venv/bin/activate
exec python3 app.py "$@"
