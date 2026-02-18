import streamlit as st

def render(ai):
    st.title("🛒 Market Basket Analysis")
    st.write("Find 'Frequently Bought Together' items.")
    
    df_assoc = ai.get_associations()
    
    # SEARCH BAR
    search_term = st.text_input("🔍 Search for a Product (e.g., 'HDD', 'Camera')", "")
    
    # Filter Logic
    if search_term:
        filtered_assoc = df_assoc[
            df_assoc['product_a'].str.contains(search_term, case=False) | 
            df_assoc['product_b'].str.contains(search_term, case=False)
        ]
    else:
        filtered_assoc = df_assoc

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Association Rules ({len(filtered_assoc)} found)")
        st.dataframe(
            filtered_assoc, 
            column_config={
                "product_a": "If they buy...",
                "product_b": "...Pitch this!",
                "times_bought_together": st.column_config.NumberColumn("Frequency")
            },
            use_container_width=True,
            hide_index=True
        )
        
    with col2:
        st.info("💡 **Sales Script:**")
        st.write("""
        "Sir, most customers who buy [Product A] also pick up [Product B]. Should I add that to your order?"
        """)