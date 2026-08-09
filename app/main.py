"""
AI-Powered Enterprise Data Assistant (RAG + Cortex)
Main Streamlit Application - Dual Mode (Demo / Snowflake)

Author: Innocent Mamvura
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

# Ensure repo root is in path for app.* imports
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Load environment variables
load_dotenv()

# App imports
from app.components.chat import render_chat_interface
from app.components.dashboard import render_financial_dashboard
from app.components.document_viewer import render_document_viewer
from app.utils.data_loader import load_demo_data, load_snowflake_data

# Page configuration
st.set_page_config(
    page_title="AI-Powered Enterprise Data Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #29B5E8;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .mode-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .mode-demo {
        background-color: #E8F5E9;
        color: #2E7D32;
    }
    .mode-snowflake {
        background-color: #E3F2FD;
        color: #1565C0;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        'chat_history': [],
        'selected_ticker': 'MSFT',
        'selected_doc': None,
        'current_page': '💬 RAG Chat',
        'pending_query': None,
        'mode': os.getenv('APP_MODE', 'demo'),
        'data_loaded': False,
        'filings': None,
        'embeddings': None,
        'xbrl_data': None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar():
    """Render the sidebar navigation and controls."""
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/f/fa/Snowflake_Logo.svg", width=150)
        st.markdown("### AI-Powered Enterprise Data Assistant")
        st.markdown("---")
        
        # Mode indicator
        mode = st.session_state.mode
        mode_class = "mode-demo" if mode == "demo" else "mode-snowflake"
        mode_label = "🟢 DEMO MODE" if mode == "demo" else "❄️ SNOWFLAKE MODE"
        st.markdown(f'<span class="mode-badge {mode_class}">{mode_label}</span>', 
                   unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Company selector
        st.markdown("#### Select Company")
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
        selected = st.selectbox(
            "Company",
            tickers,
            index=tickers.index(st.session_state.selected_ticker),
            label_visibility="collapsed"
        )
        if selected != st.session_state.selected_ticker:
            st.session_state.selected_ticker = selected
            st.rerun()
        
        st.markdown("---")
        
        # Navigation
        st.markdown("#### Navigation")
        pages = ["💬 RAG Chat", "📈 Financial Dashboard", "📄 Document Viewer"]
        current_page = st.session_state.get('current_page', '💬 RAG Chat')
        try:
            current_index = pages.index(current_page)
        except ValueError:
            current_index = 0
        
        page = st.radio(
            "Go to",
            pages,
            index=current_index,
            label_visibility="collapsed"
        )
        
        # Update current page in session state if changed
        if page != current_page:
            st.session_state.current_page = page
            st.rerun()
        
        st.markdown("---")
        
        # About
        with st.expander("About this project"):
            st.markdown("""
            **Built with:**
            - Snowflake Cortex AI
            - Snowpark Python
            - Streamlit
            - SEC EDGAR Data
            
            **Author:** Innocent Mamvura  
            **Role:** Lead Data Scientist
            """)
        
        return page


def render_header():
    """Render the main header."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="main-header">🤖 AI-Powered Enterprise Data Assistant</div>', 
                   unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Enterprise-grade financial document analysis powered by Snowflake AI</div>', 
                   unsafe_allow_html=True)
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.info(f"🕐 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


def main():
    """Main application entry point."""
    init_session_state()
    
    # Load data if not already loaded
    if not st.session_state.data_loaded:
        with st.spinner("Loading financial data..."):
            try:
                if st.session_state.mode == "demo":
                    filings, embeddings, xbrl = load_demo_data()
                else:
                    filings, embeddings, xbrl = load_snowflake_data()
                
                st.session_state.filings = filings
                st.session_state.embeddings = embeddings
                st.session_state.xbrl_data = xbrl
                st.session_state.data_loaded = True
            except Exception as e:
                st.error(f"Error loading data: {e}")
                st.session_state.data_loaded = True
    
    # Render UI
    page = render_sidebar()
    render_header()
    
    # Route to page
    if "RAG Chat" in page:
        render_chat_interface()
    elif "Financial Dashboard" in page:
        render_financial_dashboard()
    elif "Document Viewer" in page:
        render_document_viewer()


if __name__ == "__main__":
    main()
