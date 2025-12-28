import streamlit as st
from modules import database, ui

def show(user, role):
    st.title("📜 Histórico")
    df = database.load_trades(user)
    
    if not df.empty:
        df = df.sort_values('created_at', ascending=False)
        for _, row in df.iterrows():
            res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
            st.markdown(f"""
            <div class="trade-card">
                <div style="display:flex; justify-content:space-between;">
                    <strong>{row['ativo']} ({row['direcao']})</strong>
                    <span class="{res_class}">${row['resultado']:,.2f}</span>
                </div>
                <small>{row['data']} | {row['grupo_vinculo']}</small>
            </div>
            """, unsafe_allow_html=True)
            if row.get('prints'): st.image(row['prints'], width=300)
    else:
        st.info("Histórico vazio.")
