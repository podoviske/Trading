import streamlit as st
import pandas as pd
from supabase import create_client
import time

# --- 1. CONEXÃO ---
def get_supabase():
    try:
        if "supabase" in st.session_state: return st.session_state["supabase"]
        else:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
    except: return None

def load_trades_db():
    try:
        sb = get_supabase()
        res = sb.table("trades").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['created_at'] = pd.to_datetime(df['created_at'])
            if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
            # Garante float para exibição
            df['resultado'] = df['resultado'].astype(float)
            df['lote'] = df['lote'].astype(float)
            df['pts_medio'] = df['pts_medio'].astype(float)
        return df
    except: return pd.DataFrame()

# --- 2. CSS ESPECÍFICO DOS CARDS (Trazido da v201) ---
# Injetamos aqui para garantir que funcione mesmo se o main.css falhar
st.markdown("""
    <style>
    .trade-card {
        background-color: #161616;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 15px;
        border: 1px solid #333;
        transition: transform 0.2s, border-color 0.2s;
    }
    .trade-card:hover {
        transform: translateY(-3px);
        border-color: #B20000;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .card-img-container {
        width: 100%; height: 140px; background-color: #222;
        border-radius: 5px; overflow: hidden; display: flex;
        align-items: center; justify-content: center; margin-bottom: 10px;
    }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 14px; font-weight: 700; color: white; margin-bottom: 2px; }
    .card-sub { font-size: 11px; color: #888; margin-bottom: 8px; }
    
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }
    </style>
""", unsafe_allow_html=True)

# --- 3. POP-UP DE DETALHES (DIALOG) ---
@st.dialog("Detalhes da Operação", width="large")
def show_trade_details(row, user, role):
    # Área da Imagem (Full Screen Nativo do Streamlit)
    if row.get('prints'):
        st.markdown("### 📸 Evidência")
        # O use_container_width=True ativa o comportamento responsivo
        # O usuário pode clicar nas setas de expansão nativas da imagem
        st.image(row['prints'], use_container_width=True)
    else:
        st.info("Sem Print disponível.")
    
    st.markdown("---")
    
    # Grid de Informações
    c1, c2, c3 = st.columns(3)
    
    # Coluna 1
    c1.markdown(f"**📅 Data:** {row['data']}")
    c1.markdown(f"**📈 Ativo:** {row['ativo']}")
    c1.markdown(f"**📂 Grupo:** {row['grupo_vinculo']}")
    
    # Coluna 2
    c2.markdown(f"**⚖️ Lote:** {row['lote']}")
    c2.markdown(f"**🎯 Pontos:** {row['pts_medio']:.2f} pts")
    c2.markdown(f"**🔄 Direção:** {row['direcao']}")
    
    # Coluna 3
    c3.markdown(f"**🧠 Contexto:** {row['contexto']}")
    c3.markdown(f"**🧘 Estado:** {row.get('comportamento', '-')}")
    
    st.markdown("---")
    
    # Resultado Gigante
    res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
    st.markdown(f"<h1 style='color:{res_c}; text-align:center; font-size:50px; margin:0;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botão de Excluir
    if st.button("🗑️ DELETAR REGISTRO PERMANENTEMENTE", type="primary", use_container_width=True):
        sb = get_supabase()
        sb.table("trades").delete().eq("id", row['id']).execute()
        st.toast("Registro deletado!", icon="🗑️")
        time.sleep(1)
        st.rerun()

# --- 4. TELA PRINCIPAL (GALERIA) ---
def show(user, role):
    st.title("📜 Galeria de Trades")
    
    dfh = load_trades_db()
    
    # Filtra pelo usuário logado
    if not dfh.empty:
        dfh = dfh[dfh['usuario'] == user]
    
    if not dfh.empty:
        # --- BARRA DE FILTROS (Igual v201) ---
        with st.expander("🔍 Filtros", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            
            # Filtros Dinâmicos
            all_assets = sorted(list(dfh['ativo'].unique())) if 'ativo' in dfh.columns else ["NQ", "MNQ"]
            all_contexts = sorted(list(dfh['contexto'].unique())) if 'contexto' in dfh.columns else []
            all_groups = sorted(list(dfh['grupo_vinculo'].unique())) if 'grupo_vinculo' in dfh.columns else []
            
            fa = c1.multiselect("Ativo", all_assets)
            fr = c2.selectbox("Resultado", ["Todos", "Wins", "Losses"])
            fc = c3.multiselect("Contexto", all_contexts)
            fg = c4.multiselect("Grupo", all_groups)
            
            # Aplicação dos Filtros
            if fa: dfh = dfh[dfh['ativo'].isin(fa)]
            if fc: dfh = dfh[dfh['contexto'].isin(fc)]
            if fg: dfh = dfh[dfh['grupo_vinculo'].isin(fg)]
            if fr == "Wins": dfh = dfh[dfh['resultado'] > 0]
            if fr == "Losses": dfh = dfh[dfh['resultado'] < 0]
            
            # Ordenação: Mais recente primeiro
            dfh = dfh.sort_values('created_at', ascending=False)

        st.markdown(f"**Exibindo {len(dfh)} operações**")
        st.markdown("---")

        # --- GRID DE CARDS ---
        # Cria um grid de 4 colunas
        cols = st.columns(4)
        
        for i, (index, row) in enumerate(dfh.iterrows()):
            # Define em qual coluna o card vai cair (0, 1, 2 ou 3)
            col_idx = i % 4
            
            with cols[col_idx]:
                # Prepara dados visuais
                res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                res_fmt = f"${row['resultado']:,.2f}"
                
                # HTML da Imagem (Fallback se não tiver print)
                if row.get('prints'):
                    img_html = f'<img src="{row["prints"]}" class="card-img">' 
                else:
                    img_html = '<div style="width:100%; height:100%; background:#222; display:flex; align-items:center; justify-content:center; color:#555; font-size:12px;">Sem Foto</div>'
                
                # Renderiza o Card HTML
                st.markdown(f"""
                    <div class="trade-card">
                        <div class="card-img-container">{img_html}</div>
                        <div class="card-title">{row['ativo']} - {row['direcao']}</div>
                        <div class="card-sub">{row['data']} • {row['grupo_vinculo']}</div>
                        <div class="{res_class}">{res_fmt}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Botão "Ver" (Abre o Pop-up)
                if st.button("👁️ Detalhes", key=f"btn_{row['id']}", use_container_width=True):
                    show_trade_details(row, user, role)
                    
    else:
        st.info("Nenhuma operação registrada ainda. Vá em 'Registrar Trade' para começar!")
