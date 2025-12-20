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

# --- SISTEMA DE LOGIN SEGURO ---
def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    def password_entered():
        if (
            st.session_state["username"] == "admin" 
            and st.session_state["password"] == "1234"
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("""
            <style>
            .login-container {
                max-width: 400px;
                margin: 50px auto;
                padding: 20px;
                background-color: #161616;
                border-radius: 15px;
                border: 1px solid #B20000;
                text-align: center;
            }
            .logo-main { color: #B20000; font-size: 50px; font-weight: 900; }
            .logo-sub { color: white; font-size: 35px; font-weight: 700; margin-top: -15px; }
            @media (max-width: 768px) {
                .login-container { margin: 20px auto; width: 90%; }
                .logo-main { font-size: 40px; }
                .logo-sub { font-size: 28px; }
            }
            </style>
        """, unsafe_allow_html=True)
        
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.markdown('<div class="login-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div>', unsafe_allow_html=True)
            st.write("---")
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("😕 Credenciais incorretas.")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return st.session_state["password_correct"]

# --- EXECUÇÃO DO APP ---
if check_password():

    # --- DIRETÓRIOS E PERSISTÊNCIA ---
    IMG_DIR = "trade_prints"
    if not os.path.exists(IMG_DIR):
        os.makedirs(IMG_DIR)

    CSV_FILE = 'evotrade_data.csv'
    ATM_FILE = 'atm_configs.json'
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}

    # --- ESTILO CSS GERAL PREMIUM (RESPONSIVO) ---
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
        .stApp { background-color: #0F0F0F; }
        
        /* Dashboard Metric Cards */
        .metric-container {
            background-color: #161616;
            border: 1px solid #262626;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.2s;
            margin-bottom: 10px;
        }
        .metric-container:hover { border-color: #B20000; transform: translateY(-2px); }
        .metric-label { color: #888; font-size: 11px; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }
        .metric-value { color: white; font-size: 20px; font-weight: bold; }
        
        /* Ajustes Mobile para Métricas */
        @media (max-width: 768px) {
            .metric-value { font-size: 18px; }
            .metric-container { padding: 15px; }
            [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
        }

        @keyframes blinking {
            0% { background-color: #440000; }
            50% { background-color: #B20000; }
            100% { background-color: #440000; }
        }
        .piscante-erro {
            padding: 15px; border-radius: 5px; color: white; font-weight: bold;
            text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000;
        }
        .logo-container { padding: 10px 5px; display: flex; flex-direction: column; }
        .logo-main-side { color: #B20000; font-size: 26px; font-weight: 900; line-height: 1; }
        .logo-sub-side { color: white; font-size: 22px; font-weight: 700; margin-top: -5px; }
        
        .stButton > button { width: 100%; border-radius: 8px; font-weight: 600; }

        .trade-card {
            background-color: #161616; border: 1px solid #333; border-radius: 12px;
            margin-bottom: 20px; overflow: hidden; display: flex; flex-direction: column; height: auto; min-height: 320px;
        }
        .img-container {
            width: 100%; height: 160px; overflow: hidden; background-color: #000;
            display: flex; align-items: center; justify-content: center; border-bottom: 1px solid #333;
        }
        .img-container img { width: 100% !important; height: 100% !important; object-fit: cover !important; }
        .card-footer { padding: 12px; text-align: center; }
        
        /* Ajuste de Galeria Mobile */
        @media (max-width: 768px) {
            .trade-card { margin-bottom: 15px; }
        }
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
        cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID', 'Prints', 'Notas']
        if os.path.exists(CSV_FILE):
            try:
                df = pd.read_csv(CSV_FILE)
                if 'ID' not in df.columns: df['ID'] = [str(uuid.uuid4()) for _ in range(len(df))]
                if 'Prints' not in df.columns: df['Prints'] = ""
                if 'Notas' not in df.columns: df['Notas'] = ""
                df['Data'] = pd.to_datetime(df['Data']).dt.date
                return df
            except: return pd.DataFrame(columns=cols)
        return pd.DataFrame(columns=cols)

    def get_base64(path):
        try:
            with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
        except: return None

    def card_metric(label, value, color="white"):
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color: {color};">{value}</div>
            </div>
        """, unsafe_allow_html=True)

    atm_db = load_atm()
    df = load_data()

    # --- MODAL ---
    @st.dialog("Detalhes do Trade", width="large")
    def expand_modal(trade_id):
        current_df = load_data()
        row = current_df[current_df['ID'] == trade_id].iloc[0]
        c1, c2 = st.columns([1.5, 1])
        with c1:
            raw_prints = str(row['Prints']) if pd.notna(row['Prints']) else ""
            p_list = [p.strip() for p in raw_prints.split("|") if p.strip() and os.path.exists(p.strip())]
            if p_list:
                tabs = st.tabs([f"Print {i+1}" for i in range(len(p_list))])
                for i, tab in enumerate(tabs):
                    with tab: st.image(p_list[i], use_container_width=True)
            else: st.info("Sem print disponível.")
            st.markdown("---")
            notas_input = st.text_area("Notas:", value=str(row['Notas']) if pd.notna(row['Notas']) else "", height=150)
            if st.button("💾 Salvar Notas"):
                current_df.loc[current_df['ID'] == trade_id, 'Notas'] = notas_input
                current_df.to_csv(CSV_FILE, index=False); st.success("Salvo!"); time.sleep(1); st.rerun()
        with c2:
            st.markdown(f"### Trade Info")
            st.write(f"📅 **Data:** {row['Data']} | 📈 **Ativo:** {row['Ativo']}")
            dir_color = "cyan" if row['Direcao'] == "Compra" else "orange"
            st.markdown(f"↕️ **Direção:** :{dir_color}[{row['Direcao']}]")
            st.divider()
            res_c = "#00FF88" if row['Resultado'] > 0 else "#FF4B4B"
            st.markdown(f"💰 **P&L:** <span style='color:{res_c}; font-weight:bold; font-size:20px'>${row['Resultado']:,.2f}</span>", unsafe_allow_html=True)
            st.write(f"📊 **Média Pts:** {row['Pts_Medio']:.2f}")
            if st.button("🗑️ Deletar Trade", type="primary"):
                st.session_state.to_delete = trade_id; st.rerun()

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown('<div class="logo-container"><div class="logo-main-side">EVO</div><div class="logo-sub-side">TRADE</div></div>', unsafe_allow_html=True)
        selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
            icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], styles={"nav-link-selected": {"background-color": "#B20000"}})
        st.write("---")
        if st.button("Sair / Logout"):
            del st.session_state["password_correct"]
            st.rerun()

    # --- DASHBOARD ---
    if selected == "Dashboard":
        st.markdown("## 📊 Analytics")
        if not df.empty:
            f_v = st.segmented_control("Filtrar Visão:", ["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
            df_f = df.copy() if f_v == "Capital" else df[df['Contexto'] == f_v].copy()
            if not df_f.empty:
                total = len(df_f); wins = df_f[df_f['Resultado'] > 0]; losses = df_f[df_f['Resultado'] < 0]
                wr = (len(wins)/total*100) if total > 0 else 0
                aw = wins['Resultado'].mean() if not wins.empty else 0
                al = abs(losses['Resultado'].mean()) if not losses.empty else 0
                rr = (aw/al) if al > 0 else 0
                avg_pts_gain = wins['Pts_Medio'].mean() if not wins.empty else 0
                avg_pts_loss = abs(losses['Pts_Medio'].mean()) if not losses.empty else 0
                avg_lote = df_f['Lote'].mean() if total > 0 else 0
                total_pl = df_f['Resultado'].sum()

                # Grid de métricas
                r1c1, r1c2, r1c3 = st.columns(3)
                with r1c1: card_metric("P&L TOTAL", f"${total_pl:,.2f}", "#00FF88" if total_pl > 0 else "#FF4B4B")
                with r1c2: card_metric("WIN RATE", f"{wr:.1f}%", "#B20000")
                with r1c3: card_metric("TRADES", total)
                
                r2c1, r2c2, r2c3 = st.columns(3)
                with r2c1: card_metric("RISCO:RETORNO", f"1:{rr:.2f}")
                with r2c2: card_metric("LOTE MÉDIO", f"{avg_lote:.1f}")
                with r2c3: card_metric("GAIN MÉD ($)", f"${aw:,.2f}", "#00FF88")
                
                r3c1, r3c2, r3c3 = st.columns(3)
                with r3c1: card_metric("PTS GAIN", f"{avg_pts_gain:.2f}")
                with r3c2: card_metric("PTS LOSS", f"{avg_pts_loss:.2f}")
                with r3c3: card_metric("LOSS MÉD ($)", f"$-{al:,.2f}", "#FF4B4B")
                
                st.markdown("---")
                tipo_g = st.radio("Evolução por:", ["Trade a Trade", "Tempo (Data)"], horizontal=True)
                df_g = df_f.sort_values('Data').reset_index(drop=True)
                df_g['Acumulado'] = df_g['Resultado'].cumsum()
                x_axis = df_g.index + 1 if tipo_g == "Trade a Trade" else 'Data'
                fig = px.area(df_g, x=x_axis, y='Acumulado', template="plotly_dark", markers=True)
                fig.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)', line_shape='spline')
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning(f"Sem trades para {f_v}")
        else: st.info("Aguardando dados...")

    # --- REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Registro")
        if 'n_extras' not in st.session_state: st.session_state.n_extras = 0
        if 'last_atm' not in st.session_state: st.session_state.last_atm = None
        
        c1, c2 = st.columns([3, 1])
        with c1:
            atm_sel = st.selectbox("🎯 ATM", list(atm_db.keys()))
            config = atm_db[atm_sel]
            if st.session_state.last_atm != atm_sel:
                st.session_state.n_extras = 0; st.session_state.last_atm = atm_sel; st.rerun()
        with c2:
            st.write(""); cb1, cb2 = st.columns(2)
            cb1.button("➕", on_click=lambda: st.session_state.update({"n_extras": st.session_state.n_extras + 1}))
            cb2.button("🧹", on_click=lambda: st.rerun())
            
        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            data = st.date_input("Data", datetime.now().date())
            ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
            contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
            direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        with f2:
            lote_t = st.number_input("Contratos", min_value=0, value=int(config["lote"]), key=f"lote_{atm_sel}")
            stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]), key=f"stop_{atm_sel}")
            up_files = st.file_uploader("📸 Prints", accept_multiple_files=True)
        with f3:
            st.write("**Saídas**")
            saidas = []; alocado = 0
            for i, p_c in enumerate(config["parciais"]):
                s_c1, s_c2 = st.columns(2)
                p = s_c1.number_input(f"Pts P{i+1}", value=float(p_c[0]), key=f"p_{atm_sel}_{i}")
                q = s_c2.number_input(f"Qtd P{i+1}", value=int(p_c[1]), key=f"q_{atm_sel}_{i}")
                saidas.append((p, q)); alocado += q
            for i in range(st.session_state.n_extras):
                s_c1, s_c2 = st.columns(2)
                p = s_c1.number_input(f"Pts Ex {i+1}", key=f"pe_{i}"); q = s_c2.number_input(f"Qtd Ex {i+1}", key=f"qe_{i}")
                saidas.append((p, q)); alocado += q
            if lote_t > 0 and lote_t != alocado: st.markdown(f'<div class="piscante-erro">FALTAM {lote_t-alocado} CONTRATOS</div>', unsafe_allow_html=True)
        
        r_b1, r_b2 = st.columns(2)
        with r_b1:
            if st.button("💾 REGISTRAR GAIN", use_container_width=True):
                if lote_t > 0 and alocado == lote_t:
                    res = sum([s[0]*MULTIPLIERS[ativo]*s[1] for s in saidas]); pts_m = sum([s[0]*s[1] for s in saidas]) / lote_t
                    n_id = str(uuid.uuid4()); paths = []
                    for i, f in enumerate(up_files):
                        p = os.path.join(IMG_DIR, f"{n_id}_{i}.png"); paths.append(p)
                        with open(p, "wb") as bf: bf.write(f.getbuffer())
                    n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': (stop_p*MULTIPLIERS[ativo]*lote_t), 'ID': n_id, 'Prints': "|".join(paths), 'Notas': ""}])
                    df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False); st.success("🎯 Salvo!"); time.sleep(1); st.rerun()
        with r_b2:
            if st.button("🚨 REGISTRAR STOP", type="secondary", use_container_width=True):
                if lote_t > 0 and stop_p > 0:
                    pre = -(stop_p * MULTIPLIERS[ativo] * lote_t); n_id = str(uuid.uuid4()); paths = []
                    for i, f in enumerate(up_files):
                        p = os.path.join(IMG_DIR, f"{n_id}_{i}.png"); paths.append(p)
                        with open(p, "wb") as bf: bf.write(f.getbuffer())
                    n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': pre, 'Pts_Medio': -stop_p, 'Risco_Fin': abs(pre), 'ID': n_id, 'Prints': "|".join(paths), 'Notas': ""}])
                    df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False); st.error("🚨 Stop!"); time.sleep(1); st.rerun()

    # --- CONFIGURAR ATM ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Editor")
        with st.expander("✨ Criar Novo Template", expanded=True):
            n = st.text_input("Nome")
            ca1, ca2 = st.columns(2)
            l_p = ca1.number_input("Lote Total", min_value=1)
            s_p = ca2.number_input("Stop (Pts)", min_value=0.0)
            n_p = st.number_input("Alvos", 1, 6, 1)
            novas_p = []
            for i in range(n_p):
                cp1, cp2 = st.columns(2)
                novas_p.append([cp1.number_input(f"Pts {i+1}", key=f"ap_{i}"), cp2.number_input(f"Qtd {i+1}", key=f"aq_{i}", min_value=1)])
            if st.button("💾 Salvar ATM"):
                atm_db[n] = {"lote": l_p, "stop": s_p, "parciais": novas_p}; save_atm(atm_db); st.rerun()
        st.markdown("---")
        for nome, cfg in list(atm_db.items()):
            if nome != "Personalizado":
                c_n, c_d = st.columns([4, 1])
                c_n.write(f"**{nome}** (Lote: {cfg['lote']})")
                if c_d.button("Excluir", key=f"del_{nome}"): del atm_db[nome]; save_atm(atm_db); st.rerun()

    # --- HISTÓRICO ---
    elif selected == "Histórico":
        st.title("📜 Galeria")
        if 'to_delete' in st.session_state:
            df = df[df['ID'] != st.session_state.to_delete]
            df.to_csv(CSV_FILE, index=False); del st.session_state.to_delete; st.rerun()
        if not df.empty:
            df_disp = df.iloc[::-1].copy(); df_disp['Num'] = range(len(df_disp), 0, -1)
            
            # Galeria Responsiva usando colunas
            # No mobile, o Streamlit automaticamente empilha colunas.
            for i in range(0, len(df_disp), 5):
                cols = st.columns(5)
                for j in range(5):
                    if i + j < len(df_disp):
                        row = df_disp.iloc[i + j]
                        with cols[j]:
                            p_list = str(row['Prints']).split("|") if row['Prints'] else []
                            img_html = f'<div class="img-container"><img src="data:image/png;base64,{get_base64(p_list[0])}"></div>' if p_list and os.path.exists(p_list[0]) else '<div class="img-container" style="color:#444">Sem Print</div>'
                            color = "#00FF88" if row['Resultado'] > 0 else "#FF4B4B"
                            st.markdown(f'<div class="trade-card">{img_html}<div class="card-footer"><div><b style="color:white">Trade #{row["Num"]}</b><br><small style="color:#888">{row["Contexto"]}</small></div><div style="color:{color}; font-weight:bold;">${row["Resultado"]:,.2f}</div>', unsafe_allow_html=True)
                            if st.button("Ver", key=f"v_{row['ID']}_{i+j}"): expand_modal(row['ID'])
                            st.markdown('</div></div>', unsafe_allow_html=True)
