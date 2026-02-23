import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.decomposition import PCA
import numpy as np

def render(ai):
    st.title("Partner Segmentation Distribution")
    
    # Stats
    n_clusters = ai.matrix['cluster'].nunique() - 1 
    n_outliers = len(ai.matrix[ai.matrix['cluster'] == 'Growth-Outlier'])
    
    c1, c2 = st.columns(2)
    with c1: st.metric("Total Segments Formed", n_clusters)
    with c2: st.metric("Outlier Accounts", n_outliers)
    
    # 3D Plot Logic
    # Drop categorical/non-numeric for PCA
    viz_data = np.log1p(ai.matrix.drop(columns=['cluster', 'state'], errors='ignore'))
    pca = PCA(n_components=3)
    components = pca.fit_transform(viz_data)
    
    plot_df = pd.DataFrame(components, columns=['x', 'y', 'z'])
    plot_df['Partner'] = ai.matrix.index
    plot_df['Cluster'] = ai.matrix['cluster'].astype(str)
    plot_df['State'] = ai.matrix['state']
    
    fig = px.scatter_3d(
        plot_df, x='x', y='y', z='z', 
        color='Cluster', 
        symbol='State', 
        hover_name='Partner', 
        title="Segment Analysis (Color = Segment, Shape = Region)",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    st.plotly_chart(fig, use_container_width=True)