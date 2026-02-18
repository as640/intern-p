import streamlit as st

def render(ai):
    st.title("Partner 360° Analysis")
    
    # 1. State Filter
    all_states = sorted(ai.matrix['state'].unique())
    selected_state = st.selectbox("Step 1: Select State/Region", all_states)
    
    # 2. Partner Filter (Based on State)
    filtered_partners = sorted(ai.matrix[ai.matrix['state'] == selected_state].index.unique())
    
    if not filtered_partners:
        st.warning("No partners found in this state with recent activity.")
    else:
        selected_partner = st.selectbox("Step 2: Select Partner", filtered_partners)
        
        # 3. Get Intelligence
        report = ai.get_partner_intelligence(selected_partner)
        
        if report:
            facts = report['facts']
            gaps = report['gaps']
            cluster_name = report['cluster_label']
            
            # KPI Cards
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                status = facts.get('health_status', 'Unknown')
                color = "green" if "Healthy" in status else "red"
                st.markdown(f"**Health Status**: :{color}[**{status}**]")
            with col2:
                drop = facts.get('revenue_drop_pct', 0)
                st.metric("Revenue Drop", f"{drop}%", delta=f"-{drop}%", delta_color="inverse")
            with col3:
                total_pot = gaps['Potential_Revenue'].sum() if not gaps.empty else 0
                st.metric("🔓 Unlocked Potential", f"₹{int(total_pot):,}")
            with col4:
                st.metric("AI Segment", cluster_name)

            st.markdown("---")

            # Strategy Section
            left, right = st.columns([1, 1.5])
            with left:
                st.subheader("🛡️ Retention Strategy")
                pitch = facts.get('top_affinity_pitch', None)
                if pitch and pitch != "None" and pitch != "N/A":
                    st.info(f"**🔥 Pitch This:** {pitch}")
                    st.caption("Reason: Frequent buyer of associated items.")
                else:
                    st.success("✅ No immediate missed attachments.")
                    
                if "Healthy" not in status:
                    st.error(f"⚠️ **Action:** {status}")

            with right:
                st.subheader("🚀 Peer Gap Analysis")
                if not gaps.empty:
                    st.write(f"Comparisons against **{cluster_name}** peers:")
                    st.dataframe(
                        gaps[['Product', 'Potential_Revenue', 'Peer_Avg_Spend']],
                        column_config={
                            "Product": "Missing Category",
                            "Potential_Revenue": st.column_config.NumberColumn("Potential Gain", format="₹%d"),
                            "Peer_Avg_Spend": st.column_config.NumberColumn("Cluster Avg", format="₹%d"),
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    if cluster_name == "Outlier":
                        st.warning("Partner is an Outlier (Unique buying pattern).")
                    else:
                        st.balloons()
                        st.success("🌟 Perfect Account! Matches peer average.")