#!/bin/bash
set -e

echo "=== Nirbaan ERP Model Setup ==="
echo ""

if ! command -v ollama &> /dev/null; then
    echo "ERROR: Ollama is not installed."
    echo "Download and install it from: https://ollama.com/download"
    exit 1
fi

echo "Ollama found."
echo "Registering nirbaan-erp-federated model..."
echo "This will download ~4.5GB on first run. Please wait."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ollama create nirbaan-erp-federated -f "$SCRIPT_DIR/Modelfile"

echo ""
echo "SUCCESS! Model registered as: nirbaan-erp-federated"
echo "You can now start the Nirbaan backend."
