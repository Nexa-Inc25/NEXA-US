"""
AI Document Analyzer Tool - Simplified Version
Using langchain-xai for direct Grok integration
"""
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv

# Try to import ChatXAI - if not available, provide instructions
try:
    from langchain_xai import ChatXAI
    XAI_AVAILABLE = True
except ImportError:
    XAI_AVAILABLE = False
    st.error("langchain-xai not installed. Run: pip install langchain-xai")

# Load environment variables
load_dotenv()

# Initialize session state
if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = None
if 'spec_text' not in st.session_state:
    st.session_state.spec_text = ""

# Page config
st.set_page_config(
    page_title="AI Document Analyzer",
    layout="wide"
)

st.title("AI Document Analyzer Tool")
st.markdown("**Simplified version with direct xAI/Grok integration**")

# Input for xAI API Key
col1, col2 = st.columns([2, 1])
with col1:
    # Check if key exists in environment first
    existing_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if existing_key:
        st.success("API Key detected from environment")
        xai_api_key = existing_key
    else:
        xai_api_key = st.text_input(
            "Enter your xAI API Key (from https://console.x.ai/)", 
            type="password",
            help="Your API key will be used securely for this session only"
        )

with col2:
    if st.button("Test API Connection"):
        if xai_api_key and XAI_AVAILABLE:
            try:
                os.environ["XAI_API_KEY"] = xai_api_key
                test_llm = ChatXAI(model="grok-beta", temperature=0)
                st.success("API connection successful!")
            except Exception as e:
                st.error(f"Connection failed: {str(e)}")
        else:
            st.warning("Please enter API key first")

if xai_api_key:
    os.environ["XAI_API_KEY"] = xai_api_key

# Step 1: Upload and Learn Spec Book
st.header("Step 1: Upload Spec Book (PDFs)")
st.markdown("Upload your specification documents (PG&E, SCE, SDG&E standards)")

spec_files = st.file_uploader(
    "Upload spec book files (multiple allowed)", 
    type="pdf", 
    accept_multiple_files=True,
    help="Upload documents like transformer specs, installation standards, etc."
)

if spec_files:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"Ready to process {len(spec_files)} specification files")
    with col2:
        if st.button("Learn Spec Book", type="primary"):
            with st.spinner("Extracting text from PDFs..."):
                spec_text = ""
                for file in spec_files:
                    try:
                        reader = PdfReader(file)
                        for page in reader.pages:
                            spec_text += page.extract_text() + "\n"
                    except Exception as e:
                        st.warning(f"Error reading {file.name}: {str(e)}")
                
                st.session_state.spec_text = spec_text
                st.success(f"Extracted {len(spec_text):,} characters from spec books")
            
            # Chunk and embed
            with st.spinner("Creating chunks and embeddings..."):
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000, 
                    chunk_overlap=200,
                    separators=["\n\n", "\n", ".", " "]
                )
                chunks = text_splitter.split_text(spec_text)
                st.info(f"Created {len(chunks)} chunks")
            
            with st.spinner("Building FAISS index with local embeddings..."):
                embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={'device': 'cpu'}
                )
                st.session_state.vectorstore = FAISS.from_texts(chunks, embeddings)
            
            st.success("Spec book learned! Ready for audit analysis.")
            
            # Show statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Documents", len(spec_files))
            with col2:
                st.metric("Chunks Created", len(chunks))
            with col3:
                st.metric("Avg Chunk Size", f"{len(spec_text)//len(chunks)} chars")

# Step 2: Upload Audit Document and Analyze
st.header("Step 2: Upload Audit Document")
st.markdown("Upload your quality assurance audit report containing infractions")

audit_file = st.file_uploader(
    "Upload quality assurance audit PDF", 
    type="pdf",
    help="Document should contain 'go-back' items, infractions, violations, etc."
)

if audit_file and st.session_state.vectorstore:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"Ready to analyze {audit_file.name}")
    with col2:
        if st.button("Analyze Audit", type="primary", disabled=not xai_api_key):
            if not XAI_AVAILABLE:
                st.error("langchain-xai not installed. Run: pip install langchain-xai")
                st.stop()
            
            # Extract audit text
            with st.spinner("Extracting audit text..."):
                reader = PdfReader(audit_file)
                audit_text = ""
                for page in reader.pages:
                    audit_text += page.extract_text() + "\n"
                st.success(f"Extracted {len(audit_text):,} characters from audit")
            
            # Extract infractions
            with st.spinner("Finding infractions..."):
                # Enhanced keyword list for construction domain
                keywords = [
                    "go-back", "go back", "goback",
                    "infraction", "violation", "issue",
                    "non-compliance", "non-compliant", "noncompliant",
                    "defect", "deficiency", "discrepancy",
                    "failed", "incorrect", "improper",
                    "missing", "inadequate", "insufficient"
                ]
                
                infractions = []
                for line in audit_text.split("\n"):
                    if any(kw in line.lower() for kw in keywords):
                        line = line.strip()
                        if len(line) > 10:  # Filter out very short lines
                            infractions.append(line)
                
                # Remove duplicates while preserving order
                seen = set()
                unique_infractions = []
                for inf in infractions:
                    if inf not in seen:
                        seen.add(inf)
                        unique_infractions.append(inf)
                
                infractions = unique_infractions[:20]  # Limit to top 20 to avoid API overuse
            
            if not infractions:
                st.warning("No potential 'go-back' infractions found in audit.")
                st.info("Make sure your audit contains keywords like: go-back, infraction, violation, etc.")
            else:
                st.info(f"Found {len(infractions)} potential infractions")
                
                # Setup LLM and QA chain
                with st.spinner("Initializing xAI/Grok..."):
                    try:
                        llm = ChatXAI(
                            model="grok-beta",  # or "grok-2" if available
                            temperature=0.1,
                            max_tokens=500
                        )
                    except Exception as e:
                        st.error(f"Failed to initialize Grok: {str(e)}")
                        st.info("Check your API key and subscription at https://console.x.ai/")
                        st.stop()
                    
                    # Enhanced prompt template
                    prompt_template = """You are a construction specification expert analyzing audit infractions.
                    
                    Using the specification context provided, analyze this infraction:
                    "{infraction}"
                    
                    Determine:
                    1. Is this a VALID infraction according to specifications? (TRUE/FALSE)
                    2. Can this be APPEALED/REPEALED? (YES/NO)
                    3. CONFIDENCE level (HIGH/MEDIUM/LOW) based on spec match
                    4. If appealable, list SPECIFIC REASONS from the specifications
                    5. Quote the relevant SPECIFICATION SECTION if found
                    
                    Context from specifications:
                    {context}
                    
                    Format your answer as:
                    VALID: [TRUE/FALSE]
                    APPEALABLE: [YES/NO]
                    CONFIDENCE: [HIGH/MEDIUM/LOW]
                    SPECIFICATION: [Quote or section reference]
                    REASONING: [Your detailed analysis]
                    """
                    
                    PROMPT = PromptTemplate(
                        template=prompt_template, 
                        input_variables=["infraction", "context"]
                    )
                    
                    qa_chain = RetrievalQA.from_chain_type(
                        llm=llm,
                        chain_type="stuff",
                        retriever=st.session_state.vectorstore.as_retriever(
                            search_kwargs={"k": 5}  # Retrieve top 5 relevant chunks
                        ),
                        chain_type_kwargs={"prompt": PROMPT}
                    )
                
                # Analyze each infraction
                st.header("Analysis Results")
                
                for i, infraction in enumerate(infractions, 1):
                    with st.expander(f"Infraction {i}: {infraction[:80]}...", expanded=(i==1)):
                        st.write(f"**Full Text:** {infraction}")
                        
                        with st.spinner(f"Analyzing infraction {i}/{len(infractions)}..."):
                            try:
                                # Run analysis
                                result = qa_chain.run(infraction)
                                
                                # Display structured results
                                st.markdown("### Analysis")
                                st.text(result)
                                
                                # Parse and highlight key findings
                                if "VALID: TRUE" in result:
                                    st.error("Valid Infraction - Requires Correction")
                                elif "VALID: FALSE" in result:
                                    st.success("Invalid Infraction - Can Be Disputed")
                                
                                if "APPEALABLE: YES" in result:
                                    st.info("This infraction can be appealed")
                                
                                if "CONFIDENCE: HIGH" in result:
                                    st.metric("Confidence", "HIGH", delta="Strong match with specs")
                                elif "CONFIDENCE: MEDIUM" in result:
                                    st.metric("Confidence", "MEDIUM", delta="Partial match")
                                elif "CONFIDENCE: LOW" in result:
                                    st.metric("Confidence", "LOW", delta="Weak correlation")
                                    
                            except Exception as e:
                                st.error(f"Analysis failed: {str(e)}")
                                st.info("This might be due to API limits or connection issues")
                        
                        st.divider()

elif audit_file and not st.session_state.vectorstore:
    st.warning("Please learn the spec book first before analyzing audit")
elif not audit_file and st.session_state.vectorstore:
    st.info("Spec book loaded. Now upload an audit document to analyze")

# Footer with instructions
st.markdown("---")
with st.expander("Deployment Instructions"):
    st.markdown("""
    ### Deploy on Render.com
    
    1. **Create requirements.txt:**
    ```
    streamlit
    pypdf2
    langchain
    langchain-community
    langchain-xai
    faiss-cpu
    sentence-transformers
    python-dotenv
    ```
    
    2. **Push to GitHub:**
    ```bash
    git add app_simple.py requirements.txt
    git commit -m "Simplified AI analyzer"
    git push
    ```
    
    3. **On Render.com:**
    - Create new Web Service
    - Connect GitHub repo
    - Build command: `pip install -r requirements.txt`
    - Start command: `streamlit run app_simple.py --server.port $PORT`
    - Add environment variable: `XAI_API_KEY=your_key`
    
    4. **Testing locally:**
    ```bash
    streamlit run app_simple.py
    ```
    """)

with st.expander("Tips & Troubleshooting"):
    st.markdown("""
    ### Common Issues:
    
    **No infractions found:**
    - Check that your audit contains keywords: go-back, violation, infraction
    - Try adding more keywords to the detection list
    
    **API errors:**
    - Verify your xAI API key at https://console.x.ai/
    - Check your subscription tier (grok-beta vs grok-2)
    - Monitor rate limits
    
    **Slow performance:**
    - Reduce chunk size (currently 1000 chars)
    - Limit number of infractions analyzed
    - Use caching for repeated analyses
    
    **Better accuracy:**
    - Upload more comprehensive spec documents
    - Increase retrieval k value (currently 5)
    - Fine-tune the prompt template
    """)

# Show current configuration
with st.sidebar:
    st.header("Current Configuration")
    st.write(f"**Vectorstore:** {'Loaded' if st.session_state.vectorstore else 'Not loaded'}")
    st.write(f"**Spec Text:** {len(st.session_state.spec_text):,} chars")
    st.write(f"**API Key:** {'Configured' if xai_api_key else 'Not set'}")
    st.write(f"**langchain-xai:** {'Available' if XAI_AVAILABLE else 'Not installed'}")
    
    if not XAI_AVAILABLE:
        st.error("Install langchain-xai:")
        st.code("pip install langchain-xai")
