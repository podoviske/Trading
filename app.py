import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu

# Configuração da Página
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# --- ESTILO CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #111111 !important;
        border-right: 1px solid #1E1E1E;
    }
    .stApp {
        background-color: #0F0F0F;
    }
    .sidebar-category {
        color: #555555;
        font-size: 0.70rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-top: 25px;
        margin-left: 15px;
        margin-bottom: 5px;
        letter-spacing: 1px;
    }
    div[data-baseweb="input"], div[data-baseweb="select"], .stTextArea textarea {
        background-color: #1A1A1A !important;
        border: 1px solid #2A2A2A !important;
        color: white !important;
    }
    .stButton>button {
        background-color: #B20000 !important;
        color: white !important;
        border: none !important;
        border-radius: 4px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #FF0000 !important;
        box-shadow: 0px 0px 10px rgba(255, 0, 0, 0.4);
    }
    /* Estilização da Logo EvoTrade no Topo */
    .logo-container {
        padding: 20px 15px;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }
    .logo-main {
        color: #B20000;
        font-size: 26px;
        font-weight: 900;
        line-height: 1;
        letter-spacing: -1px;
    }
    .logo-sub {
        color: white;
        font-size: 22px;
        font-weight: 700;
        margin-top: -5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÃO DE DADOS ---
CSV_FILE = 'evotrade_data.csv'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'Faixa', 'Resultado', 'Pts_Medio', 'Risco_Fin']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data']).dt.date
                return df
        except:
            pass
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

df = load_data()

# --- LÓGICA DE ESTADO ---
if 'n_parciais' not in st.session_state:
    st.session_state.n_parciais = 1

def adicionar_parcial():
    if st.session_state.n_parciais < 6: st.session_state.n_parciais += 1
def limpar_parciais():
    st.session_state.n_parciais = 1

# --- SIDEBAR ---
with st.sidebar:
    # Logo EVO TRADE centralizada no topo da sidebar
    st.markdown("""
        <div class="logo-container">
            <div class="logo-main">EVO</div>
            <div class="logo-sub">TRADE</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="sidebar-category">Menu</p>', unsafe_allow_html=True)
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Registrar Trade", "Histórico"],
        icons=["grid-1x2", "currency-dollar", "clock-history"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#666", "font-size": "16px"}, 
            "nav-link": {"font-size": "14px", "text-align": "left", "color": "#AAA", "padding": "10px"},
            "nav-link-selected": {"background-color": "#B20000", "color": "white", "border-radius": "5px"},
        }
    )
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div style="position: fixed; bottom: 20px; left: 20px; color: #555; font-size: 14px; cursor: pointer;">📤 Sair</div>', unsafe_allow_html=True)

# --- PÁGINAS ---

if selected == "Registrar Trade":
    st.title("Registro de Trade")
    
    col_t, col_b = st.columns([3, 1])
    with col_b:
        c1, c2 = st.columns(2)
        with c1: st.button("➕ Parcial", on_click=adicionar_parcial, use_container_width=True)
        with c2: st.button("🧹 Reset", on_click=limpar_parciais, use_container_width=True)

    with st.form("trade_form"):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            data = st.date_input("Data da Operação", datetime.now())
            ativo = st.selectbox("Ativo/Servidor", ["MNQ", "NQ"])
            contexto = st.selectbox("Contexto/Tipo", ["Contexto A", "Contexto B", "Contexto C"])
            direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            entrada = st.number_input("Preço de Entrada", step=0.25, format="%.2f")
        with c2:
            lote_total = st.number_input("Contratos Totais", min_value=1, step=1)
            stop_pts = st.number_input("Risco em Pontos", step=0.25)
            risco_calc = stop_pts * MULTIPLIERS[ativo] * lote_total
            st.metric("Risco Calculado", f"${risco_calc:.2f}")
        with c3:
            st.write("**Saídas / Parciais**")
            saidas = []
            alocado = 0
            for i in range(st.session_state.n_parciais):
                s1, s2 = st.columns(2)
                with s1: p = st.number_input(f"Pts Parcial {i+1}", key=f"p_{i}")
                with s2: q = st.number_input(f"Contratos P{i+1}", min_value=0, key=f"q_{i}")
                saidas.append((p, q)); alocado += q
            
            if lote_total - alocado != 0:
                st.warning(f"Faltam {lote_total - alocado} contratos.")

        if st.form_submit_button("REGISTRAR TRADE"):
            if alocado == lote_total:
                res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas])
                pts_m = sum([s[0] * s[1] for s in saidas]) / lote_total
                faixa = "Até 10" if lote_total <= 10 else "11-20" if lote_total <= 20 else "20+"
                
                novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'Faixa': faixa, 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': risco_calc}])
                df = pd.concat([df, novo], ignore_index=True)
                save_data(df)
                st.success("Registrado com sucesso!")
                st.rerun()
            else:
                st.error("A soma das parciais deve bater com o lote!")

elif selected == "Dashboard":
    st.title("EvoTrade Analytics")
    if not df.empty:
        k1, k2, k3 = st.columns(3)
        k1.metric("P&L Total", f"${df['Resultado'].sum():.2f}")
        k2.metric("Taxa de Acerto", f"{(len(df[df['Resultado']>0])/len(df)*100):.1f}%")
        k3.metric("Risco Médio", f"${df['Risco_Fin'].mean():.2f}")
        
        st.markdown("---")
        df_ev = df.sort_values('Data').copy()
        df_ev['Acumulado'] = df_ev['Resultado'].cumsum()
        fig = px.area(df_ev, x='Data', y='Acumulado', title="Curva de Capital", template="plotly_dark", color_discrete_sequence=['#B20000'])
        fig.update_traces(line_shape='spline', fillcolor='rgba(178, 0, 0, 0.1)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para exibir.")

elif selected == "Histórico":
    st.title("Histórico de Trades")
    if not df.empty:
        st.dataframe(df.sort_values('Data', ascending=False), use_container_width=True)
    else:
        st.write("Histórico vazio.")
