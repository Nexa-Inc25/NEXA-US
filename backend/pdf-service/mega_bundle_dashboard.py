#!/usr/bin/env python3
"""
Streamlit Dashboard for Mega Bundle Analysis
Provides UI for PMs and Bidders to upload and analyze job bundles
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
from pathlib import Path
import time

# Configuration
API_BASE_URL = "http://localhost:8001"  # Update for production
st.set_page_config(
    page_title="NEXA Mega Bundle Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .medium-font {
        font-size:20px !important;
        font-weight: bold;
    }
    .profit-positive {
        color: #28a745;
        font-weight: bold;
    }
    .profit-negative {
        color: #dc3545;
        font-weight: bold;
    }
    .stProgress > div > div > div > div {
        background-color: #28a745;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    """Main dashboard application"""
    
    # Header
    st.markdown('<p class="big-font">🎯 NEXA Mega Bundle Analyzer</p>', unsafe_allow_html=True)
    st.markdown("**Analyze 3500+ job packages for profitability and optimal scheduling**")
    
    # Sidebar for navigation
    with st.sidebar:
        st.markdown("### Navigation")
        page = st.radio(
            "Select Function",
            ["📤 Upload Bundle", "📊 Analysis Results", "📅 Schedule Optimizer", "💰 Pre-Bid Analysis", "📈 Dashboard"]
        )
        
        # User info (mock for demo)
        st.markdown("---")
        st.markdown("### User")
        user_role = st.selectbox("Role", ["PM", "Bidder", "Executive"])
        st.info(f"Logged in as: {user_role}")
    
    # Main content based on selection
    if page == "📤 Upload Bundle":
        upload_bundle_page()
    elif page == "📊 Analysis Results":
        analysis_results_page()
    elif page == "📅 Schedule Optimizer":
        schedule_optimizer_page()
    elif page == "💰 Pre-Bid Analysis":
        pre_bid_analysis_page()
    elif page == "📈 Dashboard":
        executive_dashboard()

def upload_bundle_page():
    """Upload bundle page"""
    
    st.markdown('<p class="medium-font">📤 Upload New Mega Bundle</p>', unsafe_allow_html=True)
    
    # Mode selection
    col1, col2 = st.columns(2)
    with col1:
        mode = st.radio(
            "Analysis Mode",
            ["post-win", "pre-bid"],
            help="Post-win: Analyze with known contract rates\nPre-bid: Estimate costs and recommend bid"
        )
    
    with col2:
        if mode == "pre-bid":
            profit_margin = st.slider(
                "Target Profit Margin (%)",
                min_value=10,
                max_value=40,
                value=20,
                step=5
            ) / 100
        else:
            profit_margin = 0.20
    
    st.markdown("---")
    
    # File uploads
    st.markdown("### Upload Files")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        job_zip = st.file_uploader(
            "Job Packages ZIP (Required)",
            type=["zip"],
            help="ZIP file containing all job PDFs (3500+)"
        )
        if job_zip:
            st.success(f"✅ {job_zip.name} ({job_zip.size / 1024 / 1024:.1f} MB)")
    
    with col2:
        bid_sheet = st.file_uploader(
            "Bid Sheet (Optional)",
            type=["pdf", "csv", "xlsx"],
            help="Unit price bid sheet"
        )
        if bid_sheet:
            st.success(f"✅ {bid_sheet.name}")
    
    with col3:
        contract = st.file_uploader(
            "Contract (Optional)",
            type=["pdf"],
            help="Contract with rates (post-win mode)"
        )
        if contract:
            st.success(f"✅ {contract.name}")
    
    st.markdown("---")
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            max_daily_hours = st.number_input(
                "Max Daily Hours",
                min_value=8,
                max_value=16,
                value=12,
                help="Maximum working hours per day"
            )
        
        with col2:
            prioritize = st.selectbox(
                "Optimization Priority",
                ["profit", "schedule", "compliance"],
                help="What to optimize for"
            )
        
        with col3:
            num_crews = st.number_input(
                "Number of Crews",
                min_value=1,
                max_value=10,
                value=3,
                help="Available crew count"
            )
    
    # Process button
    if st.button("🚀 Process Bundle", type="primary", disabled=not job_zip):
        if job_zip:
            with st.spinner("Uploading and processing bundle..."):
                # Prepare files for upload
                files = {
                    "job_zip": (job_zip.name, job_zip.getvalue(), "application/zip")
                }
                if bid_sheet:
                    files["bid_sheet"] = (bid_sheet.name, bid_sheet.getvalue(), "application/octet-stream")
                if contract:
                    files["contract"] = (contract.name, contract.getvalue(), "application/pdf")
                
                # Set parameters
                params = {
                    "mode": mode,
                    "profit_margin": profit_margin,
                    "max_daily_hours": max_daily_hours,
                    "prioritize": prioritize
                }
                
                try:
                    # Upload to API
                    response = requests.post(
                        f"{API_BASE_URL}/mega-bundle/upload",
                        files=files,
                        params=params,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ Bundle uploaded successfully!")
                        st.info(f"Bundle ID: **{result['bundle_id']}**")
                        
                        # Store in session state
                        st.session_state['current_bundle_id'] = result['bundle_id']
                        
                        # Show processing status
                        show_processing_status(result['bundle_id'])
                    else:
                        st.error(f"Upload failed: {response.text}")
                        
                except Exception as e:
                    st.error(f"Error uploading bundle: {e}")

def show_processing_status(bundle_id: str):
    """Show real-time processing status"""
    
    st.markdown("### Processing Status")
    
    # Create placeholders
    status_placeholder = st.empty()
    progress_placeholder = st.empty()
    details_placeholder = st.empty()
    
    # Poll for status
    max_polls = 60  # 5 minutes max
    for i in range(max_polls):
        try:
            response = requests.get(f"{API_BASE_URL}/mega-bundle/status/{bundle_id}")
            if response.status_code == 200:
                status = response.json()
                
                # Update status
                if status['status'] == 'processing':
                    status_placeholder.info(f"⏳ Status: Processing... ({status.get('progress', 0)}%)")
                    progress_placeholder.progress(status.get('progress', 0) / 100)
                elif status['status'] == 'analyzing':
                    status_placeholder.info(f"🔍 Status: Analyzing jobs... ({status.get('progress', 0)}%)")
                    progress_placeholder.progress(status.get('progress', 0) / 100)
                elif status['status'] == 'complete':
                    status_placeholder.success("✅ Processing complete!")
                    progress_placeholder.progress(1.0)
                    
                    # Show summary
                    if 'summary' in status:
                        show_summary_metrics(status['summary'])
                    
                    # Show download link
                    st.markdown(f"[📥 Download Full Report]({API_BASE_URL}/mega-bundle/download/{bundle_id}?format=excel)")
                    break
                elif status['status'] == 'failed':
                    status_placeholder.error(f"❌ Processing failed: {status.get('error', 'Unknown error')}")
                    break
                
                time.sleep(5)  # Poll every 5 seconds
            else:
                st.error(f"Failed to get status: {response.text}")
                break
                
        except Exception as e:
            st.error(f"Error checking status: {e}")
            break

def show_summary_metrics(summary: dict):
    """Display summary metrics"""
    
    st.markdown("### 📊 Summary Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Jobs",
            f"{summary.get('total_jobs', 0):,}",
            delta=None
        )
    
    with col2:
        total_profit = summary.get('total_profit', 0)
        color = "profit-positive" if total_profit > 0 else "profit-negative"
        st.markdown(f"**Total Profit**")
        st.markdown(f'<p class="{color}">${total_profit:,.2f}</p>', unsafe_allow_html=True)
    
    with col3:
        st.metric(
            "Profit Margin",
            summary.get('profit_margin', '0%'),
            delta=None
        )
    
    with col4:
        st.metric(
            "Est. Days",
            summary.get('estimated_days', 0),
            delta=None
        )
    
    # Additional metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Cost",
            f"${summary.get('total_cost', 0):,.2f}"
        )
    
    with col2:
        st.metric(
            "Total Revenue",
            f"${summary.get('total_revenue', 0):,.2f}"
        )
    
    with col3:
        st.metric(
            "Labor Hours",
            f"{summary.get('total_labor_hours', 0):,.0f}"
        )

def analysis_results_page():
    """Show detailed analysis results"""
    
    st.markdown('<p class="medium-font">📊 Analysis Results</p>', unsafe_allow_html=True)
    
    # Get bundle ID from session or input
    bundle_id = st.session_state.get('current_bundle_id', '')
    bundle_id = st.text_input("Bundle ID", value=bundle_id)
    
    if bundle_id:
        try:
            # Get analysis results
            response = requests.get(f"{API_BASE_URL}/mega-bundle/download/{bundle_id}?format=json")
            
            if response.status_code == 200:
                result = response.json()
                
                # Show tabs for different views
                tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Job Breakdown", "Schedule", "Profitability"])
                
                with tab1:
                    show_summary_tab(result)
                
                with tab2:
                    show_job_breakdown_tab(result)
                
                with tab3:
                    show_schedule_tab(result)
                
                with tab4:
                    show_profitability_tab(result)
            else:
                st.error(f"Failed to load results: {response.text}")
                
        except Exception as e:
            st.error(f"Error loading results: {e}")

def show_summary_tab(result: dict):
    """Show summary tab"""
    
    summary = result.get('summary', {})
    
    # Key metrics
    st.markdown("### Key Metrics")
    show_summary_metrics(summary)
    
    # Bid recommendation (if pre-bid mode)
    if 'bid_recommendation' in result and result['bid_recommendation']:
        st.markdown("### 💰 Bid Recommendation")
        bid = result['bid_recommendation']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Minimum Bid", f"${bid['minimum_bid']:,.2f}")
        with col2:
            st.metric("Recommended Bid", f"${bid['recommended_bid']:,.2f}")
        with col3:
            st.metric("Break Even", f"${bid['break_even']:,.2f}")
        
        st.info(f"Target Margin: {bid['target_margin']} | Confidence: {bid['confidence']}")

def show_job_breakdown_tab(result: dict):
    """Show job breakdown tab"""
    
    st.markdown("### Job Breakdown by Tag")
    
    breakdown = result.get('job_breakdown', {})
    
    # By tag summary
    if 'by_tag' in breakdown:
        tag_data = breakdown['by_tag']
        if tag_data:
            df = pd.DataFrame.from_dict(tag_data, orient='index')
            df = df.reset_index().rename(columns={'index': 'Tag'})
            
            # Create chart
            fig = px.bar(
                df,
                x='Tag',
                y='total_profit',
                color='avg_margin',
                title="Profitability by Job Tag",
                labels={'total_profit': 'Total Profit ($)', 'avg_margin': 'Avg Margin (%)'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Show table
            st.dataframe(df, use_container_width=True)
    
    # High profit jobs
    if 'high_profit' in breakdown:
        st.markdown("### 🏆 Top 10 Most Profitable Jobs")
        df = pd.DataFrame(breakdown['high_profit'])
        if not df.empty:
            st.dataframe(
                df[['job_id', 'tag', 'profit', 'profit_margin', 'compliance']],
                use_container_width=True
            )
    
    # High risk jobs
    if 'high_risk' in breakdown:
        st.markdown("### ⚠️ High Risk Jobs")
        df = pd.DataFrame(breakdown['high_risk'])
        if not df.empty:
            st.dataframe(df, use_container_width=True)

def show_schedule_tab(result: dict):
    """Show schedule optimization tab"""
    
    st.markdown("### Optimized Schedule")
    
    schedule = result.get('optimized_schedule', result.get('schedule', {}))
    
    if schedule and 'days' in schedule:
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Days", schedule.get('total_days', 0))
        with col2:
            st.metric("Total Crews", len(schedule.get('crews', [])))
        with col3:
            st.metric("Travel Hours", f"{schedule.get('total_travel_hours', 0):.1f}")
        
        # Daily schedule
        st.markdown("### Daily Schedule")
        
        days_data = []
        for day in schedule.get('days', [])[:30]:  # Show first 30 days
            for crew in day.get('crews', []):
                days_data.append({
                    'Day': day['day'],
                    'Date': day.get('date', ''),
                    'Crew': crew['crew_id'],
                    'Jobs': len(crew['jobs']),
                    'Hours': crew['total_hours'],
                    'Zones': ', '.join(crew['zones'])
                })
        
        if days_data:
            df = pd.DataFrame(days_data)
            st.dataframe(df, use_container_width=True)
            
            # Gantt chart
            fig = px.timeline(
                df,
                x_start='Date',
                x_end='Date',
                y='Crew',
                color='Hours',
                title="Crew Schedule Timeline"
            )
            st.plotly_chart(fig, use_container_width=True)

def show_profitability_tab(result: dict):
    """Show profitability analysis tab"""
    
    st.markdown("### Profitability Analysis")
    
    breakdown = result.get('job_breakdown', {})
    
    # Profitability tiers
    if 'by_profitability' in breakdown:
        tiers = breakdown['by_profitability']
        
        # Create pie chart
        tier_data = []
        for tier, data in tiers.items():
            tier_data.append({
                'Tier': tier.replace('_', ' ').title(),
                'Count': data['count'],
                'Total Profit': data['total_profit']
            })
        
        if tier_data:
            df = pd.DataFrame(tier_data)
            
            fig = px.pie(
                df,
                values='Count',
                names='Tier',
                title="Jobs by Profitability Tier"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Show table
            st.dataframe(df, use_container_width=True)

def schedule_optimizer_page():
    """Schedule optimization page"""
    
    st.markdown('<p class="medium-font">📅 Schedule Optimizer</p>', unsafe_allow_html=True)
    
    # Input parameters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        optimization_priority = st.selectbox(
            "Optimization Priority",
            ["Maximize Profit", "Minimize Duration", "Balance Workload"],
            help="What to optimize the schedule for"
        )
    
    with col2:
        crew_count = st.number_input(
            "Available Crews",
            min_value=1,
            max_value=20,
            value=5,
            help="Number of crews available"
        )
    
    with col3:
        daily_hours = st.slider(
            "Max Daily Hours",
            min_value=8,
            max_value=16,
            value=12,
            help="Maximum working hours per day"
        )
    
    # Geographic clustering
    st.markdown("### Geographic Clustering")
    
    col1, col2 = st.columns(2)
    
    with col1:
        cluster_radius = st.slider(
            "Cluster Radius (miles)",
            min_value=1,
            max_value=20,
            value=5,
            help="Maximum radius for job clusters"
        )
    
    with col2:
        min_cluster_size = st.number_input(
            "Min Jobs per Cluster",
            min_value=1,
            max_value=20,
            value=5,
            help="Minimum jobs to form a cluster"
        )
    
    # Dependencies
    st.markdown("### Job Dependencies")
    
    dependency_rules = st.multiselect(
        "Apply dependency rules",
        ["Poles before crossarms", "Underground before above ground", "Main line before service"],
        default=["Poles before crossarms"]
    )
    
    if st.button("🔄 Re-optimize Schedule", type="primary"):
        st.info("Schedule optimization would run here with selected parameters")
        # In production, this would call the API to re-run optimization

def pre_bid_analysis_page():
    """Pre-bid analysis for bidders"""
    
    st.markdown('<p class="medium-font">💰 Pre-Bid Analysis</p>', unsafe_allow_html=True)
    
    st.info("This mode helps bidders estimate costs and determine minimum bid prices for profitability")
    
    # Risk assessment
    st.markdown("### Risk Assessment")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        risk_threshold = st.slider(
            "Compliance Risk Threshold",
            min_value=60,
            max_value=95,
            value=75,
            step=5,
            help="Minimum compliance score to accept job"
        )
    
    with col2:
        contingency = st.slider(
            "Contingency (%)",
            min_value=5,
            max_value=30,
            value=15,
            step=5,
            help="Contingency buffer for unknowns"
        )
    
    with col3:
        overhead = st.slider(
            "Overhead (%)",
            min_value=10,
            max_value=30,
            value=20,
            step=5,
            help="Overhead percentage"
        )
    
    # Margin calculator
    st.markdown("### Margin Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        estimated_cost = st.number_input(
            "Estimated Total Cost ($)",
            min_value=0,
            value=1000000,
            step=10000,
            help="Total estimated cost for all jobs"
        )
    
    with col2:
        target_margin = st.slider(
            "Target Profit Margin (%)",
            min_value=10,
            max_value=40,
            value=20,
            step=5
        )
    
    # Calculate recommended bid
    contingency_amount = estimated_cost * (contingency / 100)
    overhead_amount = estimated_cost * (overhead / 100)
    total_cost = estimated_cost + contingency_amount + overhead_amount
    min_bid = total_cost * (1 + target_margin / 100)
    
    # Display results
    st.markdown("### 💵 Bid Recommendation")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Base Cost", f"${estimated_cost:,.2f}")
    
    with col2:
        st.metric("Total Cost (with contingency/overhead)", f"${total_cost:,.2f}")
    
    with col3:
        st.metric("**Recommended Bid**", f"${min_bid:,.2f}", delta=f"+{target_margin}% margin")
    
    # Profit security assessment
    profit = min_bid - total_cost
    roi = (profit / total_cost) * 100
    
    st.markdown("### Profit Security Assessment")
    
    if roi >= 20:
        st.success(f"✅ **SECURE** - Expected ROI: {roi:.1f}%")
    elif roi >= 15:
        st.warning(f"⚠️ **MODERATE** - Expected ROI: {roi:.1f}%")
    else:
        st.error(f"❌ **RISKY** - Expected ROI: {roi:.1f}%")

def executive_dashboard():
    """Executive dashboard with high-level metrics"""
    
    st.markdown('<p class="medium-font">📈 Executive Dashboard</p>', unsafe_allow_html=True)
    
    # Get list of recent bundles
    try:
        response = requests.get(f"{API_BASE_URL}/mega-bundle/list?limit=10")
        if response.status_code == 200:
            data = response.json()
            bundles = data.get('bundles', [])
            
            if bundles:
                # Summary metrics across all bundles
                total_jobs = sum(b.get('total_jobs', 0) for b in bundles)
                total_profit = sum(b.get('total_profit', 0) for b in bundles)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Bundles", len(bundles))
                
                with col2:
                    st.metric("Total Jobs Analyzed", f"{total_jobs:,}")
                
                with col3:
                    st.metric("Total Profit Potential", f"${total_profit:,.2f}")
                
                # Bundle comparison table
                st.markdown("### Recent Bundle Analyses")
                
                df = pd.DataFrame(bundles)
                if not df.empty:
                    df['created'] = pd.to_datetime(df['created']).dt.strftime('%Y-%m-%d %H:%M')
                    st.dataframe(
                        df[['bundle_id', 'created', 'mode', 'total_jobs', 'total_profit', 'profit_margin']],
                        use_container_width=True
                    )
                    
                    # Profit trend chart
                    fig = px.line(
                        df,
                        x='created',
                        y='total_profit',
                        title="Profit Trend Across Bundles",
                        markers=True
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No bundles analyzed yet. Upload a bundle to get started!")
                
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")

if __name__ == "__main__":
    main()
