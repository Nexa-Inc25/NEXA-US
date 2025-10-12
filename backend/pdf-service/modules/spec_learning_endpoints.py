#!/usr/bin/env python3
"""
Spec Learning Endpoints for PG&E Standards
Allows uploading and learning from spec books
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import os
import pickle
from pathlib import Path
import pypdf
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spec-learning", tags=["Spec Learning"])

class SpecLearningSystem:
    """System for learning from PG&E spec documents"""
    
    def __init__(self, data_dir="/data"):
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            self.data_dir = Path("./data")
            self.data_dir.mkdir(exist_ok=True)
        
        self.embeddings_path = self.data_dir / "spec_embeddings.pkl"
        self.specs_dir = self.data_dir / "specs"
        self.specs_dir.mkdir(exist_ok=True)
        
        # Load sentence transformer
        logger.info("Loading sentence transformer for spec learning...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Load existing embeddings if available
        self.spec_chunks = []
        self.spec_embeddings = None
        self.load_existing_embeddings()
    
    def load_existing_embeddings(self):
        """Load existing spec embeddings"""
        if self.embeddings_path.exists():
            try:
                with open(self.embeddings_path, 'rb') as f:
                    data = pickle.load(f)
                    self.spec_chunks = data.get('chunks', [])
                    self.spec_embeddings = data.get('embeddings', None)
                logger.info(f"Loaded {len(self.spec_chunks)} existing spec chunks")
            except Exception as e:
                logger.error(f"Failed to load embeddings: {e}")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> List[str]:
        """Extract text chunks from PDF"""
        chunks = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text:
                        # Split into paragraphs
                        paragraphs = text.split('\n\n')
                        for para in paragraphs:
                            if len(para.strip()) > 50:  # Minimum chunk size
                                # Add source metadata
                                chunk = f"{para.strip()} [Source: {pdf_path.name}, Page {page_num+1}]"
                                chunks.append(chunk)
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
        
        return chunks
    
    def learn_from_spec(self, pdf_path: Path) -> Dict[str, Any]:
        """Learn from a spec PDF"""
        
        # Extract text chunks
        logger.info(f"Extracting text from {pdf_path.name}...")
        new_chunks = self.extract_text_from_pdf(pdf_path)
        
        if not new_chunks:
            return {
                'success': False,
                'message': 'No text extracted from PDF'
            }
        
        # Generate embeddings for new chunks
        logger.info(f"Generating embeddings for {len(new_chunks)} chunks...")
        new_embeddings = self.embedder.encode(new_chunks, convert_to_tensor=False)
        
        # Merge with existing embeddings
        if self.spec_embeddings is not None:
            self.spec_chunks.extend(new_chunks)
            self.spec_embeddings = np.vstack([self.spec_embeddings, new_embeddings])
        else:
            self.spec_chunks = new_chunks
            self.spec_embeddings = new_embeddings
        
        # Save updated embeddings
        self.save_embeddings()
        
        # Calculate stats
        file_hash = hashlib.md5(open(pdf_path, 'rb').read()).hexdigest()
        
        return {
            'success': True,
            'file': pdf_path.name,
            'file_hash': file_hash,
            'chunks_added': len(new_chunks),
            'total_chunks': len(self.spec_chunks),
            'embedding_dim': self.spec_embeddings.shape[1],
            'timestamp': datetime.now().isoformat()
        }
    
    def save_embeddings(self):
        """Save embeddings to disk"""
        data = {
            'chunks': self.spec_chunks,
            'embeddings': self.spec_embeddings,
            'metadata': {
                'model': 'all-MiniLM-L6-v2',
                'num_chunks': len(self.spec_chunks),
                'embedding_dim': self.spec_embeddings.shape[1] if self.spec_embeddings is not None else 0,
                'last_updated': datetime.now().isoformat()
            }
        }
        
        with open(self.embeddings_path, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Saved {len(self.spec_chunks)} spec chunks to {self.embeddings_path}")
    
    def search_specs(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """Search for relevant spec sections"""
        
        if self.spec_embeddings is None or len(self.spec_chunks) == 0:
            return []
        
        # Generate query embedding
        query_embedding = self.embedder.encode(query)
        
        # Calculate similarities
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity([query_embedding], self.spec_embeddings)[0]
        
        # Get top matches above threshold
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] >= threshold:
                results.append({
                    'chunk': self.spec_chunks[idx][:500],  # First 500 chars
                    'similarity': float(similarities[idx]),
                    'source': self._extract_source(self.spec_chunks[idx])
                })
        
        return results
    
    def _extract_source(self, chunk: str) -> str:
        """Extract source from chunk"""
        import re
        source_match = re.search(r'\[Source: ([^\]]+)\]', chunk)
        if source_match:
            return source_match.group(1)
        return "Unknown"
    
    def get_stats(self) -> Dict:
        """Get current learning stats"""
        return {
            'total_chunks': len(self.spec_chunks),
            'embedding_dim': self.spec_embeddings.shape[1] if self.spec_embeddings is not None else 0,
            'embeddings_size_kb': self.embeddings_path.stat().st_size / 1024 if self.embeddings_path.exists() else 0,
            'specs_learned': len(list(self.specs_dir.glob("*.pdf"))),
            'ready': self.spec_embeddings is not None and len(self.spec_chunks) > 0
        }

# Initialize the learning system
spec_learner = SpecLearningSystem()

@router.post("/learn-spec")
async def learn_from_spec_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload and learn from a PG&E spec PDF
    
    This endpoint:
    1. Accepts PDF spec documents
    2. Extracts text chunks
    3. Generates embeddings
    4. Stores for future cross-referencing
    """
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save uploaded file
    file_path = spec_learner.specs_dir / file.filename
    content = await file.read()
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Learn from the spec
    result = spec_learner.learn_from_spec(file_path)
    
    if result['success']:
        return {
            "message": f"Successfully learned from {file.filename}",
            "chunks_added": result['chunks_added'],
            "total_chunks": result['total_chunks'],
            "file_hash": result['file_hash']
        }
    else:
        raise HTTPException(status_code=500, detail=result['message'])

@router.post("/learn-specs-batch")
async def learn_from_multiple_specs(
    files: List[UploadFile] = File(...)
):
    """
    Upload and learn from multiple spec PDFs at once
    """
    
    results = []
    total_chunks_added = 0
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            results.append({
                'file': file.filename,
                'success': False,
                'message': 'Not a PDF file'
            })
            continue
        
        # Save and learn from file
        file_path = spec_learner.specs_dir / file.filename
        content = await file.read()
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        result = spec_learner.learn_from_spec(file_path)
        
        if result['success']:
            total_chunks_added += result['chunks_added']
        
        results.append({
            'file': file.filename,
            'success': result['success'],
            'chunks_added': result.get('chunks_added', 0)
        })
    
    return {
        "files_processed": len(files),
        "total_chunks_added": total_chunks_added,
        "total_chunks": len(spec_learner.spec_chunks),
        "results": results
    }

@router.get("/search-specs")
async def search_spec_database(
    query: str,
    top_k: int = 5,
    threshold: float = 0.7
):
    """
    Search the learned spec database
    
    Args:
        query: Search query (e.g., "pole clearance requirements")
        top_k: Number of top results to return
        threshold: Minimum similarity threshold (0-1)
    """
    
    results = spec_learner.search_specs(query, top_k, threshold)
    
    return {
        "query": query,
        "num_results": len(results),
        "results": results
    }

@router.get("/spec-learning-stats")
async def get_spec_learning_stats():
    """
    Get statistics about the spec learning system
    """
    
    stats = spec_learner.get_stats()
    
    return {
        "status": "ready" if stats['ready'] else "needs_training",
        "statistics": stats,
        "message": "Upload PG&E spec PDFs to /learn-spec endpoint" if not stats['ready'] else "System ready for queries"
    }

@router.delete("/clear-specs")
async def clear_spec_database():
    """
    Clear all learned specs (use with caution!)
    """
    
    # Clear embeddings
    spec_learner.spec_chunks = []
    spec_learner.spec_embeddings = None
    
    # Delete embeddings file
    if spec_learner.embeddings_path.exists():
        os.remove(spec_learner.embeddings_path)
    
    # Clear spec files
    for pdf_file in spec_learner.specs_dir.glob("*.pdf"):
        os.remove(pdf_file)
    
    return {
        "message": "Spec database cleared successfully",
        "status": "empty"
    }

def integrate_spec_learning(app):
    """
    Add spec learning endpoints to the main app
    """
    app.include_router(router)
    logger.info("✅ Spec learning endpoints added: /spec-learning/*")
    logger.info("   - /learn-spec: Upload single PDF")
    logger.info("   - /learn-specs-batch: Upload multiple PDFs")
    logger.info("   - /search-specs: Search learned specs")
    logger.info("   - /spec-learning-stats: Get system stats")
