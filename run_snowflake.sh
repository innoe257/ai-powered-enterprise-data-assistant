#!/bin/bash
# Run the AI-Powered Enterprise Data Assistant in Snowflake mode locally

cd "$(dirname "$0")"

export APP_MODE=snowflake
export SNOWFLAKE_ACCOUNT=KFRSGXO-ME10745
export SNOWFLAKE_USER=INNOCENT
export SNOWFLAKE_PASSWORD='q~aVD!3UMQ4k"n8'
export SNOWFLAKE_ROLE=ACCOUNTADMIN
export SNOWFLAKE_WAREHOUSE=FINANCIAL_RAG_WH
export SNOWFLAKE_DATABASE=FINANCIAL_RAG
export SNOWFLAKE_SCHEMA=PUBLIC

echo "=========================================="
echo "Starting AI-Powered Enterprise Data Assistant"
echo "Mode: SNOWFLAKE"
echo "Account: $SNOWFLAKE_ACCOUNT"
echo "=========================================="
echo ""

streamlit run streamlit_app.py
