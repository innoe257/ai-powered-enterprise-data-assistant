"""
Generate Demo Embeddings - Lightweight Version
Author: Innocent Mamvura

Generates embeddings in batches to avoid OOM.
"""

import os
import sys
import pickle
import re
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def chunk_text(text, chunk_size=512, chunk_overlap=50):
    """Simple text chunking."""
    text = re.sub(r'\s+', ' ', text)
    
    if len(text) <= chunk_size:
        return [{'chunk_index': 0, 'text': text, 'char_count': len(text), 'word_count': len(text.split())}]
    
    chunks = []
    chunk_index = 0
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        if end < len(text):
            for sep in [". ", " ", ""]:
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


def load_filing_metadata():
    """Load filing metadata."""
    import pandas as pd
    manifest_path = DATA_DIR / "filings" / "manifest.csv"
    text_dir = DATA_DIR / "filings" / "text"
    
    if not manifest_path.exists():
        return []
    
    df = pd.read_csv(manifest_path)
    filings = []
    
    for _, row in df.iterrows():
        txt_path = text_dir / row['filename']
        if txt_path.exists():
            filings.append({
                'ticker': row['ticker'],
                'form_type': row['form_type'],
                'filing_date': row['filing_date'],
                'filename': row['filename'],
                'filepath': str(txt_path),
                'size_bytes': row['size_bytes'],
                'word_count': row['word_count'],
            })
    
    return filings


def generate_embeddings_batch():
    """Generate embeddings in small batches."""
    
    try:
        from sentence_transformers import SentenceTransformer
        import faiss
    except ImportError:
        print("Please install: pip install sentence-transformers faiss-cpu")
        return None
    
    print("Loading model (this may take a minute)...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    
    print("Loading filings...")
    filings = load_filing_metadata()
    print(f"Found {len(filings)} filings")
    
    all_chunks = []
    all_embeddings = []
    
    # Process in smaller batches
    batch_size = 16
    
    for i, filing in enumerate(filings):
        if not filing.get('filepath') or not os.path.exists(filing['filepath']):
            continue
        
        print(f"[{i+1}/{len(filings)}] {filing['ticker']} {filing['form_type']}...")
        
        try:
            with open(filing['filepath'], 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"  Error reading file: {e}")
            continue
        
        chunks = chunk_text(text, chunk_size=512, chunk_overlap=50)
        
        # Process chunks in batches
        for batch_start in range(0, len(chunks), batch_size):
            batch_chunks = chunks[batch_start:batch_start + batch_size]
            texts = [c['text'] for c in batch_chunks]
            
            if texts:
                try:
                    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
                    
                    for j, (chunk, emb) in enumerate(zip(batch_chunks, embeddings)):
                        global_idx = batch_start + j
                        all_chunks.append({
                            'chunk_id': f"{filing['ticker']}_{filing['form_type']}_{filing['filing_date']}_{global_idx}",
                            'filing_id': f"{filing['ticker']}_{filing['form_type']}_{filing['filing_date']}",
                            'ticker': filing['ticker'],
                            'form_type': filing['form_type'],
                            'filing_date': filing['filing_date'],
                            'chunk_index': global_idx,
                            'text': chunk['text'][:1000],  # Limit stored text
                            'char_count': chunk['char_count'],
                            'word_count': chunk['word_count']
                        })
                        all_embeddings.append(emb)
                except Exception as e:
                    print(f"  Error encoding batch: {e}")
    
    if not all_embeddings:
        print("No embeddings generated!")
        return None
    
    print(f"\nBuilding FAISS index with {len(all_embeddings)} vectors...")
    dimension = len(all_embeddings[0])
    index = faiss.IndexFlatIP(dimension)
    
    embeddings_array = np.array(all_embeddings).astype('float32')
    faiss.normalize_L2(embeddings_array)
    index.add(embeddings_array)
    
    embeddings_data = {
        'index': index,
        'chunks': all_chunks,
        'vectors': embeddings_array,
        'model_name': 'all-MiniLM-L6-v2',
        'dimension': dimension
    }
    
    output_path = DATA_DIR / "embeddings" / "document_embeddings.pkl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'wb') as f:
        pickle.dump(embeddings_data, f)
    
    print(f"\n✅ Embeddings saved to: {output_path}")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Vector dimension: {dimension}")
    
    return embeddings_data


if __name__ == "__main__":
    result = generate_embeddings_batch()
    if result is None:
        print("\n⚠️  Embedding generation failed. The app will use keyword search fallback.")
