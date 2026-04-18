#!/bin/bash

# Ensure we are in the correct directory
cd "$(dirname "$0")"

echo "========================================="
echo "🚀 Starting Cloud-Native PM Dashboard..."
echo "========================================="
echo "Installing/checking dependencies..."
python -m pip install -r requirements.txt -q

echo "Starting Uvicorn Server on port 8000..."
echo "Auto-reload is enabled for changes to .py, .md, and .html files."
echo "Press Ctrl+C to stop the server."
echo "========================================="

# Run uvicorn with reload enabled, watching for changes in specific directories/file types
python -m uvicorn main:app --reload --reload-include "*.md" --reload-include "*.html" --port 8000
