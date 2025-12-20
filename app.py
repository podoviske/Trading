import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
import json
import time
from PIL import Image

# --- CONFIGURAÇÃO E DIRETÓRIOS ---
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

IMG_DIR = "trade_prints"
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

# --- ESTILO CSS PROFISSIONAL (CORREÇÃO DE ENQUADRAMENTO) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    
    /* Grid da Galeria */
    .trade-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 12px;
        margin-bottom: 20px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        transition: transform 0.2s;
    }
    .trade-card:hover { border-color: #B20000; transform: translateY(-3px); }

    /* Janela de Imagem Fixa (Estilo Janela de Prédio) */
    .img-container {
        width: 100%;
        height: 180px;
        background-color: #111;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        border-bottom: 1px solid #333;
    }
    
    .img-container img {
        width: 100%;
        height: 100%;
        object-fit: cover; /* Corta a imagem para preencher o quadro sem distorcer */
    }

    .info-padding { padding: 15px; text-align: center; }
    .stButton > button { width: 100%; border-radius: 8px; }
    
    /* Pop-up Dialog */
    div[data-testid="stDialog"] div[role="dialog"] {
        background-color: #0F0F0F !important;
        border: 1px solid #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def load_atm():
    if os.path.exists(ATM_FILE):
        try:
            with open(ATM_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"Personalizado": {"lote": 1, "stop": 0.0, "parciais": []}} # Lote inicial 1 para evitar erro

def save_atm(configs):
    with open(ATM_FILE, 'w') as f: json.dump(configs, f)

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID', 'Prints']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'ID' not in df.columns: df['ID'] = [f"ID_{int(time.time())}_{i}" for i in range(len(df))]
            if 'Prints' not in df.columns: df['Prints'] = ""
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

atm_db = load_atm()
df = load_data()

# --- POP-UP DE DETALHES ---
@st.dialog("Detalhes da Operação", width="large")
def show_details(trade_id):
    row = df[df['ID'] == trade_id].iloc[0]
    col_img, col_txt = st.columns([2, 1])
    
    with col_img:
        p_list = str(row['Prints']).split("|") if row['Prints'] and pd.notna(row['Prints']) else []
        if p_list and os.path.exists(p_list[0]):
            st.image(p_list[0], use_container_width=True)
        else:
            st.info("Nenhum print anexado.")
            
    with col_txt:
        st.subheader(f"Trade #{df[df['ID'] == trade_id].index[0] + 1}")
        st.write(f"**Data:** {row['Data']}")
        st.write(f"**Ativo:** {row['Ativo']} | **Direção:** {row['Direcao']}")
        res_color = "green" if row['Resultado'] > 0 else "red"
        st.markdown(f"**Resultado:** :{res_color}[${row['Resultado']:,.2f}]")
        st.write(f"**Contexto:** {row['Contexto']}")
        st.write(f"**Estratégia:** {row['ATM']}")
        
        st.divider()
        if st.button("Excluir Trade", type="secondary"):
            st.session_state.to_delete = trade_id
            st.rerun()

# --- MENU LATERAL ---
with st.sidebar:
    st.markdown('<div style="padding:20px 10px"><span style="color:#B20000; font-size:28px; font-weight:900">EVO</span><span style="color:white; font-size:24px; font-weight:700">TRADE</span></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], default_index=1)

# --- PÁGINA: REGISTRAR TRADE ---
if selected == "Registrar Trade":
    st.title("Registro de Trade")
    atm_sel = st.selectbox("🎯 Estratégia ATM", options=list(atm_db.keys()))
    config = atm_db[atm_sel]
    
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
    with c2:
        # CORREÇÃO DO ERRO DE VALOR MÍNIMO
        val_lote = int(config.get("lote", 1))
        lote_t = st.number_input("Lote Total", min_value=1, value=max(1, val_lote))
        stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config.get("stop", 0)))
        st.metric("Risco Total", f"${(stop_p * MULTIPLIERS[ativo] * lote_t):,.2f}")
        up_files = st.file_uploader("📸 Anexar Prints", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
    
    # ... (Lógica de saídas mantida) ...

# --- PÁGINA: HISTÓRICO (CORREÇÃO DOS "BURACOS") ---
elif selected == "Histórico":
    st.title("📜 Galeria de Operações")
    
    if 'to_delete' in st.session_state:
        df = df[df['ID'] != st.session_state.to_delete]
        df.to_csv(CSV_FILE, index=False)
        del st.session_state.to_delete
        st.rerun()

    if not df.empty:
        df_disp = df.copy()
        df_disp['Num'] = range(1, len(df_disp) + 1)
        df_disp = df_disp.iloc[::-1]
        
        cols = st.columns(4)
        for i, (_, row) in enumerate(df_disp.iterrows()):
            with cols[i % 4]:
                # CORREÇÃO: Encapsulando tudo no card HTML para evitar desalinhamento
                st.markdown('<div class="trade-card">', unsafe_allow_html=True)
                
                # Janela de Imagem
                p_list = str(row['Prints']).split("|") if row['Prints'] and pd.notna(row['Prints']) else []
                if p_list and os.path.exists(p_list[0]):
                    st.markdown(f'<div class="img-container">', unsafe_allow_html=True)
                    st.image(p_list[0], use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="img-container"><span style="color:#555">Sem Print</span></div>', unsafe_allow_html=True)
                
                # Informações
                st.markdown(f'<div class="info-padding">', unsafe_allow_html=True)
                st.write(f"**Trade #{row['Num']}**")
                st.caption(f"Contexto: {row['Contexto']}")
                color = "green" if row['Resultado'] > 0 else "red"
                st.markdown(f"**:{color}[${row['Resultado']:,.2f}]**")
                if st.button("Ver", key=f"btn_{row['ID']}"):
                    show_details(row['ID'])
                st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.info("Histórico vazio.")

# ... (Restante das páginas: Dashboard e Configurar ATM mantidas) ...
