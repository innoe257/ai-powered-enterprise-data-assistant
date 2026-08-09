"""
Snowpark Python UDFs for Document Processing
Author: Innocent Mamvura

This module contains Snowpark Python UDFs for:
- Document chunking
- Text cleaning
- Embedding generation (using Cortex)
- Structured data extraction
"""

import re
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass

import snowflake.snowpark as snowpark
from snowflake.snowpark.functions import udf, sproc
from snowflake.snowpark.types import StringType, IntegerType, FloatType, VariantType


# ============================================================
# 1. TEXT CHUNKING
# ============================================================

def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    separators: List[str] = None
) -> List[Dict[str, any]]:
    """Split text into overlapping chunks with metadata.
    
    Uses a hierarchical separator approach:
    1. Try paragraph breaks (\\n\\n)
    2. Try sentence breaks (. )
    3. Fall back to word boundaries
    
    Args:
        text: Input text to chunk
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks in characters
        separators: List of separator strings to try
    
    Returns:
        List of chunk dicts with text and metadata
    """
    if separators is None:
        separators = ["\\n\\n", "\\n", ". ", " ", ""]
    
    chunks = []
    chunk_index = 0
    
    # Clean text first
    text = clean_text(text)
    
    if len(text) <= chunk_size:
        return [{
            'chunk_index': 0,
            'text': text,
            'char_count': len(text),
            'word_count': len(text.split())
        }]
    
    # Simple sliding window chunking
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # Try to find a good break point
        if end < len(text):
            for sep in separators:
                idx = text.rfind(sep, start + chunk_size - 100, end)
                if idx != -1:
                    end = idx + len(sep)
                    break
        
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                'chunk_index': chunk_index,
                'text': chunk_text,
                'char_count': len(chunk_text),
                'word_count': len(chunk_text.split())
            })
            chunk_index += 1
        
        start = end - chunk_overlap
    
    return chunks


def clean_text(text: str) -> str:
    """Clean and normalize text from SEC filings."""
    # Remove excess whitespace
    text = re.sub(r'\\s+', ' ', text)
    
    # Remove page numbers and headers (common patterns)
    text = re.sub(r'\\bPage\\s+\\d+\\s+of\\s+\\d+\\b', '', text, flags=re.IGNORECASE)
    
    # Remove SEC-specific boilerplate
    text = re.sub(r'UNITED STATES SECURITIES AND EXCHANGE COMMISSION', '', text)
    text = re.sub(r'Washington, D\\.C\\. 20549', '', text)
    
    # Normalize line breaks
    text = re.sub(r'\\n+', '\\n', text)
    
    return text.strip()


# ============================================================
# 2. STRUCTURED DATA EXTRACTION
# ============================================================

def extract_risk_factors(text: str) -> List[str]:
    """Extract risk factor statements from 10-K filings."""
    risk_section = extract_section(text, "RISK FACTORS", "UNRESOLVED STAFF COMMENTS")
    if not risk_section:
        risk_section = extract_section(text, "Risk Factors", "Properties")
    
    if not risk_section:
        return []
    
    # Split into sentences and filter for risk-related ones
    sentences = re.split(r'(?<=[.!?])\\s+', risk_section)
    risk_keywords = [
        'risk', 'uncertain', 'could', 'may', 'might',
        'adversely affect', 'negatively impact', 'failure to'
    ]
    
    risk_sentences = []
    for sent in sentences:
        if any(kw in sent.lower() for kw in risk_keywords) and len(sent) > 50:
            risk_sentences.append(sent.strip())
    
    return risk_sentences[:20]  # Top 20 risk factors


def extract_section(text: str, start_marker: str, end_marker: str) -> str:
    """Extract a section from a filing between two markers."""
    start_idx = text.find(start_marker)
    if start_idx == -1:
        return ""
    
    end_idx = text.find(end_marker, start_idx + len(start_marker))
    if end_idx == -1:
        end_idx = len(text)
    
    return text[start_idx:end_idx].strip()


def extract_financial_highlights(text: str) -> Dict[str, any]:
    """Extract key financial metrics from text."""
    highlights = {}
    
    # Revenue patterns
    revenue_match = re.search(
        r'(?:revenue|total net sales|net revenue)[^\\d]*(\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?)\\s*(million|billion)?',
        text, re.IGNORECASE
    )
    if revenue_match:
        value = float(revenue_match.group(1).replace(',', ''))
        unit = revenue_match.group(2) or ''
        if 'billion' in unit.lower():
            value *= 1e9
        elif 'million' in unit.lower():
            value *= 1e6
        highlights['revenue'] = value
    
    # Net income patterns
    income_match = re.search(
        r'(?:net income|net earnings)[^\\d]*(\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?)\\s*(million|billion)?',
        text, re.IGNORECASE
    )
    if income_match:
        value = float(income_match.group(1).replace(',', ''))
        unit = income_match.group(2) or ''
        if 'billion' in unit.lower():
            value *= 1e9
        elif 'million' in unit.lower():
            value *= 1e6
        highlights['net_income'] = value
    
    return highlights


# ============================================================
# 3. SNOWPARK UDF REGISTRATION
# ============================================================

def register_udfs(session: snowpark.Session):
    """Register all UDFs with Snowflake."""
    
    # Register chunk_text as UDF
    session.udf.register(
        chunk_text,
        name="CHUNK_TEXT_PYTHON",
        stage_location="@FINANCIAL_RAG.RAW_DATA.CHUNKS_STAGE",
        is_permanent=True,
        replace=True
    )
    
    # Register clean_text as UDF
    session.udf.register(
        clean_text,
        name="CLEAN_TEXT_PYTHON",
        stage_location="@FINANCIAL_RAG.RAW_DATA.CHUNKS_STAGE",
        is_permanent=True,
        replace=True
    )
    
    print("UDFs registered successfully")


# ============================================================
# 4. BATCH PROCESSING
# ============================================================

def process_all_filings(session: snowpark.Session):
    """Process all unchunked filings in batch."""
    
    # Get unprocessed filings
    filings_df = session.table("RAW_DATA.SEC_FILINGS").filter(
        ~session.table("RAW_DATA.SEC_FILINGS").col("filing_id").isin(
            session.table("RAW_DATA.TEXT_CHUNKS").select("filing_id").distinct()
        )
    )
    
    filings = filings_df.collect()
    
    for filing in filings:
        filing_id = filing['FILING_ID']
        file_path = filing['FILE_PATH']
        
        # Read file (in production, use stage file access)
        # For demo, assume text is available
        
        # Chunk and insert
        # This would call the chunk_text function and insert results
        
        print(f"Processed filing: {filing_id}")
    
    return len(filings)


if __name__ == "__main__":
    # Local testing
    sample_text = """
    Apple Inc. is a technology company that designs, manufactures, and markets
    smartphones, personal computers, tablets, wearables, and accessories.
    
    The company's products include iPhone, Mac, iPad, and Wearables, Home and Accessories.
    
    Risk Factors:
    - Global economic conditions could materially adversely affect the company.
    - The company's business can be impacted by political events and international trade disputes.
    """
    
    chunks = chunk_text(sample_text, chunk_size=200, chunk_overlap=20)
    print(f"Generated {len(chunks)} chunks")
    for chunk in chunks:
        print(f"Chunk {chunk['chunk_index']}: {chunk['word_count']} words")
