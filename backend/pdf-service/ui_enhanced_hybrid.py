"""
NEXA Document Intelligence - Hybrid Version
Combines custom NER with optional xAI API fallback for complex cases
"""
import streamlit as st
import os
import numpy as np
import faiss
import pickle
from sentence_transformers import SentenceTransformer
import pdfplumber
import pytesseract
from PIL import Image
import io
import logging
import time
import torch
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from custom_taggers import train_pos_tagger, train_ner_tagger
import requests
import json

# Configuration
USE_XAI_FALLBACK = os.environ.get('USE_XAI_FALLBACK', 'false').lower() == 'true'
XAI_API_KEY = os.environ.get('XAI_API_KEY', '')
XAI_CONFIDENCE_THRESHOLD = 0.7  # Use xAI if our confidence is below this

# Download NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('maxent_ne_chunker', quiet=True)
    nltk.download('words', quiet=True)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache model to load once
@st.cache_resource
def load_model():
    try:
        logger.info("Loading Sentence-BERT model...")
        model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda' if torch.cuda.is_available() else 'cpu')
        logger.info("Model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        st.error(f"Failed to load model: {e}")
        return None

# Cache custom taggers
@st.cache_resource
def load_custom_taggers():
    try:
        logger.info("Loading custom taggers...")
        pos_tagger = train_pos_tagger()
        ner_tagger = train_ner_tagger()
        logger.info("Custom taggers loaded successfully")
        return pos_tagger, ner_tagger
    except Exception as e:
        logger.error(f"Error loading custom taggers: {e}")
        return None, None

# Initialize model and taggers
model = None
try:
    model = load_model()
except Exception as e:
    logger.error(f"Failed to initialize model: {e}")
    model = None

pos_tagger, ner_tagger = load_custom_taggers()

# Get stopwords
try:
    stop_words = set(stopwords.words('english'))
    stop_words -= {'must', 'shall', 'should', 'not', 'no'}
except:
    stop_words = set()

def call_xai_api(spec_text, infraction, confidence_score):
    """
    Call xAI API for complex analysis when our confidence is low
    """
    if not XAI_API_KEY:
        return None
        
    prompt = f"""
    You are an expert in utility construction specifications.
    
    Specification excerpt: {spec_text[:10000]}
    
    Infraction found: {infraction}
    
    Our system confidence: {confidence_score:.2%}
    
    Please analyze:
    1. Is this infraction valid according to the specification?
    2. What specific section/requirement was violated?
    3. Can this infraction be appealed? If yes, why?
    4. Provide confidence level: HIGH/MEDIUM/LOW
    
    Be precise and reference specific section numbers.
    """
    
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "grok-beta",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.1  # Low temperature for consistency
    }
    
    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions", 
            headers=headers, 
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"]
            return result
        else:
            logger.error(f"xAI API error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error calling xAI API: {e}")
        return None

def extract_text_from_pdf(pdf_file):
    """Enhanced PDF extraction with OCR fallback"""
    text = ""
    images = []
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                
                if page_text:
                    text += page_text + "\n"
                    logger.info(f"Extracted text from page {i+1}")
                else:
                    # OCR fallback
                    logger.info(f"Page {i+1} appears to be an image, attempting OCR...")
                    try:
                        pil_image = page.to_image(resolution=300).original
                        ocr_text = pytesseract.image_to_string(pil_image)
                        if ocr_text.strip():
                            text += f"\n[OCR Page {i+1}]\n{ocr_text}\n"
                            logger.info(f"OCR successful for page {i+1}")
                    except Exception as e:
                        logger.warning(f"OCR failed for page {i+1}: {e}")
                        
        if not text.strip():
            logger.warning("No text extracted from PDF")
            return None
            
        return text
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        st.error(f"Error processing PDF: {e}")
        return None

def chunk_text(text, max_tokens=200, overlap=50):
    """Enhanced chunking with NER awareness"""
    if not text or not text.strip():
        return []
    
    # Use sentence tokenization
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        tokens = word_tokenize(sentence)
        
        # Apply NER tagging if available
        ner_tags = []
        if ner_tagger:
            try:
                ner_tags = ner_tagger.tag(tokens)
            except:
                ner_tags = [(token, 'O') for token in tokens]
        
        # Add sentence to chunk
        current_chunk.extend(tokens)
        current_length += len(tokens)
        
        # Check if we should start a new chunk
        if current_length >= max_tokens:
            # Look for section boundaries in NER tags
            section_found = False
            for token, tag in ner_tags:
                if 'SECTION' in tag:
                    section_found = True
                    break
            
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                
                # Overlap handling
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:]
                    current_length = overlap
                else:
                    current_chunk = []
                    current_length = 0
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    logger.info(f"Created {len(chunks)} chunks from text")
    return chunks

def generate_embeddings(chunks):
    """Generate embeddings for text chunks"""
    if not chunks:
        return np.array([])
    if model is None:
        logger.error("Model not available for embedding generation")
        return np.array([])
    
    embeddings = model.encode(chunks, show_progress_bar=True)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return embeddings

def create_faiss_index(embeddings, index_path="faiss_index.bin"):
    """Create FAISS index for similarity search"""
    if embeddings.shape[0] == 0:
        return None
    
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)
    faiss.write_index(index, index_path)
    logger.info(f"FAISS index created with {embeddings.shape[0]} embeddings")
    return index

# Streamlit UI
st.set_page_config(
    page_title="NEXA Document Intelligence - Hybrid",
    page_icon="🚧",
    layout="wide"
)

st.title("🚧 NEXA Document Intelligence System")
st.markdown("**Enterprise Construction Specification Analyzer with AI Enhancement**")

# Sidebar for configuration
st.sidebar.header("⚙️ Configuration")
use_xai = st.sidebar.checkbox("Enable xAI API for complex cases", value=USE_XAI_FALLBACK)
if use_xai and not XAI_API_KEY:
    st.sidebar.warning("⚠️ xAI API key not configured")
    st.sidebar.info("Set XAI_API_KEY environment variable")

confidence_threshold = st.sidebar.slider(
    "Confidence threshold for xAI fallback",
    min_value=0.5,
    max_value=0.95,
    value=XAI_CONFIDENCE_THRESHOLD,
    step=0.05
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 System Performance")
st.sidebar.metric("NER F1-Score", "82.9%")
st.sidebar.metric("Entity Types", "11")
st.sidebar.metric("Training Samples", "~500")

# Check if model is loaded
if model is None:
    st.error("⚠️ Model failed to load. Please contact support.")
    st.stop()

# Main tabs
tabs = st.tabs(["📚 Learn Specification", "📋 Analyze Audit", "✅ Results", "🤖 AI Analysis"])

# Tab 1: Learn Specification
with tabs[0]:
    st.header("Upload Specification Book")
    spec_file = st.file_uploader("Choose a spec book PDF", type="pdf")
    
    if spec_file:
        with st.spinner("Processing specification book..."):
            start = time.time()
            spec_text = extract_text_from_pdf(spec_file)
            
            if spec_text is None:
                st.error("Cannot process specification book. Please check the PDF content.")
            else:
                chunks = chunk_text(spec_text)
                
                if len(chunks) < 1:
                    st.error("No valid text chunks extracted from the specification book.")
                else:
                    # Show entity statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Chunks Created", len(chunks))
                    with col2:
                        st.metric("Processing Time", f"{time.time() - start:.2f}s")
                    with col3:
                        st.metric("Avg Chunk Size", f"{len(spec_text)//len(chunks)} chars")
                    
                    embeddings = generate_embeddings(chunks)
                    
                    if embeddings.shape[0] == 0:
                        st.error("Failed to generate embeddings from the specification book.")
                    else:
                        index = create_faiss_index(embeddings)
                        
                        if index is None:
                            st.error("Failed to create FAISS index.")
                        else:
                            with open("spec_chunks.pkl", "wb") as f:
                                pickle.dump(chunks, f)
                            
                            st.success(f"✅ Specification book processed successfully!")
                            
                            # Show sample entities detected
                            if ner_tagger:
                                sample_chunk = chunks[0] if chunks else ""
                                sample_tokens = word_tokenize(sample_chunk)[:50]
                                sample_ner = ner_tagger.tag(sample_tokens)
                                
                                entities_found = [f"{token} ({tag})" for token, tag in sample_ner if tag != 'O']
                                if entities_found:
                                    st.info(f"Sample entities detected: {', '.join(entities_found[:10])}")

# Tab 2: Analyze Audit
with tabs[1]:
    st.header("Upload Audit Report")
    audit_file = st.file_uploader("Choose an audit report PDF", type="pdf")
    
    if audit_file:
        with st.spinner("Processing audit report..."):
            audit_text = extract_text_from_pdf(audit_file)
            
            if audit_text is None:
                st.error("Cannot process audit report. Please check the PDF content.")
            else:
                audit_chunks = chunk_text(audit_text, max_tokens=100)
                
                with open("audit_chunks.pkl", "wb") as f:
                    pickle.dump(audit_chunks, f)
                
                st.success(f"✅ Audit report processed: {len(audit_chunks)} chunks created")

# Tab 3: Results
with tabs[2]:
    st.header("Infraction Analysis Results")
    
    if os.path.exists("spec_chunks.pkl") and os.path.exists("audit_chunks.pkl"):
        if st.button("🔍 Find Infractions", type="primary"):
            with st.spinner("Analyzing infractions..."):
                # Load data
                spec_chunks = pickle.load(open("spec_chunks.pkl", "rb"))
                audit_chunks = pickle.load(open("audit_chunks.pkl", "rb"))
                index = faiss.read_index("faiss_index.bin")
                
                results = []
                for audit_chunk in audit_chunks:
                    # Check for infraction keywords
                    if any(keyword in audit_chunk.lower() for keyword in 
                           ['infraction', 'violation', 'non-compliant', 'failed', 'incorrect']):
                        
                        # Find matching spec sections
                        query_embedding = model.encode([audit_chunk])
                        D, I = index.search(query_embedding, k=3)
                        
                        confidence = 1.0 / (1.0 + D[0][0])  # Convert distance to confidence
                        
                        result = {
                            'infraction': audit_chunk,
                            'confidence': confidence,
                            'spec_sections': [spec_chunks[i] for i in I[0]],
                            'distances': D[0].tolist()
                        }
                        results.append(result)
                
                # Display results
                for i, result in enumerate(results):
                    with st.expander(f"Infraction {i+1} - Confidence: {result['confidence']:.2%}"):
                        st.write("**Infraction:**", result['infraction'])
                        
                        st.write("**Matching Spec Sections:**")
                        for j, spec_section in enumerate(result['spec_sections']):
                            st.write(f"{j+1}. {spec_section[:200]}...")
                        
                        # xAI fallback for low confidence
                        if use_xai and result['confidence'] < confidence_threshold and XAI_API_KEY:
                            with st.spinner("Consulting xAI for deeper analysis..."):
                                xai_analysis = call_xai_api(
                                    result['spec_sections'][0],
                                    result['infraction'],
                                    result['confidence']
                                )
                                
                                if xai_analysis:
                                    st.markdown("### 🤖 xAI Enhanced Analysis")
                                    st.markdown(xai_analysis)
                                else:
                                    st.warning("xAI analysis unavailable")
                
                st.success(f"Analysis complete! Found {len(results)} potential infractions")
    else:
        st.info("Please upload both specification book and audit report first")

# Tab 4: AI Analysis (Direct xAI)
with tabs[3]:
    st.header("🤖 Direct AI Analysis")
    st.markdown("Use this for complex queries that need advanced reasoning")
    
    if XAI_API_KEY:
        query = st.text_area("Enter your analysis query", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            use_spec_context = st.checkbox("Include spec book context", value=True)
        with col2:
            use_audit_context = st.checkbox("Include audit context", value=True)
        
        if st.button("🧠 Analyze with xAI", type="primary"):
            context = ""
            
            if use_spec_context and os.path.exists("spec_chunks.pkl"):
                spec_chunks = pickle.load(open("spec_chunks.pkl", "rb"))
                context += f"Specification context:\n{' '.join(spec_chunks[:5])[:5000]}\n\n"
            
            if use_audit_context and os.path.exists("audit_chunks.pkl"):
                audit_chunks = pickle.load(open("audit_chunks.pkl", "rb"))
                context += f"Audit context:\n{' '.join(audit_chunks[:5])[:5000]}\n\n"
            
            full_query = f"{context}\nQuery: {query}"
            
            with st.spinner("Analyzing with xAI..."):
                headers = {
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "grok-beta",
                    "messages": [{"role": "user", "content": full_query}],
                    "max_tokens": 1000,
                    "temperature": 0.2
                }
                
                try:
                    response = requests.post(
                        "https://api.x.ai/v1/chat/completions",
                        headers=headers,
                        json=data,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        result = response.json()["choices"][0]["message"]["content"]
                        st.markdown("### Analysis Result")
                        st.markdown(result)
                    else:
                        st.error(f"API Error: {response.status_code}")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.warning("xAI API key not configured. Set XAI_API_KEY environment variable to enable this feature.")
        st.info("This feature provides advanced reasoning capabilities for complex specification questions.")
