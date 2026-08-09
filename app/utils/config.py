"""Application Configuration Utilities."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AppConfig:
    """Application configuration."""
    
    # Mode
    mode: str = "demo"  # 'demo' or 'snowflake'
    
    # Snowflake (only used in snowflake mode)
    snowflake_account: Optional[str] = None
    snowflake_user: Optional[str] = None
    snowflake_password: Optional[str] = None
    snowflake_role: str = "ACCOUNTADMIN"
    snowflake_warehouse: str = "COMPUTE_WH"
    snowflake_database: str = "FINANCIAL_RAG"
    snowflake_schema: str = "PUBLIC"
    
    # App
    debug: bool = False
    max_results: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 50


def get_config() -> AppConfig:
    """Load configuration from environment variables."""
    return AppConfig(
        mode=os.getenv('APP_MODE', 'demo'),
        snowflake_account=os.getenv('SNOWFLAKE_ACCOUNT'),
        snowflake_user=os.getenv('SNOWFLAKE_USER'),
        snowflake_password=os.getenv('SNOWFLAKE_PASSWORD'),
        snowflake_role=os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
        snowflake_warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
        snowflake_database=os.getenv('SNOWFLAKE_DATABASE', 'FINANCIAL_RAG'),
        snowflake_schema=os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
        debug=os.getenv('DEBUG', 'false').lower() == 'true',
        max_results=int(os.getenv('MAX_RESULTS', '5')),
    )
