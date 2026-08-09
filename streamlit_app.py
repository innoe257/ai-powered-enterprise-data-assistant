"""
AI-Powered Enterprise Data Assistant (RAG + Cortex)
Streamlit Cloud Entry Point

This file exists at the repo root so Streamlit Cloud can find it.
All actual code lives in the app/ package.
"""

import sys
from pathlib import Path

# Add repo root to path so 'app' package is importable
REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT))

# Run app/main.py as a module so package imports work correctly
import runpy
runpy.run_module('app.main', run_name='__main__')
