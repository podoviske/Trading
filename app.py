import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu

# Configuração da Página
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# --- ESTILO CSS PARA ALINHAMENTO FORÇADO ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }

    /* Forçar todos os blocos de input a terem a mesma margem superior */
    .stNumberInput, .stSelectbox, .stTextInput, .stDateInput, .stRadio {
        margin-top: 0px !important;
    }

    /* Ajuste para o texto de 'Saídas' ficar alinhado com o topo da coluna da esquerda */
    .header-style {
        font-size: 14px;
        font-weight: bold;
        color: #B20000;
        margin-bottom: 22px; /* Espaço para compensar a label dos campos da esquerda */
    }

    @keyframes blinking {
        0% { background-color: #440000; }
        50% { background-color: #B20000; }
        100% { background-color: #440000; }
    }
    .piscante-erro {
        padding: 10px; border-radius: 5px; color: white; font-weight: bold;
        text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000;
        margin-top: 15px;
    }

    .logo-container { padding: 20px 15px; }
    .logo-main { color: #B20000; font-size: 26px; font-weight: 900; line-height: 1; }
    .logo-sub { color: white; font-size: 22px; font-weight: 700; margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- DADOS ---
CSV_FILE = 'evotrade_data.csv'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'Faixa', 'Resultado', 'Pts_Medio', 'Risco_Fin']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE); df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: pass
    return pd.DataFrame(columns=cols)

df = load_data()

# --- ESTADO ---
if 'n_parciais' not in st.session_state: st.session_state.n_parciais = 1
def adicionar_parcial(): 
    if st.session_state.n_parciais < 6: st.session_state.n_parciais += 1
def limpar_parciais(): st.session_state.n_parciais = 1

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="logo-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "clock-history"], styles={
            "nav-link-selected": {"background-color": "#B20000", "color": "white"}
        })

# --- PÁGINAS ---
if selected == "Registrar Trade":
    st.title("Registro de Trade")
    
    # Grid Principal
    col_dados, col_parciais = st.columns([2, 3])

    with col_dados:
        st.markdown('<p style="height:22px;"></p>', unsafe_allow_html=True) # Espaçador de alinhamento
        d1, d2 = st.columns(2)
        with d1:
            data = st.date_input("Data", datetime.now())
            ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        with d2:
            contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
            direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        
        l1, l2 = st.columns(2)
        with l1:
            lote_total = st.number_input("Contratos", min_value=0, step=1, value=0)
        with l2:
            stop_pts = st.number_input("Stop (Pontos)", min_value=0.0, value=0.0)
        
        risco_calc = stop_pts * MULTIPLIERS[ativo] * lote_total
        if lote_total > 0 and stop_pts > 0:
            st.metric("Risco Total", f"${risco_calc:,.2f}")

    with col_parciais:
        # Título e Botões alinhados
        h1, h2 = st.columns([2, 1])
        with h1: st.markdown('<p class="header-style">SAÍDAS / PARCIAIS</p>', unsafe_allow_html=True)
        with h2:
            sub1, sub2 = st.columns(2)
            sub1.button("➕", on_click=adicionar_parcial)
            sub2.button("🧹", on_click=limpar_parciais)

        saidas_list = []
        contratos_alocados = 0
        
        # Gerar parciais com alinhamento forçado
        for i in range(st.session_state.n_parciais):
            p1, p2 = st.columns(2)
            with p1:
                p = st.number_input(f"Pontos P{i+1}", key=f"pts_{i}", value=0.0)
            with p2:
                q = st.number_input(f"Qtd P{i+1}", key=f"qtd_{i}", value=0, step=1)
            saidas_list.append((p, q))
            contratos_alocados += q
        
        if lote_total > 0:
            resta = lote_total - contratos_alocados
            if resta != 0:
                msg = f"FALTAM {resta} CONTRATOS" if resta > 0 else f"EXCESSO DE {abs(resta)} CONTRATOS"
                st.markdown(f'<div class="piscante-erro">{msg}</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Posição Completa")

    st.markdown("---")
    reg1, reg2 = st.columns(2)
    with reg1:
        if st.button("💾 REGISTRAR GAIN"):
            if lote_total > 0 and contratos_alocados == lote_total:
                res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas_list])
                pts_m = sum([s[0] * s[1] for s in saidas_list]) / lote_total
                novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'Faixa': "Trade", 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': risco_calc}])
                df = pd.concat([df, novo], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.rerun()

    with reg2:
        if st.button("🚨 REGISTRAR STOP FULL", type="secondary"):
            if lote_total > 0 and stop_pts > 0:
                prejuizo = -(stop_pts * MULTIPLIERS[ativo] * lote_total)
                novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'Faixa': "Trade", 'Resultado': prejuizo, 'Pts_Medio': -stop_pts, 'Risco_Fin': risco_calc}])
                df = pd.concat([df, novo], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.rerun()
