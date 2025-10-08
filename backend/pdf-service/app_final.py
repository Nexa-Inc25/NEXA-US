"""
AI Document Analyzer - Main Streamlit Application
NEXA Document Intelligence System
Following the complete specification guide
"""
import streamlit as st
import os
import shutil
from pathlib import Path
from datetime import datetime
import json
from utils import (
    learn_spec_book, 
    analyze_audit, 
    extract_text_from_pdf,
    extract_infractions,
    validate_environment,
    GrokLLM
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Page configuration
st.set_page_config(
    page_title="AI Document Analyzer",
    layout="wide"
)

st.title("AI Document Analyzer")
st.markdown("**Analyzes construction audit documents against PG&E/SCE/SDG&E specifications**")

# Initialize session state
if 'index_loaded' not in st.session_state:
    st.session_state.index_loaded = False
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = []
if 'spec_files_processed' not in st.session_state:
    st.session_state.spec_files_processed = []

# Create data directory
os.makedirs("data", exist_ok=True)

# Environment validation
with st.sidebar:
    st.header("System Status")
    
    env_checks = validate_environment()
    
    if env_checks['xai_api_key']:
        st.success("xAI/Grok API Connected")
    else:
        st.warning("xAI API Key Missing")
        st.info("Set XAI_API_KEY or GROK_API_KEY in .env file")
    
    if env_checks['spec_index']:
        st.success("Spec Index Found")
        st.session_state.index_loaded = True
    else:
        st.info("No spec index yet")
    
    st.markdown("---")
    st.markdown("### Statistics")
    st.metric("Specs Processed", len(st.session_state.spec_files_processed))
    st.metric("Infractions Analyzed", len(st.session_state.analysis_results))
    
    st.markdown("---")
    with st.expander("Deployment Guide"):
        st.markdown("""
        ### Deploy on Render.com
        
        1. **Create .env file:**
        ```
        XAI_API_KEY=your_key_here
        # or GROK_API_KEY=your_key_here
        ```
        
        2. **Push to GitHub:**
        ```bash
        git add .
        git commit -m "AI Document Analyzer"
        git push origin main
        ```
        
        3. **On Render.com:**
        - New > Web Service
        - Connect GitHub repo
        - Runtime: Python 3
        - Build: `pip install -r requirements.txt`
        - Start: `streamlit run app_final.py --server.port $PORT`
        - Add environment variable: XAI_API_KEY
        
        4. **Access at:**
        `your-app.onrender.com`
        """)

# Main content area
tab1, tab2, tab3 = st.tabs(["Learn Spec Book", "Analyze Audit", "Results"])

# Tab 1: Upload and Learn Spec Book
with tab1:
    st.header("Step 1: Upload Specification Documents")
    st.markdown("""
    Upload your specification PDFs (PG&E transformer docs, SCE standards, SDG&E requirements, etc.)
    The system will extract text, chunk it, create embeddings, and build a searchable index.
    """)
    
    spec_files = st.file_uploader(
        "Upload spec PDFs",
        type="pdf",
        accept_multiple_files=True,
        help="Upload documents like '045786 open wye to zig-zag.pdf', transformer specs, etc."
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("Learn Spec Book", type="primary", disabled=not spec_files):
            if spec_files:
                pdf_paths = []
                
                # Save uploaded files
                with st.spinner("Saving uploaded files..."):
                    for file in spec_files:
                        path = f"data/{file.name}"
                        with open(path, "wb") as f:
                            f.write(file.getbuffer())
                        pdf_paths.append(path)
                        st.session_state.spec_files_processed.append(file.name)
                
                # Process and index
                with st.spinner("Processing and indexing spec book... This may take a few minutes."):
                    try:
                        vectorstore = learn_spec_book(pdf_paths)
                        st.session_state.index_loaded = True
                        st.success(f"Spec book learned! Indexed {len(spec_files)} documents.")
                        
                        # Show statistics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Documents", len(spec_files))
                        with col2:
                            total_size = sum(os.path.getsize(p) for p in pdf_paths)
                            st.metric("Total Size", f"{total_size / 1024 / 1024:.1f} MB")
                        with col3:
                            st.metric("Status", "Ready")
                        
                        # Clean up temp files (optional)
                        if st.checkbox("Delete temporary files after indexing"):
                            for path in pdf_paths:
                                os.remove(path)
                            st.info("Temporary files deleted. Index retained.")
                    
                    except Exception as e:
                        st.error(f"Error processing spec book: {str(e)}")
    
    with col2:
        if st.button("Clear Index"):
            if os.path.exists("spec_index"):
                shutil.rmtree("spec_index")
                st.session_state.index_loaded = False
                st.session_state.spec_files_processed = []
                st.info("Index cleared")

# Tab 2: Upload and Analyze Audit
with tab2:
    st.header("Step 2: Upload Audit Document")
    st.markdown("""
    Upload your quality audit or inspection report PDF.
    The system will extract infractions (go-back items, violations, etc.) and analyze them against the spec book.
    """)
    
    if not st.session_state.index_loaded:
        st.warning("Please learn the spec book first in the 'Learn Spec Book' tab")
    
    audit_file = st.file_uploader(
        "Upload audit PDF",
        type="pdf",
        disabled=not st.session_state.index_loaded,
        help="Upload an audit document containing 'go-back' items or infractions"
    )
    
    if st.button("Analyze Audit", type="primary", disabled=not (audit_file and st.session_state.index_loaded)):
        if audit_file and st.session_state.index_loaded:
            # Save audit file
            audit_path = f"data/{audit_file.name}"
            with open(audit_path, "wb") as f:
                f.write(audit_file.getbuffer())
            
            # Load vectorstore
            try:
                embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
                vectorstore = FAISS.load_local("spec_index", embeddings, allow_dangerous_deserialization=True)
            except Exception as e:
                st.error(f"Error loading index: {e}")
                st.stop()
            
            # Extract and preview infractions
            with st.spinner("Extracting infractions from audit..."):
                audit_text = extract_text_from_pdf(audit_path)
                infractions = extract_infractions(audit_text)
                
                if infractions:
                    st.info(f"Found {len(infractions)} potential infractions")
                    
                    # Show preview
                    with st.expander("Preview Extracted Infractions"):
                        for i, inf in enumerate(infractions[:5], 1):
                            st.write(f"{i}. **{inf['type']}**: {inf['description'][:100]}...")
                            st.write(f"   Severity: {inf['severity']}")
                else:
                    st.warning("No infractions detected. Check if document contains 'go-back', 'violation', 'infraction' keywords")
            
            # Analyze
            with st.spinner("Analyzing infractions against specifications..."):
                results = analyze_audit(audit_path, vectorstore, use_grok=env_checks['xai_api_key'])
                st.session_state.analysis_results = results
                st.success(f"Analysis complete! Analyzed {len(results)} infractions.")
            
            # Clean up
            if st.checkbox("Delete audit file after analysis"):
                os.remove(audit_path)
                st.info("Audit file deleted. Results retained.")

# Tab 3: View Results
with tab3:
    st.header("Analysis Results")
    
    if st.session_state.analysis_results:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_infractions = len(st.session_state.analysis_results)
        valid_count = sum(1 for r in st.session_state.analysis_results if "VALID: TRUE" in r.get('analysis', ''))
        appealable_count = sum(1 for r in st.session_state.analysis_results if "APPEALABLE: YES" in r.get('analysis', ''))
        high_severity = sum(1 for r in st.session_state.analysis_results if r.get('severity') == 'HIGH')
        
        with col1:
            st.metric("Total Infractions", total_infractions)
        with col2:
            st.metric("Valid Infractions", valid_count)
        with col3:
            st.metric("Appealable", appealable_count)
        with col4:
            st.metric("High Severity", high_severity)
        
        st.markdown("---")
        
        # Detailed results
        for i, res in enumerate(st.session_state.analysis_results, 1):
            severity_icon = {
                'HIGH': '[HIGH]',
                'MEDIUM': '[MEDIUM]',
                'LOW': '[LOW]'
            }.get(res.get('severity', 'MEDIUM'), '[UNKNOWN]')
            
            with st.expander(f"{severity_icon} Infraction {i}: {res['infraction'][:80]}..."):
                st.write(f"**Full Infraction:** {res['infraction']}")
                st.write(f"**Severity:** {res.get('severity', 'Unknown')}")
                
                st.markdown("### Analysis")
                analysis_text = res['analysis']
                
                # Parse and highlight key findings
                if "VALID: TRUE" in analysis_text:
                    st.error("Valid Infraction - Requires Correction")
                elif "VALID: FALSE" in analysis_text:
                    st.success("Invalid Infraction - Can Be Disputed")
                
                if "APPEALABLE: YES" in analysis_text:
                    st.info("This infraction can be appealed")
                
                # Show full analysis
                st.text(analysis_text)
        
        # Export functionality
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            # JSON export
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'total_infractions': total_infractions,
                'valid_count': valid_count,
                'appealable_count': appealable_count,
                'results': st.session_state.analysis_results
            }
            
            st.download_button(
                label="Download Results (JSON)",
                data=json.dumps(export_data, indent=2),
                file_name=f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            # Generate summary report
            if st.button("Generate Summary Report"):
                summary = f"""
                # Audit Analysis Summary Report
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                
                ## Overview
                - Total Infractions: {total_infractions}
                - Valid Infractions: {valid_count}
                - Appealable: {appealable_count}
                - High Severity: {high_severity}
                
                ## Detailed Findings
                """
                
                for i, res in enumerate(st.session_state.analysis_results, 1):
                    summary += f"\n### {i}. {res['infraction']}\n"
                    summary += f"Severity: {res.get('severity', 'Unknown')}\n"
                    summary += f"Analysis:\n{res['analysis']}\n"
                    summary += "-" * 50 + "\n"
                
                st.download_button(
                    label="Download Summary Report",
                    data=summary,
                    file_name=f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
    else:
        st.info("No results yet. Upload and analyze an audit document to see results.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p><strong>NEXA Document Intelligence</strong> | AI-Powered Construction Audit Analysis</p>
    <p>Powered by xAI Grok, FAISS, and LangChain | <a href='https://x.ai/api'>Get xAI API Key</a></p>
</div>
""", unsafe_allow_html=True)
