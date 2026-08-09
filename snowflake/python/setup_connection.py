"""
Snowflake Connection Setup and Database Initialization
Author: Innocent Mamvura

This script tests the Snowflake connection using credentials from .env file.
Run this after creating your .env file with your Snowflake credentials.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def test_connection():
    """Test Snowflake connection using environment variables."""
    try:
        import snowflake.connector
        from dotenv import load_dotenv
        
        # Load from .env file
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            print(f"⚠️  .env file not found at {env_path}")
            print("   Copy .env.example to .env and fill in your credentials.")
            return False
        
        account = os.getenv('SNOWFLAKE_ACCOUNT')
        user = os.getenv('SNOWFLAKE_USER')
        password = os.getenv('SNOWFLAKE_PASSWORD')
        
        if not all([account, user, password]):
            print("❌ Missing Snowflake credentials in .env file")
            print("   Required: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD")
            return False
        
        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            role=os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'FINANCIAL_RAG_WH'),
            database=os.getenv('SNOWFLAKE_DATABASE', 'FINANCIAL_RAG'),
            schema=os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
            login_timeout=15
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        version = cursor.fetchone()[0]
        print(f"✅ Connected to Snowflake! Version: {version}")
        
        cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE()")
        user, role, wh, db = cursor.fetchone()
        print(f"   User: {user}")
        print(f"   Role: {role}")
        print(f"   Warehouse: {wh}")
        print(f"   Database: {db}")
        
        # Check if FINANCIAL_RAG database exists
        cursor.execute("SHOW DATABASES LIKE 'FINANCIAL_RAG'")
        if cursor.fetchone():
            print(f"   ✅ FINANCIAL_RAG database found")
        else:
            print(f"   ⚠️  FINANCIAL_RAG database not found. Run snowflake/sql/01_setup_database.sql first.")
        
        cursor.close()
        conn.close()
        return True
        
    except ImportError:
        print("❌ snowflake-connector-python not installed")
        print("   Run: pip install snowflake-connector-python")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing Snowflake connection...")
    print("=" * 50)
    success = test_connection()
    sys.exit(0 if success else 1)
