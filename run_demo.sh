#!/bin/bash
# Run the AI-Powered Enterprise Data Assistant in Demo mode locally

cd "$(dirname "$0")"

export APP_MODE=demo

echo "=========================================="
echo "Starting AI-Powered Enterprise Data Assistant"
echo "Mode: DEMO (local files)"
echo "=========================================="
echo ""

streamlit run streamlit_app.py
