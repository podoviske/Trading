import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
import json

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

# --- PERSISTÊNCIA DE DADOS E ATM ---
CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

def load_atm():
    if os.path.exists(ATM_FILE):
        with open(ATM_FILE, 'r') as f: return json.load(f)
    return {"Personalizado": {"lote": 0, "stop": 0.0, "parciais": []}}

def save_atm(configs):
    with open(ATM_FILE, 'w') as f: json.dump(configs, f)

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: pass
    return pd.DataFrame(columns=cols)

# Inicialização
atm_db = load_atm()
df = load_data()

# --- ESTADO ---
if 'n_parciais_manual' not in st.session_state:
    st.session_state.n_parciais_manual = 0

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="logo-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], styles={
            "nav-link-selected": {"background-color": "#B20000", "color": "white"}
        })

# --- PÁGINA: CONFIGURAR ATM ---
if selected == "Configurar ATM":
    st.title("⚙️ Editor de Estratégias ATM")
    
    with st.expander("✨ Criar Novo ATM", expanded=True):
        nome_novo = st.text_input("Nome da Estratégia (ex: Scalp 10pts)")
        c1, c2 = st.columns(2)
        lote_novo = c1.number_input("Lote Padrão", min_value=1, step=1)
        stop_novo = c2.number_input("Stop Padrão (Pts)", min_value=0.0, step=0.25)
        
        n_p = st.slider("Quantidade de Parciais", 1, 6, 1)
        novas_parciais = []
        cols_p = st.columns(n_p)
        for i in range(n_p):
            with cols_p[i]:
                pts = st.number_input(f"Pts Alvo {i+1}", key=f"new_p_{i}")
                qtd = st.number_input(f"Contratos {i+1}", key=f"new_q_{i}", min_value=1, step=1)
                novas_parciais.append([pts, qtd])
        
        if st.button("💾 Salvar Estratégia"):
            if nome_novo:
                atm_db[nome_novo] = {"lote": lote_novo, "stop": stop_novo, "parciais": novas_parciais}
                save_atm(atm_db)
                st.success(f"ATM '{nome_novo}' salvo!")
                st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Gerenciar Existentes")
    for nome in list(atm_db.keys()):
        if nome != "Personalizado":
            c_n, c_b = st.columns([4, 1])
            c_n.write(f"**{nome}** ({atm_db[nome]['lote']} Contratos)")
            if c_b.button("Excluir", key=f"del_{nome}"):
                del atm_db[nome]
                save_atm(atm_db)
                st.rerun()

# --- PÁGINA: REGISTRAR TRADE ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    
    # BOTÕES DE CONTROLE (VOLTARAM!)
    c_btn1, c_btn2 = st.columns([4, 1])
    with c_btn2:
        col_add, col_res = st.columns(2)
        if col_add.button("➕"): st.session_state.n_parciais_manual += 1
        if col_res.button("🧹"): 
            st.session_state.n_parciais_manual = 0
            st.rerun()

    atm_lista = list(atm_db.keys())
    atm_selecionado = st.selectbox("🎯 Estratégia ATM", atm_lista)
    config = atm_db[atm_selecionado]

    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2.5])
    
    with c1:
        data = st.date_input("Data", datetime.now())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)

    with c2:
        lote_total = st.number_input("Lote Total", min_value=0, step=1, value=config["lote"])
        stop_pts = st.number_input("Stop (Pontos)", min_value=0.0, value=config["stop"])
        risco_calc = stop_pts * MULTIPLIERS[ativo] * lote_total
        if lote_total > 0: st.metric("Risco Total", f"${risco_calc:,.2f}")

    with c3:
        st.write("**Saídas / Parciais**")
        saidas_list = []
        contratos_alocados = 0
        
        # Unir parciais do ATM com parciais extras manuais
        n_total_p = len(config["parciais"]) + st.session_state.n_parciais_manual
        
        for i in range(n_total_p):
            s1, s2 = st.columns(2)
            default_p = config["parciais"][i][0] if i < len(config["parciais"]) else 0.0
            default_q = config["parciais"][i][1] if i < len(config["parciais"]) else 0
            
            with s1: p = st.number_input(f"Pts P{i+1}", key=f"pts_{i}", value=default_p)
            with s2: q = st.number_input(f"Qtd P{i+1}", key=f"qtd_{i}", value=default_q, step=1)
            saidas_list.append((p, q))
            contratos_alocados += q
        
        if lote_total > 0:
            resta = lote_total - contratos_alocados
            if resta != 0:
                st.markdown(f'<div class="piscante-erro">{"FALTAM" if resta > 0 else "EXCESSO DE"} {abs(resta)} CONTRATOS</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Posição Completa")

    st.markdown("---")
    reg1, reg2 = st.columns(2)
    with reg1:
        if st.button("💾 REGISTRAR GAIN"):
            if lote_total > 0 and contratos_alocados == lote_total:
                res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas_list])
                pts_m = sum([s[0] * s[1] for s in saidas_list]) / lote_total
                novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'ATM': atm_selecionado, 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': risco_calc}])
                df = pd.concat([df, novo], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.rerun()

    with reg2:
        if st.button("🚨 REGISTRAR STOP FULL", type="secondary"):
            if lote_total > 0 and stop_pts > 0:
                prejuizo = -(stop_pts * MULTIPLIERS[ativo] * lote_total)
                novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'ATM': atm_selecionado, 'Resultado': prejuizo, 'Pts_Medio': -stop_pts, 'Risco_Fin': risco_calc}])
                df = pd.concat([df, novo], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.rerun()

# (Dashboard e Histórico seguem conforme as versões anteriores)
elif selected == "Dashboard":
    st.title("EvoTrade Analytics")
    if not df.empty:
        total_pnl = df['Resultado'].sum()
        k1, k2, k3 = st.columns(3)
        k1.metric("Win Rate", f"{(len(df[df['Resultado']>0])/len(df)*100):.1f}%")
        k2.metric("P&L Total", f"${total_pnl:,.2f}")
        k3.metric("Trades", len(df))
        st.
