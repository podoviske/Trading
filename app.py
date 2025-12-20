import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
import json
import time
from PIL import Image

# --- CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# Diretórios e Arquivos
IMG_DIR = "trade_prints"
if not os.path.exists(IMG_DIR): os.makedirs(IMG_DIR)
CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

# --- ESTILO CSS (FOCO NO ALINHAMENTO DE JANELAS) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    
    /* CONTAINER DO CARD (O APARTAMENTO) */
    .trade-window {
        background-color: #161616;
        border: 1px solid #333;
        border-radius: 12px;
        margin-bottom: 20px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        height: 320px; /* Altura total fixa do card */
    }
    .trade-window:hover { border-color: #B20000; box-shadow: 0px 0px 15px rgba(178, 0, 0, 0.4); }

    /* A JANELA (CORTE FIXO DA IMAGEM) */
    .image-crop-container {
        width: 100%;
        height: 180px; /* Janela de visualização fixa */
        overflow: hidden;
        background-color: #000;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* FORÇANDO O ENQUADRAMENTO MILIMÉTRICO */
    .image-crop-container img {
        width: 100% !important;
        height: 100% !important;
        object-fit: cover !important; /* Recorta as sobras e centraliza */
        object-position: center !important;
    }

    .trade-footer { padding: 12px; text-align: center; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
    .stButton > button { width: 100%; border-radius: 8px; font-weight: 600; }
    
    /* SELETOR SEGMENTADO E ALERTAS */
    div[data-testid="stSegmentedControl"] button { background-color: #1E1E1E !important; color: white !important; border: none !important; }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] { background-color: #B20000 !important; }
    
    @keyframes blinking { 0% { background-color: #440000; } 50% { background-color: #B20000; } 100% { background-color: #440000; } }
    .piscante-erro { padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; animation: blinking 2s infinite; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def load_atm():
    if os.path.exists(ATM_FILE):
        try:
            with open(ATM_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"Personalizado": {"lote": 0, "stop": 0.0, "parciais": []}}

def save_atm(configs):
    with open(ATM_FILE, 'w') as f: json.dump(configs, f)

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID', 'Prints']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            for col in cols: 
                if col not in df.columns: df[col] = ""
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

atm_db = load_atm()
df = load_data()

# --- POP-UP DE EXPANSÃO (MODAL) ---
@st.dialog("Visão Panorâmica do Trade", width="large")
def expand_trade_modal(trade_id):
    row = df[df['ID'] == trade_id].iloc[0]
    c_img, c_det = st.columns([2, 1])
    with c_img:
        p_list = str(row['Prints']).split("|") if row['Prints'] else []
        if p_list and os.path.exists(p_list[0]): st.image(p_list[0], use_container_width=True)
        else: st.info("Sem print anexado.")
    with c_det:
        st.subheader(f"Trade Detalhado")
        st.write(f"📅 **Data:** {row['Data']}")
        st.write(f"🏗️ **Contexto:** {row['Contexto']}")
        color = "green" if row['Resultado'] > 0 else "red"
        st.markdown(f"💰 **Resultado:** :{color}[${row['Resultado']:,.2f}]")
        st.write(f"🎯 **Ativo:** {row['Ativo']} | {row['Direcao']}")
        st.write(f"⚙️ **ATM:** {row['ATM']}")
        st.divider()
        if st.button("🗑️ Excluir Operação"):
            st.session_state.to_delete = trade_id
            st.rerun()

# --- MENU LATERAL ---
with st.sidebar:
    st.markdown('<div style="padding:20px 10px"><span style="color:#B20000; font-size:28px; font-weight:900">EVO</span><span style="color:white; font-size:24px; font-weight:700">TRADE</span></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], default_index=0)

# --- PÁGINA: DASHBOARD ---
if selected == "Dashboard":
    st.title("📊 Analytics")
    if not df.empty:
        filtro_view = st.segmented_control("Visualizar:", options=["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
        df_f = df[df['Contexto'] == filtro_view] if filtro_view != "Capital" else df.copy()
        
        tipo_grafico = st.radio("Evolução por:", ["Tempo (Data)", "Trade a Trade"], horizontal=True)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("P&L Total", f"${df_f['Resultado'].sum():,.2f}")
        m2.metric("Trades", len(df_f))
        m3.metric("Win Rate", f"{(len(df_f[df_f['Resultado']>0])/len(df_f)*100):.1f}%" if len(df_f)>0 else "0%")
        m4.metric("Risco Médio", f"${df_f['Risco_Fin'].mean():,.2f}" if not df_f.empty else "$0")
        
        st.markdown("---")
        df_g = df_f.sort_values('Data').reset_index()
        df_g['Acumulado'] = df_g['Resultado'].cumsum()
        x_axis = 'Data' if tipo_grafico == "Tempo (Data)" else df_g.index + 1
        
        fig = px.area(df_g, x=x_axis, y='Acumulado', title=f"Equity Curve - {filtro_view}", template="plotly_dark")
        fig.update_traces(line_color='#B20000', line_shape='spline', fillcolor='rgba(178, 0, 0, 0.2)', mode='lines')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Registre trades para ver os dados.")

# --- PÁGINA: REGISTRAR TRADE ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    atm_sel = st.selectbox("🎯 Estratégia ATM", options=list(atm_db.keys()))
    config = atm_db[atm_sel]
    
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
    with c2:
        lote_t = st.number_input("Lote Total", min_value=1, value=int(config["lote"]))
        stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]))
        up_files = st.file_uploader("📸 Prints (Upload ou Ctrl+V)", accept_multiple_files=True)
    with c3:
        st.write("**Gestão de Saídas**")
        saidas = []; alocado = 0
        for i, p_c in enumerate(config["parciais"]):
            sc1, sc2 = st.columns(2)
            pts = sc1.number_input(f"Pts P{i+1}", key=f"pts_{i}", value=float(p_c[0]))
            qtd = sc2.number_input(f"Qtd P{i+1}", key=f"qtd_{i}", value=int(p_c[1]))
            saidas.append((pts, qtd)); alocado += qtd
        if lote_t > 0:
            if lote_t != alocado: st.markdown(f'<div class="piscante-erro">FALTAM {lote_t - alocado} CONTRATOS</div>', unsafe_allow_html=True)
            else: st.success("✅ Posição Completa")

    if st.button("💾 REGISTRAR OPERAÇÃO"):
        if lote_t == alocado:
            t_id = f"ID_{int(time.time())}"
            paths = [os.path.join(IMG_DIR, f"{t_id}_{i}.png") for i, f in enumerate(up_files)]
            for i, f in enumerate(up_files):
                with open(paths[i], "wb") as bf: bf.write(f.getbuffer())
            res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas])
            n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': (res/(lote_t*MULTIPLIERS[ativo])), 'Risco_Fin': (stop_p * MULTIPLIERS[ativo] * lote_t), 'ID': t_id, 'Prints': "|".join(paths)}])
            df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
            st.success("🎯 Trade Salvo!"); time.sleep(1); st.rerun()

# --- PÁGINA: HISTÓRICO (GALERIA DE JANELAS) ---
elif selected == "Histórico":
    st.title("📜 Galeria do Prédio")
    if 'to_delete' in st.session_state:
        df = df[df['ID'] != st.session_state.to_delete]
        df.to_csv(CSV_FILE, index=False); del st.session_state.to_delete; st.rerun()

    if not df.empty:
        df_disp = df.copy(); df_disp['Num'] = range(1, len(df_disp) + 1)
        df_disp = df_disp.iloc[::-1]
        cols = st.columns(5)
        for i, (_, row) in enumerate(df_disp.iterrows()):
            with cols[i % 5]:
                # CARD COM ENQUADRAMENTO CSS
                st.markdown(f'''
                <div class="trade-window">
                    <div class="image-crop-container">
                        <img src="data:image/png;base64,{""}">''', unsafe_allow_html=True)
                
                p_list = str(row['Prints']).split("|") if row['Prints'] else []
                if p_list and os.path.exists(p_list[0]): st.image(p_list[0])
                else: st.markdown('<div style="color:#444; font-size:12px">Sem Print</div>', unsafe_allow_html=True)
                
                st.markdown(f'''</div>
                    <div class="trade-footer">
                        <div><b>Trade #{row['Num']}</b><br><small>{row['Contexto']}</small></div>
                        <div style="color:{"#00FF88" if row['Resultado'] > 0 else "#FF4B4B"}; font-weight:bold">${row['Resultado']:,.2f}</div>
                ''', unsafe_allow_html=True)
                if st.button("Ver", key=f"btn_{row['ID']}"): expand_trade_modal(row['ID'])
                st.markdown('</div></div>', unsafe_allow_html=True)
    else: st.info("Vazio.")

# --- CONFIGURAR ATM ---
elif selected == "Configurar ATM":
    st.title("⚙️ Editor de Estratégias")
    with st.expander("✨ Criar Novo Template"):
        n = st.text_input("Nome"); l = st.number_input("Lote", 1); s = st.number_input("Stop Pts", 0.0)
        np = st.number_input("Saídas", 1, 6); nps = []
        for i in range(np):
            c1, c2 = st.columns(2)
            nps.append([c1.number_input(f"Alvo {i+1}", key=f"ap{i}"), c2.number_input(f"Qtd {i+1}", key=f"aq{i}")])
        if st.button("Salvar ATM"):
            atm_db[n] = {"lote": l, "stop": s, "parciais": nps}
            save_atm(atm_db); st.rerun()
