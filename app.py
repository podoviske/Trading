import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
import json
import time
from PIL import Image
import io

# --- CONFIGURAÇÃO DE PÁGINA E DIRETÓRIOS ---
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# Diretório para salvar os prints das operações
IMG_DIR = "trade_prints"
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

# --- ESTILO CSS CUSTOMIZADO (VISUAL DE JANELAS DE PRÉDIO) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    
    /* Moldura da Janela (Card) */
    .trade-window {
        background-color: #161616;
        border: 1px solid #333;
        border-radius: 12px;
        margin-bottom: 20px;
        overflow: hidden;
        transition: all 0.3s ease;
        display: flex;
        flex-direction: column;
    }
    .trade-window:hover { border-color: #B20000; box-shadow: 0px 4px 15px rgba(178, 0, 0, 0.3); }

    /* A Janela (Corte da Imagem Fixa) */
    .image-crop {
        width: 100%;
        height: 150px; 
        overflow: hidden;
        background-color: #000;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .image-crop img {
        width: 100%;
        height: 100%;
        object-fit: cover; 
    }

    /* Informações abaixo da janela */
    .trade-info-box { padding: 12px; text-align: center; }
    
    /* Botões e Seletores */
    .stButton > button { width: 100%; border-radius: 8px; }
    div[data-testid="stSegmentedControl"] button {
        background-color: #1E1E1E !important; color: #FFFFFF !important; border: none !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background-color: #B20000 !important; font-weight: bold !important;
    }
    
    @keyframes blinking {
        0% { background-color: #440000; } 50% { background-color: #B20000; } 100% { background-color: #440000; }
    }
    .piscante-erro {
        padding: 15px; border-radius: 5px; color: white; font-weight: bold;
        text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000; margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE PERSISTÊNCIA ---
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
            if 'ID' not in df.columns: df['ID'] = [f"ID_{int(time.time())}_{i}" for i in range(len(df))]
            if 'Prints' not in df.columns: df['Prints'] = ""
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

atm_db = load_atm()
df = load_data()

# --- POP-UP DE EXPANSÃO (MODAL) ---
@st.dialog("Visão Detalhada da Operação", width="large")
def expand_trade_modal(trade_id):
    row = df[df['ID'] == trade_id].iloc[0]
    c_img, c_det = st.columns([2, 1])
    
    with c_img:
        p_list = str(row['Prints']).split("|") if row['Prints'] and pd.notna(row['Prints']) else []
        if p_list and os.path.exists(p_list[0]):
            st.image(p_list[0], use_container_width=True)
        else:
            st.info("Nenhum print anexado a este trade.")
            
    with c_det:
        st.subheader(f"Trade #{df[df['ID'] == trade_id].index[0] + 1}")
        st.write(f"**Data:** {row['Data']}")
        st.write(f"**Ativo:** {row['Ativo']} | **Direção:** {row['Direcao']}")
        res_color = "green" if row['Resultado'] > 0 else "red"
        st.markdown(f"**Resultado:** :{res_color}[${row['Resultado']:,.2f}]")
        st.write(f"**Contexto:** {row['Contexto']}")
        st.write(f"**ATM:** {row['ATM']}")
        st.write(f"**Lote:** {row['Lote']}")
        
        st.divider()
        if st.button("🗑️ Deletar Registro", type="secondary"):
            st.session_state.to_delete = trade_id
            st.rerun()

# --- MENU LATERAL ---
with st.sidebar:
    st.markdown('<div style="padding:20px 10px"><span style="color:#B20000; font-size:28px; font-weight:900">EVO</span><span style="color:white; font-size:24px; font-weight:700">TRADE</span></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], default_index=0)

# --- PÁGINA: DASHBOARD ---
if selected == "Dashboard":
    st.title("📊 EvoTrade Analytics")
    if not df.empty:
        filtro_view = st.segmented_control("Visualizar:", options=["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
        df_f = df[df['Contexto'] == filtro_view] if filtro_view != "Capital" else df.copy()
        
        tipo_grafico = st.radio("Evolução por:", ["Tempo (Data)", "Trade a Trade"], horizontal=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("P&L Total", f"${df_f['Resultado'].sum():,.2f}")
        m2.metric("Total Trades", len(df_f))
        m3.metric("Win Rate", f"{(len(df_f[df_f['Resultado']>0])/len(df_f)*100):.1f}%" if not df_f.empty else "0%")
        
        st.markdown("---")
        df_g = df_f.sort_values('Data').reset_index()
        df_g['Acumulado'] = df_g['Resultado'].cumsum()
        x_axis = 'Data' if tipo_grafico == "Tempo (Data)" else df_g.index + 1
        
        fig = px.area(df_g, x=x_axis, y='Acumulado', title=f"Curva de Capital - {filtro_view}", template="plotly_dark")
        fig.update_traces(line_color='#B20000', line_shape='spline', fillcolor='rgba(178, 0, 0, 0.2)', mode='lines')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

# --- PÁGINA: REGISTRAR TRADE ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    atm_sel = st.selectbox("🎯 Estratégia ATM", options=list(atm_db.keys()))
    config = atm_db[atm_sel]
    key_prefix = atm_sel.replace(" ", "_")
    
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
    with c2:
        lote_t = st.number_input("Lote Total", min_value=0, value=int(config["lote"]), key=f"lt_{key_prefix}")
        stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]), key=f"st_{key_prefix}")
        st.metric("Risco", f"${(stop_p * MULTIPLIERS[ativo] * lote_t):,.2f}")
        up_files = st.file_uploader("📸 Prints (Upload ou Ctrl+V)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
    with c3:
        st.write("**Saídas**")
        saidas = []; alocado = 0
        for i, p_c in enumerate(config["parciais"]):
            s1, s2 = st.columns(2)
            pts = s1.number_input(f"Pts P{i+1}", key=f"pts_{i}_{key_prefix}", value=float(p_c[0]))
            qtd = s2.number_input(f"Qtd P{i+1}", key=f"qtd_{i}_{key_prefix}", value=int(p_c[1]))
            saidas.append((pts, qtd)); alocado += qtd
        if lote_t > 0:
            if lote_t - alocado != 0: st.markdown(f'<div class="piscante-erro">FALTAM {lote_t - alocado} CONTRATOS</div>', unsafe_allow_html=True)
            else: st.success("✅ Posição Completa")

    if st.button("💾 REGISTRAR TRADE"):
        if lote_t > 0 and alocado == lote_t:
            t_id = f"ID_{int(time.time())}"
            paths = []
            for i, f in enumerate(up_files):
                p = os.path.join(IMG_DIR, f"{t_id}_{i}.png"); paths.append(p)
                with open(p, "wb") as bf: bf.write(f.getbuffer())
            res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas])
            n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': (res/(lote_t*MULTIPLIERS[ativo])), 'Risco_Fin': (stop_p * MULTIPLIERS[ativo] * lote_t), 'ID': t_id, 'Prints': "|".join(paths)}])
            df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
            st.success("🎯 Salvo!"); time.sleep(1); st.rerun()

# --- PÁGINA: HISTÓRICO (JANELAS DE PRÉDIO) ---
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
        
        cols = st.columns(5) # 5 janelas por linha
        for i, (_, row) in enumerate(df_disp.iterrows()):
            with cols[i % 5]:
                # Início da Janela
                st.markdown('<div class="trade-window">', unsafe_allow_html=True)
                
                # A Janela (Imagem com corte fixo)
                p_list = str(row['Prints']).split("|") if row['Prints'] and pd.notna(row['Prints']) else []
                if p_list and os.path.exists(p_list[0]):
                    img = Image.open(p_list[0])
                    st.image(img, use_container_width=True)
                else:
                    st.markdown('<div class="image-crop"><div style="color:#444">Sem Print</div></div>', unsafe_allow_html=True)
                
                # Info da Base
                st.markdown(f'<div class="trade-info-box">', unsafe_allow_html=True)
                st.markdown(f"**Trade #{row['Num']}**")
                st.caption(f"**{row['Contexto']}**")
                color = "green" if row['Resultado'] > 0 else "red"
                st.markdown(f":{color}[${row['Resultado']:,.2f}]")
                
                if st.button("Ver Trade", key=f"btn_{row['ID']}", type="primary"):
                    expand_trade_modal(row['ID'])
                
                st.markdown('</div></div>', unsafe_allow_html=True)
    else: st.info("Sem registros no histórico.")

# --- PÁGINA: CONFIGURAR ATM ---
elif selected == "Configurar ATM":
    st.title("⚙️ Editor ATM")
    with st.expander("✨ Criar Novo Template"):
        n = st.text_input("Nome"); l = st.number_input("Lote Total", 1); s = st.number_input("Stop Pts", 0.0)
        np = st.number_input("Qtd Saídas", 1, 6); nps = []
        for i in range(np):
            c1, c2 = st.columns(2)
            nps.append([c1.number_input(f"Pts P{i+1}", key=f"ap{i}"), c2.number_input(f"Qtd P{i+1}", key=f"aq{i}")])
        if st.button("💾 Salvar"):
            atm_db[n] = {"lote": l, "stop": s, "parciais": nps}
            save_atm(atm_db); st.success("ATM Salva!"); st.rerun()
