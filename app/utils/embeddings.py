"""Embedding and RAG Utilities."""

import os
import re
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional


def search_documents(
    query: str,
    embeddings: Optional[dict],
    filings: List[dict],
    top_k: int = 5
) -> List[dict]:
    """Search for relevant documents using embeddings or keyword matching.
    
    Args:
        query: User query string
        embeddings: Pre-computed embeddings dict (or None)
        filings: List of filing metadata
        top_k: Number of results to return
    
    Returns:
        List of relevant document dicts with content snippets
    """
    if embeddings and 'vectors' in embeddings and 'chunks' in embeddings:
        return semantic_search(query, embeddings, top_k)
    else:
        return keyword_search(query, filings, top_k)


def semantic_search(query: str, embeddings: dict, top_k: int) -> List[dict]:
    """Perform semantic search using pre-computed embeddings."""
    try:
        from sentence_transformers import SentenceTransformer
        import faiss
        
        # Load model (cached)
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Encode query
        query_vec = model.encode([query])
        
        # Search FAISS index
        index = embeddings.get('index')
        chunks = embeddings.get('chunks', [])
        
        if index is None or not chunks:
            return []
        
        distances, indices = index.search(query_vec.astype('float32'), top_k)
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(chunks):
                chunk = chunks[idx]
                results.append({
                    'ticker': chunk.get('ticker', ''),
                    'form_type': chunk.get('form_type', ''),
                    'filing_date': chunk.get('filing_date', ''),
                    'content': chunk.get('text', '')[:500] + "...",
                    'score': float(distance),
                    'source': f"{chunk.get('ticker', '')} {chunk.get('form_type', '')} ({chunk.get('filing_date', '')})"
                })
        
        return results
    except Exception as e:
        print(f"Semantic search error: {e}")
        return []


def keyword_search(query: str, filings: List[dict], top_k: int) -> List[dict]:
    """Fallback keyword-based search."""
    query_terms = query.lower().split()
    results = []
    
    for filing in filings:
        if not filing.get('filepath'):
            continue
        
        try:
            with open(filing['filepath'], 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            continue
        
        # Simple scoring: count query term occurrences
        score = sum(content.lower().count(term) for term in query_terms)
        
        if score > 0:
            # Extract snippet around first match
            snippet = extract_snippet(content, query_terms[0])
            
            results.append({
                'ticker': filing['ticker'],
                'form_type': filing['form_type'],
                'filing_date': filing['filing_date'],
                'content': snippet,
                'score': score,
                'source': f"{filing['ticker']} {filing['form_type']} ({filing['filing_date']})"
            })
    
    # Sort by score and return top_k
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]


def extract_snippet(content: str, keyword: str, context: int = 200) -> str:
    """Extract a text snippet around a keyword match."""
    idx = content.lower().find(keyword)
    if idx == -1:
        return content[:400] + "..."
    
    start = max(0, idx - context)
    end = min(len(content), idx + len(keyword) + context)
    snippet = content[start:end]
    
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."
    
    return snippet


def generate_response(
    query: str,
    relevant_docs: List[dict],
    xbrl_data: Dict[str, dict]
) -> Tuple[str, List[str]]:
    """Generate a response based on retrieved documents.
    
    In demo mode, this uses a rule-based approach.
    In Snowflake mode, this would call Cortex COMPLETE.
    """
    sources = [doc['source'] for doc in relevant_docs]
    
    # Build context from retrieved documents
    context = "\n\n".join([
        f"Source: {doc['source']}\n{doc['content']}"
        for doc in relevant_docs[:3]
    ])
    
    # Check if query is about specific companies
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
    mentioned_tickers = [t for t in tickers if t.lower() in query.lower()]
    
    # Build response based on query type
    response = build_rule_based_response(query, relevant_docs, xbrl_data, mentioned_tickers)
    
    return response, sources


def build_rule_based_response(
    query: str,
    docs: List[dict],
    xbrl_data: Dict[str, dict],
    tickers: List[str]
) -> str:
    """Build a rule-based response for demo mode."""
    
    query_lower = query.lower()
    
    # Revenue comparison
    if 'revenue' in query_lower and len(tickers) >= 2:
        return build_comparison_response(tickers, xbrl_data, 'revenue', 'Revenue')
    
    # Net income comparison
    if 'net income' in query_lower and len(tickers) >= 2:
        return build_comparison_response(tickers, xbrl_data, 'netincome', 'Net Income')
    
    # Risk factors
    if 'risk' in query_lower or 'risk factor' in query_lower:
        return build_risk_response(docs)
    
    # AI-related
    if 'ai' in query_lower or 'artificial intelligence' in query_lower:
        return build_ai_response(docs)
    
    # Default: summarize retrieved docs
    return build_summary_response(docs)


def build_comparison_response(
    tickers: List[str],
    xbrl_data: Dict[str, dict],
    metric_key: str,
    metric_name: str
) -> str:
    """Build a comparison response for financial metrics."""
    lines = [f"## {metric_name} Comparison\n"]
    
    for ticker in tickers:
        if ticker in xbrl_data and metric_key in xbrl_data[ticker]:
            df = xbrl_data[ticker][metric_key]
            if df is not None and not df.empty:
                latest = df.sort_values('period_end', ascending=False).iloc[0]
                value = latest['numeric_value']
                period = f"{latest['fiscal_year']} {latest['fiscal_period']}"
                
                if value >= 1e12:
                    formatted = f"${value/1e12:.2f}T"
                elif value >= 1e9:
                    formatted = f"${value/1e9:.2f}B"
                elif value >= 1e6:
                    formatted = f"${value/1e6:.2f}M"
                else:
                    formatted = f"${value:,.0f}"
                
                lines.append(f"**{ticker}:** {formatted} ({period})")
    
    lines.append("\n*Data sourced from SEC EDGAR XBRL filings.*")
    return "\n".join(lines)


def build_risk_response(docs: List[dict]) -> str:
    """Build a response about risk factors."""
    lines = ["## Risk Factors Mentioned\n"]
    
    # Extract risk-related sentences from docs
    risk_keywords = ['risk', 'uncertainty', 'competition', 'regulation', 'litigation', 'cybersecurity']
    
    for doc in docs:
        content = doc.get('content', '')
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        risk_sentences = [
            s for s in sentences
            if any(kw in s.lower() for kw in risk_keywords)
            and len(s) > 50
        ]
        
        if risk_sentences:
            lines.append(f"### {doc['source']}")
            for sent in risk_sentences[:3]:
                lines.append(f"- {sent}")
            lines.append("")
    
    lines.append("*Note: This is a demo response. In production, Snowflake Cortex would provide comprehensive analysis.*")
    return "\n".join(lines)


def build_ai_response(docs: List[dict]) -> str:
    """Build a response about AI-related content."""
    lines = ["## AI & Technology Mentions\n"]
    
    ai_keywords = ['artificial intelligence', 'machine learning', 'generative ai', 'llm', 'neural network']
    
    for doc in docs:
        content = doc.get('content', '').lower()
        
        mentions = [kw for kw in ai_keywords if kw in content]
        if mentions:
            lines.append(f"**{doc['source']}** mentions: {', '.join(mentions)}")
    
    lines.append("\n*For detailed AI strategy analysis, switch to Snowflake mode with Cortex AI.*")
    return "\n".join(lines)


def build_summary_response(docs: List[dict]) -> str:
    """Build a generic summary response."""
    lines = ["## Document Analysis\n"]
    lines.append("Based on the retrieved financial documents:\n")
    
    for doc in docs[:3]:
        lines.append(f"### {doc['source']}")
        lines.append(f"{doc['content'][:300]}...")
        lines.append("")
    
    lines.append("---")
    lines.append("*This is a demo response using local data. Connect to Snowflake for AI-powered analysis with Cortex COMPLETE.*")
    return "\n".join(lines)
