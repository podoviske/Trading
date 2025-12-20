import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
import json
import time
import uuid
import base64

# --- CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# Diretórios e Arquivos
IMG_DIR = "trade_prints"
if not os.path.exists(IMG_DIR): os.makedirs(IMG_DIR)
CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

# --- FUNÇÃO PARA TRATAR IMAGEM NO HISTÓRICO (PRENDE NO BALÃO) ---
def get_image_base64(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

# --- ESTILO CSS (O SEGREDO DO ALINHAMENTO) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    
    /* MOLDURA DA JANELA (O PRÉDIO) */
    .trade-window {
        background-color: #161616;
        border: 1px solid #333;
        border-radius: 12px;
        margin-bottom: 20px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        height: 340px;
    }
    .trade-window:hover { border-color: #B20000; box-shadow: 0px 0px 15px rgba(178, 0, 0, 0.4); }

    /* A JANELA COM RECORTE FORÇADO */
    .image-crop-container {
        width: 100%;
        height: 180px;
        overflow: hidden;
        background-color: #000;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .image-crop-container img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: center;
    }

    .trade-footer { 
        padding: 12px; 
        text-align: center; 
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        height: 160px;
    }

    .logo-container { padding: 20px 15px; display: flex; flex-direction: column; }
    .logo-main { color: #B20000; font-size: 26px; font-weight: 900; line-height: 1; }
    .logo-sub { color: white; font-size: 22px; font-weight: 700; margin-top: -5px; }
    
    .stButton > button { width: 100%; border-radius: 8px; font-weight: 600; }
    
    @keyframes blinking { 0% { background-color: #440000; } 50% { background-color: #B20000; } 100% { background-color: #440000; } }
    .piscante-erro { padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; animation: blinking 2s infinite; }

    div[data-testid="stSegmentedControl"] button { background-color: #1E1E1E !important; color: white !important; border: none !important; }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] { background-color: #B20000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE PERSISTÊNCIA ---
def load_atm():
    if os.path.exists(ATM_FILE):
        try: return json.load(open(ATM_FILE))
        except: pass
    return {"Personalizado": {"lote": 1, "stop": 0.0, "parciais": []}}

def save_atm(configs):
    with open(ATM_FILE, 'w') as f: json.dump(configs, f)

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID', 'Prints']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'ID' not in df.columns: df['ID'] = [str(uuid.uuid4()) for _ in range(len(df))]
            if 'Prints' not in df.columns: df['Prints'] = ""
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

atm_db = load_atm()
df = load_data()

# --- POP-UP DE DETALHES ---
@st.dialog("Visão Detalhada do Trade", width="large")
def expand_trade_modal(trade_id):
    temp_df = load_data()
    row = temp_df[temp_df['ID'] == trade_id].iloc[0]
    c_img, c_det = st.columns([2, 1])
    with c_img:
        p_list = str(row['Prints']).split("|") if row['Prints'] else []
        if p_list and os.path.exists(p_list[0]): st.image(p_list[0], use_container_width=True)
        else: st.info("Sem print disponível.")
    with c_det:
        st.subheader("Informações")
        st.write(f"📅 **Data:** {row['Data']} | **Ativo:** {row['Ativo']}")
        st.write(f"🏗️ **Contexto:** {row['Contexto']} | **ATM:** {row['ATM']}")
        color = "green" if row['Resultado'] > 0 else "red"
        st.markdown(f"💰 **Resultado:** :{color}[${row['Resultado']:,.2f}]")
        st.divider()
        if st.button("🗑️ Excluir Operação", type="secondary", key=f"modal_del_{trade_id}"):
            st.session_state.to_delete = trade_id
            st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="logo-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], styles={"nav-link-selected": {"background-color": "#B20000"}})

# --- PÁGINA: DASHBOARD ---
if selected == "Dashboard":
    st.title("📊 EvoTrade Analytics")
    if not df.empty:
        filtro = st.segmented_control("Visualizar:", options=["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
        df_f = df[df['Contexto'] == filtro] if filtro != "Capital" else df.copy()
        tipo_g = st.radio("Evolução por:", ["Tempo (Data)", "Trade a Trade"], horizontal=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("P&L Total", f"${df_f['Resultado'].sum():,.2f}")
        m2.metric("Win Rate", f"{(len(df_f[df_f['Resultado']>0])/len(df_f)*100):.1f}%" if len(df_f)>0 else "0%")
        m3.metric("Total Trades", len(df_f))
        df_g = df_f.sort_values('Data').reset_index()
        df_g['Acumulado'] = df_g['Resultado'].cumsum()
        x_axis = 'Data' if tipo_g == "Tempo (Data)" else df_g.index + 1
        fig = px.area(df_g, x=x_axis, y='Acumulado', template="plotly_dark")
        fig.update_traces(line_color='#B20000', line_shape='spline', fillcolor='rgba(178, 0, 0, 0.2)')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

# --- PÁGINA: REGISTRAR TRADE ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    atm_sel = st.selectbox("🎯 ATM", options=list(atm_db.keys()))
    config = atm_db[atm_sel]
    if 'n_extras' not in st.session_state: st.session_state.n_extras = 0
    
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
    with c2:
        lote_t = st.number_input("Lote Total", min_value=1, value=max(1, int(config.get("lote", 1))))
        stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config.get("stop", 0)))
        up_files = st.file_uploader("📸 Prints (Ctrl+V)", accept_multiple_files=True)
        if st.button("➕ Adicionar Extra"): st.session_state.n_extras += 1
    with c3:
        st.write("**Saídas**")
        saidas = []; alocado = 0
        for i, p_c in enumerate(config.get("parciais", [])):
            sc1, sc2 = st.columns(2)
            pts = sc1.number_input(f"Pts P{i+1}", value=float(p_c[0]), key=f"pts_{i}")
            qtd = sc2.number_input(f"Qtd P{i+1}", value=int(p_c[1]), key=f"qtd_{i}")
            saidas.append((pts, qtd)); alocado += qtd
        for i in range(st.session_state.n_extras):
            sc1, sc2 = st.columns(2)
            pts = sc1.number_input(f"Pts Extra {i+1}", key=f"ex_p_{i}")
            qtd = sc2.number_input(f"Qtd Extra {i+1}", key=f"ex_q_{i}")
            saidas.append((pts, qtd)); alocado += qtd
        if lote_t != alocado: st.markdown(f'<div class="piscante-erro">FALTAM {lote_t - alocado} CONTRATOS</div>', unsafe_allow_html=True)
        else: st.success("✅ OK")

    if st.button("💾 REGISTRAR"):
        if lote_t == alocado:
            t_id = str(uuid.uuid4())
            paths = []
            for i, f in enumerate(up_files):
                p = os.path.join(IMG_DIR, f"{t_id}_{i}.png"); paths.append(p)
                with open(p, "wb") as bf: bf.write(f.getbuffer())
            res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas])
            n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': (res/(lote_t*MULTIPLIERS[ativo])), 'Risco_Fin': (stop_p * MULTIPLIERS[ativo] * lote_t), 'ID': t_id, 'Prints': "|".join(paths)}])
            df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
            st.success("Salvo!"); st.session_state.n_extras = 0; time.sleep(1); st.rerun()

# --- PÁGINA: HISTÓRICO ---
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
                st.markdown('<div class="trade-window">', unsafe_allow_html=True)
                p_list = str(row['Prints']).split("|") if row['Prints'] else []
                if p_list and os.path.exists(p_list[0]):
                    img_b64 = get_image_base64(p_list[0])
                    st.markdown(f'<div class="image-crop-container"><img src="data:image/png;base64,{img_b64}"></div>', unsafe_allow_html=True)
                else: st.markdown('<div class="image-crop-container" style="color:#444">Sem Print</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="trade-footer"><div><b>Trade #{row["Num"]}</b><br><small>{row["Contexto"]}</small></div>', unsafe_allow_html=True)
                color = "green" if row["Resultado"]>0 else "red"
                st.markdown(f'<div style="color:{"#00FF88" if row["Resultado"]>0 else "#FF4B4B"}; font-weight:bold">${row["Resultado"]:,.2f}</div>', unsafe_allow_html=True)
                if st.button("Ver", key=f"btn_{row['ID']}_{i}"): expand_trade_modal(row['ID'])
                st.markdown('</div></div>', unsafe_allow_html=True)
    else: st.info("Vazio.")

# --- PÁGINA: CONFIGURAR ATM ---
elif selected == "Configurar ATM":
    st.title("⚙️ Editor ATM")
    with st.expander("✨ Novo Template"):
        n = st.text_input("Nome"); l = st.number_input("Lote", 1); s = st.number_input("Stop", 0.0)
        np = st.number_input("Saídas", 1, 6); nps = []
        for i in range(np):
            c1, c2 = st.columns(2)
            nps.append([c1.number_input(f"Alvo {i+1}", key=f"ap{i}"), c2.number_input(f"Qtd {i+1}", key=f"aq{i}")])
        if st.button("Salvar ATM"):
            atm_db[n] = {"lote": l, "stop": s, "parciais": nps}
            save_atm(atm_db); st.rerun()
