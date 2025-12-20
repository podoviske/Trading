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

# --- DIRETÓRIOS E PERSISTÊNCIA ---
IMG_DIR = "trade_prints"
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

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
    
    .stButton > button { width: 100%; border-radius: 8px; font-weight: 600; }
    .stButton > button[kind="secondary"] {
        color: #FF4B4B !important; border: 1px solid #FF4B4B !important; background: transparent !important;
    }
    div[data-testid="stSegmentedControl"] button {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background-color: #B20000 !important;
        font-weight: bold !important;
    }

    /* CSS DA GALERIA (O PRÉDIO) */
    .trade-window {
        background-color: #161616;
        border: 1px solid #333;
        border-radius: 12px;
        margin-bottom: 20px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        height: 360px;
    }
    .trade-window:hover { border-color: #B20000; box-shadow: 0px 0px 15px rgba(178, 0, 0, 0.4); }

    .image-crop-container {
        width: 100%;
        height: 180px;
        overflow: hidden;
        background-color: #000;
        display: flex;
        align-items: center;
        justify-content: center;
        border-bottom: 1px solid #333;
    }
    
    .image-crop-container img {
        width: 100% !important;
        height: 180px !important;
        object-fit: cover !important;
        object-position: center !important;
    }

    .trade-footer { 
        padding: 15px; 
        text-align: center; 
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        flex-grow: 1;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def load_atm():
    if os.path.exists(ATM_FILE):
        try:
            with open(ATM_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"Personalizado": {"lote": 1, "stop": 0.0, "parciais": []}}

def save_atm(configs):
    with open(ATM_FILE, 'w') as f: json.dump(configs, f)

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID', 'Prints']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'ID' not in df.columns:
                df['ID'] = [str(uuid.uuid4()) for _ in range(len(df))]
            if 'Prints' not in df.columns:
                df['Prints'] = ""
            for col in cols:
                if col not in df.columns: df[col] = 0
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def get_image_base64(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

atm_db = load_atm()
df = load_data()

# --- ESTADO ---
if 'n_extras' not in st.session_state: st.session_state.n_extras = 0
if 'confirmar_limpeza' not in st.session_state: st.session_state.confirmar_limpeza = False

def on_atm_change():
    st.session_state.n_extras = 0

# --- POP-UP DETALHES ---
@st.dialog("Visão Detalhada do Trade", width="large")
def expand_trade_modal(trade_id):
    temp_df = load_data()
    row_list = temp_df[temp_df['ID'] == trade_id]
    if row_list.empty:
        st.error("Trade não encontrado.")
        return
    row = row_list.iloc[0]
    c_img, c_det = st.columns([2, 1])
    with c_img:
        p_list = str(row['Prints']).split("|") if row['Prints'] else []
        if p_list and os.path.exists(p_list[0]):
            st.image(p_list[0], use_container_width=True)
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
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], styles={
            "nav-link-selected": {"background-color": "#B20000", "color": "white"}
        })

# --- ABA: DASHBOARD ---
if selected == "Dashboard":
    st.title("📊 EvoTrade Analytics")
    if not df.empty:
        filtro_view = st.segmented_control("Visualizar:", options=["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
        df_f = df.copy()
        if filtro_view != "Capital": df_f = df[df['Contexto'] == filtro_view]
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("P&L Total", f"${df_f['Resultado'].sum():,.2f}")
        m2.metric("Win Rate", f"{(len(df_f[df_f['Resultado']>0])/len(df_f)*100):.1f}%" if len(df_f)>0 else "0%")
        m3.metric("Total Trades", len(df_f))
        m4.metric("Ganho Médio", f"${df_f[df_f['Resultado']>0]['Resultado'].mean():,.2f}" if not df_f[df_f['Resultado']>0].empty else "$0")
        m5.metric("Perda Média", f"${abs(df_f[df_f['Resultado']<0]['Resultado'].mean()):,.2f}" if not df_f[df_f['Resultado']<0].empty else "$0")

        st.markdown("---")
        tipo_g = st.radio("Evolução por:", ["Tempo (Data)", "Trade a Trade"], horizontal=True)
        df_g = df_f.sort_values('Data').reset_index(drop=True)
        df_g['Acumulado'] = df_g['Resultado'].cumsum()
        x_axis = 'Data' if tipo_g == "Tempo (Data)" else df_g.index + 1
        fig = px.area(df_g, x=x_axis, y='Acumulado', template="plotly_dark")
        fig.update_traces(line_color='#B20000', line_shape='spline', fillcolor='rgba(178, 0, 0, 0.2)')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

# --- ABA: REGISTRAR TRADE ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    c_topo1, c_topo2 = st.columns([3, 1])
    with c_topo1:
        atm_sel_nome = st.selectbox("🎯 Estratégia ATM", options=list(atm_db.keys()), key='atm_selecionado', on_change=on_atm_change)
        config = atm_db[atm_sel_nome]
    with c_topo2:
        st.write("") 
        cb1, cb2 = st.columns(2)
        cb1.button("➕", on_click=lambda: st.session_state.update({"n_extras": st.session_state.n_extras + 1}))
        cb2.button("🧹", on_click=lambda: st.rerun())
    st.markdown("---")
    key_prefix = atm_sel_nome.replace(" ", "_")
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
    with c2:
        lote_t = st.number_input("Contratos", min_value=1, step=1, value=int(config["lote"]), key=f"lote_{key_prefix}")
        stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]), key=f"stop_{key_prefix}")
        risco = stop_p * MULTIPLIERS[ativo] * lote_t
        if lote_t > 0: st.metric("Risco Total", f"${risco:,.2f}")
        up_files = st.file_uploader("📸 Prints (Upload ou Ctrl+V)", accept_multiple_files=True)
    with c3:
        st.write("**Saídas Executadas**")
        saidas = []; alocado = 0
        for i, p_config in enumerate(config["parciais"]):
            s1, s2 = st.columns(2)
            p = s1.number_input(f"Pts P{i+1}", key=f"p_atm_{i}_{key_prefix}", value=float(p_config[0]))
            q = s2.number_input(f"Qtd P{i+1}", key=f"q_atm_{i}_{key_prefix}", value=int(p_config[1]), step=1)
            saidas.append((p, q)); alocado += q
        for i in range(st.session_state.n_extras):
            idx = len(config["parciais"]) + i
            s1, s2 = st.columns(2)
            p = s1.number_input(f"Pts Extra {i+1}", key=f"p_ext_{idx}_{key_prefix}", value=0.0)
            q = s2.number_input(f"Qtd Extra {i+1}", key=f"q_ext_{idx}_{key_prefix}", value=0, step=1)
            saidas.append((p, q)); alocado += q
        if lote_t > 0:
            resta = lote_t - alocado
            if resta != 0:
                msg = f"FALTAM {resta} CONTRATOS" if resta > 0 else f"EXCESSO DE {abs(resta)} CONTRATOS"
                st.markdown(f'<div class="piscante-erro">{msg}</div>', unsafe_allow_html=True)
            else: st.success("✅ Posição Completa")

    st.markdown("---")
    r1, r2 = st.columns(2)
    with r1:
        if st.button("💾 REGISTRAR GAIN", use_container_width=True):
            if lote_t > 0 and alocado == lote_t:
                res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas])
                pts_m = sum([s[0] * s[1] for s in saidas]) / lote_t
                n_id = str(uuid.uuid4())
                paths = []
                for i, f in enumerate(up_files):
                    p = os.path.join(IMG_DIR, f"{n_id}_{i}.png")
                    with open(p, "wb") as bf: bf.write(f.getbuffer())
                    paths.append(p)
                n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel_nome, 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': risco, 'ID': n_id, 'Prints': "|".join(paths)}])
                df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.success("🎯 Trade registrado!"); time.sleep(1); st.rerun()
    with r2:
        if st.button("🚨 REGISTRAR STOP FULL", type="secondary", use_container_width=True):
            if lote_t > 0 and stop_p > 0:
                pre = -(stop_p * MULTIPLIERS[ativo] * lote_t)
                n_id = str(uuid.uuid4())
                n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel_nome, 'Resultado': pre, 'Pts_Medio': -stop_p, 'Risco_Fin': risco, 'ID': n_id, 'Prints': ""}])
                df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.error("🚨 Stop registrado!"); time.sleep(1); st.rerun()

# --- ABA: CONFIGURAR ATM ---
elif selected == "Configurar ATM":
    st.title("⚙️ Editor de Estratégias ATM")
    with st.expander("✨ Criar Novo Template", expanded=True):
        n = st.text_input("Nome"); l = st.number_input("Lote Total", 1); s = st.number_input("Stop (Pts)", 0.0)
        np = st.number_input("Número de Alvos", 1, 6); nps = []
        for i in range(np):
            c1, c2 = st.columns(2)
            pt = c1.number_input(f"Alvo {i+1} Pts", key=f"conf_pts_{i}", value=0.0)
            qt = c2.number_input(f"Contratos {i+1}", key=f"conf_qtd_{i}", min_value=1, step=1)
            nps.append([pt, qt])
        if st.button("💾 Salvar ATM"):
            atm_db[n] = {"lote": l, "stop": s, "parciais": nps}
            save_atm(atm_db); st.success("ATM Salva!"); st.rerun()
    st.markdown("---")
    for nome in list(atm_db.keys()):
        if nome != "Personalizado":
            cn, cb = st.columns([4, 1]); cn.write(f"**{nome}**")
            if cb.button("Excluir", key=f"del_{nome}"): del atm_db[nome]; save_atm(atm_db); st.rerun()

# --- ABA: HISTÓRICO ---
elif selected == "Histórico":
    st.title("📜 Galeria de Operações")
    if 'to_delete' in st.session_state:
        df = df[df['ID'] != st.session_state.to_delete]
        df.to_csv(CSV_FILE, index=False); del st.session_state.to_delete; st.rerun()
    
    if not df.empty:
        col_export, col_limpar = st.columns([4, 1])
        csv_data = df.to_csv(index=False).encode('utf-8')
        col_export.download_button("📥 Backup (CSV)", data=csv_data, file_name="backup_trades.csv")
        if not st.session_state.confirmar_limpeza:
            if col_limpar.button("🗑️ LIMPAR TUDO", type="secondary"): 
                st.session_state.confirmar_limpeza = True; st.rerun()
        else:
            if st.button("✅ CONFIRMAR LIMPEZA"):
                if os.path.exists(CSV_FILE): os.remove(CSV_FILE)
                st.session_state.confirmar_limpeza = False; st.rerun()
        
        st.markdown("---")
        df_disp = df.copy(); df_disp['Num'] = range(1, len(df_disp) + 1)
        df_disp = df_disp.iloc[::-1]
        
        num_trades = len(df_disp)
        for i in range(0, num_trades, 5):
            cols = st.columns(5)
            for j in range(5):
                if i + j < num_trades:
                    row = df_disp.iloc[i + j]
                    with cols[j]:
                        st.markdown('<div class="trade-window">', unsafe_allow_html=True)
                        p_list = str(row['Prints']).split("|") if row['Prints'] else []
                        if p_list and os.path.exists(p_list[0]):
                            img_b64 = get_image_base64(p_list[0])
                            if img_b64:
                                st.markdown(f'<div class="image-crop-container"><img src="data:image/png;base64,{img_b64}"></div>', unsafe_allow_html=True)
                            else: st.markdown('<div class="image-crop-container" style="color:#444">Erro imagem</div>', unsafe_allow_html=True)
                        else: st.markdown('<div class="image-crop-container"><span style="color:#444; font-size:12px">Sem Print</span></div>', unsafe_allow_html=True)
                        
                        color = "#00FF88" if row['Resultado'] > 0 else "#FF4B4B"
                        st.markdown(f'''
                            <div class="trade-footer">
                                <div><b style="color:white">Trade #{row["Num"]}</b><br><small style="color:#888">{row["Contexto"]}</small></div>
                                <div style="color:{color}; font-weight:bold; font-size:1.1rem">${row["Resultado"]:,.2f}</div>
                        ''', unsafe_allow_html=True)
                        if st.button("Ver", key=f"btn_hist_{row['ID']}_{i+j}"): expand_trade_modal(row['ID'])
                        st.markdown('</div></div>', unsafe_allow_html=True)
    else: st.info("Vazio.")
