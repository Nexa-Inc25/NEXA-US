"""
AI Document Analyzing Tool with Optimized Chunking
Enhanced for construction specification documents
"""
import streamlit as st
import PyPDF2
from io import BytesIO
import requests
import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from optimized_chunking import ConstructionSpecChunker, retrieve_with_context

# Set your xAI API key as an environment variable
XAI_API_KEY = os.environ.get('XAI_API_KEY')

st.set_page_config(
    page_title="NEXA Document Intelligence",
    page_icon="🚧",
    layout="wide"
)

st.title("🚧 AI Document Analyzing Tool")
st.markdown("**Optimized chunking for construction specifications**")

# Initialize chunker
@st.cache_resource
def get_chunker():
    return ConstructionSpecChunker()

@st.cache_resource
def get_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

chunker = get_chunker()
model = get_model()

# Sidebar for chunking configuration
st.sidebar.header("⚙️ Chunking Configuration")
chunk_strategy = st.sidebar.selectbox(
    "Chunking Strategy",
    ["Smart (Section-Aware)", "Fixed Size", "Paragraph-Based"]
)

if chunk_strategy == "Smart (Section-Aware)":
    optimal_chunk_size = st.sidebar.slider(
        "Optimal Chunk Size",
        min_value=500,
        max_value=2000,
        value=1200,
        step=100
    )
    chunker.OPTIMAL_CHUNK_SIZE = optimal_chunk_size
    
    overlap_ratio = st.sidebar.slider(
        "Overlap Ratio",
        min_value=0.05,
        max_value=0.30,
        value=0.15,
        step=0.05
    )
    chunker.OVERLAP_RATIO = overlap_ratio

retrieval_k = st.sidebar.slider(
    "Number of chunks to retrieve",
    min_value=3,
    max_value=15,
    value=5
)

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📚 Upload Spec Book PDFs")
    spec_files = st.file_uploader(
        "Upload spec book PDFs (can be multiple)",
        type="pdf",
        accept_multiple_files=True
    )

with col2:
    st.header("📋 Upload Audit Document")
    audit_file = st.file_uploader(
        "Upload the audit document",
        type="pdf"
    )

# Process specifications
spec_text = ""
chunks = []
chunk_metadata = []
index = None

if spec_files:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, spec_file in enumerate(spec_files):
        status_text.text(f"Processing {spec_file.name}...")
        pdf_reader = PyPDF2.PdfReader(BytesIO(spec_file.read()))
        
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                spec_text += f"\n--- Page {page_num + 1} from {spec_file.name} ---\n"
                spec_text += page_text + "\n"
        
        progress_bar.progress((i + 1) / len(spec_files))
    
    status_text.text("Creating optimized chunks...")
    
    # Use optimized chunking
    if chunk_strategy == "Smart (Section-Aware)":
        chunk_objects = chunker.chunk_text_smart(spec_text)
        chunks = [c['text'] for c in chunk_objects]
        chunk_metadata = chunk_objects
    else:
        # Fallback to simple chunking
        chunks = spec_text.split('\n\n')
        chunks = [c.strip() for c in chunks if len(c.strip()) > 50]
        chunk_metadata = [{'text': c, 'id': i} for i, c in enumerate(chunks)]
    
    st.success(f"✅ Spec books loaded: {len(spec_text):,} characters")
    
    # Display chunking statistics
    if chunk_metadata:
        stats = chunker.calculate_chunk_statistics(chunk_metadata)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Chunks", stats['total_chunks'])
        with col2:
            st.metric("Avg Size", f"{stats['avg_size']:.0f} chars")
        with col3:
            st.metric("Complete Sections", stats.get('complete_sections', 'N/A'))
        with col4:
            st.metric("Partial Sections", stats.get('partial_sections', 'N/A'))
    
    # Create FAISS index
    status_text.text("Creating FAISS index...")
    try:
        embeddings = model.encode(chunks, show_progress_bar=True)
        embeddings = np.array(embeddings).astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        index.add(embeddings)
        
        st.success(f"✅ Indexed {len(chunks)} chunks with FAISS")
        
        # Show chunk distribution
        with st.expander("📊 Chunk Size Distribution"):
            import matplotlib.pyplot as plt
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
            
            # Histogram
            sizes = [len(c) for c in chunks]
            ax1.hist(sizes, bins=20, edgecolor='black')
            ax1.axvline(chunker.OPTIMAL_CHUNK_SIZE, color='r', linestyle='--', label='Optimal Size')
            ax1.set_xlabel('Chunk Size (characters)')
            ax1.set_ylabel('Count')
            ax1.set_title('Chunk Size Distribution')
            ax1.legend()
            
            # Box plot
            ax2.boxplot(sizes)
            ax2.set_ylabel('Chunk Size (characters)')
            ax2.set_title('Chunk Size Statistics')
            
            st.pyplot(fig)
        
    except Exception as e:
        st.error(f"Error creating FAISS index: {e}")
        status_text.text("")
    
    progress_bar.empty()
    status_text.empty()

# Process audit and analyze
if audit_file and chunks and index:
    with st.spinner("Processing audit document..."):
        pdf_reader = PyPDF2.PdfReader(BytesIO(audit_file.read()))
        audit_text = ""
        for page in pdf_reader.pages:
            audit_text += page.extract_text() + "\n"
    
    st.success(f"✅ Audit document loaded: {len(audit_text):,} characters")
    
    # Analyze button
    if st.button("🔍 Analyze Infractions", type="primary"):
        # Extract infractions
        with st.spinner("Extracting infractions with AI..."):
            headers = {
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            extract_prompt = f"""
            You are an expert in extracting infractions from construction audit documents.
            Identify ALL infractions, violations, go-back items, and non-compliances.
            
            Focus on:
            - Equipment violations (poles, transformers, cables)
            - Installation issues (spacing, mounting, grounding)
            - Material non-compliance (grades, specifications)
            - Testing failures (voltage, insulation, load)
            - Safety violations
            
            Output in JSON format:
            {{
              "infractions": [
                {{
                  "description": "Full description",
                  "code": "Code or ID",
                  "type": "EQUIPMENT/INSTALLATION/MATERIAL/TESTING/SAFETY",
                  "severity": "HIGH/MEDIUM/LOW",
                  "location": "Location if mentioned"
                }}
              ]
            }}
            
            Audit text (first 15000 chars):
            {audit_text[:15000]}
            """
            
            data = {
                "model": "grok-beta",
                "messages": [{"role": "user", "content": extract_prompt}],
                "temperature": 0.1
            }
            
            try:
                response = requests.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                result_text = response.json()["choices"][0]["message"]["content"]
                
                # Parse JSON from response
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    extracted = json.loads(json_match.group())
                else:
                    extracted = json.loads(result_text)
                
                infractions = extracted.get('infractions', [])
                
                if not infractions:
                    st.info("No infractions found in the audit document.")
                else:
                    st.subheader(f"🚨 Analyzing {len(infractions)} Infractions")
                    
                    # Create tabs for different views
                    tab1, tab2, tab3 = st.tabs(["Detailed Analysis", "Summary", "Export"])
                    
                    with tab1:
                        for i, inf in enumerate(infractions, 1):
                            infraction_desc = inf.get('description', '')
                            
                            # Determine optimal K based on infraction type
                            infraction_type = inf.get('type', 'default').lower()
                            optimal_k = chunker.get_optimal_k_for_retrieval(infraction_type)
                            
                            # Severity icon
                            severity = inf.get('severity', 'MEDIUM')
                            severity_icon = {
                                'HIGH': '🔴',
                                'MEDIUM': '🟡',
                                'LOW': '🟢'
                            }.get(severity, '⚪')
                            
                            with st.expander(f"{severity_icon} Infraction {i}: {infraction_desc[:60]}..."):
                                # Infraction details
                                col1, col2 = st.columns([3, 1])
                                
                                with col1:
                                    st.write(f"**Description:** {infraction_desc}")
                                    if inf.get('code'):
                                        st.write(f"**Code:** {inf['code']}")
                                    if inf.get('location'):
                                        st.write(f"**Location:** {inf['location']}")
                                
                                with col2:
                                    st.write(f"**Type:** {inf.get('type', 'Unknown')}")
                                    st.write(f"**Severity:** {severity}")
                                
                                # Retrieve relevant chunks with enhanced context
                                with st.spinner(f"Searching {optimal_k} relevant spec sections..."):
                                    relevant_results = retrieve_with_context(
                                        infraction_desc,
                                        chunk_metadata,
                                        index,
                                        model,
                                        k=optimal_k
                                    )
                                
                                # Display relevant chunks
                                if relevant_results:
                                    st.markdown("### 📖 Relevant Specifications")
                                    for j, result in enumerate(relevant_results, 1):
                                        chunk = result['chunk']
                                        relevance = result['relevance']
                                        
                                        # Color code by relevance
                                        if relevance > 0.8:
                                            relevance_color = "🟢"
                                        elif relevance > 0.6:
                                            relevance_color = "🟡"
                                        else:
                                            relevance_color = "🔴"
                                        
                                        st.write(f"{relevance_color} **Section {j}** (Relevance: {relevance:.1%})")
                                        if 'header' in chunk:
                                            st.write(f"*{chunk['header']}*")
                                        st.write(chunk['text'][:300] + "...")
                                
                                # Analyze with xAI
                                relevant_text = "\n\n".join([
                                    r['chunk']['text'] for r in relevant_results
                                ])
                                
                                analyze_prompt = f"""
                                Relevant specification sections:
                                {relevant_text[:10000]}
                                
                                Infraction: {infraction_desc}
                                Type: {inf.get('type', 'Unknown')}
                                
                                Analyze if this infraction is valid or appealable:
                                1. VERDICT: Valid or Appealable
                                2. CONFIDENCE: High/Medium/Low
                                3. SPEC REFERENCE: Quote exact specification
                                4. REASONING: Clear explanation
                                5. ACTION: Recommended action
                                """
                                
                                data['messages'] = [{"role": "user", "content": analyze_prompt}]
                                
                                with st.spinner("Analyzing with AI..."):
                                    response = requests.post(
                                        "https://api.x.ai/v1/chat/completions",
                                        headers=headers,
                                        json=data
                                    )
                                    analysis = response.json()["choices"][0]["message"]["content"]
                                
                                st.markdown("### 🔬 Analysis Result")
                                st.text(analysis)
                    
                    with tab2:
                        # Summary statistics
                        st.markdown("### 📊 Infraction Summary")
                        
                        # Group by type
                        type_counts = {}
                        severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
                        
                        for inf in infractions:
                            inf_type = inf.get('type', 'Unknown')
                            type_counts[inf_type] = type_counts.get(inf_type, 0) + 1
                            
                            severity = inf.get('severity', 'MEDIUM')
                            severity_counts[severity] = severity_counts.get(severity, 0) + 1
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**By Type:**")
                            for type_name, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                                st.write(f"- {type_name}: {count}")
                        
                        with col2:
                            st.markdown("**By Severity:**")
                            for sev, count in severity_counts.items():
                                icon = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}[sev]
                                st.write(f"{icon} {sev}: {count}")
                    
                    with tab3:
                        # Export functionality
                        st.markdown("### 📥 Export Results")
                        
                        export_data = {
                            'timestamp': str(st.session_state.get('analysis_timestamp', '')),
                            'spec_files': [f.name for f in spec_files],
                            'audit_file': audit_file.name,
                            'infractions': infractions,
                            'chunking_stats': chunker.calculate_chunk_statistics(chunk_metadata)
                        }
                        
                        st.download_button(
                            label="Download JSON Report",
                            data=json.dumps(export_data, indent=2),
                            file_name="infraction_analysis.json",
                            mime="application/json"
                        )
            
            except Exception as e:
                st.error(f"Error in analysis: {str(e)}")

else:
    if not spec_files:
        st.info("👈 Please upload specification book PDFs")
    elif not audit_file:
        st.info("👈 Please upload an audit document")
    elif not index:
        st.warning("⚠️ Spec book indexing incomplete")

# Footer with optimization tips
st.markdown("---")
with st.expander("🎯 Chunking Optimization Tips"):
    st.markdown("""
    ### Optimal Settings by Document Type:
    
    **PG&E/SCE/SDG&E Specifications:**
    - Chunk Size: 1200-1500 chars
    - Overlap: 15-20%
    - Strategy: Section-aware
    - Retrieval: 5-8 chunks
    
    **Audit Documents:**
    - Chunk Size: 800-1000 chars
    - Overlap: 10%
    - Strategy: Paragraph-based
    - Retrieval: 8-10 chunks
    
    **Why These Settings Work:**
    - Construction specs have clear section boundaries
    - Technical requirements often span multiple paragraphs
    - Measurements and standards need full context
    - Overlapping preserves continuity across chunks
    """)

# Check API key
if not XAI_API_KEY:
    st.error("⚠️ XAI_API_KEY not set. Please configure in environment variables.")
    st.info("Run: `export XAI_API_KEY=your_key_here` or set in .env file")
