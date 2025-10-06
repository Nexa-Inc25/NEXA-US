"""
NEXA AI Document Analyzer - Streamlit Frontend Service
Aligns with Phase 1-3 of NEXA Roadmap for AI-driven processing
"""

import streamlit as st
import os
import pickle
from sentence_transformers import SentenceTransformer, util
from pypdf import PdfReader
import nltk
import re
import torch
import psycopg2
from datetime import datetime
import json
import numpy as np

# Page configuration MUST be first Streamlit command
st.set_page_config(
    page_title="NEXA AI Document Analyzer Enterprise",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Download NLTK data after page config
nltk.download('punkt', quiet=True)

# Use lightweight model; check for GPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

# Database connection (keep for future integration)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/nexa_db")

# Persistence (attach Render Disk for production; fallback to temp)
EMBEDDINGS_PATH = os.environ.get('RENDER_DISK_PATH', '/tmp') + '/spec_embeddings.pkl'

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main {
        padding-top: 1rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #4682B4;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
        border: none;
    }
    .stButton>button:hover {
        background-color: #5A7A9A;
        box-shadow: 0 4px 12px rgba(70, 130, 180, 0.3);
    }
    .success-box {
        background-color: rgba(0, 255, 136, 0.1);
        border-left: 4px solid #00ff88;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: rgba(255, 170, 0, 0.1);
        border-left: 4px solid #ffaa00;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .error-box {
        background-color: rgba(255, 0, 85, 0.1);
        border-left: 4px solid #ff0055;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 0.5rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #4682B4;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.5rem;
    }
    /* Progress bar tint */
    .stProgress > div > div > div {
        background-color: #4682B4;
    }
    /* DataFrame table styling */
    .stDataFrame { border: 1px solid #E2E8F0; }
    .stDataFrame th, .stDataFrame td { border-bottom: 1px solid #E2E8F0; padding: 8px; }
    .stDataFrame th { background-color: #F8FAFC; font-weight: 600; color: #2D3748; }
    div[data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    .sidebar-status {
        padding: 1rem;
        background-color: white;
        border-radius: 8px;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Session state initialization
if "token" not in st.session_state:
    st.session_state.token = "mock-jwt-token"  # Mocked for now
    st.session_state.user_id = "anonymous"

if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None

if "spec_loaded" not in st.session_state:
    st.session_state.spec_loaded = False

# Auth check (mocked for development)
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"

if AUTH_ENABLED and not st.session_state.token:
    st.header("🔐 Login to NEXA AI Document Analyzer")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("Please authenticate to access the system")
        if st.button("Login with Auth0", type="primary"):
            # In production, this would redirect to Auth0
            st.session_state.token = "mock-jwt-token"
            st.session_state.user_id = "authenticated-user"
            st.rerun()
    st.stop()

# Sidebar
with st.sidebar:
    st.title("🔍 NEXA AI Analyzer")
    st.markdown("---")
    
    # Service status check (cached)
    with st.container():
        health_data = get_health_status()
        if health_data.get("status") == "error":
            st.markdown('<div class="sidebar-status">', unsafe_allow_html=True)
            st.error("❌ API Offline")
            st.caption("Check backend service")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            spec_loaded = bool(health_data.get("index_loaded", False))
            chunks_loaded = int(health_data.get("chunks_loaded", 0))
            st.session_state.spec_loaded = spec_loaded
            st.markdown('<div class="sidebar-status">', unsafe_allow_html=True)
            if spec_loaded:
                st.success("✅ Service Online")
                st.info(f"📚 Spec Chunks: {chunks_loaded}")
            else:
                st.warning("⚠️ No Spec Loaded")
                st.caption("Upload spec books to begin")
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Navigation
    page = st.radio(
        "Navigation",
        ["📚 Upload Spec Book", "🔍 Analyze Audit", "📊 Summary Dashboard", "ℹ️ About"],
        label_visibility="collapsed"
    )

# Helper functions
async def upload_files_async(url, files, token):
    """Async file upload with progress tracking"""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    async with aiohttp.ClientSession() as session:
        form_data = aiohttp.FormData()
        for file in files:
            form_data.add_field(
                'spec_files',
                file.getvalue(),
                filename=file.name,
                content_type='application/pdf'
            )
        
        async with session.post(url, headers=headers, data=form_data) as response:
            return await response.json(), response.status

def create_confidence_chart(confidence):
    """Create a gauge chart for confidence visualization"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=confidence * 100,
        title={'text': "Average Confidence"},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#00d4ff"},
            'steps': [
                {'range': [0, 50], 'color': "rgba(255, 0, 85, 0.2)"},
                {'range': [50, 70], 'color': "rgba(255, 170, 0, 0.2)"},
                {'range': [70, 100], 'color': "rgba(0, 255, 136, 0.2)"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def create_summary_metrics(analysis):
    """Create summary metric cards"""
    total = len(analysis)
    valid = sum(1 for item in analysis if item["validity"] == "YES")
    repealable = sum(1 for item in analysis if item["repealable"] == "YES")
    avg_confidence = sum(item['confidence'] for item in analysis) / total if total > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f'''<div class="metric-card">
                <div class="metric-value">{total}</div>
                <div class="metric-label">Total Infractions</div>
            </div>''',
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f'''<div class="metric-card">
                <div class="metric-value" style="color: #00ff88;">{valid}</div>
                <div class="metric-label">Valid Infractions</div>
            </div>''',
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            f'''<div class="metric-card">
                <div class="metric-value" style="color: #ffaa00;">{repealable}</div>
                <div class="metric-label">Repealable</div>
            </div>''',
            unsafe_allow_html=True
        )
    
    with col4:
        st.plotly_chart(create_confidence_chart(avg_confidence), use_container_width=True)

# Main content
if page == "📚 Upload Spec Book":
    st.header("📚 Upload Specification Books")
    st.markdown("Upload one or more PDF specification books to create your knowledge base.")
    
    with st.expander("ℹ️ Instructions", expanded=False):
        st.markdown("""
        - Upload multiple spec PDFs (e.g., PG&E Greenbook sections)
        - Each file must be under 50 MB
        - Files will be concatenated and processed together
        - Processing time depends on total page count
        - Typical processing: ~30s for 500 pages on Render Pro
        """)
    
    spec_files = st.file_uploader(
        "Choose spec book PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="spec_uploader",
        help="Select one or more PDF files to upload"
    )
    
    if spec_files:
        total_size = sum(f.size for f in spec_files)
        total_size_mb = total_size / (1024 * 1024)
        
        st.info(f"📁 Selected {len(spec_files)} files ({total_size_mb:.1f} MB total)")
        
        # Check file sizes
        oversized = [f.name for f in spec_files if f.size > 50 * 1024 * 1024]
        if oversized:
            st.error(f"❌ Files exceeding 50 MB: {', '.join(oversized)}")
        else:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if st.button("🚀 Process Specification Books", type="primary", disabled=bool(oversized)):
                    start_time = time.time()
                    
                    with st.spinner("Processing spec books... This may take a few minutes."):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            # Update progress
                            status_text.text(f"Uploading {len(spec_files)} files...")
                            progress_bar.progress(25)
                            
                            # Run async upload
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            result, status_code = loop.run_until_complete(
                                upload_files_async(f"{API_URL}/learn-spec/", spec_files, st.session_state.token)
                            )
                            
                            progress_bar.progress(100)
                            
                            if status_code == 200:
                                elapsed = time.time() - start_time
                                st.session_state.spec_loaded = True
                                
                                # Show success message
                                st.markdown(
                                    f'''<div class="success-box">
                                        <h4>✅ Specification Books Processed Successfully!</h4>
                                        <p>• Files processed: {result.get('files_processed', len(spec_files))}</p>
                                        <p>• Total chunks: {result.get('total_chunks', 0)}</p>
                                        <p>• Processing time: {elapsed:.1f} seconds</p>
                                    </div>''',
                                    unsafe_allow_html=True
                                )
                                
                                st.balloons()
                            else:
                                st.error(f"❌ Failed to process: {result.get('detail', 'Unknown error')}")
                        
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                        
                        finally:
                            progress_bar.empty()
                            status_text.empty()

elif page == "🔍 Analyze Audit":
    st.header("🔍 Analyze Audit Document")
    
    if not st.session_state.spec_loaded:
        st.warning("⚠️ Please upload specification books first!")
        if st.button("Go to Spec Upload"):
            st.rerun()
        st.stop()
    
    st.markdown("Upload a QA audit document to analyze infractions against your specifications.")
    
    audit_file = st.file_uploader(
        "Choose an audit PDF",
        type=["pdf"],
        key="audit_uploader",
        help="Upload a QA audit document with infractions"
    )
    
    if audit_file:
        if audit_file.size > 50 * 1024 * 1024:
            st.error("❌ File exceeds 50 MB limit")
        else:
            st.info(f"📄 Selected: {audit_file.name} ({audit_file.size / 1024 / 1024:.1f} MB)")
            
            # Analysis parameters
            col1, col2 = st.columns(2)
            with col1:
                confidence_threshold = st.slider(
                    "Confidence Threshold (%)",
                    min_value=50,
                    max_value=90,
                    value=70,
                    step=5,
                    help="Infractions below this confidence are considered repealable"
                )
            
            if st.button("🔍 Analyze Audit", type="primary"):
                start_time = time.time()
                
                with st.spinner("Analyzing audit document..."):
                    try:
                        # Prepare request
                        files = {"audit_file": (audit_file.name, audit_file.getvalue(), "application/pdf")}
                        params = {
                            "user_id": st.session_state.user_id,
                            "confidence_threshold": confidence_threshold / 100
                        }
                        
                        # Send request
                        response = requests.post(
                            f"{API_URL}/analyze-audit/",
                            files=files,
                            params=params,
                            timeout=120
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            elapsed = time.time() - start_time
                            
                            # Store results
                            st.session_state.analysis_results = result.get("analysis", [])
                            
                            # Display summary
                            st.success(f"✅ Analysis complete in {elapsed:.1f} seconds!")
                            
                            if result.get("analysis"):
                                # Show metrics
                                create_summary_metrics(result["analysis"])
                                
                                # Show detailed results
                                st.subheader("Detailed Analysis")
                                
                                # Create DataFrame
                                df = pd.DataFrame(result["analysis"])
                                
                                # Filters
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    validity_filter = st.selectbox("Filter by Validity", ["All", "YES", "NO"])
                                with col2:
                                    repealable_filter = st.selectbox("Filter by Repealable", ["All", "YES", "NO"])
                                
                                # Apply filters
                                filtered_df = df.copy()
                                if validity_filter != "All":
                                    filtered_df = filtered_df[filtered_df["validity"] == validity_filter]
                                if repealable_filter != "All":
                                    filtered_df = filtered_df[filtered_df["repealable"] == repealable_filter]
                                
                                # Display table
                                st.dataframe(
                                    filtered_df,
                                    use_container_width=True,
                                    height=400,
                                    column_config={
                                        "confidence": st.column_config.ProgressColumn(
                                            "Confidence",
                                            min_value=0,
                                            max_value=1,
                                            format="%.1f%%"
                                        ),
                                        "reasons": st.column_config.TextColumn(
                                            "Reasons",
                                            width="large"
                                        )
                                    }
                                )
                                
                                # Export options
                                st.subheader("Export Results")
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.download_button(
                                        label="📥 Download JSON",
                                        data=json.dumps(result, indent=2),
                                        file_name=f"audit_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                        mime="application/json"
                                    )
                                
                                with col2:
                                    csv = filtered_df.to_csv(index=False)
                                    st.download_button(
                                        label="📥 Download CSV",
                                        data=csv,
                                        file_name=f"audit_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                
                                with col3:
                                    if st.button("📄 Generate PDF Report"):
                                        # Generate PDF closeout
                                        pdf_response = requests.post(
                                            f"{API_URL}/closeout/generate",
                                            json={"analysis": result["analysis"]},
                                            params={"user_id": st.session_state.user_id}
                                        )
                                        if pdf_response.status_code == 200:
                                            st.download_button(
                                                label="📥 Download PDF Report",
                                                data=pdf_response.content,
                                                file_name=f"closeout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                                mime="application/pdf"
                                            )
                                        else:
                                            st.error("Failed to generate PDF")
                            else:
                                st.warning("No infractions found in the document")
                        else:
                            st.error(f"❌ Analysis failed: {response.text}")
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

elif page == "📊 Summary Dashboard":
    st.header("📊 Analysis Summary Dashboard")
    
    if not st.session_state.analysis_results:
        st.info("No analysis results available. Please analyze an audit first.")
        if st.button("Go to Audit Analysis"):
            st.rerun()
        st.stop()
    
    results = st.session_state.analysis_results
    
    # Create metrics
    create_summary_metrics(results)
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Validity pie chart
        validity_counts = pd.DataFrame(results)['validity'].value_counts()
        fig_validity = px.pie(
            values=validity_counts.values,
            names=validity_counts.index,
            title="Infraction Validity",
            color_discrete_map={"YES": "#00ff88", "NO": "#ff0055"}
        )
        st.plotly_chart(fig_validity, use_container_width=True)
    
    with col2:
        # Confidence distribution
        confidences = [item['confidence'] * 100 for item in results]
        fig_conf = px.histogram(
            x=confidences,
            nbins=20,
            title="Confidence Distribution",
            labels={'x': 'Confidence (%)', 'y': 'Count'},
            color_discrete_sequence=['#00d4ff']
        )
        fig_conf.add_vline(x=70, line_dash="dash", line_color="red", annotation_text="Threshold")
        st.plotly_chart(fig_conf, use_container_width=True)
    
    # Top infractions table
    st.subheader("Infraction Details")
    df = pd.DataFrame(results)
    df['confidence_pct'] = df['confidence'].apply(lambda x: f"{x*100:.1f}%")
    
    # Sort by confidence
    df_sorted = df.sort_values('confidence', ascending=False)
    
    st.dataframe(
        df_sorted[['infraction', 'validity', 'repealable', 'confidence_pct', 'spec_refs']],
        use_container_width=True,
        height=400
    )

elif page == "ℹ️ About":
    st.header("ℹ️ About NEXA AI Document Analyzer")
    
    st.markdown("""
    ### 🎯 Purpose
    The NEXA AI Document Analyzer is designed to automate the analysis of QA audit documents 
    against specification books, identifying which infractions are valid and which can be repealed.
    
    ### 🔧 How It Works
    1. **Learn Specifications**: Upload one or more PDF specification books (e.g., PG&E Greenbook sections)
    2. **Analyze Audits**: Upload QA audit documents containing infractions
    3. **AI Analysis**: The system uses embeddings to cross-reference infractions against specs
    4. **Confidence Scoring**: Each infraction gets a confidence score (0-100%)
    5. **Repealability**: Infractions below the confidence threshold are marked as repealable
    
    ### 📊 Key Features
    - **Multiple Spec Support**: Process multiple specification PDFs together
    - **Batch Processing**: Handles large documents up to 50 MB each
    - **Smart Extraction**: Detects various infraction patterns (go-back, violations, etc.)
    - **PDF Reports**: Generate professional closeout reports
    - **Export Options**: Download results as JSON, CSV, or PDF
    
    ### 🚀 Performance
    - **Processing Speed**: ~30 seconds for 500 pages
    - **Accuracy**: 70%+ confidence threshold for validity
    - **Capacity**: Handles 200+ MB of spec books total
    - **Scalability**: Dual-service architecture on Render Pro
    
    ### 🔒 Security
    - Auth0 integration ready (currently mocked)
    - Audit logging for compliance
    - Secure PostgreSQL storage with pgvector
    
    ### 📞 Support
    For issues or questions, contact the NEXA development team.
    
    ---
    **Version**: 2.0.0 | **Last Updated**: {datetime.now().strftime('%Y-%m-%d')}
    """)

# Footer
st.markdown("---")
st.caption(f"NEXA AI Document Analyzer | Connected to: {API_URL}")
