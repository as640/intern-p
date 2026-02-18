import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.cluster import HDBSCAN 
from sklearn.compose import ColumnTransformer
import urllib.parse

class SalesIntelligenceEngine:
    def __init__(self):
        # Database Connection (Secured)
        raw_pass = "Sheero@10"
        encoded_pass = urllib.parse.quote_plus(raw_pass)
        # Using 127.0.0.1 for stability on Mac/Linux
        self.db_url = f'postgresql://postgres:{encoded_pass}@127.0.0.1:5432/dsr_live_db'
        self.engine = create_engine(self.db_url)
        
        # Data Placeholders
        self.df_ml = None
        self.df_fact = None
        self.matrix = None
        self.df_stock_stats = None 
        
    def load_data(self):
        """Loads critical data for analysis"""
        # 1. Main Transaction Data (View ALREADY contains 'state')
        self.df_ml = pd.read_sql("SELECT * FROM view_ml_input", self.engine)
        
        # 2. Partner Intelligence Data (Health, Churn, Pitches)
        self.df_fact = pd.read_sql("SELECT * FROM fact_sales_intelligence", self.engine).set_index('company_name')
        
        # 3. Inventory Stats (For Liquidation Tab)
        try:
            self.df_stock_stats = pd.read_sql("SELECT product_name, total_stock_qty, max_age_days FROM view_ageing_stock", self.engine)
        except:
            self.df_stock_stats = pd.DataFrame(columns=['product_name', 'total_stock_qty', 'max_age_days'])

    def run_clustering(self):
        """Runs HDBSCAN Clustering with State Logic"""
        if self.df_ml is None: self.load_data()

        # Pivot the data (Rows=Companies, Cols=Product Groups)
        product_pivot = self.df_ml.pivot_table(index='company_name', columns='group_name', values='total_spend', fill_value=0)
        
        # Map States (Trusting the SQL View)
        # We perform a group-by or drop_duplicates to ensure unique index
        state_map = self.df_ml[['company_name', 'state']].drop_duplicates('company_name').set_index('company_name')
        
        # Join Spending Data + Location Data
        data_combined = product_pivot.join(state_map)
        
        # Log & Scale
        numeric_cols = product_pivot.columns
        data_combined[numeric_cols] = np.log1p(data_combined[numeric_cols])

        # Preprocess: Scale Numbers, Encode States
        preprocessor = ColumnTransformer(transformers=[
            ('num', RobustScaler(), numeric_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['state'])
        ])
        
        X = preprocessor.fit_transform(data_combined)
        
        # HDBSCAN Clustering
        hdb = HDBSCAN(min_cluster_size=3, min_samples=2, metric='euclidean')
        
        self.matrix = product_pivot
        self.matrix['cluster'] = hdb.fit_predict(X)
        self.matrix['state'] = data_combined['state']
        
        return self.matrix

    def get_partner_intelligence(self, partner_name):
        """Returns full partner report"""
        if partner_name not in self.matrix.index: return None

        # Static Data
        try: facts = self.df_fact.loc[partner_name]
        except KeyError: facts = pd.Series({'health_status': 'Unknown', 'revenue_drop_pct': 0, 'top_affinity_pitch': 'None'})

        # Dynamic Gaps
        cluster_id = self.matrix.loc[partner_name, 'cluster']
        gaps_df = pd.DataFrame()
        cluster_label = "Outlier"

        if cluster_id != -1:
            cluster_label = f"Cluster {cluster_id}"
            peers = self.matrix[self.matrix['cluster'] == cluster_id].drop(index=partner_name)
            
            if not peers.empty:
                # Exclude non-numeric cols for averaging
                peer_avg = peers.drop(columns=['cluster', 'state']).mean()
                partner_actual = self.matrix.loc[partner_name].drop(['cluster', 'state'])
                
                diff = peer_avg - partner_actual
                valid_gaps = diff[diff > 10000].sort_values(ascending=False)
                
                if not valid_gaps.empty:
                    gaps_df = pd.DataFrame({
                        'Product': valid_gaps.index,
                        'Potential_Revenue': valid_gaps.values,
                        'Peer_Avg_Spend': peer_avg[valid_gaps.index].values
                    })

        return {'facts': facts, 'gaps': gaps_df, 'cluster_label': cluster_label}

    def get_associations(self):
        return pd.read_sql("SELECT * FROM view_product_associations LIMIT 200", self.engine)

    def get_dead_stock(self):
        return pd.read_sql("SELECT * FROM view_stock_liquidation_leads", self.engine)
        
    def get_stock_details(self, product_name):
        """Get the specific stats for a dead stock item"""
        if self.df_stock_stats is None or self.df_stock_stats.empty:
            return None
        
        row = self.df_stock_stats[self.df_stock_stats['product_name'] == product_name]
        if not row.empty:
            return row.iloc[0]
        return None