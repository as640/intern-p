import streamlit as st
import sys
import os

# Link to backend (ml_engine)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ml_engine.sales_model import SalesIntelligenceEngine

# Import Tabs
from tabs import partner_360, market_basket, inventory, clustering

# --- PAGE SETUP ---
st.set_page_config(page_title="Sales Intelligence Suite", layout="wide")

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
    st.error(f"System Initialization Error: {e}")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("Navigation")

# Refresh Button
if st.sidebar.button("Refresh Data"):
    st.cache_resource.clear()
    st.rerun()

nav = st.sidebar.radio("Modules", [
    "Partner 360° Overview", 
    "Market Basket Analysis", 
    "Inventory Liquidation", 
    "Partner Segmentation"
])

# --- ROUTING LOGIC ---
if nav == "Partner 360° Overview":
    partner_360.render(ai)

elif nav == "Market Basket Analysis":
    market_basket.render(ai)

elif nav == "Inventory Liquidation":
    inventory.render(ai)

elif nav == "Partner Segmentation":
    clustering.render(ai)