"""
Utility functions for PDF processing and RAG
NEXA Document Intelligence System
"""
import os
import requests
import hashlib
from typing import List, Dict, Any
import PyPDF2
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.schema import Document
from dotenv import load_dotenv
import re

load_dotenv()

class GrokLLM:
    """xAI Grok API wrapper for LangChain compatibility"""
    
    def __init__(self):
        self.api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY or GROK_API_KEY not found in environment")
        self.base_url = "https://api.x.ai/v1/chat/completions"
        self.cache = {}
    
    def __call__(self, prompt: str, use_cache: bool = True) -> str:
        """Call Grok API with caching"""
        # Check cache
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
        if use_cache and prompt_hash in self.cache:
            return self.cache[prompt_hash]
        
        try:
            response = requests.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "grok-beta",  # or "grok-4" when available
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,  # Low for consistency
                    "max_tokens": 1000
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()["choices"][0]["message"]["content"]
                self.cache[prompt_hash] = result
                return result
            else:
                return f"API Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error calling Grok API: {str(e)}"

def extract_text_from_pdf(file_path: str) -> str:
    """Extract full text from PDF with error handling"""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {i+1} ---\n{page_text}"
            return text
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""

def extract_infractions(audit_text: str) -> List[Dict[str, str]]:
    """Extract infractions using improved patterns"""
    infractions = []
    
    # Enhanced patterns for construction infractions
    patterns = [
        r'(?i)(go[-\s]?back[s]?):?\s*([^\n]+)',
        r'(?i)(infraction[s]?|violation[s]?):?\s*([^\n]+)',
        r'(?i)(non[-\s]?complian[ce|t]):?\s*([^\n]+)',
        r'(?i)(defect[s]?|issue[s]?):?\s*([^\n]+)',
        r'(?i)(failed\s+inspection):?\s*([^\n]+)',
        r'(?i)(not\s+per\s+spec[s]?):?\s*([^\n]+)',
        r'(?i)(incorrect\s+installation):?\s*([^\n]+)',
        r'(?i)(inadequate\s+[^:]+):?\s*([^\n]+)',
        r'(?i)(missing\s+[^:]+):?\s*([^\n]+)',
        r'(?i)(improper\s+[^:]+):?\s*([^\n]+)',
    ]
    
    seen = set()
    for pattern in patterns:
        matches = re.findall(pattern, audit_text)
        for match in matches:
            if isinstance(match, tuple):
                type_str = match[0] if len(match) > 0 else "Unknown"
                desc = match[1] if len(match) > 1 else match[0]
            else:
                type_str = "Infraction"
                desc = match
            
            # Avoid duplicates
            desc_hash = hashlib.md5(desc.encode()).hexdigest()
            if desc_hash not in seen:
                seen.add(desc_hash)
                
                # Determine severity based on keywords
                severity = "MEDIUM"
                desc_lower = desc.lower()
                if any(word in desc_lower for word in ["safety", "hazard", "critical", "danger", "fatal"]):
                    severity = "HIGH"
                elif any(word in desc_lower for word in ["minor", "cosmetic", "suggested", "recommended"]):
                    severity = "LOW"
                
                infractions.append({
                    "type": type_str.strip(),
                    "description": desc.strip(),
                    "severity": severity
                })
    
    return infractions

def learn_spec_book(pdf_paths: List[str], index_path: str = "spec_index") -> FAISS:
    """Process and index spec book PDFs with optimized chunking"""
    docs = []
    
    print(f"Processing {len(pdf_paths)} PDF files...")
    
    for path in pdf_paths:
        try:
            # Use PyPDFLoader for better document structure
            loader = PyPDFLoader(path)
            loaded_docs = loader.load()
            
            # Add metadata
            for doc in loaded_docs:
                doc.metadata["source_file"] = os.path.basename(path)
                doc.metadata["doc_type"] = "specification"
            
            docs.extend(loaded_docs)
        except Exception as e:
            print(f"Error loading {path}: {e}")
            # Fallback to direct text extraction
            text = extract_text_from_pdf(path)
            if text:
                doc = Document(
                    page_content=text,
                    metadata={"source_file": os.path.basename(path), "doc_type": "specification"}
                )
                docs.append(doc)
    
    if not docs:
        raise ValueError("No documents could be loaded from the provided PDFs")
    
    # Optimized chunking for construction specs
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,  # Larger for comprehensive context
        chunk_overlap=300,  # More overlap for continuity
        separators=["\n\n\n", "\n\n", "\n", ".", " "],
        length_function=len
    )
    
    chunks = splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks from {len(docs)} documents")
    
    # Create embeddings and index
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    # Save index
    vectorstore.save_local(index_path)
    print(f"Index saved to {index_path}")
    
    return vectorstore

def analyze_audit(audit_path: str, vectorstore: FAISS, use_grok: bool = True) -> List[Dict[str, Any]]:
    """Analyze audit against spec book with enhanced analysis"""
    
    # Extract audit text
    audit_text = extract_text_from_pdf(audit_path)
    
    # Extract infractions with improved patterns
    infractions = extract_infractions(audit_text)
    
    if not infractions:
        return [{"infraction": "None found", "analysis": "No infractions detected in the audit document"}]
    
    print(f"Found {len(infractions)} infractions")
    
    # Initialize LLM
    if use_grok:
        try:
            llm = GrokLLM()
        except ValueError as e:
            print(f"Grok API not available: {e}")
            use_grok = False
    
    # Create QA chain if LLM available
    if use_grok:
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}  # Retrieve more for better context
            )
        )
    
    results = []
    for inf in infractions:
        infraction_str = f"{inf['type']}: {inf['description']}"
        
        if use_grok:
            # Enhanced prompt for better analysis
            query = f"""
            Analyze this construction audit infraction against the specification book:
            
            INFRACTION: {infraction_str}
            SEVERITY: {inf['severity']}
            
            Please determine:
            1. Is this a valid infraction according to specifications? (TRUE/FALSE)
            2. Can this infraction be appealed/repealed? (YES/NO)
            3. Confidence level (0-100%)
            4. If appealable, list specific reasons from the specifications
            5. Quote the relevant specification section if found
            
            Format your response as:
            VALID: [TRUE/FALSE]
            APPEALABLE: [YES/NO]
            CONFIDENCE: [XX%]
            SPECIFICATION: [Quote or section reference]
            REASONING: [Detailed explanation]
            """
            
            response = qa_chain.run(query)
        else:
            # Fallback to similarity search without LLM
            relevant_docs = vectorstore.similarity_search(infraction_str, k=3)
            
            if relevant_docs:
                best_score = relevant_docs[0].metadata.get('score', 0.5)
                
                if best_score > 0.7:
                    response = f"""
                    VALID: TRUE
                    APPEALABLE: NO
                    CONFIDENCE: {int(best_score * 100)}%
                    SPECIFICATION: Found in {relevant_docs[0].metadata.get('source_file', 'specification')}
                    REASONING: Strong match with specifications
                    """
                else:
                    response = f"""
                    VALID: UNCERTAIN
                    APPEALABLE: YES
                    CONFIDENCE: {int(best_score * 100)}%
                    SPECIFICATION: Weak match in {relevant_docs[0].metadata.get('source_file', 'specification')}
                    REASONING: Low correlation with specifications, manual review recommended
                    """
            else:
                response = """
                VALID: UNKNOWN
                APPEALABLE: POSSIBLY
                CONFIDENCE: 0%
                SPECIFICATION: No matching specification found
                REASONING: Unable to find relevant specification for this infraction
                """
        
        results.append({
            "infraction": infraction_str,
            "severity": inf['severity'],
            "analysis": response
        })
    
    return results

def validate_environment() -> Dict[str, bool]:
    """Validate environment setup"""
    checks = {
        "xai_api_key": bool(os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")),
        "openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "data_directory": os.path.exists("data"),
        "spec_index": os.path.exists("spec_index")
    }
    
    # Create data directory if missing
    if not checks["data_directory"]:
        os.makedirs("data", exist_ok=True)
        checks["data_directory"] = True
    
    return checks
