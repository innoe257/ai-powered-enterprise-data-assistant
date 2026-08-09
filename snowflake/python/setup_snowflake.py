#!/usr/bin/env python3
"""
Snowflake Setup Script - Complete Backend Setup
Runs SQL setup scripts and loads demo data.
"""
import sys
from pathlib import Path
import snowflake.connector

PROJECT_ROOT = Path(__file__).parent.parent.parent
SQL_DIR = PROJECT_ROOT / "snowflake" / "sql"
DATA_DIR = PROJECT_ROOT / "data"

# Credentials
ACCOUNT = "KFRSGXO-ME10745"
USER = "INNOCENT"
PASSWORD = 'q~aVD!3UMQ4k"n8'
ROLE = "ACCOUNTADMIN"

def get_connection():
    """Connect to Snowflake."""
    print(f"Connecting to Snowflake account: {ACCOUNT}...")
    conn = snowflake.connector.connect(
        account=ACCOUNT,
        user=USER,
        password=PASSWORD,
        role=ROLE,
        login_timeout=20
    )
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_VERSION()")
    version = cursor.fetchone()[0]
    print(f"✅ Connected! Snowflake version: {version}")
    cursor.close()
    return conn

def run_sql_file(conn, filepath):
    """Execute SQL statements from a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Split by semicolons, but be careful with statements inside $$ blocks
    statements = []
    current = ""
    in_dollar_block = False
    
    for line in content.split('\n'):
        stripped = line.strip()
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('--'):
            continue
        
        current += line + '\n'
        
        # Track $$ blocks (Snowflake stored procedures/functions)
        if '$$' in line:
            in_dollar_block = not in_dollar_block
        
        # End of statement (semicolon not inside $$ block)
        if stripped.endswith(';') and not in_dollar_block:
            statements.append(current.strip())
            current = ""
    
    cursor = conn.cursor()
    success = 0
    failed = 0
    
    for stmt in statements:
        if not stmt.strip():
            continue
        try:
            cursor.execute(stmt)
            success += 1
        except Exception as e:
            # Some statements may fail if objects already exist, etc.
            # Only print actual errors for critical statements
            err_str = str(e).lower()
            if 'already exists' in err_str or 'does not exist' in err_str:
                success += 1  # Expected, not a real failure
            else:
                print(f"   ⚠️  SQL warning: {e}")
                failed += 1
    
    cursor.close()
    print(f"   ✅ {success} statements executed, {failed} warnings")
    return success, failed

def setup_database(conn):
    """Run 01_setup_database.sql"""
    print("\n📦 Running 01_setup_database.sql...")
    return run_sql_file(conn, SQL_DIR / "01_setup_database.sql")

def setup_trial_backend(conn):
    """Run 02_trial_backend.sql"""
    print("\n⚙️  Running 02_trial_backend.sql...")
    return run_sql_file(conn, SQL_DIR / "02_trial_backend.sql")

def load_sec_filings(conn):
    """Load SEC filing metadata."""
    import csv
    manifest_path = DATA_DIR / "filings" / "manifest.csv"
    if not manifest_path.exists():
        print(f"⚠️  Manifest not found: {manifest_path}")
        return 0
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM FINANCIAL_RAG.RAW_DATA.SEC_FILINGS")
    
    count = 0
    with open(manifest_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filing_id = f"{row['ticker']}_{row['form_type']}_{row['filing_date']}"
            cursor.execute("""
                INSERT INTO FINANCIAL_RAG.RAW_DATA.SEC_FILINGS 
                (filing_id, ticker, form_type, filing_date, fiscal_year, fiscal_period, 
                 file_path, file_size_bytes, content_hash, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
            """, (
                filing_id, row['ticker'], row['form_type'], row['filing_date'],
                int(row.get('fiscal_year', 0)) or None, row.get('fiscal_period'),
                f"@{row['filename']}", int(row.get('size_bytes', 0)),
                row.get('content_hash', 'demo')
            ))
            count += 1
    
    conn.commit()
    cursor.close()
    print(f"✅ Loaded {count} filings into RAW_DATA.SEC_FILINGS")
    return count

def load_text_chunks(conn):
    """Chunk and load text data."""
    import csv, re
    text_dir = DATA_DIR / "filings" / "text"
    manifest_path = DATA_DIR / "filings" / "manifest.csv"
    
    if not manifest_path.exists():
        return 0
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM FINANCIAL_RAG.RAW_DATA.TEXT_CHUNKS")
    
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
            text = re.sub(r'\s+', ' ', text)
            chunk_size = 1000
            chunk_overlap = 100
            
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
                    chunks.append(chunk_text)
                start = end - chunk_overlap
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{filing_id}_chunk_{i}"
                cursor.execute("""
                    INSERT INTO FINANCIAL_RAG.RAW_DATA.TEXT_CHUNKS 
                    (chunk_id, filing_id, ticker, form_type, chunk_index, chunk_text, char_count, word_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    chunk_id, filing_id, ticker, form_type, i,
                    chunk[:9999], len(chunk), len(chunk.split())
                ))
                count += 1
            
            print(f"   {ticker} {form_type}: {len(chunks)} chunks")
    
    conn.commit()
    cursor.close()
    print(f"✅ Loaded {count} chunks into RAW_DATA.TEXT_CHUNKS")
    return count

def load_financial_metrics(conn):
    """Load XBRL financial metrics."""
    import pandas as pd
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
    metrics = ['revenue', 'netincome', 'totalassets', 'operatingincome', 'freecashflow']
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM FINANCIAL_RAG.PROCESSED_DATA.FINANCIAL_METRICS")
    
    metric_labels = {
        'revenue': 'Revenue', 'netincome': 'Net Income',
        'totalassets': 'Total Assets', 'operatingincome': 'Operating Income',
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
                        INSERT INTO FINANCIAL_RAG.PROCESSED_DATA.FINANCIAL_METRICS 
                        (metric_id, ticker, concept, metric_name, value, unit, 
                         period_start, period_end, fiscal_year, fiscal_period, 
                         statement_type, form_type, filing_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        metric_id, ticker, row.get('concept', metric),
                        metric_labels.get(metric, metric), value,
                        row.get('unit', 'USD'), row.get('period_start'),
                        row.get('period_end'),
                        int(row.get('fiscal_year', 0)) if pd.notna(row.get('fiscal_year')) else None,
                        row.get('fiscal_period', 'FY'), row.get('statement_type', 'Income Statement'),
                        row.get('form_type', '10-K'), row.get('filing_date')
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
    """Load company info dimension."""
    companies = [
        ('AAPL', '0000320193', 'Apple Inc.', 'NASDAQ', 'Technology', 'Consumer Electronics'),
        ('MSFT', '0000789019', 'Microsoft Corporation', 'NASDAQ', 'Technology', 'Software'),
        ('GOOGL', '0001652044', 'Alphabet Inc.', 'NASDAQ', 'Technology', 'Internet Services'),
        ('AMZN', '0001018724', 'Amazon.com Inc.', 'NASDAQ', 'Consumer Discretionary', 'E-Commerce'),
        ('NVDA', '0001013480', 'NVIDIA Corporation', 'NASDAQ', 'Technology', 'Semiconductors'),
        ('TSLA', '0001318605', 'Tesla Inc.', 'NASDAQ', 'Consumer Discretionary', 'Automotive'),
    ]
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM FINANCIAL_RAG.PROCESSED_DATA.COMPANY_INFO")
    
    for ticker, cik, name, exchange, sector, industry in companies:
        cursor.execute("""
            INSERT INTO FINANCIAL_RAG.PROCESSED_DATA.COMPANY_INFO 
            (ticker, cik, company_name, exchange, sector, industry)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ticker, cik, name, exchange, sector, industry))
    
    conn.commit()
    cursor.close()
    print(f"✅ Loaded {len(companies)} companies into PROCESSED_DATA.COMPANY_INFO")

def verify_data(conn):
    """Verify all data was loaded."""
    cursor = conn.cursor()
    tables = [
        ('FINANCIAL_RAG.RAW_DATA.SEC_FILINGS', 'filing_id'),
        ('FINANCIAL_RAG.RAW_DATA.TEXT_CHUNKS', 'chunk_id'),
        ('FINANCIAL_RAG.PROCESSED_DATA.FINANCIAL_METRICS', 'metric_id'),
        ('FINANCIAL_RAG.PROCESSED_DATA.COMPANY_INFO', 'ticker'),
    ]
    
    print("\n📊 Data Verification:")
    print("=" * 50)
    all_good = True
    for table, pk in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        status = "✅" if count > 0 else "⚠️"
        if count == 0:
            all_good = False
        print(f"   {status} {table}: {count} rows")
    
    cursor.close()
    return all_good

def main():
    print("=" * 60)
    print("Snowflake Backend Setup for AI-Powered Enterprise Data Assistant")
    print("=" * 60)
    
    try:
        conn = get_connection()
        
        # Step 1: Database setup
        setup_database(conn)
        
        # Step 2: Trial backend functions
        setup_trial_backend(conn)
        
        # Step 3: Load data
        print("\n📥 Loading demo data...")
        print("-" * 50)
        load_sec_filings(conn)
        load_text_chunks(conn)
        load_financial_metrics(conn)
        load_company_info(conn)
        
        # Step 4: Verify
        all_good = verify_data(conn)
        
        conn.close()
        
        print("\n" + "=" * 60)
        if all_good:
            print("🎉 Snowflake backend setup complete!")
            print("\nNext steps:")
            print("   1. Set APP_MODE=snowflake in your .env file")
            print("   2. Add your CLAUDE_API_KEY for AI-powered responses")
            print("   3. Run: streamlit run streamlit_app.py")
        else:
            print("⚠️  Some tables are empty. Check the output above.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
