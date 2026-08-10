# AI-Powered Enterprise Data Assistant
## Technical Documentation & Architecture Guide

**Author:** Innocent Mamvura  
**Role:** Lead Data Scientist | AI/ML & GenAI Specialist  
**Repository:** [github.com/innoe257/ai-powered-enterprise-data-assistant](https://github.com/innoe257/ai-powered-enterprise-data-assistant)  
**Live Demo:** [streamlit.app](https://innoe257-ai-powered-enterprise-data-assist-streamlit-app-fmkywe.streamlit.app/)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Data Pipeline](#4-data-pipeline)
5. [Snowflake Backend](#5-snowflake-backend)
6. [RAG Implementation](#6-rag-implementation)
7. [Local Development](#7-local-development)
8. [Deployment](#8-deployment)
9. [Key Features & Screenshots](#9-key-features--screenshots)
10. [Future Enhancements](#10-future-enhancements)

---

## 1. Executive Summary

This project demonstrates an **enterprise-grade AI-powered financial document analysis system** built on the Snowflake Data Cloud. It combines Retrieval-Augmented Generation (RAG) with real-time SEC filing data to enable natural language querying of financial documents.

### What It Does
- **Ingests** SEC EDGAR filings (10-K, 10-Q, 8-K) for 6 major tech companies
- **Processes** text into searchable chunks using Snowflake tables
- **Searches** documents using keyword-based retrieval
- **Generates** AI-powered responses using Claude API (Anthropic)
- **Visualizes** financial metrics with interactive Plotly dashboards
- **Deploys** as a Streamlit web application

### Business Value
- Reduces financial analysis time from hours to seconds
- Enables non-technical stakeholders to query complex financial data
- Demonstrates enterprise data architecture best practices
- Showcases modern AI/ML integration patterns

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                             │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  RAG Chat   │  │ Financial       │  │  Document Viewer            │  │
│  │  (Q&A)      │  │ Dashboard       │  │  (SEC Filing Browser)       │  │
│  └──────┬──────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
│         │                  │                         │                  │
│         └──────────────────┼─────────────────────────┘                  │
│                            ▼                                           │
│                    ┌───────────────┐                                   │
│                    │   Streamlit   │                                   │
│                    │   Frontend    │                                   │
│                    └───────┬───────┘                                   │
└────────────────────────────┼───────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │ Document Search │  │ Response Gen    │  │ Data Loader             │  │
│  │ (Keyword + RAG) │  │ (Claude API)    │  │ (Demo / Snowflake)      │  │
│  └────────┬────────┘  └────────┬────────┘  └────────────┬────────────┘  │
│           │                    │                        │               │
│           └────────────────────┼────────────────────────┘               │
│                                ▼                                        │
│                    ┌───────────────────────┐                            │
│                    │   Python Backend      │                            │
│                    │   (app/ package)      │                            │
│                    └───────────┬───────────┘                            │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                       │
│                                                                         │
│   ┌─────────────────┐         ┌─────────────────────────────────────┐  │
│   │  Local Files    │         │  Snowflake Data Cloud               │  │
│   │  (Demo Mode)    │         │  (Production Mode)                  │  │
│   │                 │         │                                     │  │
│   │  data/filings/  │◄───────►│  ┌─────────┐  ┌─────────┐         │  │
│   │  - CSV metadata │         │  │ RAW_DATA│  │PROCESSED│         │  │
│   │  - Text files   │         │  │         │  │  _DATA  │         │  │
│   │  - XBRL metrics │         │  │SEC_FILINGS│ │FINANCIAL│         │  │
│   │                 │         │  │TEXT_CHUNKS│ │ METRICS │         │  │
│   └─────────────────┘         │  └─────────┘  └─────────┘         │  │
│                               │                                     │  │
│                               │  ┌─────────┐  ┌─────────┐         │  │
│                               │  │VECTOR_  │  │ANALYTICS│         │  │
│                               │  │ STORE   │  │  VIEWS  │         │  │
│                               │  └─────────┘  └─────────┘         │  │
│                               └─────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### Core Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Streamlit | Web UI, widgets, data visualization |
| **Backend** | Python 3.12 | Application logic, data processing |
| **Data Warehouse** | Snowflake | Structured data storage, SQL analytics |
| **AI/LLM** | Anthropic Claude 3.5 Sonnet | Natural language response generation |
| **Data Viz** | Plotly | Interactive financial charts |
| **Data Processing** | Pandas, NumPy | Data manipulation and analysis |
| **Version Control** | Git + GitHub | Source control and CI/CD |

### Python Dependencies

```
streamlit>=1.28.0          # Web application framework
pandas>=2.0.0              # Data manipulation
numpy>=1.24.0              # Numerical computing
plotly>=5.18.0             # Interactive charts
anthropic>=0.21.0          # Claude API client
python-dotenv>=1.0.0       # Environment variables
snowflake-connector-python>=3.2.0  # Snowflake connection
```

---

## 4. Data Pipeline

### 4.1 Data Sources

**SEC EDGAR Database** (Electronic Data Gathering, Analysis, and Retrieval)
- Company filings: 10-K (Annual), 10-Q (Quarterly), 8-K (Current Reports)
- Companies tracked: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA
- Data includes: Filing text, XBRL financial metrics, metadata

### 4.2 Pipeline Stages

```
Stage 1: INGESTION
├── Download SEC filings from EDGAR API
├── Extract text content (HTML → plain text)
└── Parse XBRL financial data (revenue, net income, assets, etc.)

Stage 2: PROCESSING
├── Chunk text into 1,000-character segments with 100-char overlap
├── Normalize financial metrics (decimal values, fiscal periods)
├── Assign unique IDs to filings and chunks
└── Build filing metadata manifest

Stage 3: STORAGE (Snowflake)
├── Load filings into RAW_DATA.SEC_FILINGS
├── Load chunks into RAW_DATA.TEXT_CHUNKS
├── Load metrics into PROCESSED_DATA.FINANCIAL_METRICS
├── Load company info into PROCESSED_DATA.COMPANY_INFO
└── Create analytics views for reporting

Stage 4: RETRIEVAL
├── User submits natural language query
├── System searches TEXT_CHUNKS for keyword matches
├── Ranks results by term frequency relevance score
└── Returns top-K most relevant document segments

Stage 5: GENERATION
├── Build context from retrieved documents
├── Extract financial metrics for mentioned companies
├── Call Claude API with structured prompt
└── Return AI-generated response with citations
```

---

## 5. Snowflake Backend

### 5.1 Database Architecture

```sql
-- Warehouse Configuration
CREATE WAREHOUSE FINANCIAL_RAG_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 300
    AUTO_RESUME = TRUE;

-- Database & Schemas
CREATE DATABASE FINANCIAL_RAG;
CREATE SCHEMA RAW_DATA;       -- Source data
CREATE SCHEMA PROCESSED_DATA; -- Cleaned metrics
CREATE SCHEMA VECTOR_STORE;   -- Embeddings & search history
CREATE SCHEMA ANALYTICS;      -- Views & dashboards
```

### 5.2 Core Tables

#### RAW_DATA.SEC_FILINGS
Stores filing metadata for all tracked companies.

| Column | Type | Description |
|--------|------|-------------|
| filing_id | VARCHAR(50) PK | Unique identifier (TICKER_FORM_DATE) |
| ticker | VARCHAR(10) | Stock ticker symbol |
| form_type | VARCHAR(20) | Filing type (10-K, 10-Q, 8-K) |
| filing_date | DATE | SEC filing date |
| fiscal_year | INT | Reporting fiscal year |
| file_size_bytes | INT | Document size |

**Current data:** 21 filings across 6 companies

#### RAW_DATA.TEXT_CHUNKS
Stores processed text segments for search and retrieval.

| Column | Type | Description |
|--------|------|-------------|
| chunk_id | VARCHAR(50) PK | Unique chunk identifier |
| filing_id | VARCHAR(50) FK | Parent filing reference |
| ticker | VARCHAR(10) | Company ticker |
| chunk_index | INT | Position in document |
| chunk_text | VARCHAR(10000) | Text content segment |
| word_count | INT | Words in chunk |

**Current data:** 934 chunks from 21 filings

#### PROCESSED_DATA.FINANCIAL_METRICS
Stores structured XBRL financial data.

| Column | Type | Description |
|--------|------|-------------|
| metric_id | VARCHAR(50) PK | Unique metric record |
| ticker | VARCHAR(10) | Company ticker |
| metric_name | VARCHAR(100) | Metric label (Revenue, Net Income, etc.) |
| value | DECIMAL(20,2) | Numeric value |
| fiscal_year | INT | Reporting year |
| fiscal_period | VARCHAR(5) | FY, Q1, Q2, Q3, Q4 |

**Current data:** 600 metric records across 5 metrics × 6 companies

### 5.3 Analytics Views

```sql
-- Latest metrics snapshot per company
CREATE VIEW ANALYTICS.VW_LATEST_METRICS AS
SELECT ticker, metric_name, value, fiscal_year, fiscal_period
FROM PROCESSED_DATA.FINANCIAL_METRICS
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ticker, metric_name 
    ORDER BY period_end DESC
) = 1;

-- Revenue summary by company and year
CREATE VIEW ANALYTICS.VW_REVENUE_SUMMARY AS
SELECT ticker, fiscal_year,
    MAX(CASE WHEN fiscal_period = 'FY' THEN value END) AS annual_revenue
FROM PROCESSED_DATA.FINANCIAL_METRICS
WHERE metric_name = 'Revenue'
GROUP BY ticker, fiscal_year;
```

### 5.4 Search Functions

```sql
-- Keyword search across text chunks
CREATE FUNCTION KEYWORD_SEARCH(
    query_text STRING,
    ticker_filter STRING DEFAULT NULL,
    top_k INT DEFAULT 5
)
RETURNS TABLE (chunk_id STRING, ticker STRING, chunk_text VARCHAR, relevance FLOAT)
LANGUAGE SQL
AS $$
    SELECT chunk_id, ticker, chunk_text,
        (LENGTH(chunk_text) - LENGTH(REPLACE(UPPER(chunk_text), UPPER(query_text), '')))
        / GREATEST(LENGTH(query_text), 1) AS relevance
    FROM RAW_DATA.TEXT_CHUNKS
    WHERE chunk_text ILIKE '%' || query_text || '%'
    ORDER BY relevance DESC
    LIMIT top_k
$$;
```

---

## 6. RAG Implementation

### 6.1 Retrieval Strategy

The system uses **keyword-based retrieval** optimized for SEC filing text:

```python
def keyword_search(query: str, filings: list, top_k: int = 5) -> list:
    # 1. Tokenize query into terms (> 2 chars)
    query_terms = [t for t in query.lower().split() if len(t) > 2]
    
    # 2. Score each document by term frequency
    for filing in filings:
        score = sum(content.lower().count(term) for term in query_terms)
        if score > 0:
            results.append({
                'source': f"{ticker} {form_type} ({date})",
                'content': extract_snippet(content, query_terms[0]),
                'score': score
            })
    
    # 3. Return top-K by score
    return sorted(results, key=lambda x: x['score'], reverse=True)[:top_k]
```

### 6.2 Natural Language Understanding

Maps company names to ticker symbols for flexible querying:

```python
COMPANY_TO_TICKER = {
    'apple': 'AAPL', 'microsoft': 'MSFT',
    'google': 'GOOGL', 'alphabet': 'GOOGL',
    'amazon': 'AMZN', 'nvidia': 'NVDA', 'tesla': 'TSLA'
}

# "Compare Apple and Microsoft revenue" → ['AAPL', 'MSFT']
```

### 6.3 Response Generation Pipeline

```
User Query
    │
    ▼
┌─────────────────┐
│ 1. Extract      │
│    tickers from │
│    query        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Search       │
│    documents    │
│    (top_k=5)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ 3. Try Claude   │────►│ 4. Fallback to  │
│    API          │ No  │    rule-based   │
│    (if key set) │     │    response     │
└─────────────────┘     └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ AI-generated    │     │ Template-based  │
│ analysis with   │     │ comparison/sum- │
│ citations       │     │ mary/risk/etc   │
└─────────────────┘     └─────────────────┘
```

### 6.4 Claude API Prompt Structure

```
System: You are a financial analyst AI assistant. Answer questions 
based on the provided SEC filing context. Be concise, factual, and 
cite specific data points.

Context:
Document: AAPL 10-Q (2026-07-31)
[excerpt text...]

Document: MSFT 10-K (2026-07-29)
[excerpt text...]

AAPL Financial Data:
  - Revenue: $364,357,000,000 (2026 Q3)
  
MSFT Financial Data:
  - Revenue: $331,840,000,000 (2026 FY)

Question: Compare revenue growth between Apple and Microsoft
```

---

## 7. Local Development

### 7.1 Prerequisites

```bash
# Python 3.10+
python --version

# Git
git --version
```

### 7.2 Setup

```bash
# Clone repository
git clone https://github.com/innoe257/ai-powered-enterprise-data-assistant.git
cd ai-powered-enterprise-data-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 7.3 Running Locally

#### Option A: Demo Mode (local files, no Snowflake needed)

```bash
./run_demo.sh
# Or manually:
export APP_MODE=demo
streamlit run streamlit_app.py
```

#### Option B: Snowflake Mode (live database)

```bash
# Set credentials (or add to .env file)
export SNOWFLAKE_ACCOUNT=KFRSGXO-ME10745
export SNOWFLAKE_USER=INNOCENT
export SNOWFLAKE_PASSWORD='your_password'
export SNOWFLAKE_ROLE=ACCOUNTADMIN
export SNOWFLAKE_WAREHOUSE=FINANCIAL_RAG_WH
export SNOWFLAKE_DATABASE=FINANCIAL_RAG

# Run
./run_snowflake.sh
# Or manually:
export APP_MODE=snowflake
streamlit run streamlit_app.py
```

App opens at: **http://localhost:8501**

### 7.4 Environment Variables

| Variable | Required For | Description |
|----------|-------------|-------------|
| `APP_MODE` | Both | `demo` or `snowflake` |
| `SNOWFLAKE_ACCOUNT` | Snowflake mode | Account identifier |
| `SNOWFLAKE_USER` | Snowflake mode | Username |
| `SNOWFLAKE_PASSWORD` | Snowflake mode | Password |
| `SNOWFLAKE_ROLE` | Snowflake mode | Default: ACCOUNTADMIN |
| `SNOWFLAKE_WAREHOUSE` | Snowflake mode | Default: FINANCIAL_RAG_WH |
| `CLAUDE_API_KEY` | AI responses | Anthropic API key (optional) |

---

## 8. Deployment

### 8.1 Streamlit Cloud Deployment

**Current deployment:** [Live App](https://innoe257-ai-powered-enterprise-data-assist-streamlit-app-fmkywe.streamlit.app/)

**Steps:**
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect GitHub repository
4. Set main file: `streamlit_app.py`
5. Add secrets (optional): `CLAUDE_API_KEY`
6. Deploy

**File structure for deployment:**
```
repo-root/
├── streamlit_app.py          # Entry point (required by Streamlit Cloud)
├── app/
│   ├── main.py               # Main app logic
│   ├── components/
│   │   ├── chat.py           # RAG chat interface
│   │   ├── dashboard.py      # Financial dashboard
│   │   └── document_viewer.py # Document browser
│   └── utils/
│       ├── data_loader.py    # Data loading (demo + snowflake)
│       ├── embeddings.py     # Search + AI response generation
│       └── config.py         # Configuration
├── data/
│   └── filings/              # Local demo data
├── snowflake/
│   ├── sql/                  # Database setup scripts
│   └── python/               # Data loading scripts
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

### 8.2 Snowflake Setup (One-Time)

```bash
# Step 1: Run database setup SQL
# In Snowflake worksheet, execute:
snowflake/sql/01_setup_database.sql

# Step 2: Run trial account functions
snowflake/sql/02_trial_backend.sql

# Step 3: Load demo data
python snowflake/python/setup_snowflake.py
```

---

## 9. Key Features & Screenshots

### 9.1 RAG Chat Interface

Natural language Q&A powered by retrieved SEC filing content.

**Example queries that work:**
- "Compare revenue growth between Apple and Microsoft"
- "What are NVIDIA's main risk factors?"
- "How does Amazon's free cash flow compare to Alphabet?"
- "What AI-related investments are mentioned across all filings?"

**Response types:**
- **Financial comparisons** with exact figures from XBRL data
- **Risk factor analysis** extracted from filing text
- **Document summaries** with source citations
- **AI-generated insights** (when Claude API key is configured)

### 9.2 Financial Dashboard

Interactive charts showing:
- Revenue trends by quarter/year
- Profitability metrics (Revenue, Net Income, Operating Income)
- Key financial ratios
- Latest financial data tables

### 9.3 Document Viewer

Browse and search individual SEC filings:
- Filter by company (dropdown selector)
- Click to view full filing text
- Search within document for keywords
- View document metadata (size, word count, date)

---

## 10. Future Enhancements

### Short Term
- [ ] Add more companies (META, JPM, JNJ, etc.)
- [ ] Implement Snowflake Cortex Search for semantic similarity
- [ ] Add caching layer for frequent queries
- [ ] Export responses as PDF reports

### Medium Term
- [ ] Real-time SEC filing ingestion pipeline
- [ ] Vector embeddings using Snowflake Cortex EMBED_TEXT
- [ ] Multi-modal support (tables, charts from filings)
- [ ] User authentication and query history

### Long Term
- [ ] Custom fine-tuned financial LLM
- [ ] Predictive analytics (trend forecasting)
- [ ] Multi-language support
- [ ] Integration with Bloomberg/Reuters APIs

---

## Appendix A: Project Metrics

| Metric | Value |
|--------|-------|
| Companies tracked | 6 (AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA) |
| SEC filings loaded | 21 |
| Text chunks indexed | 934 |
| Financial metrics | 600 records |
| Snowflake tables | 6 |
| Snowflake views | 4 |
| Code files | 15+ |
| GitHub commits | 20+ |

## Appendix B: Snowflake Object Inventory

### Warehouses
- `FINANCIAL_RAG_WH` (XSMALL) — General queries
- `FINANCIAL_RAG_COMPUTE_WH` (SMALL) — Compute-intensive tasks

### Databases
- `FINANCIAL_RAG` — Main application database

### Schemas
- `RAW_DATA` — Source filings and text chunks
- `PROCESSED_DATA` — Cleaned financial metrics
- `VECTOR_STORE` — Embeddings and search history
- `ANALYTICS` — Reporting views

### Tables
- `RAW_DATA.SEC_FILINGS` (21 rows)
- `RAW_DATA.TEXT_CHUNKS` (934 rows)
- `PROCESSED_DATA.FINANCIAL_METRICS` (600 rows)
- `PROCESSED_DATA.COMPANY_INFO` (6 rows)
- `VECTOR_STORE.DOCUMENT_EMBEDDINGS`
- `VECTOR_STORE.SEARCH_HISTORY`

### Views
- `ANALYTICS.VW_REVENUE_SUMMARY`
- `ANALYTICS.VW_LATEST_METRICS`
- `ANALYTICS.VW_FILING_OVERVIEW`
- `ANALYTICS.VW_METRICS_COMPARISON`

### Functions
- `KEYWORD_SEARCH()` — Text chunk search
- `GET_COMPANY_METRICS()` — Financial metrics aggregation

### Procedures
- `LOG_SEARCH()` — Search analytics logging

---

*Built with ❄️ Snowflake, 🤖 Claude AI, and 📊 Streamlit by Innocent Mamvura*
