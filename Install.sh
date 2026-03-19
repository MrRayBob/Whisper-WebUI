#!/bin/bash
set -euo pipefail

TORCH_EXTRA_INDEX_URL="${TORCH_EXTRA_INDEX_URL:-https://download.pytorch.org/whl/cu128}"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

python3 -m pip install -U pip "setuptools<82" wheel
python3 -m pip install -r requirements.txt --extra-index-url "$TORCH_EXTRA_INDEX_URL"
python3 -m pip install --no-build-isolation -r requirements-legacy.txt

echo "Requirements installed successfully."

deactivate
