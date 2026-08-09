"""
Snowflake Connection Setup and Database Initialization
Author: Innocent Mamvura
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

def create_env_file():
    """Create .env file with Snowflake credentials."""
    env_content = """SNOWFLAKE_ACCOUNT=KFRSGXO-ME10745
SNOWFLAKE_USER=KFRSGXO-ME10745
SNOWFLAKE_PASSWORD=q~aVD!3UMQ4k"n8
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=FINANCIAL_RAG
SNOWFLAKE_SCHEMA=PUBLIC
APP_MODE=snowflake
"""
    env_path = PROJECT_ROOT / ".env"
    with open(env_path, 'w') as f:
        f.write(env_content)
    print(f"Created {env_path}")

def test_connection():
    """Test Snowflake connection."""
    try:
        import snowflake.connector
        from dotenv import load_dotenv
        
        load_dotenv(PROJECT_ROOT / ".env")
        
        conn = snowflake.connector.connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            role=os.getenv('SNOWFLAKE_ROLE'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE'),
            schema=os.getenv('SNOWFLAKE_SCHEMA')
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        version = cursor.fetchone()[0]
        print(f"✅ Connected to Snowflake! Version: {version}")
        
        cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE()")
        user, role, wh = cursor.fetchone()
        print(f"   User: {user}, Role: {role}, Warehouse: {wh}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    create_env_file()
    print("\nTesting Snowflake connection...")
    test_connection()
