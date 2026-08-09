"""Embedding and RAG Utilities - Streamlit Cloud Compatible."""

import os
import re
from typing import List, Dict, Tuple, Optional


# Company name → ticker mapping for natural language queries
COMPANY_TO_TICKER = {
    'apple': 'AAPL',
    'microsoft': 'MSFT',
    'google': 'GOOGL',
    'alphabet': 'GOOGL',
    'amazon': 'AMZN',
    'nvidia': 'NVDA',
    'tesla': 'TSLA',
}


def search_documents(
    query: str,
    embeddings: Optional[dict],
    filings: List[dict],
    top_k: int = 5
) -> List[dict]:
    """Search for relevant documents. Uses keyword search (works everywhere)."""
    return keyword_search(query, filings, top_k)


def keyword_search(query: str, filings: List[dict], top_k: int) -> List[dict]:
    """Keyword-based search - no heavy ML dependencies."""
    query_terms = [t for t in query.lower().split() if len(t) > 2]
    if not query_terms:
        query_terms = [query.lower()]

    results = []

    for filing in filings:
        # Try content field first (Snowflake mode), then local filepath
        content = None
        if filing.get('content'):
            content = filing['content']
        elif filing.get('filepath'):
            try:
                with open(filing['filepath'], 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
        
        if not content:
            continue

        # Score by term frequency
        score = sum(content.lower().count(term) for term in query_terms)

        if score > 0:
            snippet = extract_snippet(content, query_terms[0])
            results.append({
                'ticker': filing['ticker'],
                'form_type': filing['form_type'],
                'filing_date': filing['filing_date'],
                'content': snippet,
                'score': score,
                'source': f"{filing['ticker']} {filing['form_type']} ({filing['filing_date']})"
            })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]


def extract_snippet(content: str, keyword: str, context: int = 250) -> str:
    """Extract a text snippet around a keyword match."""
    idx = content.lower().find(keyword)
    if idx == -1:
        return content[:500] + "..."

    start = max(0, idx - context)
    end = min(len(content), idx + len(keyword) + context)
    snippet = content[start:end]

    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."

    return snippet


def extract_tickers_from_query(query: str) -> List[str]:
    """Extract tickers from query using both symbols and company names."""
    query_lower = query.lower()
    tickers = []
    
    # Check for ticker symbols
    all_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
    for t in all_tickers:
        if t.lower() in query_lower:
            tickers.append(t)
    
    # Check for company names
    for name, ticker in COMPANY_TO_TICKER.items():
        if name in query_lower and ticker not in tickers:
            tickers.append(ticker)
    
    return tickers


def generate_response(
    query: str,
    relevant_docs: List[dict],
    xbrl_data: Dict[str, dict]
) -> Tuple[str, List[str]]:
    """Generate a response using Claude API if available, else rule-based."""
    sources = [doc['source'] for doc in relevant_docs]

    # Try Claude API first
    api_key = os.getenv('CLAUDE_API_KEY')
    if api_key:
        try:
            return generate_claude_response(query, relevant_docs, xbrl_data, api_key), sources
        except Exception as e:
            print(f"Claude API error: {e}, falling back to rule-based")

    # Fallback to rule-based
    mentioned_tickers = extract_tickers_from_query(query)
    response = build_rule_based_response(query, relevant_docs, xbrl_data, mentioned_tickers)
    return response, sources


def generate_claude_response(
    query: str,
    relevant_docs: List[dict],
    xbrl_data: Dict[str, dict],
    api_key: str
) -> str:
    """Generate response using Claude API."""
    from anthropic import Anthropic

    # Build context from documents
    context_parts = []
    for doc in relevant_docs[:3]:
        context_parts.append(f"Document: {doc['source']}\n{doc['content'][:800]}")

    # Add XBRL data for mentioned tickers
    mentioned_tickers = extract_tickers_from_query(query)

    xbrl_context = ""
    for ticker in mentioned_tickers:
        if ticker in xbrl_data:
            xbrl_context += f"\n{ticker} Financial Data:\n"
            for metric_name, df in xbrl_data[ticker].items():
                if df is not None and not df.empty:
                    latest = df.sort_values('period_end', ascending=False).iloc[0]
                    value = latest['numeric_value']
                    if value is not None and not (hasattr(value, 'isna') and value.isna()):
                        xbrl_context += f"  - {metric_name}: ${value:,.0f} ({latest['fiscal_year']} {latest['fiscal_period']})\n"

    system_prompt = """You are a financial analyst AI assistant. Answer questions based on the provided SEC filing context. Be concise, factual, and cite specific data points when available. If the context doesn't contain the answer, say so clearly."""

    user_prompt = f"""Context from SEC filings:
{chr(10).join(context_parts)}

{xbrl_context}

Question: {query}

Please provide a clear, analytical answer based on the context above."""

    client = Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    return message.content[0].text


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

    # Total assets
    if 'asset' in query_lower and len(tickers) >= 2:
        return build_comparison_response(tickers, xbrl_data, 'totalassets', 'Total Assets')

    # Operating income
    if 'operating income' in query_lower and len(tickers) >= 2:
        return build_comparison_response(tickers, xbrl_data, 'operatingincome', 'Operating Income')

    # Free cash flow
    if 'free cash flow' in query_lower or 'fcf' in query_lower:
        return build_comparison_response(tickers, xbrl_data, 'freecashflow', 'Free Cash Flow')

    # Risk factors
    if 'risk' in query_lower:
        return build_risk_response(docs)

    # AI-related
    if 'ai' in query_lower or 'artificial intelligence' in query_lower or 'machine learning' in query_lower:
        return build_ai_response(docs)

    # Default: summarize retrieved docs or show metrics
    if len(tickers) == 1:
        return build_single_company_response(tickers[0], xbrl_data, docs)

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

                if value is None or (hasattr(value, 'isna') and value.isna()):
                    continue

                if abs(value) >= 1e12:
                    formatted = f"${abs(value)/1e12:.2f}T"
                elif abs(value) >= 1e9:
                    formatted = f"${abs(value)/1e9:.2f}B"
                elif abs(value) >= 1e6:
                    formatted = f"${abs(value)/1e6:.2f}M"
                else:
                    formatted = f"${abs(value):,.0f}"

                lines.append(f"**{ticker}:** {formatted} ({period})")

    if len(lines) == 1:
        lines.append("*No data available for the requested comparison.*")

    lines.append("\n*Data sourced from SEC EDGAR XBRL filings.*")
    return "\n".join(lines)


def build_single_company_response(ticker: str, xbrl_data: Dict[str, dict], docs: List[dict]) -> str:
    """Build a summary response for a single company."""
    lines = [f"## {ticker} Financial Summary\n"]

    metrics_map = {
        'revenue': 'Revenue',
        'netincome': 'Net Income',
        'totalassets': 'Total Assets',
        'operatingincome': 'Operating Income',
        'freecashflow': 'Free Cash Flow'
    }

    if ticker in xbrl_data:
        for key, label in metrics_map.items():
            if key in xbrl_data[ticker] and xbrl_data[ticker][key] is not None:
                df = xbrl_data[ticker][key]
                if not df.empty:
                    latest = df.sort_values('period_end', ascending=False).iloc[0]
                    value = latest['numeric_value']
                    if value is not None and not (hasattr(value, 'isna') and value.isna()):
                        if abs(value) >= 1e12:
                            formatted = f"${abs(value)/1e12:.2f}T"
                        elif abs(value) >= 1e9:
                            formatted = f"${abs(value)/1e9:.2f}B"
                        elif abs(value) >= 1e6:
                            formatted = f"${abs(value)/1e6:.2f}M"
                        else:
                            formatted = f"${abs(value):,.0f}"
                        period = f"{latest['fiscal_year']} {latest['fiscal_period']}"
                        lines.append(f"**{label}:** {formatted} ({period})")

    if docs:
        lines.append("\n### Recent Document Mentions")
        for doc in docs[:3]:
            lines.append(f"- {doc['source']}")

    return "\n".join(lines)


def build_risk_response(docs: List[dict]) -> str:
    """Build a response about risk factors."""
    lines = ["## Risk Factors Mentioned\n"]

    risk_keywords = ['risk', 'uncertain', 'competition', 'regulation', 'litigation', 'cybersecurity', 'volatil']

    found_any = False
    for doc in docs:
        content = doc.get('content', '')
        sentences = re.split(r'(?<=[.!?])\s+', content)

        risk_sentences = [
            s for s in sentences
            if any(kw in s.lower() for kw in risk_keywords)
            and len(s) > 40
        ]

        if risk_sentences:
            found_any = True
            lines.append(f"### {doc['source']}")
            for sent in risk_sentences[:3]:
                lines.append(f"- {sent.strip()}")
            lines.append("")

    if not found_any:
        lines.append("*No specific risk factors found in the retrieved documents. Try searching for a specific company.*")

    return "\n".join(lines)


def build_ai_response(docs: List[dict]) -> str:
    """Build a response about AI-related content."""
    lines = ["## AI & Technology Mentions\n"]

    ai_keywords = ['artificial intelligence', 'machine learning', 'generative ai', 'llm', 'neural network', 'deep learning', 'automation']

    found_any = False
    for doc in docs:
        content = doc.get('content', '').lower()
        mentions = [kw for kw in ai_keywords if kw in content]
        if mentions:
            found_any = True
            lines.append(f"**{doc['source']}** mentions: {', '.join(mentions)}")

    if not found_any:
        lines.append("*No AI-specific mentions found in retrieved documents. Try a more specific query.*")

    return "\n".join(lines)


def build_summary_response(docs: List[dict]) -> str:
    """Build a generic summary response."""
    if not docs:
        return "I couldn't find specific information about that in the available filings. Try asking about:\n\n- Revenue or financial metrics for a specific company\n- Risk factors\n- AI or technology investments\n- Compare metrics between companies (e.g., 'Compare Apple and Microsoft revenue')"

    lines = ["## Document Analysis\n"]
    lines.append("Based on the retrieved financial documents:\n")

    for doc in docs[:3]:
        lines.append(f"### {doc['source']}")
        content = doc['content'][:400]
        lines.append(f"{content}...")
        lines.append("")

    lines.append("---")
    lines.append("*Add your CLAUDE_API_KEY to .env or Streamlit secrets for AI-powered responses.*")
    return "\n".join(lines)
