-- ============================================================
-- Snowflake Backend Setup for TRIAL Accounts
-- Author: Innocent Mamvura
-- Description: Sets up basic functions that work on trial accounts.
--              No Cortex AI required. The Streamlit app uses
--              Claude API for AI responses instead.
-- ============================================================

USE DATABASE FINANCIAL_RAG;
USE SCHEMA VECTOR_STORE;
USE WAREHOUSE FINANCIAL_RAG_WH;

-- ---------------------------------------------------------
-- 1. KEYWORD SEARCH FUNCTION (works on all accounts)
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION KEYWORD_SEARCH(
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
    relevance FLOAT
)
LANGUAGE SQL
AS
$$
    SELECT
        tc.chunk_id,
        tc.filing_id,
        tc.ticker,
        sf.form_type,
        tc.chunk_text,
        -- Simple relevance score based on term frequency
        (
            LENGTH(tc.chunk_text) - LENGTH(REPLACE(UPPER(tc.chunk_text), UPPER(query_text), ''))
        ) / GREATEST(LENGTH(query_text), 1) * 1.0 AS relevance
    FROM RAW_DATA.TEXT_CHUNKS tc
    JOIN RAW_DATA.SEC_FILINGS sf ON tc.filing_id = sf.filing_id
    WHERE 
        (ticker_filter IS NULL OR tc.ticker = ticker_filter)
        AND tc.chunk_text ILIKE '%' || query_text || '%'
    ORDER BY relevance DESC
    LIMIT top_k
$$;

-- ---------------------------------------------------------
-- 2. FINANCIAL METRICS AGGREGATION FUNCTION
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION GET_COMPANY_METRICS(ticker_code STRING)
RETURNS TABLE (
    metric_name STRING,
    latest_value DECIMAL(20,2),
    latest_period STRING,
    yoy_growth_percent DECIMAL(10,2)
)
LANGUAGE SQL
AS
$$
    SELECT
        metric_name,
        value AS latest_value,
        fiscal_year || ' ' || fiscal_period AS latest_period,
        -- Calculate YoY growth if we have prior year data
        (
            (value - LAG(value) OVER (PARTITION BY metric_name ORDER BY period_end)) 
            / NULLIF(LAG(value) OVER (PARTITION BY metric_name ORDER BY period_end), 0)
        ) * 100 AS yoy_growth_percent
    FROM PROCESSED_DATA.FINANCIAL_METRICS
    WHERE ticker = ticker_code
    QUALIFY ROW_NUMBER() OVER (PARTITION BY metric_name ORDER BY period_end DESC) = 1
    ORDER BY metric_name
$$;

-- ---------------------------------------------------------
-- 3. SEARCH LOGGING (for analytics)
-- ---------------------------------------------------------

CREATE OR REPLACE PROCEDURE LOG_SEARCH(
    p_query_text STRING,
    p_results_count INT,
    p_response_time_ms INT
)
RETURNS STRING
LANGUAGE SQL
AS
$$
    INSERT INTO VECTOR_STORE.SEARCH_HISTORY (
        search_id, 
        query_text, 
        results_json, 
        response_time_ms
    )
    VALUES (
        UUID_STRING(),
        p_query_text,
        TO_VARIANT(OBJECT_CONSTRUCT('result_count', p_results_count)),
        p_response_time_ms
    );
    
    SELECT 'Search logged' AS result;
$$;

-- ---------------------------------------------------------
-- 4. FILING SUMMARY VIEW
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW ANALYTICS.VW_FILING_OVERVIEW AS
SELECT
    sf.ticker,
    ci.company_name,
    sf.form_type,
    sf.filing_date,
    COUNT(tc.chunk_id) AS total_chunks,
    SUM(tc.word_count) AS total_words,
    MAX(tc.created_at) AS last_processed_at
FROM RAW_DATA.SEC_FILINGS sf
LEFT JOIN RAW_DATA.TEXT_CHUNKS tc ON sf.filing_id = tc.filing_id
LEFT JOIN PROCESSED_DATA.COMPANY_INFO ci ON sf.ticker = ci.ticker
GROUP BY sf.ticker, ci.company_name, sf.form_type, sf.filing_date;

-- ---------------------------------------------------------
-- 5. METRICS COMPARISON VIEW
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW ANALYTICS.VW_METRICS_COMPARISON AS
SELECT
    m.ticker,
    ci.company_name,
    ci.sector,
    m.metric_name,
    m.value,
    m.unit,
    m.fiscal_year,
    m.fiscal_period,
    m.period_end,
    RANK() OVER (PARTITION BY m.metric_name, m.fiscal_year ORDER BY m.value DESC) AS rank_by_value
FROM PROCESSED_DATA.FINANCIAL_METRICS m
JOIN PROCESSED_DATA.COMPANY_INFO ci ON m.ticker = ci.ticker
WHERE m.value IS NOT NULL;

-- ---------------------------------------------------------
-- DONE
-- ---------------------------------------------------------
SELECT 'Trial account setup complete! No Cortex AI required.' AS status;
