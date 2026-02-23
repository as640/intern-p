import os
import urllib.parse
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.compose import ColumnTransformer

class SalesIntelligenceEngine:
    def __init__(self):
        # 1. Look for a cloud database URL first (For Railway Deployment)
        env_db_url = os.getenv("DATABASE_URL")
        
        if env_db_url:
            # SQLAlchemy requires 'postgresql://', but Railway sometimes gives 'postgres://'
            if env_db_url.startswith("postgres://"):
                env_db_url = env_db_url.replace("postgres://", "postgresql://", 1)
            self.db_url = env_db_url
        else:
            # 2. Fallback to your local database (For Local Testing)
            raw_pass = "Sheero@10"
            encoded_pass = urllib.parse.quote_plus(raw_pass)
            self.db_url = f'postgresql://postgres:{encoded_pass}@127.0.0.1:5432/dsr_live_db'
            
        self.engine = create_engine(self.db_url)
        
        self.df_ml = None
        self.df_fact = None
        self.matrix = None
        self.df_stock_stats = None 
        
    def load_data(self):
        """Loads critical data for analysis"""
        self.df_ml = pd.read_sql("SELECT * FROM view_ml_input", self.engine)
        self.df_fact = pd.read_sql("SELECT * FROM fact_sales_intelligence", self.engine).set_index('company_name')
        
        try:
            self.df_stock_stats = pd.read_sql("SELECT product_name, total_stock_qty, max_age_days FROM view_ageing_stock", self.engine)
        except:
            self.df_stock_stats = pd.DataFrame(columns=['product_name', 'total_stock_qty', 'max_age_days'])

    def _process_segment(self, subset_df, method='hdbscan'):
        """Helper to run clustering on a specific slice of data"""
        if subset_df.empty: return pd.Series()

        # 1. Pivot just this subset
        product_pivot = subset_df.pivot_table(index='company_name', columns='group_name', values='total_spend', fill_value=0)
        
        # 2. Map States
        state_map = subset_df[['company_name', 'state']].drop_duplicates('company_name').set_index('company_name')
        data_combined = product_pivot.join(state_map)
        
        # 3. Preprocess (Log + Scale + Encode State)
        numeric_cols = product_pivot.columns
        # Important: Log transform to handle huge value differences
        data_combined[numeric_cols] = np.log1p(data_combined[numeric_cols])

        preprocessor = ColumnTransformer(transformers=[
            ('num', RobustScaler(), numeric_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['state'])
        ])
        
        X = preprocessor.fit_transform(data_combined)
        
        # 4. Run Algorithm
        if method == 'kmeans':
            # Force Whales into 4 distinct groups
            model = KMeans(n_clusters=4, random_state=42)
            labels = model.fit_predict(X)
            return pd.Series([f"VIP-{l}" for l in labels], index=product_pivot.index)
            
        else: # HDBSCAN for the masses
            # 'leaf' method creates smaller, tighter clusters
            model = HDBSCAN(min_cluster_size=3, min_samples=2, metric='euclidean', cluster_selection_method='leaf')
            labels = model.fit_predict(X)
            return pd.Series([f"Growth-{l}" if l != -1 else "Growth-Outlier" for l in labels], index=product_pivot.index)

    def run_clustering(self):
        """Runs the Two-Tier Strategy"""
        if self.df_ml is None: self.load_data()

        # 1. Calculate Total Spend per Partner
        partner_totals = self.df_ml.groupby('company_name')['total_spend'].sum()
        
        # 2. Determine Cutoff (Pareto: Top 20%)
        cutoff = partner_totals.quantile(0.80)
        
        whales_list = partner_totals[partner_totals >= cutoff].index
        masses_list = partner_totals[partner_totals < cutoff].index
        
        # 3. Split the Main DataFrame
        df_whales = self.df_ml[self.df_ml['company_name'].isin(whales_list)]
        df_masses = self.df_ml[self.df_ml['company_name'].isin(masses_list)]
        
        print(f"Clustering {len(whales_list)} VIPs and {len(masses_list)} Standard Partners...")
        
        vip_labels = self._process_segment(df_whales, method='kmeans')
        growth_labels = self._process_segment(df_masses, method='hdbscan')
        
        # 4. Combine Results
        all_labels = pd.concat([vip_labels, growth_labels])
        
        # 5. Build Final Matrix for Dashboard
        self.matrix = self.df_ml.pivot_table(index='company_name', columns='group_name', values='total_spend', fill_value=0)
        self.matrix['state'] = self.df_ml[['company_name', 'state']].drop_duplicates('company_name').set_index('company_name')['state']
        
        # Map the calculated labels
        self.matrix['cluster'] = all_labels
        self.matrix['cluster'] = self.matrix['cluster'].fillna("Growth-Outlier")
        
        return self.matrix

    def get_partner_intelligence(self, partner_name):
        """Returns full partner report with WALLET SHARE comparison"""
        if partner_name not in self.matrix.index: return None

        # 1. Get Facts (Updated to use revenue_variance_pct)
        try: 
            facts = self.df_fact.loc[partner_name]
        except KeyError: 
            facts = pd.Series({'health_status': 'Unknown', 'revenue_variance_pct': 0, 'top_affinity_pitch': 'None'})

        cluster_id = self.matrix.loc[partner_name, 'cluster']
        gaps_df = pd.DataFrame()
        
        # 2. Peer Comparison (Wallet Share Logic)
        if "Outlier" not in cluster_id:
            # Get Peers in same cluster
            peers = self.matrix[self.matrix['cluster'] == cluster_id]
            
            # A. PEER WALLET SHARE (The Benchmark)
            peer_total_spend = peers.drop(columns=['cluster', 'state']).sum(axis=0)
            peer_total_budget = peer_total_spend.sum()
            
            if peer_total_budget > 0:
                peer_wallet_share = peer_total_spend / peer_total_budget
            else:
                peer_wallet_share = peer_total_spend * 0

            # B. PARTNER WALLET SHARE (The Current Status)
            partner_actual = self.matrix.loc[partner_name].drop(['cluster', 'state'])
            partner_total_budget = partner_actual.sum()
            
            if partner_total_budget > 0:
                partner_wallet_share = partner_actual / partner_total_budget
            else:
                partner_wallet_share = partner_actual * 0

            # C. Calculate Target Spend & Gap
            target_spend = peer_wallet_share * partner_total_budget
            raw_gap = target_spend - partner_actual
            
            # D. Convert to Monthly & Filter
            monthly_gaps = raw_gap / 9 
            valid_gaps = monthly_gaps[monthly_gaps > 2000].sort_values(ascending=False)

            if not valid_gaps.empty:
                gaps_df = pd.DataFrame({
                    'Product': valid_gaps.index,
                    'Potential_Revenue': valid_gaps.values,
                    # Show BOTH percentages now
                    'Partner_Share': (partner_wallet_share[valid_gaps.index] * 100).values,
                    'Peer_Share': (peer_wallet_share[valid_gaps.index] * 100).values
                })

        return {'facts': facts, 'gaps': gaps_df, 'cluster_label': cluster_id}
        
    def get_associations(self):
        return pd.read_sql("SELECT * FROM view_product_associations LIMIT 200", self.engine)

    def get_dead_stock(self):
        return pd.read_sql("SELECT * FROM view_stock_liquidation_leads", self.engine)
        
    def get_stock_details(self, product_name):
        if self.df_stock_stats is None or self.df_stock_stats.empty: return None
        row = self.df_stock_stats[self.df_stock_stats['product_name'] == product_name]
        if not row.empty: return row.iloc[0]
        return None