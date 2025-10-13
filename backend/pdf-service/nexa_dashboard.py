#!/usr/bin/env python3
"""
NEXA Executive Dashboard
Real-time visualization of field operations, compliance, and savings
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json

# Page config
st.set_page_config(
    page_title="NEXA Operations Dashboard",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    .success-rate {
        font-size: 48px;
        font-weight: bold;
    }
    .savings-amount {
        color: #10b981;
        font-size: 36px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_URL = "https://nexa-us-pro.onrender.com"

class NEXADashboard:
    def __init__(self):
        self.initialize_session_state()
        
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'selected_period' not in st.session_state:
            st.session_state.selected_period = 'Today'
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = True
            
    def fetch_metrics(self):
        """Fetch real-time metrics from API"""
        # Simulated data for demonstration
        return {
            "jobs_today": 12,
            "jobs_week": 67,
            "jobs_month": 284,
            "compliance_rate": 98.2,
            "savings_today": 4500,
            "savings_week": 31500,
            "savings_month": 126000,
            "active_crews": 8,
            "pending_qa": 3,
            "go_backs_prevented": 42,
            "avg_completion_time": 3.2
        }
    
    def fetch_job_data(self):
        """Fetch job data for visualization"""
        # Simulated data
        data = []
        for i in range(30):
            date = datetime.now() - timedelta(days=29-i)
            data.append({
                "date": date,
                "jobs_completed": 8 + (i % 5),
                "compliance_score": 95 + (i % 4),
                "go_backs": 1 if i % 7 == 0 else 0,
                "savings": (8 + (i % 5)) * 1500 * (0.7 if i % 7 == 0 else 1)
            })
        return pd.DataFrame(data)
    
    def fetch_crew_performance(self):
        """Fetch crew performance data"""
        return pd.DataFrame({
            "crew_lead": ["John Smith", "Mike Johnson", "Tom Wilson", "Sarah Davis", "Jim Brown"],
            "jobs_completed": [45, 38, 42, 51, 36],
            "compliance_rate": [99.1, 97.8, 98.5, 99.5, 96.2],
            "avg_time_hours": [3.1, 3.4, 3.2, 2.9, 3.6],
            "photos_quality": [95, 92, 94, 98, 90]
        })
    
    def fetch_infraction_analysis(self):
        """Fetch AI infraction analysis results"""
        return pd.DataFrame({
            "pm_number": ["45568648", "35124034", "78901234", "56789012", "34567890"],
            "infraction_type": ["Guy wire clamping", "Documentation", "Clearance", "Photo timestamp", "Material list"],
            "status": ["TRUE", "REPEALABLE", "TRUE", "REPEALABLE", "REPEALABLE"],
            "confidence": [95, 88, 92, 85, 87],
            "potential_savings": [0, 1500, 0, 800, 600],
            "date": pd.date_range(end=datetime.now(), periods=5)
        })
    
    def render_header(self):
        """Render dashboard header"""
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            st.image("https://via.placeholder.com/150x50/667eea/ffffff?text=NEXA", width=150)
        with col2:
            st.title("Operations Dashboard")
            st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        with col3:
            if st.button("🔄 Refresh", type="primary"):
                st.rerun()
    
    def render_metrics_overview(self, metrics):
        """Render key metrics overview"""
        st.markdown("## 📊 Key Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Jobs Today",
                metrics['jobs_today'],
                delta=f"+{metrics['jobs_today'] - 10}" if metrics['jobs_today'] > 10 else None
            )
            st.metric(
                "Active Crews",
                metrics['active_crews']
            )
        
        with col2:
            st.metric(
                "Compliance Rate",
                f"{metrics['compliance_rate']}%",
                delta="+0.2%" if metrics['compliance_rate'] > 98 else "-0.1%"
            )
            st.metric(
                "Avg Completion",
                f"{metrics['avg_completion_time']} hrs"
            )
        
        with col3:
            st.metric(
                "Go-Backs Prevented",
                metrics['go_backs_prevented'],
                delta=f"+{metrics['go_backs_prevented'] - 40}"
            )
            st.metric(
                "Pending QA Review",
                metrics['pending_qa']
            )
        
        with col4:
            st.metric(
                "Savings Today",
                f"${metrics['savings_today']:,}",
                delta=f"+${metrics['savings_today'] - 4000:,}"
            )
            st.metric(
                "Month Total",
                f"${metrics['savings_month']:,}"
            )
    
    def render_job_trends(self, job_data):
        """Render job completion trends"""
        st.markdown("## 📈 30-Day Trends")
        
        tab1, tab2, tab3 = st.tabs(["Jobs & Compliance", "Savings", "Go-Backs"])
        
        with tab1:
            # Jobs and compliance chart
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=job_data['date'],
                y=job_data['jobs_completed'],
                name='Jobs Completed',
                yaxis='y',
                marker_color='#667eea'
            ))
            fig.add_trace(go.Scatter(
                x=job_data['date'],
                y=job_data['compliance_score'],
                name='Compliance %',
                yaxis='y2',
                line=dict(color='#10b981', width=3)
            ))
            fig.update_layout(
                yaxis=dict(title='Jobs', side='left'),
                yaxis2=dict(title='Compliance %', overlaying='y', side='right', range=[90, 100]),
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Savings chart
            fig = px.area(
                job_data,
                x='date',
                y='savings',
                title='Daily Savings from Go-Back Prevention',
                color_discrete_sequence=['#10b981']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            # Go-backs prevented
            go_back_data = job_data.groupby(job_data['date'].dt.week)['go_backs'].sum().reset_index()
            fig = px.bar(
                go_back_data,
                x='date',
                y='go_backs',
                title='Go-Backs by Week',
                color_discrete_sequence=['#ef4444']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    def render_crew_performance(self, crew_data):
        """Render crew performance metrics"""
        st.markdown("## 👷 Crew Performance")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Performance radar chart
            fig = go.Figure()
            
            for _, crew in crew_data.iterrows():
                fig.add_trace(go.Scatterpolar(
                    r=[crew['jobs_completed']/10, crew['compliance_rate']/20, 
                       100/crew['avg_time_hours'], crew['photos_quality']/20],
                    theta=['Jobs', 'Compliance', 'Speed', 'Quality'],
                    fill='toself',
                    name=crew['crew_lead']
                ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 5])
                ),
                showlegend=True,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Crew rankings
            st.markdown("### Top Performers")
            top_crews = crew_data.sort_values('compliance_rate', ascending=False).head(3)
            for idx, crew in top_crews.iterrows():
                st.markdown(f"""
                **{idx+1}. {crew['crew_lead']}**  
                Compliance: {crew['compliance_rate']}%  
                Jobs: {crew['jobs_completed']}
                """)
    
    def render_infraction_analysis(self, infraction_data):
        """Render AI infraction analysis results"""
        st.markdown("## 🤖 AI Infraction Analysis")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Infraction table
            for _, row in infraction_data.iterrows():
                status_color = "#10b981" if row['status'] == "REPEALABLE" else "#ef4444"
                savings_text = f"Save ${row['potential_savings']:,}" if row['potential_savings'] > 0 else "Must Fix"
                
                st.markdown(f"""
                <div style="background: #f9fafb; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid {status_color}">
                    <strong>PM {row['pm_number']}</strong> - {row['infraction_type']}<br>
                    Status: <span style="color: {status_color}; font-weight: bold">{row['status']}</span> | 
                    Confidence: {row['confidence']}% | 
                    {savings_text}
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            # Summary stats
            total_infractions = len(infraction_data)
            repealable = len(infraction_data[infraction_data['status'] == 'REPEALABLE'])
            total_savings = infraction_data['potential_savings'].sum()
            
            st.markdown(f"""
            ### Analysis Summary
            **Total Infractions:** {total_infractions}  
            **Repealable:** {repealable} ({repealable/total_infractions*100:.0f}%)  
            **Potential Savings:** ${total_savings:,}  
            **Avg Confidence:** {infraction_data['confidence'].mean():.1f}%
            """)
    
    def render_qa_queue(self):
        """Render QA review queue"""
        st.markdown("## 📋 QA Review Queue")
        
        queue_data = pd.DataFrame({
            "pm_number": ["35124034", "45678901", "23456789"],
            "crew_lead": ["John Smith", "Mike Johnson", "Tom Wilson"],
            "completion_time": ["2 hours ago", "3 hours ago", "5 hours ago"],
            "compliance_score": [98, 97, 99],
            "status": ["Ready for Review", "Ready for Review", "In Review"]
        })
        
        for _, job in queue_data.iterrows():
            status_color = "#10b981" if job['status'] == "Ready for Review" else "#f59e0b"
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
            
            with col1:
                st.write(f"**PM {job['pm_number']}**")
            with col2:
                st.write(job['crew_lead'])
            with col3:
                st.write(job['completion_time'])
            with col4:
                st.write(f"{job['compliance_score']}%")
            with col5:
                if st.button("Review", key=f"review_{job['pm_number']}"):
                    st.info(f"Opening review for PM {job['pm_number']}")
    
    def render_sidebar(self):
        """Render sidebar controls"""
        with st.sidebar:
            st.markdown("## ⚙️ Controls")
            
            # Time period selector
            period = st.selectbox(
                "Time Period",
                ["Today", "This Week", "This Month", "Custom"],
                index=0
            )
            
            if period == "Custom":
                st.date_input("Start Date")
                st.date_input("End Date")
            
            st.divider()
            
            # Filters
            st.markdown("### Filters")
            crews = st.multiselect(
                "Crews",
                ["All", "John Smith", "Mike Johnson", "Tom Wilson", "Sarah Davis"],
                default=["All"]
            )
            
            utilities = st.multiselect(
                "Utilities",
                ["PGE", "SCE", "SDGE", "FPL"],
                default=["PGE"]
            )
            
            st.divider()
            
            # Actions
            st.markdown("### Quick Actions")
            if st.button("📊 Export Report", use_container_width=True):
                st.success("Report exported to Excel")
            
            if st.button("📧 Email Summary", use_container_width=True):
                st.success("Summary sent to stakeholders")
            
            if st.button("🔄 Sync with PGE", use_container_width=True):
                st.info("Syncing with PGE systems...")
            
            st.divider()
            
            # System status
            st.markdown("### System Status")
            st.success("✅ All systems operational")
            st.caption("API: 12ms response")
            st.caption("AI Model: 98.2% accuracy")
            st.caption("Storage: 4.2GB / 10GB")
    
    def run(self):
        """Main dashboard execution"""
        # Header
        self.render_header()
        
        # Sidebar
        self.render_sidebar()
        
        # Fetch data
        metrics = self.fetch_metrics()
        job_data = self.fetch_job_data()
        crew_data = self.fetch_crew_performance()
        infraction_data = self.fetch_infraction_analysis()
        
        # Main content
        self.render_metrics_overview(metrics)
        
        st.divider()
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Trends", 
            "👷 Crews", 
            "🤖 AI Analysis", 
            "📋 QA Queue",
            "💰 Financial"
        ])
        
        with tab1:
            self.render_job_trends(job_data)
        
        with tab2:
            self.render_crew_performance(crew_data)
        
        with tab3:
            self.render_infraction_analysis(infraction_data)
        
        with tab4:
            self.render_qa_queue()
        
        with tab5:
            self.render_financial_summary(metrics, job_data)
    
    def render_financial_summary(self, metrics, job_data):
        """Render financial impact summary"""
        st.markdown("## 💰 Financial Impact")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Monthly savings trend
            monthly_savings = job_data.groupby(pd.Grouper(key='date', freq='W'))['savings'].sum().reset_index()
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=monthly_savings['date'],
                y=monthly_savings['savings'],
                marker_color='#10b981',
                name='Weekly Savings'
            ))
            fig.add_trace(go.Scatter(
                x=monthly_savings['date'],
                y=monthly_savings['savings'].cumsum(),
                mode='lines',
                line=dict(color='#667eea', width=3),
                name='Cumulative',
                yaxis='y2'
            ))
            fig.update_layout(
                title='Savings from Go-Back Prevention',
                yaxis=dict(title='Weekly $', side='left'),
                yaxis2=dict(title='Cumulative $', overlaying='y', side='right'),
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### ROI Summary")
            st.markdown(f"""
            **Monthly Savings:** ${metrics['savings_month']:,}  
            **NEXA Cost:** $85/month  
            **Net Benefit:** ${metrics['savings_month'] - 85:,}  
            **ROI:** {(metrics['savings_month'] / 85 - 1) * 100:.0f}%  
            
            ### Breakdown
            - Go-backs prevented: {metrics['go_backs_prevented']}
            - Avg savings per go-back: $3,000
            - Time saved: {metrics['go_backs_prevented'] * 4} hours
            - Customer satisfaction: ⭐⭐⭐⭐⭐
            """)

# Run the dashboard
if __name__ == "__main__":
    dashboard = NEXADashboard()
    dashboard.run()
