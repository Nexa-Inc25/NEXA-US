-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create spec_chunks table with vector column
CREATE TABLE IF NOT EXISTS spec_chunks (
    id SERIAL PRIMARY KEY,
    chunk_text TEXT NOT NULL,
    embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS spec_chunks_embedding_hnsw_idx 
ON spec_chunks USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 80);

-- Verify installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
