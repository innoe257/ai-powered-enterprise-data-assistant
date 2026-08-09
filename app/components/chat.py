"""Streamlit RAG Chat Interface Component."""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from app.utils.embeddings import search_documents, generate_response
from app.utils.data_loader import get_ticker_filings
from ..utils.data_loader import get_ticker_filings
from app.utils.data_loader import get_ticker_filings


def render_chat_interface():
    """Render the RAG chat interface."""
    
    st.markdown("### 💬 Ask Financial Questions")
    st.markdown("Ask questions about financial filings, compare companies, or explore trends.")
    
    # Example queries
    with st.expander("💡 Example Questions"):
        examples = [
            "Compare revenue growth between Apple and Microsoft",
            "What are NVIDIA's main risk factors?",
            "Summarize Tesla's latest quarterly performance",
            "How does Amazon's free cash flow compare to Alphabet?",
            "What AI-related investments are mentioned across all filings?",
        ]
        for ex in examples:
            if st.button(ex, key=f"ex_{ex[:20]}"):
                st.session_state.pending_query = ex
                st.rerun()
    
    # Process pending query from example button click
    if st.session_state.get('pending_query'):
        query = st.session_state.pending_query
        st.session_state.pending_query = None  # Clear it
        process_query(query)
        return  # Stop here to avoid double-processing
    
    # Chat input
    query = st.chat_input("Ask about financial data...")
    
    if query:
        process_query(query)
    
    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])
            if 'sources' in msg:
                with st.expander("📚 Sources"):
                    for source in msg['sources']:
                        st.markdown(f"- {source}")


def process_query(query: str):
    """Process a user query through the RAG pipeline."""
    
    # Add user message
    st.session_state.chat_history.append({
        'role': 'user',
        'content': query,
        'timestamp': datetime.now().isoformat()
    })
    
    # Search relevant documents
    with st.spinner("Searching financial documents..."):
        relevant_docs = search_documents(
            query,
            st.session_state.embeddings,
            st.session_state.filings,
            top_k=5
        )
    
    # Generate response
    with st.spinner("Analyzing with AI..."):
        response, sources = generate_response(
            query,
            relevant_docs,
            st.session_state.xbrl_data
        )
    
    # Add assistant message
    st.session_state.chat_history.append({
        'role': 'assistant',
        'content': response,
        'sources': sources,
        'timestamp': datetime.now().isoformat()
    })
    
    st.rerun()
