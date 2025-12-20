import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu

# Configuração da Página
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    @keyframes blinking {
        0% { background-color: #440000; box-shadow: 0 0 5px #440000; }
        50% { background-color: #B20000; box-shadow: 0 0 20px #B20000; }
        100% { background-color: #440000; box-shadow: 0 0 5px #440000; }
    }
    .piscante-erro {
        padding: 15px; border-radius: 5px; color: white; font-weight: bold;
        text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000;
        margin-top: 10px;
    }
    .logo-container { padding: 20px 15px; display: flex; flex-direction: column; }
    .logo-main { color: #B20000; font-size: 26px; font-weight: 900; line-height: 1; }
    .logo-sub { color: white; font-size: 22px; font-weight: 700; margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE ESTRATÉGIAS ATM (Configure as suas aqui) ---
# Você pode mudar os nomes e valores conforme o seu NinjaTrader
ESTRATEGIAS_ATM = {
    "Personalizado": {"lote": 0, "stop": 0.0, "parciais": []},
    "ATM Scalp (2 contratos)": {
        "lote": 2, 
        "stop": 15.0, 
        "parciais": [(10.0, 1), (20.0, 1)] # (pontos, qtd)
    },
    "ATM Tendência (5 contratos)": {
        "lote": 5, 
        "stop": 30.0, 
        "parciais": [(20.0, 2), (40.0, 2), (60.0, 1)]
    }
}

# --- DADOS ---
CSV_FILE = 'evotrade_data.csv'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'Estrategia', 'Resultado', 'Pts_Medio', 'Risco_Fin']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: pass
    return pd.DataFrame(columns=cols)

df = load_data()

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

    # 1. SELEÇÃO DA ESTRATÉGIA ATM
    col_atm, col_blank = st.columns([2, 2])
    with col_atm:
        atm_selecionado = st.selectbox("🎯 Selecionar Estratégia ATM", list(ESTRATEGIAS_ATM.keys()))
        config = ESTRATEGIAS_ATM[atm_selecionado]

    st.markdown("---")

    c1, c2, c3 = st.columns([1, 1, 2.5])
    
    with c1:
        data = st.date_input("Data", datetime.now())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)

    with c2:
        # Puxa o lote do ATM selecionado
        lote_total = st.number_input("Contratos", min_value=0, step=1, value=config["lote"])
        # Puxa o stop do ATM selecionado
        stop_pts = st.number_input("Stop (Pontos)", min_value=0.0, value=config["stop"])
        
        risco_calc = stop_pts * MULTIPLIERS[ativo] * lote_total
        if lote_total > 0 and stop_pts > 0:
            st.metric("Risco Financeiro Total", f"${risco_calc:,.2f}")

    with c3:
        st.markdown("<p style='font-weight: bold;'>Saídas / Parciais</p>", unsafe_allow_html=True)
        saidas_list = []
        contratos_alocados = 0
        
        # Define quantas parciais mostrar (Baseado no ATM ou no mínimo 1)
        num_p = max(len(config["parciais"]), 1)
        
        for i in range(num_p):
            # Tenta pegar valor padrão do ATM se existir
            default_pts = config["parciais"][i][0] if i < len(config["parciais"]) else 0.0
            default_qtd = config["parciais"][i][1] if i < len(config["parciais"]) else 0
            
            s1, s2 = st.columns(2)
            with s1: p = st.number_input(f"Pts P{i+1}", key=f"pts_{i}", value=default_pts)
            with s2: q = st.number_input(f"Qtd P{i+1}", key=f"qtd_{i}", value=default_qtd, step=1)
            
            saidas_list.append((p, q))
            contratos_alocados += q
        
        if lote_total > 0:
            resta = lote_total - contratos_alocados
            if resta != 0:
                msg = f"FALTAM {resta} CONTRATOS" if resta > 0 else f"EXCESSO DE {abs(resta)} CONTRATOS"
                st.markdown(f'<div class="piscante-erro">{msg}</div>', unsafe_allow_html=True)
            else:
                st.success("✅ ATM Configurado Corretamente")

    st.markdown("---")
    # Botões de registro ( Gain e Stop) mantendo o fluxo anterior...
    col_save, col_stop = st.columns(2)
    with col_save:
        if st.button("💾 REGISTRAR GAIN"):
            if lote_total > 0 and contratos_alocados == lote_total:
                res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas_list])
                pts_m = sum([s[0] * s[1] for s in saidas_list]) / lote_total
                novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'Estrategia': atm_selecionado, 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': risco_calc}])
                df = pd.concat([df, novo], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.rerun()

    with col_stop:
        if st.button("🚨 REGISTRAR STOP FULL", type="secondary"):
            if lote_total > 0 and stop_pts > 0:
                prejuizo = -(stop_pts * MULTIPLIERS[ativo] * lote_total)
                novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'Estrategia': atm_selecionado, 'Resultado': prejuizo, 'Pts_Medio': -stop_pts, 'Risco_Fin': risco_calc}])
                df = pd.concat([df, novo], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.rerun()

# (Dashboard e Histórico seguem conforme as versões anteriores)
