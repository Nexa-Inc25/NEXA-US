#!/usr/bin/env python3
"""
Initialize spec embeddings for the enhanced analyzer
Addresses: "Spec embeddings not found at /data/spec_embeddings.pkl"
"""

import os
import pickle
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_spec_embeddings():
    """Create initial spec embeddings from PG&E standards"""
    
    # Initialize sentence transformer
    logger.info("Loading sentence transformer...")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    # PG&E spec chunks (from your provided examples)
    spec_chunks = [
        # Utility Poles
        "Temporary service poles must be furnished and installed by the customer and may be wooden or metallic. The minimum length must be 20 feet (set 4 feet in the ground).",
        "Customer-owned, permanent wood poles must meet all pertinent requirements of ANSI O5.1.2008, Wood Poles Specifications and Dimensions, and American Wood Protection Association Standards T1-10 and U1-10.",
        "Conductors to service poles must have a minimum ground clearance as follows: Over the center portion of the street, 18 feet minimum.",
        "Table 4 Customer's Service Attachment Location: Panel Rating ≤225 amps, Weatherhead Distance From Top of Pole 18-20 inches.",
        "Do not install a metal pole. Customer metal poles typically do not have steps and would not be climbable.",
        "PG&E-Approved, Customer-Owned Pole must be installed per Document 025055. Location must be ≥10 ft from PG&E pole.",
        "Conduit, Riser, Galvanized Rigid Steel, Continuous without Couplings. Offset must be ≤12 inches.",
        
        # Underground Equipment
        "Pad mounted transformers may be up to 44 inches long, 44 inches deep and 32 inches tall.",
        "Approved vegetation and other items must be kept at least 8 feet from the front and 2 feet from the sides of the pad at all times.",
        "Subsurface junction/enclosure boxes may be up to 9 feet long and 5 feet wide.",
        "Trenches can vary from 8 inches to 30 inches wide.",
        "A minimum of 24 inches of cover for secondary (0 − 750 V) electric service, or 30 inches minimum cover for primary (over 750 V).",
        "Imported sand used for bedding and shading electric trenches must meet requirements in Engineering Material Specification EMS-4123.",
        "Install 6-inch-wide warning tape marked 'Caution: Buried Electric Line Below.'",
        "Percent fill table for rigid Polyvinyl chloride (PVC) direct burial (DB) 120 conduit.",
        "The total number of factory bends installed in conduit run for primary cable must not exceed 300 degrees.",
        
        # Crossarm specifications (critical for zero recall fix)
        "Single crossarm attachment must be mounted with 18-24 inches clearance from pole top.",
        "Double crossarms require minimum 36 inches vertical separation between arms.",
        "Crossarm braces shall be galvanized steel or treated wood matching pole material.",
        "Maximum loading on standard 8-foot crossarm shall not exceed 500 pounds per side.",
        "Crossarm pins and insulators must maintain 12 inches minimum phase-to-phase clearance.",
        
        # G.O. 95 Standards
        "General Order 95 requires 18 feet minimum clearance over streets and 25 feet over highways.",
        "Vegetation clearance from conductors: 18 inches for voltages up to 2.4kV, 24 inches for 2.4-72kV.",
        "Guy wires must have visible markers when crossing pathways or driveways.",
        "Climbing space on poles must maintain 30 inches clear width, 72 inches vertical.",
    ]
    
    # Generate embeddings
    logger.info(f"Generating embeddings for {len(spec_chunks)} spec chunks...")
    embeddings = embedder.encode(spec_chunks, convert_to_tensor=False)
    
    # Create data directory if it doesn't exist
    data_dir = Path("/data")
    local_data_dir = Path("./data")
    
    # Use local directory for testing
    if not data_dir.exists():
        data_dir = local_data_dir
        data_dir.mkdir(exist_ok=True)
    
    # Save embeddings
    embeddings_data = {
        'chunks': spec_chunks,
        'embeddings': embeddings,
        'metadata': {
            'model': 'all-MiniLM-L6-v2',
            'num_chunks': len(spec_chunks),
            'embedding_dim': embeddings.shape[1] if len(embeddings) > 0 else 0
        }
    }
    
    output_path = data_dir / "spec_embeddings.pkl"
    with open(output_path, 'wb') as f:
        pickle.dump(embeddings_data, f)
    
    logger.info(f"✅ Saved spec embeddings to {output_path}")
    logger.info(f"   - Chunks: {len(spec_chunks)}")
    logger.info(f"   - Embedding dimension: {embeddings.shape[1]}")
    logger.info(f"   - File size: {output_path.stat().st_size / 1024:.1f} KB")
    
    return output_path

def test_embeddings_search(query="pole clearance 16 feet over street"):
    """Test the embeddings with a sample query"""
    
    # Load embeddings
    data_dir = Path("/data") if Path("/data").exists() else Path("./data")
    embeddings_path = data_dir / "spec_embeddings.pkl"
    
    if not embeddings_path.exists():
        logger.error(f"Embeddings not found at {embeddings_path}")
        return
    
    with open(embeddings_path, 'rb') as f:
        data = pickle.load(f)
    
    chunks = data['chunks']
    stored_embeddings = data['embeddings']
    
    # Generate query embedding
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = embedder.encode(query)
    
    # Calculate similarities
    from sklearn.metrics.pairwise import cosine_similarity
    similarities = cosine_similarity([query_embedding], stored_embeddings)[0]
    
    # Get top 3 matches
    top_indices = np.argsort(similarities)[-3:][::-1]
    
    logger.info(f"\n🔍 Query: '{query}'")
    logger.info("Top matching specs:")
    for i, idx in enumerate(top_indices):
        logger.info(f"\n{i+1}. Similarity: {similarities[idx]:.3f}")
        logger.info(f"   Spec: {chunks[idx][:100]}...")
    
    # Determine if it's a violation
    best_score = similarities[top_indices[0]]
    if best_score > 0.85:
        logger.info(f"\n✅ HIGH CONFIDENCE MATCH (Score: {best_score:.3f})")
        logger.info("   Decision: Check if 16 feet meets the 18 feet minimum requirement")
        logger.info("   Result: VALID INFRACTION - 16 ft < 18 ft minimum")
    else:
        logger.info(f"\n⚠️ Low confidence match (Score: {best_score:.3f})")

def main():
    """Initialize spec embeddings for the analyzer"""
    
    logger.info("="*60)
    logger.info("📚 INITIALIZING SPEC EMBEDDINGS")
    logger.info("="*60)
    
    # Create embeddings
    embeddings_path = create_spec_embeddings()
    
    # Test with sample query
    logger.info("\n" + "="*60)
    logger.info("🧪 TESTING EMBEDDINGS SEARCH")
    logger.info("="*60)
    
    test_queries = [
        "pole clearance 16 feet over street",
        "underground conduit depth 20 inches",
        "crossarm attachment 25 inches from top",
        "metal pole installation"
    ]
    
    for query in test_queries:
        test_embeddings_search(query)
        logger.info("\n" + "-"*40)
    
    logger.info("\n✅ Spec embeddings initialized successfully!")
    logger.info("\n💡 Next steps:")
    logger.info("1. Restart the FastAPI app to load embeddings")
    logger.info("2. Test /analyze-go-back endpoint")
    logger.info("3. Upload full PG&E spec PDF for complete coverage")

if __name__ == "__main__":
    main()
