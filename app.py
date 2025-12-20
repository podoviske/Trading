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

# --- ESTILO CSS GERAL (PROTEGIDO) ---
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
        background-color: #1E1E1E !important; color: #FFFFFF !important; border: none !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background-color: #B20000 !important; font-weight: bold !important;
    }

    /* ESTILO DO HISTÓRICO - ISOLADO */
    .trade-card {
        background-color: #161616; border: 1px solid #333; border-radius: 12px;
        margin-bottom: 20px; overflow: hidden; display: flex; flex-direction: column; height: 380px;
    }
    .trade-card:hover { border-color: #B20000; box-shadow: 0px 0px 15px rgba(178, 0, 0, 0.4); }
    .img-container {
        width: 100%; height: 180px; overflow: hidden; background-color: #000;
        display: flex; align-items: center; justify-content: center; border-bottom: 1px solid #333;
    }
    .img-container img { width: 100% !important; height: 100% !important; object-fit: cover !important; }
    .card-footer { padding: 15px; text-align: center; display: flex; flex-direction: column; justify-content: space-between; flex-grow: 1; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES ---
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
            if 'ID' not in df.columns: df['ID'] = [str(uuid.uuid4()) for _ in range(len(df))]
            if 'Prints' not in df.columns: df['Prints'] = ""
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def get_base64(path):
    try:
        with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return None

atm_db = load_atm()
df = load_data()

# --- MODAL ---
@st.dialog("Detalhes", width="large")
def expand_modal(trade_id):
    row = df[df['ID'] == trade_id].iloc[0]
    c1, c2 = st.columns([2, 1])
    with c1:
        p = str(row['Prints']).split("|")[0] if row['Prints'] else ""
        if p and os.path.exists(p): st.image(p, use_container_width=True)
        else: st.info("Sem print.")
    with c2:
        st.write(f"📅 {row['Data']} | {row['Ativo']}")
        res_c = "green" if row['Resultado'] > 0 else "red"
        st.markdown(f"💰 **Resultado:** :{res_c}[${row['Resultado']:,.2f}]")
        if st.button("🗑️ Deletar"):
            st.session_state.to_delete = trade_id
            st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="logo-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], styles={"nav-link-selected": {"background-color": "#B20000"}})

# --- DASHBOARD ---
if selected == "Dashboard":
    st.title("📊 EvoTrade Analytics")
    if not df.empty:
        f_v = st.segmented_control("Visualizar:", options=["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
        df_f = df[df['Contexto'] == f_v] if f_v != "Capital" else df.copy()
        
        total_trades = len(df_f)
        wins = df_f[df_f['Resultado'] > 0]
        losses = df_f[df_f['Resultado'] < 0]
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        avg_win = wins['Resultado'].mean() if not wins.empty else 0
        avg_loss = abs(losses['Resultado'].mean()) if not losses.empty else 0
        rr_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("P&L Total", f"${df_f['Resultado'].sum():,.2f}")
        m2.metric("Win Rate", f"{win_rate:.1f}%")
        m3.metric("Risco:Retorno", f"1:{rr_ratio:.2f}")
        m4.metric("Ganho Médio", f"${avg_win:,.2f}")
        m5.metric("Perda Média", f"$-{avg_loss:,.2f}")
        
        st.markdown("---")
        tipo_g = st.radio("Evolução por:", ["Tempo (Data)", "Trade a Trade"], horizontal=True)
        df_g = df_f.sort_values('Data').reset_index(drop=True)
        df_g['Acumulado'] = df_g['Resultado'].cumsum()
        x_axis = 'Data' if tipo_g == "Tempo (Data)" else df_g.index + 1
        
        fig = px.area(df_g, x=x_axis, y='Acumulado', template="plotly_dark")
        fig.update_traces(line_color='#B20000', line_shape='spline', fillcolor='rgba(178, 0, 0, 0.2)', mode='lines')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

# --- REGISTRAR TRADE ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    if 'n_extras' not in st.session_state: st.session_state.n_extras = 0
    c_topo1, c_topo2 = st.columns([3, 1])
    with c_topo1:
        atm_sel = st.selectbox("🎯 Estratégia ATM", list(atm_db.keys()), on_change=lambda: st.session_state.update({"n_extras": 0}))
        config = atm_db[atm_sel]
    with c_topo2:
        st.write(""); cb1, cb2 = st.columns(2)
        cb1.button("➕", on_click=lambda: st.session_state.update({"n_extras": st.session_state.n_extras + 1}))
        cb2.button("🧹", on_click=lambda: st.rerun())
    
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
    with c2:
        lote_t = st.number_input("Contratos", min_value=0, value=int(config["lote"]))
        stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]))
        if lote_t > 0: st.metric("Risco Total", f"${(stop_p * MULTIPLIERS[ativo] * lote_t):,.2f}")
        up_files = st.file_uploader("📸 Prints", accept_multiple_files=True)
    with c3:
        st.write("**Saídas Executadas**")
        saidas = []; alocado = 0
        for i, p_c in enumerate(config["parciais"]):
            s1, s2 = st.columns(2)
            p = s1.number_input(f"Pts P{i+1}", value=float(p_c[0]), key=f"p_{i}")
            q = s2.number_input(f"Qtd P{i+1}", value=int(p_c[1]), key=f"q_{i}")
            saidas.append((p, q)); alocado += q
        for i in range(st.session_state.n_extras):
            s1, s2 = st.columns(2)
            p = s1.number_input(f"Pts Ex {i+1}", key=f"pe_{i}")
            q = s2.number_input(f"Qtd Ex {i+1}", key=f"qe_{i}")
            saidas.append((p, q)); alocado += q
        if lote_t > 0 and lote_t != alocado: st.markdown(f'<div class="piscante-erro">FALTAM {lote_t-alocado} CONTRATOS</div>', unsafe_allow_html=True)
        elif lote_t == alocado and lote_t > 0: st.success("✅ Posição Completa")

    st.markdown("---")
    r1, r2 = st.columns(2)
    with r1:
        if st.button("💾 REGISTRAR GAIN", use_container_width=True):
            if lote_t > 0 and alocado == lote_t:
                res = sum([s[0]*MULTIPLIERS[ativo]*s[1] for s in saidas])
                pts_m = sum([s[0]*s[1] for s in saidas]) / lote_t
                n_id = str(uuid.uuid4())
                paths = []
                for i, f in enumerate(up_files):
                    p = os.path.join(IMG_DIR, f"{n_id}_{i}.png"); paths.append(p)
                    with open(p, "wb") as bf: bf.write(f.getbuffer())
                n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': (stop_p*MULTIPLIERS[ativo]*lote_t), 'ID': n_id, 'Prints': "|".join(paths)}])
                df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.success("🎯 Trade registrado!"); time.sleep(1); st.rerun()
    with r2:
        if st.button("🚨 REGISTRAR STOP FULL", type="secondary", use_container_width=True):
            if lote_t > 0 and stop_p > 0:
                pre = -(stop_p * MULTIPLIERS[ativo] * lote_t)
                n_id = str(uuid.uuid4())
                n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': pre, 'Pts_Medio': -stop_p, 'Risco_Fin': abs(pre), 'ID': n_id, 'Prints': ""}])
                df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.error("🚨 Stop registrado!"); time.sleep(1); st.rerun()

# --- ABA: CONFIGURAR ATM ---
elif selected == "Configurar ATM":
    st.title("⚙️ Editor de Estratégias ATM")
    with st.expander("✨ Criar Novo Template", expanded=True):
        n = st.text_input("Nome da Estratégia")
        ca1, ca2 = st.columns(2)
        l_p = ca1.number_input("Lote Total", min_value=1, step=1)
        s_p = ca2.number_input("Stop (Pts)", min_value=0.0, step=0.25)
        n_p = st.number_input("Número de Alvos", 1, 6, 1)
        novas_p = []
        for i in range(n_p):
            cp1, cp2 = st.columns(2)
            pt = cp1.number_input(f"Alvo P{i+1} (Pts)", key=f"cpt_{i}")
            qt = cp2.number_input(f"Contratos P{i+1}", key=f"cqt_{i}", min_value=1)
            novas_p.append([pt, qt])
        if st.button("💾 Salvar ATM"):
            atm_db[n] = {"lote": l_p, "stop": s_p, "parciais": novas_p}
            save_atm(atm_db); st.success("Salvo!"); st.rerun()
    for nome in list(atm_db.keys()):
        if nome != "Personalizado":
            cn, cb = st.columns([4, 1]); cn.write(f"**{nome}**")
            if cb.button("Excluir", key=f"del_{nome}"): del atm_db[nome]; save_atm(atm_db); st.rerun()

# --- ABA: HISTÓRICO (IMAGEM NO TOPO, BOTÃO E INFO ABAIXO) ---
elif selected == "Histórico":
    st.title("📜 Galeria de Operações")
    if 'to_delete' in st.session_state:
        df = df[df['ID'] != st.session_state.to_delete]
        df.to_csv(CSV_FILE, index=False); del st.session_state.to_delete; st.rerun()
    
    if not df.empty:
        st.download_button("📥 Backup CSV", data=df.to_csv(index=False).encode('utf-8'), file_name="backup.csv")
        st.markdown("---")
        df_disp = df.iloc[::-1].copy(); df_disp['Num'] = range(len(df_disp), 0, -1)
        num_trades = len(df_disp)
        
        for i in range(0, num_trades, 5):
            cols = st.columns(5)
            for j in range(5):
                if i + j < num_trades:
                    row = df_disp.iloc[i + j]
                    with cols[j]:
                        st.markdown('<div class="trade-card">', unsafe_allow_html=True)
                        
                        # --- PARTE SUPERIOR: IMAGEM/PRINT ---
                        p_list = str(row['Prints']).split("|") if row['Prints'] else []
                        img_html = ""
                        if p_list and os.path.exists(p_list[0]):
                            b64 = get_base64(p_list[0])
                            img_html = f'<div class="img-container"><img src="data:image/png;base64,{b64}"></div>'
                        else:
                            img_html = '<div class="img-container" style="color:#444; font-size:12px">Sem Print</div>'
                        st.markdown(img_html, unsafe_allow_html=True)

                        # --- PARTE INFERIOR: BOTÃO "OLHO" E INFO LADO A LADO ---
                        st.markdown('<div class="card-footer">', unsafe_allow_html=True)
                        ci1, ci2 = st.columns([1, 2])
                        with ci1:
                            if st.button("👁️", key=f"v_{row['ID']}_{i+j}", help="Ver detalhes"):
                                expand_modal(row['ID'])
                        with ci2:
                            st.markdown(f'''
                                <div style="text-align: left; line-height: 1.2;">
                                    <b style="color:white; font-size:0.85rem">Trade #{row["Num"]}</b><br>
                                    <small style="color:#888; font-size:0.7rem">{row["Contexto"]}</small>
                                </div>
                            ''', unsafe_allow_html=True)
                        
                        # Resultado Financeiro na Base
                        color = "#00FF88" if row['Resultado'] > 0 else "#FF4B4B"
                        st.markdown(f'''
                            <div style="color:{color}; font-weight:bold; font-size:1.1rem; margin-top:10px; border-top:1px solid #222; padding-top:5px;">
                                ${row["Resultado"]:,.2f}
                            </div>
                        ''', unsafe_allow_html=True)
                        
                        st.markdown('</div></div>', unsafe_allow_html=True)
    else: st.info("Vazio.")
