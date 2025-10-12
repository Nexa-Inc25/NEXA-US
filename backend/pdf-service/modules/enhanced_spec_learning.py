#!/usr/bin/env python3
"""
Enhanced Spec Learning System with FAISS and Optimized Chunking
Implements all recommendations for production-ready embeddings
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional, Tuple
import os
import pickle
import faiss
from pathlib import Path
import pdfplumber
import pypdf
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
import hashlib
from datetime import datetime
import re
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize

# Download NLTK data if needed
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

logger = logging.getLogger(__name__)

class EnhancedSpecLearningSystem:
    """
    Production-ready spec learning with FAISS indexing and optimized chunking
    Implements all recommendations from the embedding guide
    """
    
    def __init__(self, 
                 data_dir: str = "/data",
                 model_name: str = 'all-MiniLM-L6-v2',
                 chunk_size: int = 300,
                 chunk_overlap: int = 50,
                 batch_size: int = 32):
        """
        Initialize enhanced spec learning system
        
        Args:
            data_dir: Directory for persistent storage
            model_name: Sentence transformer model
            chunk_size: Number of words per chunk
            chunk_overlap: Word overlap between chunks
            batch_size: Batch size for embedding generation
        """
        
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            self.data_dir = Path("./data")
            self.data_dir.mkdir(exist_ok=True)
        
        self.embeddings_path = self.data_dir / "spec_embeddings.pkl"
        self.faiss_index_path = self.data_dir / "spec_index.faiss"
        self.specs_dir = self.data_dir / "specs"
        self.specs_dir.mkdir(exist_ok=True)
        
        # Chunking parameters
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.batch_size = batch_size
        
        # Load sentence transformer
        logger.info(f"Loading sentence transformer: {model_name}")
        self.embedder = SentenceTransformer(model_name)
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
        
        # Initialize storage
        self.spec_chunks = []
        self.spec_embeddings = None
        self.spec_metadata = []
        self.faiss_index = None
        
        # Load existing data
        self.load_existing_embeddings()
    
    def load_existing_embeddings(self):
        """Load existing embeddings and FAISS index"""
        
        # Load embeddings
        if self.embeddings_path.exists():
            try:
                with open(self.embeddings_path, 'rb') as f:
                    data = pickle.load(f)
                    self.spec_chunks = data.get('chunks', [])
                    self.spec_embeddings = data.get('embeddings', None)
                    self.spec_metadata = data.get('metadata', [])
                    # If no metadata, create empty dict for each chunk
                    if not self.spec_metadata and self.spec_chunks:
                        self.spec_metadata = [{}] * len(self.spec_chunks)
                logger.info(f"✅ Loaded {len(self.spec_chunks)} existing spec chunks")
            except Exception as e:
                logger.error(f"Failed to load embeddings: {e}")
        
        # Load FAISS index
        if self.faiss_index_path.exists():
            try:
                self.faiss_index = faiss.read_index(str(self.faiss_index_path))
                logger.info(f"✅ Loaded FAISS index with {self.faiss_index.ntotal} vectors")
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}")
                self.create_faiss_index()
        else:
            self.create_faiss_index()
    
    def create_faiss_index(self):
        """Create new FAISS index"""
        
        # Use IndexFlatIP for cosine similarity (after normalization)
        self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
        
        # Add existing embeddings if available
        if self.spec_embeddings is not None and len(self.spec_embeddings) > 0:
            # Normalize for cosine similarity
            normalized = self.spec_embeddings / np.linalg.norm(
                self.spec_embeddings, axis=1, keepdims=True
            )
            self.faiss_index.add(normalized)
            logger.info(f"Created FAISS index with {self.faiss_index.ntotal} vectors")
    
    def extract_text_with_pdfplumber(self, pdf_path: Path) -> Tuple[str, List[Dict]]:
        """
        Extract text using PDFPlumber for better handling of tables and formatting
        
        Returns:
            Tuple of (full_text, page_metadata)
        """
        
        full_text = ""
        page_metadata = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    text = page.extract_text()
                    
                    if text:
                        full_text += text + "\n\n"
                        
                        # Extract tables if present
                        tables = page.extract_tables()
                        if tables:
                            for table in tables:
                                # Convert table to text
                                table_text = "\n".join([
                                    " | ".join(str(cell) for cell in row if cell)
                                    for row in table if row
                                ])
                                full_text += f"\n[TABLE]\n{table_text}\n[/TABLE]\n\n"
                        
                        # Store metadata
                        page_metadata.append({
                            'page': page_num + 1,
                            'has_tables': len(tables) > 0 if tables else False,
                            'char_count': len(text)
                        })
                        
                        # Process in chunks for large PDFs (memory management)
                        if page_num > 0 and page_num % 50 == 0:
                            logger.info(f"Processed {page_num} pages...")
        
        except Exception as e:
            logger.error(f"PDFPlumber extraction failed: {e}")
            # Fallback to pypdf
            return self.extract_text_with_pypdf(pdf_path)
        
        return full_text, page_metadata
    
    def extract_text_with_pypdf(self, pdf_path: Path) -> Tuple[str, List[Dict]]:
        """Fallback PDF extraction using pypdf"""
        
        full_text = ""
        page_metadata = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    full_text += text + "\n\n"
                    page_metadata.append({
                        'page': page_num + 1,
                        'char_count': len(text)
                    })
        
        return full_text, page_metadata
    
    def chunk_text_with_overlap(self, text: str, source_name: str, page_metadata: List[Dict]) -> List[Dict]:
        """
        Chunk text with overlap and metadata preservation
        
        Returns:
            List of chunk dictionaries with text and metadata
        """
        
        chunks_with_metadata = []
        
        # Clean text
        text = self.clean_text(text)
        
        # Split into words
        words = word_tokenize(text)
        
        # Create overlapping chunks
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            # Skip very short chunks
            if len(chunk_text) < 50:
                continue
            
            # Estimate which page this chunk is from
            char_position = len(' '.join(words[:i]))
            page_num = self.estimate_page_number(char_position, page_metadata)
            
            # Create chunk with metadata
            chunk_dict = {
                'text': chunk_text,
                'source': source_name,
                'page': page_num,
                'chunk_index': len(chunks_with_metadata),
                'char_start': char_position,
                'char_end': char_position + len(chunk_text),
                'timestamp': datetime.now().isoformat()
            }
            
            chunks_with_metadata.append(chunk_dict)
        
        logger.info(f"Created {len(chunks_with_metadata)} chunks from {source_name}")
        return chunks_with_metadata
    
    def clean_text(self, text: str) -> str:
        """Clean text by removing headers, footers, and noise"""
        
        # Remove page numbers (various formats)
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'\n\d+\n', '\n', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove common headers/footers
        text = re.sub(r'CONFIDENTIAL.*?\n', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Copyright.*?\n', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def estimate_page_number(self, char_position: int, page_metadata: List[Dict]) -> int:
        """Estimate page number based on character position"""
        
        cumulative_chars = 0
        for meta in page_metadata:
            cumulative_chars += meta.get('char_count', 0)
            if char_position <= cumulative_chars:
                return meta['page']
        
        return len(page_metadata)  # Last page if not found
    
    def generate_embeddings_batch(self, chunks: List[Dict]) -> np.ndarray:
        """
        Generate embeddings in batches for efficiency
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Numpy array of embeddings
        """
        
        # Extract text from chunks
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings in batches
        logger.info(f"Generating embeddings for {len(texts)} chunks (batch size: {self.batch_size})")
        
        embeddings = self.embedder.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        
        return embeddings
    
    def learn_from_spec(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Complete learning pipeline for a spec PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with learning results
        """
        
        start_time = datetime.now()
        
        # Step 1: Extract text with metadata
        logger.info(f"📄 Extracting text from {pdf_path.name}...")
        full_text, page_metadata = self.extract_text_with_pdfplumber(pdf_path)
        
        if not full_text:
            return {
                'success': False,
                'message': 'No text extracted from PDF',
                'file': pdf_path.name
            }
        
        # Step 2: Chunk with overlap
        logger.info("✂️ Chunking text with overlap...")
        chunks_with_metadata = self.chunk_text_with_overlap(
            full_text, 
            pdf_path.name,
            page_metadata
        )
        
        # Step 3: Generate embeddings
        logger.info("🧮 Generating embeddings...")
        new_embeddings = self.generate_embeddings_batch(chunks_with_metadata)
        
        # Step 4: Update storage
        logger.info("💾 Updating storage and index...")
        self.update_storage(chunks_with_metadata, new_embeddings)
        
        # Step 5: Calculate statistics
        processing_time = (datetime.now() - start_time).total_seconds()
        file_hash = self.calculate_file_hash(pdf_path)
        
        return {
            'success': True,
            'file': pdf_path.name,
            'file_hash': file_hash,
            'chunks_added': len(chunks_with_metadata),
            'total_chunks': len(self.spec_chunks),
            'total_pages': len(page_metadata),
            'processing_time': f"{processing_time:.2f} seconds",
            'embedding_dim': self.embedding_dim,
            'index_size': self.faiss_index.ntotal if self.faiss_index else 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def update_storage(self, new_chunks: List[Dict], new_embeddings: np.ndarray):
        """Update embeddings storage and FAISS index"""
        
        # Extract text and metadata separately
        new_texts = [f"{chunk['text']} [Source: {chunk['source']}, Page {chunk['page']}]" 
                    for chunk in new_chunks]
        
        # Update chunks and metadata
        self.spec_chunks.extend(new_texts)
        self.spec_metadata.extend(new_chunks)
        
        # Update embeddings
        if self.spec_embeddings is None:
            self.spec_embeddings = new_embeddings
        else:
            self.spec_embeddings = np.vstack([self.spec_embeddings, new_embeddings])
        
        # Update FAISS index
        if self.faiss_index is None:
            self.create_faiss_index()
        else:
            self.faiss_index.add(new_embeddings)
        
        # Save to disk
        self.save_embeddings()
        self.save_faiss_index()
    
    def save_embeddings(self):
        """Save embeddings and metadata to pickle file"""
        
        data = {
            'chunks': self.spec_chunks,
            'embeddings': self.spec_embeddings,
            'metadata': self.spec_metadata,
            'model': 'all-MiniLM-L6-v2',
            'embedding_dim': self.embedding_dim,
            'chunk_params': {
                'size': self.chunk_size,
                'overlap': self.chunk_overlap
            },
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.embeddings_path, 'wb') as f:
            pickle.dump(data, f)
        
        file_size_mb = self.embeddings_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Saved embeddings to {self.embeddings_path} ({file_size_mb:.2f} MB)")
    
    def save_faiss_index(self):
        """Save FAISS index to disk"""
        
        if self.faiss_index is not None:
            faiss.write_index(self.faiss_index, str(self.faiss_index_path))
            logger.info(f"✅ Saved FAISS index with {self.faiss_index.ntotal} vectors")
    
    def search_specs(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """
        Search specs using FAISS for efficient similarity search
        
        Args:
            query: Search query text
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of matching chunks with scores
        """
        
        if self.faiss_index is None or self.faiss_index.ntotal == 0:
            logger.warning("No embeddings indexed yet")
            return []
        
        # Generate query embedding
        query_embedding = self.embedder.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).reshape(1, -1)
        
        # Search with FAISS
        scores, indices = self.faiss_index.search(query_embedding, top_k)
        
        # Filter by threshold and prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            # Convert numpy int64 to Python int
            idx = int(idx)
            if score >= threshold and idx < len(self.spec_chunks):
                chunk_metadata = self.spec_metadata[idx] if idx < len(self.spec_metadata) else {}
                
                results.append({
                    'chunk': self.spec_chunks[idx][:500],  # First 500 chars
                    'similarity': float(score),
                    'confidence_percentage': f"{score * 100:.1f}%",
                    'source': chunk_metadata.get('source', 'Unknown') if isinstance(chunk_metadata, dict) else 'Unknown',
                    'page': chunk_metadata.get('page', 0) if isinstance(chunk_metadata, dict) else 0,
                    'chunk_index': idx
                })
        
        return results
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for deduplication"""
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics about the spec learning system"""
        
        return {
            'total_chunks': len(self.spec_chunks),
            'total_embeddings': len(self.spec_embeddings) if self.spec_embeddings is not None else 0,
            'embedding_dimension': self.embedding_dim,
            'faiss_index_size': self.faiss_index.ntotal if self.faiss_index else 0,
            'embeddings_file_size_mb': (
                self.embeddings_path.stat().st_size / (1024 * 1024) 
                if self.embeddings_path.exists() else 0
            ),
            'faiss_index_size_mb': (
                self.faiss_index_path.stat().st_size / (1024 * 1024)
                if self.faiss_index_path.exists() else 0
            ),
            'unique_sources': len(set(m.get('source', '') for m in self.spec_metadata if isinstance(m, dict))),
            'chunk_parameters': {
                'size': self.chunk_size,
                'overlap': self.chunk_overlap
            },
            'model': 'all-MiniLM-L6-v2',
            'ready': self.faiss_index is not None and self.faiss_index.ntotal > 0
        }

def integrate_enhanced_spec_learning(app):
    """
    Integrate enhanced spec learning with FastAPI app
    """
    
    router = APIRouter(prefix="/enhanced-spec", tags=["Enhanced Spec Learning"])
    
    # Initialize the enhanced system
    spec_learner = EnhancedSpecLearningSystem()
    
    @router.post("/learn")
    async def learn_from_spec_enhanced(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = BackgroundTasks()
    ):
        """
        Enhanced spec learning with FAISS and optimized chunking
        
        Features:
        - PDFPlumber for better text extraction
        - Overlapping chunks for context preservation
        - FAISS indexing for fast similarity search
        - Batch embedding generation
        - Comprehensive metadata tracking
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
                "processing_time": result['processing_time'],
                "faiss_index_size": result['index_size']
            }
        else:
            raise HTTPException(status_code=500, detail=result['message'])
    
    @router.get("/search")
    async def search_enhanced(
        query: str,
        top_k: int = 5,
        threshold: float = 0.7
    ):
        """
        Search specs using FAISS-accelerated similarity search
        """
        
        results = spec_learner.search_specs(query, top_k, threshold)
        
        return {
            "query": query,
            "num_results": len(results),
            "results": results
        }
    
    @router.get("/stats")
    async def get_enhanced_stats():
        """Get comprehensive statistics about the spec learning system"""
        
        stats = spec_learner.get_statistics()
        
        return {
            "status": "ready" if stats['ready'] else "needs_training",
            "statistics": stats
        }
    
    app.include_router(router)
    logger.info("✅ Enhanced spec learning endpoints added")
    logger.info("   Features: PDFPlumber extraction, FAISS indexing, overlapping chunks")

if __name__ == "__main__":
    # Test the enhanced system
    system = EnhancedSpecLearningSystem()
    
    print("🎯 Enhanced Spec Learning System")
    print("="*50)
    
    stats = system.get_statistics()
    print(f"Total Chunks: {stats['total_chunks']}")
    print(f"FAISS Index: {stats['faiss_index_size']} vectors")
    print(f"Embedding Dim: {stats['embedding_dimension']}")
    print(f"Ready: {stats['ready']}")
    
    # Test search if ready
    if stats['ready']:
        results = system.search_specs("pole clearance 18 feet")
        print(f"\nSearch Results: {len(results)} matches")
        for r in results:
            print(f"  - {r['confidence_percentage']}: {r['chunk'][:100]}...")
