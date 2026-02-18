import streamlit as st

def render(ai):
    st.title("🧹 Inventory Liquidation War Room")
    
    df_dead = ai.get_dead_stock()
    
    # Filter: Only show items that match our SQL filter (>10 Qty, >60 Days)
    valid_items = ai.df_stock_stats['product_name'].unique()
    
    if len(valid_items) == 0:
        st.success("🎉 No Critical Dead Stock Found! (Nothing > 60 days & 10 units)")
        items = []
    else:
        # Sort items alphabetically
        items = sorted(valid_items)

    selected_item = st.selectbox("Select Dead Stock Item to Clear", items)
    
    # 1. Get Stock Stats
    stock_details = ai.get_stock_details(selected_item)
    
    if stock_details is not None:
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.metric("📦 Total Stock Left", f"{stock_details['total_stock_qty']} Units")
        with c2: 
            st.metric("⏳ Max Age", f"{stock_details['max_age_days']} Days")
        with c3: 
            is_critical = stock_details['max_age_days'] > 180
            st.metric("⚠️ Priority", "Critical" if is_critical else "High", 
                     delta="Action Needed" if is_critical else "Plan Sales",
                     delta_color="inverse")
    else:
        if selected_item:
            st.warning("Stock details not found in ageing view. Showing potential buyers only.")
    
    st.markdown("---")
    
    # 2. Get Leads
    if selected_item:
        leads = df_dead[df_dead['dead_stock_item'] == selected_item].sort_values('buyer_past_purchase_qty', ascending=False)
        st.subheader(f"Target Buyers ({len(leads)} Found)")
        
        st.dataframe(
            leads[['potential_buyer', 'mobile_no', 'buyer_past_purchase_qty', 'last_purchase_date']],
            column_config={
                "potential_buyer": "Partner Name",
                "mobile_no": "Contact Number",
                "buyer_past_purchase_qty": st.column_config.NumberColumn("Past Qty Bought"),
                "last_purchase_date": "Last Purchase"
            },
            use_container_width=True,
            hide_index=True
        )