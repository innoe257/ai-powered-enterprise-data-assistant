"""Data Loading Utilities."""

import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def load_demo_data() -> Tuple[List[dict], Optional[dict], Dict[str, dict]]:
    """Load demo data from local files.
    
    Returns:
        filings: List of filing metadata + content paths
        embeddings: Pre-computed embeddings (or None if not generated)
        xbrl_data: Dict mapping ticker -> metric -> DataFrame
    """
    filings = load_filing_metadata()
    embeddings = load_embeddings()
    xbrl_data = load_xbrl_data()
    return filings, embeddings, xbrl_data


def load_snowflake_data() -> Tuple[List[dict], Optional[dict], Dict[str, dict]]:
    """Load data from Snowflake backend.
    
    TODO: Implement Snowflake connector queries
    """
    # For now, fall back to demo mode
    st = __import__('streamlit')
    st.warning("Snowflake mode not yet implemented. Using demo data.")
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
                    # Clean numeric values
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
