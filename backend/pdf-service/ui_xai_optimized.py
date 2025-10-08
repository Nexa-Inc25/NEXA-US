"""
NEXA Document Intelligence - xAI Optimized Version
Lightweight implementation using xAI API with smart caching
"""
import streamlit as st
import PyPDF2
from io import BytesIO
import requests
import json
import os
import hashlib
import pickle
from datetime import datetime, timedelta

# Configuration
XAI_API_KEY = os.environ.get('XAI_API_KEY')
CACHE_EXPIRY_HOURS = 24  # Cache API responses for 24 hours

st.set_page_config(
    page_title="NEXA Document Intelligence - xAI",
    page_icon="🚧",
    layout="wide"
)

st.title("🚧 NEXA Document Intelligence Tool")
st.markdown("**AI-Powered Construction Specification Analyzer**")

# Initialize session state for caching
if 'api_cache' not in st.session_state:
    st.session_state.api_cache = {}
if 'extraction_cache' not in st.session_state:
    st.session_state.extraction_cache = {}

def get_cache_key(text):
    """Generate cache key from text content"""
    return hashlib.md5(text.encode()).hexdigest()

def call_xai_cached(prompt, cache_type='general'):
    """Call xAI API with caching to reduce costs"""
    cache_key = get_cache_key(prompt[:1000])  # Use first 1000 chars for key
    
    # Check cache
    if cache_type in st.session_state.api_cache:
        if cache_key in st.session_state.api_cache[cache_type]:
            cached_data = st.session_state.api_cache[cache_type][cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(hours=CACHE_EXPIRY_HOURS):
                return cached_data['response']
    
    # Make API call
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "grok-beta",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,  # Low temperature for consistency
        "max_tokens": 1000
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
            
            # Cache the response
            if cache_type not in st.session_state.api_cache:
                st.session_state.api_cache[cache_type] = {}
            
            st.session_state.api_cache[cache_type][cache_key] = {
                'response': result,
                'timestamp': datetime.now()
            }
            
            return result
        else:
            st.error(f"API Error: {response.status_code}")
            return None
            
    except Exception as e:
        st.error(f"Error calling xAI API: {e}")
        return None

def extract_infractions_smart(audit_text):
    """Extract infractions using xAI with NER-like approach"""
    
    # Check extraction cache first
    cache_key = get_cache_key(audit_text[:5000])
    if cache_key in st.session_state.extraction_cache:
        return st.session_state.extraction_cache[cache_key]
    
    extract_prompt = f"""
    You are an expert in construction audit document analysis with NER expertise.
    
    Extract ALL infractions, violations, non-compliances, and "go-back" items.
    Focus on construction-specific entities:
    - EQUIPMENT: poles, transformers, cables, switches
    - MATERIAL: copper, steel, concrete, PVC
    - SPECIFICATION: compression fittings, weatherproof, lockable
    - INSTALLATION: pole-mounted, underground, buried
    - MEASURE: feet, inches, voltage, amperage
    - GRADE: material grades, bolt grades
    - SECTION: specification section numbers
    - ZONE: work zones, areas
    
    Output in JSON format:
    {{
      "infractions": [
        {{
          "id": "Sequential ID",
          "description": "Full description",
          "type": "EQUIPMENT/MATERIAL/INSTALLATION/SPECIFICATION/SAFETY/OTHER",
          "code": "Code or section reference",
          "location": "Zone/area if mentioned",
          "severity": "HIGH/MEDIUM/LOW",
          "entities": ["List of specific entities mentioned"]
        }}
      ],
      "summary": {{
        "total_count": number,
        "high_severity": number,
        "categories": {{"EQUIPMENT": count, "MATERIAL": count, ...}}
      }}
    }}
    
    Audit text (first 15000 chars):
    {audit_text[:15000]}
    """
    
    result = call_xai_cached(extract_prompt, 'extraction')
    
    if result:
        try:
            extracted = json.loads(result)
            # Cache the extraction
            st.session_state.extraction_cache[cache_key] = extracted
            return extracted
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                try:
                    extracted = json.loads(json_match.group())
                    st.session_state.extraction_cache[cache_key] = extracted
                    return extracted
                except:
                    pass
    
    return None

def analyze_infraction_against_spec(infraction, spec_text):
    """Analyze a specific infraction against the specification"""
    
    analyze_prompt = f"""
    You are a construction specification expert analyzing an audit infraction.
    
    SPECIFICATION EXCERPT (first 10000 chars):
    {spec_text[:10000]}
    
    INFRACTION TO ANALYZE:
    Description: {infraction['description']}
    Type: {infraction.get('type', 'UNKNOWN')}
    Code: {infraction.get('code', 'N/A')}
    Location: {infraction.get('location', 'N/A')}
    Entities: {', '.join(infraction.get('entities', []))}
    
    PROVIDE ANALYSIS:
    1. VERDICT: VALID or APPEALABLE
    2. CONFIDENCE: HIGH/MEDIUM/LOW
    3. SPECIFICATION REFERENCE: Quote the exact spec section that supports your verdict
    4. REASONING: Clear explanation why this is valid or can be appealed
    5. RECOMMENDATION: What action should be taken
    
    Format as:
    VERDICT: [VALID/APPEALABLE]
    CONFIDENCE: [HIGH/MEDIUM/LOW]
    SPEC_REF: [Section number and quote]
    REASONING: [Your explanation]
    RECOMMENDATION: [Action to take]
    """
    
    return call_xai_cached(analyze_prompt, 'analysis')

# Sidebar metrics
st.sidebar.header("📊 Performance Metrics")
if st.sidebar.button("Clear Cache"):
    st.session_state.api_cache = {}
    st.session_state.extraction_cache = {}
    st.sidebar.success("Cache cleared!")

total_cached = sum(len(cache) for cache in st.session_state.api_cache.values())
st.sidebar.metric("Cached Responses", total_cached)
st.sidebar.metric("Est. API Calls Saved", total_cached * 0.8)
st.sidebar.metric("Est. Cost Saved", f"${total_cached * 0.05:.2f}")

# Main UI
col1, col2 = st.columns(2)

with col1:
    st.header("📚 Upload Spec Book PDFs")
    spec_files = st.file_uploader(
        "Upload spec book PDFs (can be multiple)", 
        type="pdf", 
        accept_multiple_files=True,
        key="spec_uploader"
    )

with col2:
    st.header("📋 Upload Audit Document")
    audit_file = st.file_uploader(
        "Upload the audit document", 
        type="pdf",
        key="audit_uploader"
    )

# Process spec books
spec_text = ""
if spec_files:
    with st.spinner("Processing specification books..."):
        for spec_file in spec_files:
            pdf_reader = PyPDF2.PdfReader(BytesIO(spec_file.read()))
            for page in pdf_reader.pages:
                spec_text += page.extract_text() + "\n"
        
        # Show statistics
        st.success(f"✅ Loaded {len(spec_files)} spec book(s)")
        st.info(f"📄 Total content: {len(spec_text):,} characters")

# Process audit and analyze
if audit_file and spec_text:
    pdf_reader = PyPDF2.PdfReader(BytesIO(audit_file.read()))
    audit_text = ""
    for page in pdf_reader.pages:
        audit_text += page.extract_text() + "\n"
    
    st.success("✅ Audit document loaded!")
    
    # Analysis buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        extract_btn = st.button("🔍 Extract Infractions", type="primary")
    with col2:
        analyze_btn = st.button("🧠 Analyze All", type="secondary")
    with col3:
        export_btn = st.button("📥 Export Results")
    
    if extract_btn or analyze_btn:
        with st.spinner("Extracting infractions using AI..."):
            extracted = extract_infractions_smart(audit_text)
        
        if extracted and 'infractions' in extracted:
            infractions = extracted['infractions']
            
            # Show summary
            if 'summary' in extracted:
                st.markdown("### 📊 Extraction Summary")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Infractions", extracted['summary'].get('total_count', len(infractions)))
                with col2:
                    st.metric("High Severity", extracted['summary'].get('high_severity', 0))
                with col3:
                    categories = extracted['summary'].get('categories', {})
                    if categories:
                        top_category = max(categories, key=categories.get)
                        st.metric("Top Category", f"{top_category} ({categories[top_category]})")
            
            st.markdown("### 🚨 Infractions Found")
            
            # Create tabs for different views
            view_tabs = st.tabs(["All Infractions", "By Severity", "By Category"])
            
            with view_tabs[0]:
                for i, inf in enumerate(infractions):
                    severity_color = {
                        'HIGH': '🔴',
                        'MEDIUM': '🟡',
                        'LOW': '🟢'
                    }.get(inf.get('severity', 'MEDIUM'), '⚪')
                    
                    with st.expander(
                        f"{severity_color} Infraction {inf.get('id', i+1)}: "
                        f"{inf['description'][:100]}..."
                    ):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Description:** {inf['description']}")
                            if inf.get('code'):
                                st.write(f"**Code:** {inf['code']}")
                            if inf.get('location'):
                                st.write(f"**Location:** {inf['location']}")
                            if inf.get('entities'):
                                st.write(f"**Entities:** {', '.join(inf['entities'])}")
                        
                        with col2:
                            st.write(f"**Type:** {inf.get('type', 'UNKNOWN')}")
                            st.write(f"**Severity:** {inf.get('severity', 'MEDIUM')}")
                        
                        if analyze_btn:
                            with st.spinner("Analyzing against specification..."):
                                analysis = analyze_infraction_against_spec(inf, spec_text)
                                
                                if analysis:
                                    st.markdown("---")
                                    st.markdown("### 🔬 Analysis Result")
                                    
                                    # Parse structured response
                                    lines = analysis.split('\n')
                                    verdict = "UNKNOWN"
                                    confidence = "UNKNOWN"
                                    
                                    for line in lines:
                                        if 'VERDICT:' in line:
                                            verdict = line.split('VERDICT:')[1].strip()
                                        elif 'CONFIDENCE:' in line:
                                            confidence = line.split('CONFIDENCE:')[1].strip()
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if 'APPEALABLE' in verdict:
                                            st.success(f"✅ {verdict}")
                                        else:
                                            st.error(f"❌ {verdict}")
                                    with col2:
                                        st.info(f"Confidence: {confidence}")
                                    
                                    st.text(analysis)
            
            with view_tabs[1]:
                # Group by severity
                for severity in ['HIGH', 'MEDIUM', 'LOW']:
                    severity_items = [inf for inf in infractions if inf.get('severity') == severity]
                    if severity_items:
                        st.subheader(f"{severity} Severity ({len(severity_items)} items)")
                        for inf in severity_items:
                            st.write(f"• {inf['description'][:150]}...")
            
            with view_tabs[2]:
                # Group by category
                categories = {}
                for inf in infractions:
                    cat = inf.get('type', 'OTHER')
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(inf)
                
                for cat, items in categories.items():
                    st.subheader(f"{cat} ({len(items)} items)")
                    for inf in items:
                        st.write(f"• {inf['description'][:150]}...")
            
            # Export functionality
            if export_btn:
                # Create export data
                export_data = {
                    'timestamp': datetime.now().isoformat(),
                    'spec_files': [f.name for f in spec_files],
                    'audit_file': audit_file.name,
                    'infractions': infractions,
                    'summary': extracted.get('summary', {})
                }
                
                # Offer download
                st.download_button(
                    label="📥 Download JSON Report",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"infraction_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        else:
            st.info("No infractions found in the audit document.")
else:
    if not spec_text:
        st.info("👈 Please upload specification book PDFs first")
    elif not audit_file:
        st.info("👈 Please upload an audit document")

# Footer with deployment instructions
st.markdown("---")
with st.expander("🚀 Deployment Instructions"):
    st.markdown("""
    ### Deploy on Render.com
    
    1. **Create Web Service** on Render.com
    2. **Set Build Command:** 
       ```bash
       pip install -r requirements.txt
       ```
    3. **Set Start Command:**
       ```bash
       streamlit run ui_xai_optimized.py --server.port $PORT
       ```
    4. **Environment Variables:**
       ```
       XAI_API_KEY=your_xai_api_key_here
       ```
    5. **Create requirements.txt:**
       ```
       streamlit
       PyPDF2
       requests
       ```
    
    ### Cost Optimization Tips
    - This version includes **response caching** to reduce API calls
    - Cached responses expire after 24 hours
    - Monitor the sidebar metrics to track savings
    - Average cost: ~$0.05 per unique analysis
    
    ### Performance
    - First analysis: 5-10 seconds
    - Cached analysis: <1 second
    - Handles multiple spec books
    - Structured JSON extraction
    """)

# API status check
if not XAI_API_KEY:
    st.warning("⚠️ XAI_API_KEY not set. Please configure in environment variables.")
else:
    st.sidebar.success("✅ xAI API configured")
