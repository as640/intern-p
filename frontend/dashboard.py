import streamlit as st
import sys
import os

# Link to backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ml_engine.sales_model import SalesIntelligenceEngine

# Import Tabs
from tabs import partner_360, market_basket, inventory, clustering

# --- PAGE SETUP ---
st.set_page_config(page_title="Consistent AI Suite", layout="wide", page_icon="🚀")

# --- INITIALIZE ENGINE ---
@st.cache_resource
def get_engine():
    engine = SalesIntelligenceEngine()
    engine.load_data()
    engine.run_clustering()
    return engine

try:
    ai = get_engine()
except Exception as e:
    st.error(f"Engine Failure: {e}")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("🎮 Command Center")

# Refresh Button (Crucial for live data)
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_resource.clear()
    st.rerun()

nav = st.sidebar.radio("Module", ["Partner 360° View", "Product Bundles (MBA)", "Inventory Liquidation", "Cluster Intelligence"])

# --- ROUTING LOGIC ---
if nav == "Partner 360° View":
    partner_360.render(ai)

elif nav == "Product Bundles (MBA)":
    market_basket.render(ai)

elif nav == "Inventory Liquidation":
    inventory.render(ai)

elif nav == "Cluster Intelligence":
    clustering.render(ai)