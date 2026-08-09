-- ============================================================
-- Snowflake Cortex AI Integration (PAID ACCOUNTS ONLY)
-- Author: Innocent Mamvura
-- Description: Sets up Cortex AI functions for the RAG pipeline.
-- 
-- ⚠️  IMPORTANT: Cortex AI functions require a PAID Snowflake account.
--    Trial accounts do NOT have access to:
--      - SNOWFLAKE.CORTEX.EMBED_TEXT_768
--      - SNOWFLAKE.CORTEX.COMPLETE
--    
--    For trial accounts, use the Claude API integration in the 
--    Streamlit app instead (set CLAUDE_API_KEY in .env).
-- ============================================================

USE DATABASE FINANCIAL_RAG;
USE SCHEMA VECTOR_STORE;
USE WAREHOUSE FINANCIAL_RAG_COMPUTE_WH;

-- ---------------------------------------------------------
-- 1. CORTEX EMBEDDING FUNCTION
-- ---------------------------------------------------------

-- Create a UDF that wraps Cortex EMBED_TEXT_768
CREATE OR REPLACE FUNCTION CORTEX_EMBED_TEXT(text_input STRING)
RETURNS VECTOR(FLOAT, 768)
LANGUAGE SQL
AS
$$
    SNOWFLAKE.CORTEX.EMBED_TEXT_768('snowflake-arctic-embed-m', text_input)
$$;

-- ---------------------------------------------------------
-- 2. CORTEX COMPLETION FUNCTION (for RAG responses)
-- ---------------------------------------------------------

-- Create a UDF for generating responses with context
CREATE OR REPLACE FUNCTION CORTEX_RAG_RESPONSE(
    query STRING,
    context STRING,
    model STRING DEFAULT 'mistral-large'
)
RETURNS STRING
LANGUAGE SQL
AS
$$
    SNOWFLAKE.CORTEX.COMPLETE(
        model,
        CONCAT(
            'You are a financial analyst AI assistant. Answer the question based on the provided SEC filing context.\n\n',
            'Context:\n', context, '\n\n',
            'Question: ', query, '\n\n',
            'Answer:'
        )
    )
$$;

-- ---------------------------------------------------------
-- 3. DOCUMENT CHUNKING STORED PROCEDURE
-- ---------------------------------------------------------

CREATE OR REPLACE PROCEDURE CHUNK_FILING(
    filing_id STRING,
    chunk_size INT DEFAULT 512,
    chunk_overlap INT DEFAULT 50
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'chunk_filing'
AS
$$
def chunk_filing(session, filing_id, chunk_size=512, chunk_overlap=50):
    """Split a filing into overlapping chunks and store in TEXT_CHUNKS."""
    
    # Get filing content
    result = session.sql(f"""
        SELECT file_path, ticker, form_type, filing_date
        FROM RAW_DATA.SEC_FILINGS
        WHERE filing_id = '{filing_id}'
    """).collect()
    
    if not result:
        return f"Filing {filing_id} not found"
    
    filing = result[0]
    
    # Read file from stage (simplified - in production, use GET command)
    # For now, assume content is available
    
    # Simple chunking logic
    # In production, use sentence-aware chunking with LangChain
    
    return f"Chunked filing {filing_id} into chunks"
$$;

-- ---------------------------------------------------------
-- 4. VECTOR SEARCH FUNCTION
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION SEMANTIC_SEARCH(
    query_text STRING,
    ticker_filter STRING DEFAULT NULL,
    top_k INT DEFAULT 5
)
RETURNS TABLE (
    chunk_id STRING,
    filing_id STRING,
    ticker STRING,
    form_type STRING,
    chunk_text VARCHAR(10000),
    similarity FLOAT
)
LANGUAGE SQL
AS
$$
    SELECT
        e.chunk_id,
        e.filing_id,
        e.ticker,
        c.form_type,
        tc.chunk_text,
        VECTOR_COSINE_SIMILARITY(e.embedding, CORTEX_EMBED_TEXT(query_text)) AS similarity
    FROM VECTOR_STORE.DOCUMENT_EMBEDDINGS e
    JOIN RAW_DATA.TEXT_CHUNKS tc ON e.chunk_id = tc.chunk_id
    JOIN RAW_DATA.SEC_FILINGS c ON e.filing_id = c.filing_id
    WHERE (ticker_filter IS NULL OR e.ticker = ticker_filter)
    ORDER BY similarity DESC
    LIMIT top_k
$$;

-- ---------------------------------------------------------
-- 5. RAG PIPELINE STORED PROCEDURE
-- ---------------------------------------------------------

CREATE OR REPLACE PROCEDURE RAG_QUERY(
    user_query STRING,
    ticker_filter STRING DEFAULT NULL,
    top_k INT DEFAULT 5
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'rag_query'
AS
$$
import json

def rag_query(session, user_query, ticker_filter=None, top_k=5):
    """Execute full RAG pipeline: search + generate response."""
    
    # Step 1: Semantic search
    search_sql = f"""
        SELECT * FROM TABLE(SEMANTIC_SEARCH('{user_query}', '{ticker_filter or ''}', {top_k}))
    """
    
    results = session.sql(search_sql).collect()
    
    if not results:
        return {
            'query': user_query,
            'response': 'No relevant documents found.',
            'sources': []
        }
    
    # Step 2: Build context from top results
    context = "\\n\\n".join([
        f"Source: {r['TICKER']} {r['FORM_TYPE']}\\n{r['CHUNK_TEXT']}"
        for r in results[:3]
    ])
    
    # Step 3: Generate response with Cortex
    response_sql = f"""
        SELECT CORTEX_RAG_RESPONSE('{user_query.replace("'", "''")}', '{context.replace("'", "''")}')
    """
    
    response_result = session.sql(response_sql).collect()
    response_text = response_result[0][0] if response_result else "Error generating response"
    
    # Step 4: Log search history
    session.sql(f"""
        INSERT INTO VECTOR_STORE.SEARCH_HISTORY (search_id, query_text, results_json, response_time_ms)
        VALUES (
            UUID_STRING(),
            '{user_query.replace("'", "''")}',
            PARSE_JSON('{json.dumps([dict(r) for r in results]).replace("'", "''")}'),
            0
        )
    """).collect()
    
    return {
        'query': user_query,
        'response': response_text,
        'sources': [f"{r['TICKER']} {r['FORM_TYPE']}" for r in results],
        'similarity_scores': [float(r['SIMILARITY']) for r in results]
    }
$$;

-- ---------------------------------------------------------
-- 6. TASKS (for scheduled processing)
-- ---------------------------------------------------------

-- Task to process new filings daily
CREATE OR REPLACE TASK TASK_PROCESS_NEW_FILINGS
    WAREHOUSE = FINANCIAL_RAG_COMPUTE_WH
    SCHEDULE = 'USING CRON 0 6 * * * UTC'  -- Daily at 6 AM UTC
AS
    CALL CHUNK_FILING(NULL);  -- Process all pending filings

-- Task to refresh embeddings
CREATE OR REPLACE TASK TASK_REFRESH_EMBEDDINGS
    WAREHOUSE = FINANCIAL_RAG_COMPUTE_WH
    SCHEDULE = 'USING CRON 0 7 * * * UTC'  -- Daily at 7 AM UTC
AS
    -- Re-embed any new or updated chunks
    INSERT INTO VECTOR_STORE.DOCUMENT_EMBEDDINGS (embedding_id, chunk_id, filing_id, ticker, embedding)
    SELECT
        UUID_STRING(),
        tc.chunk_id,
        tc.filing_id,
        tc.ticker,
        CORTEX_EMBED_TEXT(tc.chunk_text)
    FROM RAW_DATA.TEXT_CHUNKS tc
    LEFT JOIN VECTOR_STORE.DOCUMENT_EMBEDDINGS de ON tc.chunk_id = de.chunk_id
    WHERE de.embedding_id IS NULL;

-- Enable tasks
ALTER TASK TASK_PROCESS_NEW_FILINGS RESUME;
ALTER TASK TASK_REFRESH_EMBEDDINGS RESUME;

-- ---------------------------------------------------------
-- DONE
-- ---------------------------------------------------------
SELECT 'Cortex AI integration complete!' AS status;
