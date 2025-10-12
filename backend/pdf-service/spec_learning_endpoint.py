#!/usr/bin/env python3
"""
Spec Learning Endpoint for FastAPI
Handles PDF upload, extraction, chunking, and embedding for spec learning
"""

import os
import pickle
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

from fastapi import UploadFile, File, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
import pdfplumber
import logging

logger = logging.getLogger(__name__)

class SpecLearner:
    """Handles spec document learning and embedding"""
    
    def __init__(self, 
                 data_path: str = "/data",
                 embeddings_file: str = "spec_embeddings.pkl",
                 metadata_file: str = "spec_metadata.json"):
        
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        self.embeddings_path = self.data_path / embeddings_file
        self.metadata_path = self.data_path / metadata_file
        
        # Initialize embedder
        logger.info("Loading sentence transformer...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Load existing data if available
        self.load_existing_data()
    
    def load_existing_data(self):
        """Load existing embeddings and metadata"""
        
        if self.embeddings_path.exists():
            try:
                with open(self.embeddings_path, 'rb') as f:
                    data = pickle.load(f)
                    self.chunks = data.get('chunks', [])
                    self.embeddings = data.get('embeddings', np.array([]))
                    self.sources = data.get('sources', {})
                logger.info(f"Loaded {len(self.chunks)} existing chunks")
            except Exception as e:
                logger.error(f"Failed to load embeddings: {e}")
                self.chunks = []
                self.embeddings = np.array([])
                self.sources = {}
        else:
            self.chunks = []
            self.embeddings = np.array([])
            self.sources = {}
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
        
        import io
        text = ""
        
        try:
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            # Fallback to pypdf
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(pdf_content))
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            except Exception as e2:
                logger.error(f"Fallback extraction also failed: {e2}")
                raise HTTPException(status_code=400, detail="Failed to extract text from PDF")
        
        return text
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks"""
        
        # Clean text
        text = ' '.join(text.split())
        
        # Split into sentences (simple approach)
        sentences = text.replace('!', '.').replace('?', '.').split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            words = sentence.split()
            sentence_size = len(words)
            
            if current_size + sentence_size > chunk_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))
                # Start new chunk with overlap
                overlap_words = int(overlap)
                if len(current_chunk) > overlap_words:
                    current_chunk = current_chunk[-overlap_words:]
                    current_size = len(' '.join(current_chunk).split())
                else:
                    current_chunk = []
                    current_size = 0
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Add last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def learn_spec(self, pdf_content: bytes, filename: str, mode: str = "append") -> Dict[str, Any]:
        """
        Learn a spec document by extracting, chunking, and embedding
        
        Args:
            pdf_content: PDF file content
            filename: Original filename for tracking
            mode: "append" to add to existing, "replace" to start fresh
            
        Returns:
            Learning results with statistics
        """
        
        # Calculate file hash for deduplication
        file_hash = hashlib.md5(pdf_content).hexdigest()
        
        # Check if already processed
        if mode == "append" and file_hash in self.sources.values():
            return {
                "status": "already_processed",
                "message": f"File {filename} already in spec library",
                "total_chunks": len(self.chunks)
            }
        
        # Extract text
        logger.info(f"Extracting text from {filename}...")
        text = self.extract_text_from_pdf(pdf_content)
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text extracted from PDF")
        
        # Chunk text
        logger.info(f"Chunking text from {filename}...")
        new_chunks = self.chunk_text(text)
        
        if not new_chunks:
            raise HTTPException(status_code=400, detail="No chunks created from text")
        
        # Tag chunks with source
        tagged_chunks = [f"[Source: {filename}] {chunk}" for chunk in new_chunks]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(new_chunks)} chunks...")
        new_embeddings = self.embedder.encode(new_chunks)
        
        # Update data based on mode
        if mode == "replace":
            self.chunks = tagged_chunks
            self.embeddings = new_embeddings
            self.sources = {filename: file_hash}
            logger.info("Replaced existing spec library")
        else:  # append
            if len(self.chunks) > 0:
                self.chunks.extend(tagged_chunks)
                self.embeddings = np.vstack([self.embeddings, new_embeddings])
            else:
                self.chunks = tagged_chunks
                self.embeddings = new_embeddings
            self.sources[filename] = file_hash
            logger.info(f"Added {len(new_chunks)} chunks to spec library")
        
        # Save updated data
        self.save_data()
        
        return {
            "status": "success",
            "message": f"Learned spec from {filename}",
            "chunks_added": len(new_chunks),
            "total_chunks": len(self.chunks),
            "text_length": len(text),
            "file_hash": file_hash,
            "mode": mode
        }
    
    def save_data(self):
        """Save embeddings and metadata to disk"""
        
        try:
            # Save embeddings
            data = {
                'chunks': self.chunks,
                'embeddings': self.embeddings,
                'sources': self.sources,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.embeddings_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info(f"Saved {len(self.chunks)} chunks to {self.embeddings_path}")
            
            # Save metadata as JSON for inspection
            import json
            metadata = {
                'total_chunks': len(self.chunks),
                'total_files': len(self.sources),
                'files': list(self.sources.keys()),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise HTTPException(status_code=500, detail="Failed to save learned data")
    
    def get_library_info(self) -> Dict[str, Any]:
        """Get information about the current spec library"""
        
        return {
            "total_chunks": len(self.chunks),
            "total_files": len(self.sources),
            "files": list(self.sources.keys()),
            "embeddings_shape": self.embeddings.shape if len(self.embeddings) > 0 else None,
            "storage_path": str(self.embeddings_path)
        }

def create_spec_learning_router(data_path: str = "/data") -> APIRouter:
    """Create FastAPI router with spec learning endpoints"""
    
    router = APIRouter(tags=["Spec Learning"])
    learner = SpecLearner(data_path=data_path)
    
    @router.post("/learn-spec")
    async def learn_spec(
        file: UploadFile = File(...),
        mode: str = "append"
    ):
        """
        Upload and learn a spec PDF document.
        Extracts text, chunks it, generates embeddings, and stores for go-back analysis.
        
        Args:
            file: PDF file to learn
            mode: "append" (default) adds to existing specs, "replace" starts fresh
        """
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        max_size_mb = 100
        if len(content) > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {max_size_mb}MB"
            )
        
        try:
            # Learn the spec
            result = learner.learn_spec(content, file.filename, mode)
            return JSONResponse(content=result)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Spec learning failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/spec-library")
    async def get_spec_library():
        """Get information about the current spec library"""
        return learner.get_library_info()
    
    @router.delete("/spec-library")
    async def clear_spec_library():
        """Clear all learned specs and start fresh"""
        
        learner.chunks = []
        learner.embeddings = np.array([])
        learner.sources = {}
        learner.save_data()
        
        return {
            "status": "success",
            "message": "Spec library cleared"
        }
    
    return router

# Integration function for existing FastAPI app
def integrate_spec_learning(app, data_path: str = "/data"):
    """Add spec learning endpoints to existing FastAPI app"""
    
    router = create_spec_learning_router(data_path)
    app.include_router(router)
    logger.info("✅ Spec learning endpoints added: /learn-spec, /spec-library")

if __name__ == "__main__":
    # Test the spec learner
    learner = SpecLearner(data_path="./data")
    
    # Simulate learning from text
    test_text = """
    This is a test specification document.
    Minimum clearance over streets shall be 18 feet.
    Conduit depth requirements: 24 inches for secondary service.
    All installations must comply with G.O. 95 standards.
    """
    
    chunks = learner.chunk_text(test_text)
    print(f"Created {len(chunks)} chunks from test text")
    
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {chunk[:100]}...")
    
    print(f"\nLibrary info: {learner.get_library_info()}")
