import streamlit as st

def render(ai):
    st.title("Partner 360° Overview")
    
    # 1. Region Filter
    all_states = sorted(ai.matrix['state'].unique())
    selected_state = st.selectbox("Select Region", all_states)
    
    # 2. Partner Filter
    filtered_partners = sorted(ai.matrix[ai.matrix['state'] == selected_state].index.unique())
    
    if not filtered_partners:
        st.warning("No partner records found for the selected region.")
    else:
        selected_partner = st.selectbox("Select Partner", filtered_partners)
        
        # 3. Get Intelligence from Backend
        report = ai.get_partner_intelligence(selected_partner)
        
        if report:
            facts = report['facts']
            gaps = report['gaps']
            cluster_name = report['cluster_label']
            
            # --- KPI CARDS ---
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                status = facts.get('health_status', 'Unknown')
                st.metric("Account Health", status)
                
            with col2:
                # True Variance (Positive = Green/Up, Negative = Red/Down)
                variance = facts.get('revenue_variance_pct', 0)
                st.metric(
                    label="90-Day Revenue Variance", 
                    value=f"{variance}%", 
                    delta=f"{variance}%"
                )
                
            with col3:
                monthly_pot = gaps['Potential_Revenue'].sum() if not gaps.empty else 0
                st.metric("Estimated Monthly Gap", f"₹{int(monthly_pot):,}")
                
            with col4:
                st.metric("Account Classification", cluster_name)

            st.markdown("---")

            # --- STRATEGY & BENCHMARKING SECTION ---
            left, right = st.columns([1, 1.5])
            
            with left:
                st.subheader("Account Strategy")
                
                # Market Basket Cross-Sell Logic
                pitch = facts.get('top_affinity_pitch', None)
                if pitch and pitch != "None" and pitch != "N/A":
                    st.info(f"**Recommended Cross-Sell:** {pitch}")
                    st.caption("Based on historical transaction associations.")
                else:
                    st.success("No immediate cross-sell anomalies detected.")
                
                # Smart Contextual Alerts for Account Health
                if "Churned" in status or "Risk" in status:
                    st.error("Account requires immediate attention. High risk of churn.")
                elif "Stable" in status:
                    st.warning("Account growth is stagnant. Recommend pitching associated items.")
                elif "New" in status:
                    st.success("Newly Onboarded Account. Focus on retention and initial experience.")

            with right:
                st.subheader("Peer Benchmarking")
                if not gaps.empty:
                    st.write(f"Comparative analysis against **{cluster_name}** segment:")
                    
                    # Cross-reference with Dead Stock for Liquidation Priority
                    dead_stock_list = ai.get_dead_stock()['dead_stock_item'].unique()
                    gaps['In_Dead_Stock'] = gaps['Product'].apply(
                        lambda x: "High (Overstocked)" if x in dead_stock_list else "Standard"
                    )
                    
                    # Display the DataFrame
                    st.dataframe(
                        gaps[['Product', 'Potential_Revenue', 'Partner_Share', 'Peer_Share', 'In_Dead_Stock']], 
                        column_config={
                            "Product": "Product Category",
                            "Potential_Revenue": st.column_config.NumberColumn("Estimated Gap", format="₹%d"),
                            "Partner_Share": st.column_config.NumberColumn("Current Share", format="%.1f%%"),
                            "Peer_Share": st.column_config.NumberColumn("Segment Average", format="%.1f%%"),
                            "In_Dead_Stock": "Liquidation Priority"
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Partner is performing at or above their segment average across all categories.")