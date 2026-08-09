"""Document Viewer Component."""

import streamlit as st
import pandas as pd


def render_document_viewer():
    """Render the document browser and viewer."""
    
    filings = st.session_state.filings
    ticker = st.session_state.selected_ticker
    
    st.markdown(f"### 📄 {ticker} SEC Filings")
    st.markdown("Browse and search through SEC filings.")
    
    # Filter by ticker
    ticker_filings = [f for f in filings if f['ticker'] == ticker]
    
    if not ticker_filings:
        st.warning(f"No filings found for {ticker}")
        return
    
    # Document selector
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("#### Available Documents")
        for filing in ticker_filings:
            doc_label = f"{filing['form_type']} ({filing['filing_date']})"
            if st.button(doc_label, key=f"doc_{filing['filename']}"):
                st.session_state.selected_doc = filing
                st.rerun()
    
    with col2:
        if st.session_state.selected_doc:
            display_document(st.session_state.selected_doc)
        else:
            st.info("Select a document from the list to view")


def display_document(filing: dict):
    """Display a single document with search."""
    
    st.markdown(f"#### {filing['form_type']} - {filing['filing_date']}")
    
    # Search within document
    search_term = st.text_input("Search within document", key="doc_search")
    
    # Load content
    try:
        with open(filing['filepath'], 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        st.error(f"Error loading document: {e}")
        return
    
    # Apply search filter
    if search_term:
        lines = content.split('\n')
        matching_lines = []
        for i, line in enumerate(lines):
            if search_term.lower() in line.lower():
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context = '\n'.join(lines[start:end])
                matching_lines.append(context)
        
        if matching_lines:
            st.markdown(f"**Found {len(matching_lines)} matches:**")
            for match in matching_lines[:20]:  # Limit to 20 matches
                st.text_area("", match, height=100, disabled=True)
        else:
            st.info("No matches found")
    else:
        # Show full document (truncated)
        max_chars = 50000
        if len(content) > max_chars:
            st.markdown(f"*Document truncated ({len(content):,} chars total)*")
            content = content[:max_chars] + "\n\n... [truncated]"
        
        st.text_area("Document Content", content, height=600, disabled=True)
    
    # Document metadata
    with st.expander("Document Metadata"):
        st.json({
            'ticker': filing['ticker'],
            'form_type': filing['form_type'],
            'filing_date': filing['filing_date'],
            'filename': filing['filename'],
            'size_bytes': filing.get('size_bytes', 'N/A'),
            'word_count': filing.get('word_count', 'N/A'),
        })
