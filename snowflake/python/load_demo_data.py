"""
Load Demo SEC Filing Data into Snowflake
Author: Innocent Mamvura

This script loads the local demo SEC filing data into Snowflake tables.
Run this AFTER executing snowflake/sql/01_setup_database.sql

Requirements:
    pip install snowflake-connector-python pandas

Usage:
    python snowflake/python/load_demo_data.py
"""

import os
import sys
import csv
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
sys.path.insert(0, str(PROJECT_ROOT))


def get_snowflake_connection():
    """Create Snowflake connection from .env credentials."""
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass
    
    try:
        import snowflake.connector
    except ImportError:
        print("❌ snowflake-connector-python not installed")
        print("   Run: pip install snowflake-connector-python")
        sys.exit(1)
    
    account = os.getenv('SNOWFLAKE_ACCOUNT')
    user = os.getenv('SNOWFLAKE_USER')
    password = os.getenv('SNOWFLAKE_PASSWORD')
    
    if not all([account, user, password]):
        print("❌ Missing Snowflake credentials in .env file")
        print("   Required: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD")
        sys.exit(1)
    
    conn = snowflake.connector.connect(
        account=account,
        user=user,
        password=password,
        role=os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'FINANCIAL_RAG_WH'),
        database=os.getenv('SNOWFLAKE_DATABASE', 'FINANCIAL_RAG'),
        schema='PUBLIC',
        login_timeout=15
    )
    return conn


def load_sec_filings(conn):
    """Load SEC filing metadata into RAW_DATA.SEC_FILINGS."""
    manifest_path = DATA_DIR / "filings" / "manifest.csv"
    if not manifest_path.exists():
        print(f"⚠️  Manifest not found: {manifest_path}")
        print("   Run data_collection.py first to download filings.")
        return 0
    
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM RAW_DATA.SEC_FILINGS")
    
    count = 0
    with open(manifest_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filing_id = f"{row['ticker']}_{row['form_type']}_{row['filing_date']}"
            
            cursor.execute("""
                INSERT INTO RAW_DATA.SEC_FILINGS 
                (filing_id, ticker, form_type, filing_date, fiscal_year, fiscal_period, 
                 file_path, file_size_bytes, content_hash, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
            """, (
                filing_id,
                row['ticker'],
                row['form_type'],
                row['filing_date'],
                int(row.get('fiscal_year', 0)) or None,
                row.get('fiscal_period'),
                f"@{row['filename']}",
                int(row.get('size_bytes', 0)),
                row.get('content_hash', 'demo')
            ))
            count += 1
    
    conn.commit()
    cursor.close()
    print(f"✅ Loaded {count} filings into RAW_DATA.SEC_FILINGS")
    return count


def load_text_chunks(conn):
    """Chunk filings and load into RAW_DATA.TEXT_CHUNKS."""
    text_dir = DATA_DIR / "filings" / "text"
    manifest_path = DATA_DIR / "filings" / "manifest.csv"
    
    if not manifest_path.exists():
        return 0
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM RAW_DATA.TEXT_CHUNKS")
    
    count = 0
    with open(manifest_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row['ticker']
            form_type = row['form_type']
            filing_date = row['filing_date']
            filing_id = f"{ticker}_{form_type}_{filing_date}"
            
            txt_path = text_dir / row['filename']
            if not txt_path.exists():
                continue
            
            try:
                with open(txt_path, 'r', encoding='utf-8') as f_text:
                    text = f_text.read()
            except Exception as e:
                print(f"   ⚠️  Error reading {txt_path}: {e}")
                continue
            
            # Simple chunking
            chunks = chunk_text_simple(text, chunk_size=1000, chunk_overlap=100)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{filing_id}_chunk_{i}"
                
                cursor.execute("""
                    INSERT INTO RAW_DATA.TEXT_CHUNKS 
                    (chunk_id, filing_id, ticker, form_type, chunk_index, chunk_text, char_count, word_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    chunk_id,
                    filing_id,
                    ticker,
                    form_type,
                    i,
                    chunk['text'][:9999],  # Limit to VARCHAR(10000)
                    chunk['char_count'],
                    chunk['word_count']
                ))
                count += 1
            
            print(f"   {ticker} {form_type}: {len(chunks)} chunks")
    
    conn.commit()
    cursor.close()
    print(f"✅ Loaded {count} chunks into RAW_DATA.TEXT_CHUNKS")
    return count


def chunk_text_simple(text, chunk_size=1000, chunk_overlap=100):
    """Simple text chunking."""
    text = re.sub(r'\s+', ' ', text)
    
    if len(text) <= chunk_size:
        return [{'text': text, 'char_count': len(text), 'word_count': len(text.split())}]
    
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        if end < len(text):
            for sep in ['. ', ' ', '']:
                idx = text.rfind(sep, start + chunk_size - 200, end)
                if idx != -1:
                    end = idx + len(sep)
                    break
        
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                'text': chunk_text,
                'char_count': len(chunk_text),
                'word_count': len(chunk_text.split())
            })
        
        start = end - chunk_overlap
    
    return chunks


def load_financial_metrics(conn):
    """Load XBRL financial metrics into PROCESSED_DATA.FINANCIAL_METRICS."""
    import pandas as pd
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
    metrics = ['revenue', 'netincome', 'totalassets', 'operatingincome', 'freecashflow']
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM PROCESSED_DATA.FINANCIAL_METRICS")
    
    metric_labels = {
        'revenue': 'Revenue',
        'netincome': 'Net Income',
        'totalassets': 'Total Assets',
        'operatingincome': 'Operating Income',
        'freecashflow': 'Free Cash Flow'
    }
    
    count = 0
    for ticker in tickers:
        for metric in metrics:
            csv_path = DATA_DIR / "filings" / f"{ticker}_xbrl_{metric}.csv"
            if not csv_path.exists():
                continue
            
            try:
                df = pd.read_csv(csv_path)
                if df.empty:
                    continue
                
                for _, row in df.iterrows():
                    metric_id = f"{ticker}_{metric}_{row.get('fiscal_year', '0')}_{row.get('fiscal_period', 'FY')}"
                    value = row.get('numeric_value')
                    
                    try:
                        value = float(value) if pd.notna(value) else None
                    except (ValueError, TypeError):
                        value = None
                    
                    cursor.execute("""
                        INSERT INTO PROCESSED_DATA.FINANCIAL_METRICS 
                        (metric_id, ticker, concept, metric_name, value, unit, 
                         period_start, period_end, fiscal_year, fiscal_period, 
                         statement_type, form_type, filing_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        metric_id,
                        ticker,
                        row.get('concept', metric),
                        metric_labels.get(metric, metric),
                        value,
                        row.get('unit', 'USD'),
                        row.get('period_start'),
                        row.get('period_end'),
                        int(row.get('fiscal_year', 0)) if pd.notna(row.get('fiscal_year')) else None,
                        row.get('fiscal_period', 'FY'),
                        row.get('statement_type', 'Income Statement'),
                        row.get('form_type', '10-K'),
                        row.get('filing_date')
                    ))
                    count += 1
                
                print(f"   {ticker} {metric}: {len(df)} records")
            except Exception as e:
                print(f"   ⚠️  Error loading {csv_path}: {e}")
    
    conn.commit()
    cursor.close()
    print(f"✅ Loaded {count} financial metrics into PROCESSED_DATA.FINANCIAL_METRICS")
    return count


def load_company_info(conn):
    """Load company info dimension into PROCESSED_DATA.COMPANY_INFO."""
    companies = [
        ('AAPL', '0000320193', 'Apple Inc.', 'NASDAQ', 'Technology', 'Consumer Electronics'),
        ('MSFT', '0000789019', 'Microsoft Corporation', 'NASDAQ', 'Technology', 'Software'),
        ('GOOGL', '0001652044', 'Alphabet Inc.', 'NASDAQ', 'Technology', 'Internet Services'),
        ('AMZN', '0001018724', 'Amazon.com Inc.', 'NASDAQ', 'Consumer Discretionary', 'E-Commerce'),
        ('NVDA', '0001013480', 'NVIDIA Corporation', 'NASDAQ', 'Technology', 'Semiconductors'),
        ('TSLA', '0001318605', 'Tesla Inc.', 'NASDAQ', 'Consumer Discretionary', 'Automotive'),
    ]
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM PROCESSED_DATA.COMPANY_INFO")
    
    for ticker, cik, name, exchange, sector, industry in companies:
        cursor.execute("""
            INSERT INTO PROCESSED_DATA.COMPANY_INFO 
            (ticker, cik, company_name, exchange, sector, industry)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ticker, cik, name, exchange, sector, industry))
    
    conn.commit()
    cursor.close()
    print(f"✅ Loaded {len(companies)} companies into PROCESSED_DATA.COMPANY_INFO")


def verify_data(conn):
    """Verify data was loaded correctly."""
    cursor = conn.cursor()
    
    tables = [
        ('RAW_DATA.SEC_FILINGS', 'filing_id'),
        ('RAW_DATA.TEXT_CHUNKS', 'chunk_id'),
        ('PROCESSED_DATA.FINANCIAL_METRICS', 'metric_id'),
        ('PROCESSED_DATA.COMPANY_INFO', 'ticker'),
    ]
    
    print("\n📊 Data Verification:")
    print("=" * 50)
    
    for table, pk in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        status = "✅" if count > 0 else "⚠️"
        print(f"   {status} {table}: {count} rows")
    
    cursor.close()


if __name__ == "__main__":
    print("Loading Demo Data into Snowflake")
    print("=" * 50)
    
    try:
        conn = get_snowflake_connection()
        print("✅ Connected to Snowflake\n")
        
        # Load data
        load_sec_filings(conn)
        print()
        load_text_chunks(conn)
        print()
        load_financial_metrics(conn)
        print()
        load_company_info(conn)
        
        # Verify
        verify_data(conn)
        
        conn.close()
        print("\n🎉 Data loading complete!")
        print("\nNext steps:")
        print("   1. Set APP_MODE=snowflake in your .env")
        print("   2. Run: streamlit run app/main.py")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
