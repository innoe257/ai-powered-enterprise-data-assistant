-- ============================================================
-- AI-Powered Enterprise Data Assistant (RAG + Cortex) - Database Setup
-- Author: Innocent Mamvura
-- Description: Creates warehouses, databases, schemas, tables,
--              and stages for the financial RAG pipeline.
-- ============================================================

-- ---------------------------------------------------------
-- 1. WAREHOUSE SETUP
-- ---------------------------------------------------------

USE ROLE ACCOUNTADMIN;

-- Create dedicated warehouse for RAG workloads
CREATE WAREHOUSE IF NOT EXISTS FINANCIAL_RAG_WH
    WITH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 300
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

-- Create warehouse for compute-intensive tasks (embeddings)
CREATE WAREHOUSE IF NOT EXISTS FINANCIAL_RAG_COMPUTE_WH
    WITH
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 300
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

-- ---------------------------------------------------------
-- 2. DATABASE & SCHEMA SETUP
-- ---------------------------------------------------------

CREATE DATABASE IF NOT EXISTS FINANCIAL_RAG;
USE DATABASE FINANCIAL_RAG;

CREATE SCHEMA IF NOT EXISTS RAW_DATA;
CREATE SCHEMA IF NOT EXISTS PROCESSED_DATA;
CREATE SCHEMA IF NOT EXISTS VECTOR_STORE;
CREATE SCHEMA IF NOT EXISTS ANALYTICS;

-- ---------------------------------------------------------
-- 3. STAGES (for file ingestion)
-- ---------------------------------------------------------

USE SCHEMA RAW_DATA;

-- Stage for raw SEC filings (HTML/Text)
CREATE STAGE IF NOT EXISTS SEC_FILINGS_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Stage for raw SEC filing documents';

-- Stage for processed chunks
CREATE STAGE IF NOT EXISTS CHUNKS_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Stage for processed text chunks';

-- Stage for embeddings
CREATE STAGE IF NOT EXISTS EMBEDDINGS_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Stage for vector embeddings';

-- ---------------------------------------------------------
-- 4. RAW TABLES
-- ---------------------------------------------------------

-- Raw filing metadata
CREATE TABLE IF NOT EXISTS RAW_DATA.SEC_FILINGS (
    filing_id VARCHAR(50) PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    form_type VARCHAR(10) NOT NULL,
    filing_date DATE NOT NULL,
    fiscal_year INT,
    fiscal_period VARCHAR(5),
    accession_number VARCHAR(30),
    sec_url VARCHAR(500),
    file_path VARCHAR(500),
    file_size_bytes INT,
    content_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Raw text chunks (before embedding)
CREATE TABLE IF NOT EXISTS RAW_DATA.TEXT_CHUNKS (
    chunk_id VARCHAR(50) PRIMARY KEY,
    filing_id VARCHAR(50) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    form_type VARCHAR(10) NOT NULL,
    chunk_index INT NOT NULL,
    chunk_text VARCHAR(10000),
    char_count INT,
    word_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (filing_id) REFERENCES RAW_DATA.SEC_FILINGS(filing_id)
);

-- ---------------------------------------------------------
-- 5. VECTOR STORE TABLES (for Cortex Search)
-- ---------------------------------------------------------

USE SCHEMA VECTOR_STORE;

-- Document embeddings using VECTOR data type (768 dims for EMBED_TEXT_768)
CREATE TABLE IF NOT EXISTS VECTOR_STORE.DOCUMENT_EMBEDDINGS (
    embedding_id VARCHAR(50) PRIMARY KEY,
    chunk_id VARCHAR(50) NOT NULL,
    filing_id VARCHAR(50) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    embedding VECTOR(FLOAT, 768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Search results cache
CREATE TABLE IF NOT EXISTS VECTOR_STORE.SEARCH_HISTORY (
    search_id VARCHAR(50) PRIMARY KEY,
    query_text VARCHAR(2000),
    query_embedding VECTOR(FLOAT, 768),
    results_json VARIANT,
    response_time_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------
-- 6. STRUCTURED FINANCIAL DATA (XBRL)
-- ---------------------------------------------------------

USE SCHEMA PROCESSED_DATA;

-- Financial metrics time series
CREATE TABLE IF NOT EXISTS PROCESSED_DATA.FINANCIAL_METRICS (
    metric_id VARCHAR(50) PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    concept VARCHAR(100),
    metric_name VARCHAR(100),
    value DECIMAL(20, 2),
    unit VARCHAR(10),
    period_start DATE,
    period_end DATE,
    fiscal_year INT,
    fiscal_period VARCHAR(5),
    statement_type VARCHAR(50),
    is_audited BOOLEAN,
    data_quality VARCHAR(20),
    confidence_score DECIMAL(3, 2),
    accession_number VARCHAR(30),
    form_type VARCHAR(10),
    filing_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Company info dimension
CREATE TABLE IF NOT EXISTS PROCESSED_DATA.COMPANY_INFO (
    ticker VARCHAR(10) PRIMARY KEY,
    cik VARCHAR(20),
    company_name VARCHAR(200),
    exchange VARCHAR(20),
    sector VARCHAR(100),
    industry VARCHAR(100),
    fiscal_year_end VARCHAR(10),
    state_of_incorporation VARCHAR(10),
    shares_outstanding BIGINT,
    public_float DECIMAL(20, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------
-- 7. ANALYTICS VIEWS
-- ---------------------------------------------------------

USE SCHEMA ANALYTICS;

-- Revenue summary by company
CREATE OR REPLACE VIEW ANALYTICS.VW_REVENUE_SUMMARY AS
SELECT
    ticker,
    fiscal_year,
    MAX(CASE WHEN fiscal_period = 'FY' THEN value END) AS annual_revenue,
    MAX(CASE WHEN fiscal_period = 'Q1' THEN value END) AS q1_revenue,
    MAX(CASE WHEN fiscal_period = 'Q2' THEN value END) AS q2_revenue,
    MAX(CASE WHEN fiscal_period = 'Q3' THEN value END) AS q3_revenue,
    MAX(CASE WHEN fiscal_period = 'Q4' THEN value END) AS q4_revenue
FROM PROCESSED_DATA.FINANCIAL_METRICS
WHERE metric_name = 'Revenue'
GROUP BY ticker, fiscal_year
ORDER BY ticker, fiscal_year DESC;

-- Latest metrics snapshot
CREATE OR REPLACE VIEW ANALYTICS.VW_LATEST_METRICS AS
SELECT
    m.ticker,
    c.company_name,
    m.metric_name,
    m.value,
    m.unit,
    m.period_end,
    m.fiscal_year,
    m.fiscal_period
FROM PROCESSED_DATA.FINANCIAL_METRICS m
JOIN PROCESSED_DATA.COMPANY_INFO c ON m.ticker = c.ticker
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY m.ticker, m.metric_name
    ORDER BY m.period_end DESC
) = 1;

-- ---------------------------------------------------------
-- 8. DYNAMIC TABLES (for incremental processing)
-- ---------------------------------------------------------

USE SCHEMA PROCESSED_DATA;

-- Auto-updating chunk count per filing
CREATE OR REPLACE DYNAMIC TABLE DT_FILING_CHUNK_STATS
    TARGET_LAG = '1 HOUR'
    WAREHOUSE = FINANCIAL_RAG_COMPUTE_WH
AS
SELECT
    f.filing_id,
    f.ticker,
    f.form_type,
    f.filing_date,
    COUNT(c.chunk_id) AS chunk_count,
    SUM(c.word_count) AS total_words,
    MAX(c.created_at) AS last_chunked_at
FROM RAW_DATA.SEC_FILINGS f
LEFT JOIN RAW_DATA.TEXT_CHUNKS c ON f.filing_id = c.filing_id
GROUP BY f.filing_id, f.ticker, f.form_type, f.filing_date;

-- ---------------------------------------------------------
-- 9. ACCESS CONTROL
-- ---------------------------------------------------------

-- Create service role for application
CREATE ROLE IF NOT EXISTS FINANCIAL_RAG_ROLE;

GRANT USAGE ON WAREHOUSE FINANCIAL_RAG_WH TO ROLE FINANCIAL_RAG_ROLE;
GRANT USAGE ON WAREHOUSE FINANCIAL_RAG_COMPUTE_WH TO ROLE FINANCIAL_RAG_ROLE;

GRANT USAGE ON DATABASE FINANCIAL_RAG TO ROLE FINANCIAL_RAG_ROLE;
GRANT USAGE ON SCHEMA FINANCIAL_RAG.RAW_DATA TO ROLE FINANCIAL_RAG_ROLE;
GRANT USAGE ON SCHEMA FINANCIAL_RAG.PROCESSED_DATA TO ROLE FINANCIAL_RAG_ROLE;
GRANT USAGE ON SCHEMA FINANCIAL_RAG.VECTOR_STORE TO ROLE FINANCIAL_RAG_ROLE;
GRANT USAGE ON SCHEMA FINANCIAL_RAG.ANALYTICS TO ROLE FINANCIAL_RAG_ROLE;

-- Table permissions
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA FINANCIAL_RAG.RAW_DATA TO ROLE FINANCIAL_RAG_ROLE;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA FINANCIAL_RAG.PROCESSED_DATA TO ROLE FINANCIAL_RAG_ROLE;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA FINANCIAL_RAG.VECTOR_STORE TO ROLE FINANCIAL_RAG_ROLE;
GRANT SELECT ON ALL VIEWS IN SCHEMA FINANCIAL_RAG.ANALYTICS TO ROLE FINANCIAL_RAG_ROLE;

-- Future grants
GRANT SELECT, INSERT, UPDATE ON FUTURE TABLES IN SCHEMA FINANCIAL_RAG.RAW_DATA TO ROLE FINANCIAL_RAG_ROLE;
GRANT SELECT, INSERT, UPDATE ON FUTURE TABLES IN SCHEMA FINANCIAL_RAG.PROCESSED_DATA TO ROLE FINANCIAL_RAG_ROLE;
GRANT SELECT, INSERT, UPDATE ON FUTURE TABLES IN SCHEMA FINANCIAL_RAG.VECTOR_STORE TO ROLE FINANCIAL_RAG_ROLE;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA FINANCIAL_RAG.ANALYTICS TO ROLE FINANCIAL_RAG_ROLE;

GRANT ROLE FINANCIAL_RAG_ROLE TO USER IDENTIFIER($CURRENT_USER);

-- ---------------------------------------------------------
-- 10. SEARCH OPTIMIZATION
-- ---------------------------------------------------------

ALTER TABLE RAW_DATA.SEC_FILINGS ADD SEARCH OPTIMIZATION ON EQUALITY(ticker, form_type);
ALTER TABLE RAW_DATA.TEXT_CHUNKS ADD SEARCH OPTIMIZATION ON EQUALITY(ticker, filing_id);
ALTER TABLE PROCESSED_DATA.FINANCIAL_METRICS ADD SEARCH OPTIMIZATION ON EQUALITY(ticker, metric_name);

-- ---------------------------------------------------------
-- DONE
-- ---------------------------------------------------------
SELECT 'Database setup complete!' AS status;
