"""
Optimized Chunking Strategy for Construction Specification Documents
Tailored for PG&E, SCE, SDG&E spec books
"""
import re
from typing import List, Dict, Tuple
import numpy as np

class ConstructionSpecChunker:
    """
    Advanced chunking strategy optimized for construction specifications
    """
    
    def __init__(self):
        # Optimal sizes based on construction document analysis
        self.OPTIMAL_CHUNK_SIZE = 1200  # Sweet spot for spec context
        self.MIN_CHUNK_SIZE = 300      # Minimum viable context
        self.MAX_CHUNK_SIZE = 2000      # Max before losing focus
        self.OVERLAP_RATIO = 0.15       # 15% overlap for continuity
        
        # Construction-specific patterns
        self.section_patterns = [
            r'^\s*\d+\.\d+(?:\.\d+)*\s+',  # 1.2.3 Section numbering
            r'^Section\s+\d+',              # Section X
            r'^Article\s+\d+',              # Article X
            r'^Part\s+[IVX]+',              # Part IV
            r'^Chapter\s+\d+',              # Chapter X
            r'^Appendix\s+[A-Z]',           # Appendix A
        ]
        
        # Important keywords that shouldn't be split
        self.preserve_keywords = [
            'shall', 'must', 'required', 'prohibited', 'maximum', 'minimum',
            'voltage', 'amperage', 'clearance', 'spacing', 'grounding',
            'installation', 'testing', 'inspection', 'certification'
        ]
        
        # Entity patterns to keep together
        self.entity_patterns = [
            r'\d+\s*(?:feet|ft|inches|in|meters|m)',  # Measurements
            r'\d+\s*(?:volts|V|kV|amps|A|kVA)',       # Electrical units
            r'(?:Type|Class|Grade)\s+[A-Z0-9]+',       # Classifications
            r'ASTM\s+[A-Z]\d+',                        # Standards
            r'IEEE\s+\d+',                             # IEEE standards
            r'NESC\s+Rule\s+\d+',                      # NESC rules
        ]
    
    def chunk_text_smart(self, text: str) -> List[Dict]:
        """
        Smart chunking that preserves specification structure and context
        """
        chunks = []
        
        # Step 1: Split by major sections
        sections = self._split_by_sections(text)
        
        for section in sections:
            section_text = section['text']
            section_header = section.get('header', '')
            
            # Step 2: Check if section needs chunking
            if len(section_text) <= self.MAX_CHUNK_SIZE:
                # Small enough to keep as single chunk
                chunks.append({
                    'text': section_text,
                    'header': section_header,
                    'type': 'complete_section',
                    'size': len(section_text),
                    'id': len(chunks)
                })
            else:
                # Step 3: Smart split for large sections
                sub_chunks = self._smart_split_section(section_text, section_header)
                chunks.extend(sub_chunks)
        
        # Step 4: Add overlap connections
        chunks = self._add_smart_overlap(chunks)
        
        return chunks
    
    def _split_by_sections(self, text: str) -> List[Dict]:
        """
        Split text by section boundaries
        """
        sections = []
        lines = text.split('\n')
        current_section = []
        current_header = ""
        
        for i, line in enumerate(lines):
            # Check if line is a section header
            is_header = False
            for pattern in self.section_patterns:
                if re.match(pattern, line):
                    # Save previous section
                    if current_section:
                        sections.append({
                            'text': '\n'.join(current_section),
                            'header': current_header
                        })
                    # Start new section
                    current_header = line.strip()
                    current_section = [line]
                    is_header = True
                    break
            
            if not is_header:
                current_section.append(line)
        
        # Add last section
        if current_section:
            sections.append({
                'text': '\n'.join(current_section),
                'header': current_header
            })
        
        # If no sections found, treat as single section
        if not sections:
            sections = [{'text': text, 'header': 'Document'}]
        
        return sections
    
    def _smart_split_section(self, text: str, header: str) -> List[Dict]:
        """
        Intelligently split a large section preserving important context
        """
        chunks = []
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # Check if adding this paragraph exceeds optimal size
            if current_size + para_size > self.OPTIMAL_CHUNK_SIZE:
                # Check if we should keep important entities together
                if self._contains_important_entity(para) and current_size < self.MIN_CHUNK_SIZE:
                    # Keep entity with current chunk even if slightly over
                    current_chunk.append(para)
                    current_size += para_size
                else:
                    # Save current chunk and start new one
                    if current_chunk:
                        chunk_text = '\n\n'.join(current_chunk)
                        chunks.append({
                            'text': chunk_text,
                            'header': header,
                            'type': 'partial_section',
                            'size': len(chunk_text),
                            'id': len(chunks)
                        })
                    current_chunk = [para]
                    current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'header': header,
                'type': 'partial_section',
                'size': len(chunk_text),
                'id': len(chunks)
            })
        
        return chunks
    
    def _contains_important_entity(self, text: str) -> bool:
        """
        Check if text contains important entities that shouldn't be split
        """
        # Check for preserved keywords
        text_lower = text.lower()
        for keyword in self.preserve_keywords:
            if keyword in text_lower:
                return True
        
        # Check for entity patterns
        for pattern in self.entity_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check for tables or lists
        if '|' in text or text.count('-') > 10:  # Simple table detection
            return True
        
        return False
    
    def _add_smart_overlap(self, chunks: List[Dict]) -> List[Dict]:
        """
        Add intelligent overlap between chunks
        """
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            enhanced_chunk = chunk.copy()
            
            # Add context from previous chunk
            if i > 0 and chunks[i-1].get('header') == chunk.get('header'):
                # Same section, add overlap
                prev_text = chunks[i-1]['text']
                overlap_size = int(len(prev_text) * self.OVERLAP_RATIO)
                
                # Get last sentences from previous chunk
                prev_sentences = prev_text.split('.')
                overlap_text = ""
                for sent in reversed(prev_sentences):
                    if len(overlap_text) + len(sent) < overlap_size:
                        overlap_text = sent + "." + overlap_text
                    else:
                        break
                
                if overlap_text:
                    enhanced_chunk['overlap_context'] = overlap_text.strip()
            
            # Add metadata
            enhanced_chunk['chunk_index'] = i
            enhanced_chunk['total_chunks'] = len(chunks)
            
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
    
    def get_optimal_k_for_retrieval(self, query_type: str) -> int:
        """
        Get optimal number of chunks to retrieve based on query type
        """
        query_patterns = {
            'measurement': 8,      # Need more context for measurements
            'specification': 5,    # Standard spec lookups
            'violation': 10,       # Need broad context for violations
            'equipment': 6,        # Equipment specs
            'installation': 7,     # Installation procedures
            'testing': 6,          # Testing requirements
            'default': 5
        }
        
        query_lower = query_type.lower()
        for pattern, k in query_patterns.items():
            if pattern in query_lower:
                return k
        
        return query_patterns['default']
    
    def calculate_chunk_statistics(self, chunks: List[Dict]) -> Dict:
        """
        Calculate statistics for chunk optimization
        """
        sizes = [chunk['size'] for chunk in chunks]
        
        return {
            'total_chunks': len(chunks),
            'avg_size': np.mean(sizes),
            'median_size': np.median(sizes),
            'std_size': np.std(sizes),
            'min_size': min(sizes),
            'max_size': max(sizes),
            'complete_sections': sum(1 for c in chunks if c.get('type') == 'complete_section'),
            'partial_sections': sum(1 for c in chunks if c.get('type') == 'partial_section'),
        }


# Usage example for Streamlit integration
def optimize_chunking_for_specs(text: str, query_type: str = 'default') -> Tuple[List[Dict], int]:
    """
    Main function to use in your Streamlit app
    """
    chunker = ConstructionSpecChunker()
    
    # Create optimized chunks
    chunks = chunker.chunk_text_smart(text)
    
    # Get optimal retrieval count
    k = chunker.get_optimal_k_for_retrieval(query_type)
    
    # Get statistics for monitoring
    stats = chunker.calculate_chunk_statistics(chunks)
    
    return chunks, k, stats


# Enhanced chunking function for your existing code
def chunk_text_optimized(text: str, doc_type: str = 'specification') -> List[str]:
    """
    Drop-in replacement for your current chunk_text function
    """
    chunker = ConstructionSpecChunker()
    
    # Adjust parameters based on document type
    if doc_type == 'audit':
        chunker.OPTIMAL_CHUNK_SIZE = 800  # Smaller for audit infractions
        chunker.OVERLAP_RATIO = 0.1
    elif doc_type == 'specification':
        chunker.OPTIMAL_CHUNK_SIZE = 1200  # Larger for spec context
        chunker.OVERLAP_RATIO = 0.15
    
    chunks = chunker.chunk_text_smart(text)
    
    # Return just the text for compatibility
    return [chunk['text'] for chunk in chunks]


# Section-aware retrieval enhancement
def retrieve_with_context(query: str, chunks: List[Dict], index, model, k: int = 5) -> List[Dict]:
    """
    Enhanced retrieval that considers section context
    """
    # Encode query
    query_embedding = model.encode([query]).astype('float32')
    
    # Search in FAISS
    distances, indices = index.search(query_embedding, k * 2)  # Get more candidates
    
    # Group by section and deduplicate
    seen_sections = set()
    results = []
    
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(chunks):
            chunk = chunks[idx]
            section = chunk.get('header', '')
            
            # Prioritize complete sections
            if chunk.get('type') == 'complete_section':
                results.insert(0, {
                    'chunk': chunk,
                    'distance': dist,
                    'relevance': 1.0 / (1.0 + dist)
                })
            else:
                # Add partial sections, avoiding duplicates
                if section not in seen_sections or len(results) < k:
                    results.append({
                        'chunk': chunk,
                        'distance': dist,
                        'relevance': 1.0 / (1.0 + dist)
                    })
                    seen_sections.add(section)
            
            if len(results) >= k:
                break
    
    return results[:k]
