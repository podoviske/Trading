import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu

# Configuração da Página
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# --- ESTILO CSS (ALERTA PISCANTE EVO) ---
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
    }
    .logo-container { padding: 20px 15px; display: flex; flex-direction: column; }
    .logo-main { color: #B20000; font-size: 26px; font-weight: 900; line-height: 1; }
    .logo-sub { color: white; font-size: 22px; font-weight: 700; margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- DADOS E MULTIPLICADORES ---
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
if 'n_parciais' not in st.session_state:
    st.session_state.n_parciais = 1

def adicionar_parcial():
    if st.session_state.n_parciais < 6: st.session_state.n_parciais += 1
def limpar_parciais():
    st.session_state.n_parciais = 1

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
    
    # Botões fora do form para atualizar o estado
    c_btn1, c_btn2 = st.columns([4, 1])
    with c_btn2:
        st.button("➕ Parcial", on_click=adicionar_parcial, use_container_width=True)
        st.button("🧹 Reset", on_click=limpar_parciais, use_container_width=True)

    # Inputs principais FORA do st.form para permitir cálculo em tempo real
    c1, c2, c3 = st.columns([1, 1, 2])
    
    with c1:
        data = st.date_input("Data", datetime.now())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        entrada = st.number_input("Preço de Entrada", step=0.25, format="%.2f")

    with c2:
        lote_total = st.number_input("Lote Total (Contratos)", min_value=1, step=1, value=1)
        stop_pts = st.number_input("Stop (Pontos)", min_value=0.0, step=0.25)
        
        # CORREÇÃO DO CÁLCULO DE RISCO
        risco_calc = stop_pts * MULTIPLIERS[ativo] * lote_total
        st.metric("Risco Financeiro", f"${risco_calc:.2f}")

    with c3:
        st.write("**Saídas / Parciais**")
        saidas_list = []
        contratos_alocados = 0
        
        for i in range(st.session_state.n_parciais):
            s1, s2 = st.columns(2)
            with s1: 
                p = st.number_input(f"Pontos P{i+1}", key=f"pts_real_{i}", step=0.25)
            with s2: 
                q = st.number_input(f"Contratos P{i+1}", min_value=0, key=f"qtd_real_{i}", step=1)
            saidas_list.append((p, q))
            contratos_alocados += q
        
        # MENSAGEM DINÂMICA PISCANTE (ATUALIZA NA HORA)
        resta = lote_total - contratos_alocados
        if resta > 0:
            st.markdown(f'<div class="piscante-erro">FALTAM {resta} CONTRATOS PARA FECHAR A POSIÇÃO</div>', unsafe_allow_html=True)
        elif resta < 0:
            st.markdown(f'<div class="piscante-erro">ERRO: EXCESSO DE {abs(resta)} CONTRATOS!</div>', unsafe_allow_html=True)
        else:
            st.success("✅ Posição completa. Pronto para registrar.")

    # Botão de Salvar (agora fora do st.form para evitar conflito de atualização)
    if st.button("💾 REGISTRAR OPERAÇÃO FINAL", use_container_width=True):
        if contratos_alocados == lote_total:
            res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas_list])
            pts_m = sum([s[0] * s[1] for s in saidas_list]) / lote_total
            faixa = "Até 10" if lote_total <= 10 else "11-20" if lote_total <= 20 else "20+"
            
            novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'Faixa': faixa, 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': risco_calc}])
            df = pd.concat([df, novo], ignore_index=True)
            df.to_csv(CSV_FILE, index=False)
            st.success("Trade EvoTrade registrado com sucesso!")
            st.rerun()
        else:
            st.error("A quantidade de contratos das parciais não bate com o Lote Total.")

# (Restante do código: Dashboard e Histórico permanecem iguais)
elif selected == "Dashboard":
    st.title("EvoTrade Analytics")
    if not df.empty:
        k1, k2, k3 = st.columns(3)
        k1.metric("Faturamento Líquido", f"${df['Resultado'].sum():.2f}")
        k2.metric("Win Rate", f"{(len(df[df['Resultado']>0])/len(df)*100):.1f}%")
        k3.metric("Risco Médio", f"${df['Risco_Fin'].mean():.2f}")
        st.markdown("---")
        df_ev = df.sort_values('Data').copy()
        df_ev['Acumulado'] = df_ev['Resultado'].cumsum()
        fig = px.area(df_ev, x='Data', y='Acumulado', template="plotly_dark", color_discrete_sequence=['#B20000'])
        fig.update_traces(line_shape='spline', fillcolor='rgba(178, 0, 0, 0.1)')
        st.plotly_chart(fig, use_container_width=True)

elif selected == "Histórico":
    st.title("Histórico de Operações")
    st.dataframe(df.sort_values('Data', ascending=False), use_container_width=True)
