"""Data Loading Utilities - Updated for Snowflake Backend."""

import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def load_demo_data() -> Tuple[List[dict], Optional[dict], Dict[str, dict]]:
    """Load demo data from local files."""
    filings = load_filing_metadata()
    embeddings = load_embeddings()
    xbrl_data = load_xbrl_data()
    return filings, embeddings, xbrl_data


def load_snowflake_data() -> Tuple[List[dict], Optional[dict], Dict[str, dict]]:
    """Load data from Snowflake backend."""
    try:
        import snowflake.connector
        
        conn = snowflake.connector.connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            role=os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'FINANCIAL_RAG_WH'),
            database=os.getenv('SNOWFLAKE_DATABASE', 'FINANCIAL_RAG'),
            schema=os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
            login_timeout=15
        )
        
        # Load filings from Snowflake
        filings_df = pd.read_sql("SELECT * FROM RAW_DATA.SEC_FILINGS", conn)
        filings = filings_df.to_dict('records')
        
        # Load metrics from Snowflake
        metrics_df = pd.read_sql("SELECT * FROM PROCESSED_DATA.FINANCIAL_METRICS", conn)
        
        # Organize metrics by ticker
        xbrl_data = {}
        tickers = metrics_df['TICKER'].unique() if 'TICKER' in metrics_df.columns else []
        for ticker in tickers:
            ticker_df = metrics_df[metrics_df['TICKER'] == ticker]
            ticker_metrics = {}
            for metric_name in ticker_df['METRIC_NAME'].unique():
                metric_df = ticker_df[ticker_df['METRIC_NAME'] == metric_name].copy()
                metric_df.columns = [c.lower() for c in metric_df.columns]
                ticker_metrics[metric_name] = metric_df
            xbrl_data[ticker] = ticker_metrics
        
        conn.close()
        
        embeddings = load_embeddings()
        return filings, embeddings, xbrl_data
        
    except Exception as e:
        st = __import__('streamlit')
        st.warning(f"Snowflake connection failed: {e}. Using demo data.")
        return load_demo_data()


def load_filing_metadata() -> List[dict]:
    """Load filing metadata from manifest."""
    manifest_path = DATA_DIR / "filings" / "manifest.csv"
    text_dir = DATA_DIR / "filings" / "text"
    
    if not manifest_path.exists():
        return []
    
    df = pd.read_csv(manifest_path)
    filings = []
    
    for _, row in df.iterrows():
        txt_path = text_dir / row['filename']
        html_path = text_dir / row['html_filename']
        
        filings.append({
            'ticker': row['ticker'],
            'form_type': row['form_type'],
            'filing_date': row['filing_date'],
            'filename': row['filename'],
            'html_filename': row['html_filename'],
            'filepath': str(txt_path) if txt_path.exists() else None,
            'html_path': str(html_path) if html_path.exists() else None,
            'size_bytes': row['size_bytes'],
            'word_count': row['word_count'],
        })
    
    return filings


def load_embeddings() -> Optional[dict]:
    """Load pre-computed embeddings if available."""
    embeddings_path = DATA_DIR / "embeddings" / "document_embeddings.pkl"
    
    if embeddings_path.exists():
        import pickle
        with open(embeddings_path, 'rb') as f:
            return pickle.load(f)
    
    return None


def load_xbrl_data() -> Dict[str, dict]:
    """Load XBRL financial data for all tickers."""
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
    metrics = ['revenue', 'netincome', 'totalassets', 'operatingincome', 'freecashflow']
    
    xbrl_data = {}
    
    for ticker in tickers:
        ticker_metrics = {}
        for metric in metrics:
            csv_path = DATA_DIR / "filings" / f"{ticker}_xbrl_{metric}.csv"
            if csv_path.exists():
                try:
                    df = pd.read_csv(csv_path)
                    if 'numeric_value' in df.columns:
                        df['numeric_value'] = pd.to_numeric(df['numeric_value'], errors='coerce')
                    ticker_metrics[metric] = df
                except Exception as e:
                    print(f"Error loading {csv_path}: {e}")
                    ticker_metrics[metric] = None
            else:
                ticker_metrics[metric] = None
        
        xbrl_data[ticker] = ticker_metrics
    
    return xbrl_data


def get_ticker_filings(ticker: str, filings: List[dict]) -> List[dict]:
    """Get filings for a specific ticker."""
    return [f for f in filings if f['ticker'] == ticker]
