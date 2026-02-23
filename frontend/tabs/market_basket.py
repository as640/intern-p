import streamlit as st

def render(ai):
    st.title("Market Basket Analysis")
    st.write("Identify product associations and cross-selling opportunities based on historical purchasing patterns.")
    
    df_assoc = ai.get_associations()
    
    # SEARCH BAR
    search_term = st.text_input("Search Product Database", "")
    
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
        st.subheader(f"Association Rules ({len(filtered_assoc)} records)")
        st.dataframe(
            filtered_assoc, 
            column_config={
                "product_a": "Primary Item",
                "product_b": "Associated Item",
                "times_bought_together": st.column_config.NumberColumn("Transaction Frequency")
            },
            use_container_width=True,
            hide_index=True
        )
        
    with col2:
        st.info("**Application:**")
        st.write("Utilize these associations to recommend statistically relevant additions to the partner's current invoice.")