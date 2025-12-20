import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu

# Configuração da Página
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# --- ESTILO CSS PARA ALINHAMENTO ABSOLUTO ---
st.markdown("""
    <style>
    /* Fundo e Sidebar */
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }

    /* FORÇAR ALINHAMENTO DAS CAIXAS */
    div[data-testid="stVerticalBlock"] > div {
        gap: 0rem !important;
    }
    
    /* Padronizar altura de todos os inputs para ficarem na mesma linha */
    .stNumberInput, .stSelectbox, .stTextInput, .stDateInput {
        margin-bottom: 8px !important;
    }

    /* Alinhamento do Título das Parciais */
    .parcial-header {
        margin-bottom: 12px;
        color: #B20000;
        font-weight: bold;
        text-transform: uppercase;
        font-size: 0.9rem;
    }

    @keyframes blinking {
        0% { background-color: #440000; }
        50% { background-color: #B20000; }
        100% { background-color: #440000; }
    }
    .piscante-erro {
        padding: 10px; border-radius: 5px; color: white; font-weight: bold;
        text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000;
        margin-top: 5px;
    }

    /* Estilo dos Botões */
    .stButton > button { width: 100%; border-radius: 4px !important; }
    .stButton > button[kind="secondary"] {
        color: #FF4B4B !important; border: 1px solid #FF4B4B !important; background: transparent !important;
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
            df = pd.read_csv(CSV_FILE)
            df['Data'] = pd.to_datetime(df['Data']).dt.date
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
    
    # 1. BOTÕES DE CONTROLE (ALINHADOS)
    c_btn1, c_btn2, c_btn3 = st.columns([6, 1, 1])
    with c_btn2: st.button("➕", on_click=adicionar_parcial)
    with c_btn3: st.button("🧹", on_click=limpar_parciais)

    # 2. GRID PRINCIPAL
    # Usamos o st.container para garantir que o layout flua em blocos alinhados
    with st.container():
        col_dados, col_parciais = st.columns([2, 3])

        with col_dados:
            # Subdividindo a coluna de dados para ficar compacto
            d1, d2 = st.columns(2)
            with d1:
                data = st.date_input("Data", datetime.now())
                ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
            with d2:
                contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
                direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            
            # Linha de Baixo dos dados
            l1, l2 = st.columns(2)
            with l1:
                lote_total = st.number_input("Contratos", min_value=0, step=1, value=0)
            with l2:
                stop_pts = st.number_input("Stop (Pts)", min_value=0.0, value=0.0)
            
            risco_calc = stop_pts * MULTIPLIERS[ativo] * lote_total
            if lote_total > 0 and stop_pts > 0:
                st.metric("Risco Total", f"${risco_calc:,.2f}")

        with col_parciais:
            st.markdown('<div class="parcial-header">Saídas / Parciais (Pontos | Qtd)</div>', unsafe_allow_html=True)
            saidas_list = []
            contratos_alocados = 0
            
            # Gerando as linhas de parciais
            for i in range(st.session_state.n_parciais):
                p1, p2 = st.columns([1, 1])
                with p1:
                    p = st.number_input(f"Pts P{i+1}", key=f"pts_{i}", value=0.0, label_visibility="collapsed")
                with p2:
                    q = st.number_input(f"Qtd P{i+1}", key=f"qtd_{i}", value=0, step=1, label_visibility="collapsed")
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
    
    # 3. BOTÕES DE REGISTRO
    reg1, reg2 = st.columns(2)
    with reg1:
        if st.button("💾 REGISTRAR GAIN"):
            if lote_total > 0 and contratos_alocados == lote_total:
                res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas_list])
                pts_m = sum([s[0] * s[1] for s in saidas_list]) / lote_total
                novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'Faixa': "Trade", 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': risco_calc}])
                df = pd.concat([df, novo], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                st.rerun()

    with reg2:
        if st.button("🚨 REGISTRAR STOP FULL", type="secondary"):
            if lote_total > 0 and stop_pts > 0:
                prejuizo = -(stop_pts * MULTIPLIERS[ativo] * lote_total)
                novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'Faixa': "Trade", 'Resultado': prejuizo, 'Pts_Medio': -stop_pts, 'Risco_Fin': risco_calc}])
                df = pd.concat([df, novo], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                st.rerun()

# (Dashboard e Histórico seguem o padrão funcional)
