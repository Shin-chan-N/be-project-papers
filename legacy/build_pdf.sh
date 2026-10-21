#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/../venv/bin/python3" ]; then
    PYTHON_BIN="$SCRIPT_DIR/../venv/bin/python3"
elif [ -f "$SCRIPT_DIR/venv/bin/python3" ]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
else
    echo "Error: python3 not found."
    exit 1
fi

echo "=========================================="
echo "Compiling Survey Paper to PDF locally"
echo "=========================================="
"$PYTHON_BIN" "$SCRIPT_DIR/compile_paper.py"

echo ""
echo "Compilation complete:"
echo " - DOCX: $SCRIPT_DIR/survey_paper.docx"
echo " - PDF:  $SCRIPT_DIR/survey_paper.pdf"
pdfinfo "$SCRIPT_DIR/survey_paper.pdf" | grep -E "Pages|Title" || true
echo "=========================================="

