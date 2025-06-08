#!/bin/bash
set -e

# 1) Esegui prima python_minizinc.py
echo "→ Executing python_minizinc.py..."
python3 models/CP/python_minizinc.py

# 2) Se il comando precedente è terminato (exit code 0), esegui mcp.py
echo "→ Executing mcp.py..."
python3 mcp.py -c config.mcp

echo "→ All scripts were executed."
