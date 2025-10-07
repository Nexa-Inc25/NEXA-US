"""
Simple health check script for Render
"""
import streamlit as st

st.set_page_config(page_title="Health Check", page_icon="✅")
st.title("Health Check")
st.success("Service is healthy!")
st.json({"status": "healthy", "service": "NEXA Document Intelligence"})
