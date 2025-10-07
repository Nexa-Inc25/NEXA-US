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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache model to load once
@st.cache_resource
def load_model():
    logger.info("Loading Sentence-BERT model...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda' if torch.cuda.is_available() else 'cpu')
    return model

# Initialize model
model = load_model()

# Function to extract text from PDF with OCR fallback
def extract_text_from_pdf(pdf_file):
    logger.info("Extracting text from PDF...")
    text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    logger.info("No text found on page, attempting OCR...")
                    img = page.to_image(resolution=300).original
                    ocr_text = pytesseract.image_to_string(img, config='--psm 6')
                    text += ocr_text + "\n"
        if not text.strip():
            logger.error("No text extracted from PDF, even with OCR.")
            return None
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        st.error(f"Failed to extract text from PDF: {str(e)}")
        return None
    logger.info(f"Extracted text length: {len(text)} characters")
    return text

# Function to chunk text
def chunk_text(text, max_tokens=512):
    logger.info("Chunking text...")
    if not text:
        return []
    sentences = text.split("\n")
    chunks = []
    current_chunk = []
    current_length = 0
    for sentence in sentences:
        if not sentence.strip():
            continue
        sentence_length = len(sentence.split())
        if current_length + sentence_length > max_tokens:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_length = sentence_length
        else:
            current_chunk.append(sentence)
            current_length += sentence_length
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    if len(chunks) == 0:
        logger.warning("No valid chunks created. Adding raw text as single chunk.")
        chunks = [text] if text.strip() else []
    logger.info(f"Created {len(chunks)} chunks")
    return chunks

# Function to generate embeddings
def generate_embeddings(chunks, batch_size=16):
    logger.info(f"Generating embeddings for {len(chunks)} chunks...")
    if not chunks:
        return np.array([])
    embeddings = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        start = time.time()
        batch_embeddings = model.encode(batch, convert_to_numpy=True, batch_size=batch_size, show_progress_bar=True)
        embeddings.append(batch_embeddings)
        logger.info(f"Batch {i//batch_size + 1} processed in {time.time() - start:.2f} seconds")
    return np.vstack(embeddings) if embeddings else np.array([])

# Function to create FAISS index with fallback for small datasets
def create_faiss_index(embeddings, index_path="faiss_index.bin", min_points=10):
    logger.info("Creating FAISS index...")
    if embeddings.shape[0] == 0:
        logger.error("No embeddings to index")
        return None
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)  # Use IndexFlatL2 to avoid clustering
    index.add(embeddings)
    faiss.write_index(index, index_path)
    logger.info(f"FAISS index saved to {index_path} with {embeddings.shape[0]} embeddings")
    return index

# Function to load FAISS index
def load_faiss_index(index_path="faiss_index.bin"):
    if os.path.exists(index_path):
        logger.info(f"Loading FAISS index from {index_path}...")
        return faiss.read_index(index_path)
    return None

# Streamlit app
st.title("AI Document Analyzer")
tabs = st.tabs(["Learn Specification", "Analyze Audit", "Results"])

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
                    embeddings = generate_embeddings(chunks)
                    if embeddings.shape[0] == 0:
                        st.error("Failed to generate embeddings from the specification book.")
                    else:
                        index = create_faiss_index(embeddings)
                        if index is None:
                            st.error("Failed to create FAISS index. Please try a different PDF.")
                        else:
                            with open("spec_chunks.pkl", "wb") as f:
                                pickle.dump(chunks, f)
                            st.success(f"Specification book processed in {time.time() - start:.2f} seconds!")
                            logger.info(f"Spec book processed in {time.time() - start:.2f} seconds")

# Tab 2: Analyze Audit
with tabs[1]:
    st.header("Upload Audit Report")
    audit_file = st.file_uploader("Choose an audit report PDF", type="pdf")
    if audit_file:
        with st.spinner("Analyzing audit report..."):
            start = time.time()
            index = load_faiss_index()
            if index is None:
                st.error("Please process a specification book first.")
            else:
                audit_text = extract_text_from_pdf(audit_file)
                if audit_text is None:
                    st.error("Cannot process audit report. Please check the PDF content.")
                else:
                    infractions = [line for line in audit_text.split("\n") if line.startswith("Infraction")]
                    if not infractions:
                        st.error("No infractions found in the audit report.")
                    else:
                        infraction_embeddings = generate_embeddings(infractions)
                        if infraction_embeddings.shape[0] == 0:
                            st.error("Failed to generate embeddings for infractions.")
                        else:
                            D, I = index.search(infraction_embeddings, k=1)
                            with open("spec_chunks.pkl", "rb") as f:
                                chunks = pickle.load(f)
                            results = []
                            for i, (dist, idx) in enumerate(zip(D, I)):
                                confidence = 1 / (1 + dist[0])  # Convert distance to confidence
                                status = confidence > 0.85 and any(keyword in chunks[idx[0]].lower() for keyword in ["require", "must", "shall"])
                                results.append({
                                    "infraction": infractions[i],
                                    "status": status,
                                    "confidence": confidence,
                                    "reason": chunks[idx[0]]
                                })
                            st.session_state.results = results
                            st.success(f"Audit analysis completed in {time.time() - start:.2f} seconds!")
                            logger.info(f"Audit analysis completed in {time.time() - start:.2f} seconds")

# Tab 3: Results
with tabs[2]:
    st.header("Analysis Results")
    if "results" in st.session_state:
        for result in st.session_state.results:
            status = "Valid" if result["status"] else "Repealable"
            st.write(f"**{result['infraction']}**")
            st.write(f"- Status: {status}")
            st.write(f"- Confidence: {result['confidence']:.2f}")
            st.write(f"- Reason: {result['reason']}")
    else:
        st.info("No results available. Please analyze an audit report.")
