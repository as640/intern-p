import streamlit as st

def render(ai):
    st.title("Inventory Liquidation Dashboard")
    
    df_dead = ai.get_dead_stock()
    
    # Filter: Only show items that match our SQL filter
    valid_items = ai.df_stock_stats['product_name'].unique()
    
    if len(valid_items) == 0:
        st.success("Inventory levels are optimal. No critical aging stock identified.")
        items = []
    else:
        items = sorted(valid_items)

    selected_item = st.selectbox("Select Aging SKU", items)
    
    # 1. Get Stock Stats
    stock_details = ai.get_stock_details(selected_item)
    
    if stock_details is not None:
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.metric("Current Inventory", f"{stock_details['total_stock_qty']} Units")
        with c2: 
            st.metric("Maximum Age", f"{stock_details['max_age_days']} Days")
        with c3: 
            is_critical = stock_details['max_age_days'] > 90
            st.metric("Priority Level", "Critical" if is_critical else "Standard", 
                     delta="Immediate Action" if is_critical else "Monitor",
                     delta_color="inverse")
    else:
        if selected_item:
            st.warning("Inventory details not found. Showing potential buyers only.")
    
    st.markdown("---")
    
    # 2. Get Leads
    if selected_item:
        leads = df_dead[df_dead['dead_stock_item'] == selected_item].sort_values('buyer_past_purchase_qty', ascending=False)
        st.subheader(f"Qualified Leads ({len(leads)} Identified)")
        
        st.dataframe(
            leads[['potential_buyer', 'mobile_no', 'buyer_past_purchase_qty', 'last_purchase_date']],
            column_config={
                "potential_buyer": "Partner Name",
                "mobile_no": "Contact Information",
                "buyer_past_purchase_qty": st.column_config.NumberColumn("Historical Volume"),
                "last_purchase_date": "Last Transaction Date"
            },
            use_container_width=True,
            hide_index=True
        )