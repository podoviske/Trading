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
        0% { background-color: #440000; }
        50% { background-color: #B20000; }
        100% { background-color: #440000; }
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

# --- PERSISTÊNCIA ---
CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

def load_atm():
    if os.path.exists(ATM_FILE):
        with open(ATM_FILE, 'r') as f:
            return json.load(f)
    return {"Personalizado": {"lote": 0, "stop": 0.0, "parciais": []}}

def save_atm(configs):
    with open(ATM_FILE, 'w') as f:
        json.dump(configs, f)

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            # Garante que todas as colunas necessárias existam
            for col in cols:
                if col not in df.columns:
                    df[col] = 0 if col != 'Data' else datetime.now().date()
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

# Inicializar bases
atm_db = load_atm()
df = load_data()

# --- ESTADO ---
if 'n_extras' not in st.session_state:
    st.session_state.n_extras = 0

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
    with st.expander("✨ Criar Novo Template ATM", expanded=True):
        nome_novo = st.text_input("Nome da Estratégia")
        c1, c2 = st.columns(2)
        l_p = c1.number_input("Lote Total", min_value=1, step=1, key="new_lote")
        s_p = c2.number_input("Stop (Pts)", min_value=0.0, step=0.25, key="new_stop")
        
        n_p = st.number_input("Número de Alvos (Parciais)", 1, 6, 1, key="new_n_p")
        novas_p = []
        for i in range(n_p):
            cp1, cp2 = st.columns(2)
            pt = cp1.number_input(f"Alvo P{i+1} (Pts)", key=f"conf_pts_{i}", value=0.0)
            qt = cp2.number_input(f"Contratos P{i+1}", key=f"conf_qtd_{i}", min_value=1, step=1)
            novas_p.append([pt, qt])
        
        if st.button("💾 Salvar Estratégia"):
            if nome_novo:
                atm_db[nome_novo] = {"lote": l_p, "stop": s_p, "parciais": novas_p}
                save_atm(atm_db)
                st.success("Salvo com sucesso!")
                st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Gerenciar Estratégias")
    for nome in list(atm_db.keys()):
        if nome != "Personalizado":
            col_n, col_b = st.columns([4, 1])
            col_n.write(f"**{nome}**")
            if col_b.button("Excluir", key=f"del_{nome}"):
                del atm_db[nome]
                save_atm(atm_db)
                st.rerun()

# --- PÁGINA: REGISTRAR TRADE ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    
    c_topo1, c_topo2 = st.columns([3, 1])
    with c_topo1:
        atm_sel = st.selectbox("🎯 Estratégia ATM", list(atm_db.keys()))
        config = atm_db[atm_sel]
    with c_topo2:
        st.write("") 
        cb1, cb2 = st.columns(2)
        if cb1.button("➕"): st.session_state.n_extras += 1
        if cb2.button("🧹"):
            st.session_state.n_extras = 0
            st.rerun()

    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2.5])
    
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)

    with c2:
        lote_t = st.number_input("Lote Total", min_value=0, step=1, value=config["lote"])
        stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=config["stop"])
        risco = stop_p * MULTIPLIERS[ativo] * lote_t
        if lote_t > 0: st.metric("Risco Total", f"${risco:,.2f}")

    with c3:
        st.write("**Saídas Executadas**")
        saidas = []
        alocado = 0
        total_p = len(config["parciais"]) + st.session_state.n_extras
        
        for i in range(total_p):
            def_p = config["parciais"][i][0] if i < len(config["parciais"]) else 0.0
            def_q = config["parciais"][i][1] if i < len(config["parciais"]) else 0
            
            s1, s2 = st.columns(2)
            with s1: p = st.number_input(f"Pts P{i+1}", key=f"p_reg_{i}", value=def_p)
            with s2: q = st.number_input(f"Qtd P{i+1}", key=f"q_reg_{i}", value=def_q, step=1)
            saidas.append((p, q)); alocado += q
        
        if lote_t > 0:
            resta = lote_t - alocado
            if resta != 0:
                msg = f"FALTAM {resta} CONTRATOS" if resta > 0 else f"EXCESSO DE {abs(resta)} CONTRATOS"
                st.markdown(f'<div class="piscante-erro">{msg}</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Posição Completa")

    st.markdown("---")
    r1, r2 = st.columns(2)
    with r1:
        if st.button("💾 REGISTRAR GAIN"):
            if lote_t > 0 and alocado == lote_t:
                res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas])
                pts_m = sum([s[0] * s[1] for s in saidas]) / lote_t
                n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': risco}])
                df = pd.concat([df, n_t], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                st.rerun()

    with r2:
        if st.button("🚨 REGISTRAR STOP FULL", type="secondary"):
            if lote_t > 0 and stop_p > 0:
                pre = -(stop_p * MULTIPLIERS[ativo] * lote_t)
                n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': pre, 'Pts_Medio': -stop_p, 'Risco_Fin': risco}])
                df = pd.concat([df, n_t], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                st.rerun()

elif selected == "Dashboard":
    st.title("EvoTrade Analytics")
    if not df.empty:
        total_pnl = df['Resultado'].sum()
        k1, k2, k3 = st.columns(3)
        k1.metric("Win Rate", f"{(len(df[df['Resultado']>0])/len(df)*100):.1f}%")
        k2.metric("P&L Total", f"${total_pnl:,.2f}")
        k3.metric("Trades", len(df))
        df_sort = df.sort_values('Data')
        df_sort['Acumulado'] = df_sort['Resultado'].cumsum()
        st.plotly_chart(px.area(df_sort, x='Data', y='Acumulado', template="plotly_dark", color_discrete_sequence=['#B20000']), use_container_width=True)

elif selected == "Histórico":
    st.title("Histórico")
    st.dataframe(df.sort_values('Data', ascending=False), use_container_width=True)
