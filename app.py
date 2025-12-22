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

# --- PERSISTÊNCIA DE USUÁRIOS ---
USER_FILE = 'users.json'

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as f:
            return json.load(f)
    return {"admin": "1234"}

def save_users(users):
    with open(USER_FILE, 'w') as f:
        json.dump(users, f)

# --- SISTEMA DE LOGIN SEGURO ---
def check_password():
    users = load_users()
    def password_entered():
        u = st.session_state.get("username")
        p = st.session_state.get("password")
        if u in users and users[u] == p:
            st.session_state["password_correct"] = True
            st.session_state["logged_user"] = u
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("""
            <style>
            .login-container {
                max-width: 400px; margin: 50px auto; padding: 30px;
                background-color: #161616; border-radius: 15px;
                border: 1px solid #B20000; text-align: center;
            }
            .logo-main { color: #B20000; font-size: 50px; font-weight: 900; }
            .logo-sub { color: white; font-size: 35px; font-weight: 700; margin-top: -15px; }
            @media (max-width: 768px) { .login-container { width: 90%; } }
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

if check_password():
    # --- DIRETÓRIOS ---
    IMG_DIR = "trade_prints"
    if not os.path.exists(IMG_DIR): os.makedirs(IMG_DIR)

    CSV_FILE = 'evotrade_data.csv'
    ATM_FILE = 'atm_configs.json'
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}

    # --- ESTILO CSS PREMIUM & RESPONSIVO ---
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #0F0F0F !important; border-right: 1px solid #1E1E1E; }
        .stApp { background-color: #0F0F0F; }
        
        .sidebar-logo-box { padding: 10px 0px 30px 5px; display: flex; align-items: center; gap: 12px; }
        .evo-icon { background-color: #B20000; color: white; padding: 5px 12px; border-radius: 8px; font-weight: 900; font-size: 24px; }
        .evo-text-group { display: flex; flex-direction: column; }
        .evo-text-red { color: #B20000; font-size: 22px; font-weight: 900; line-height: 1; }
        .evo-text-white { color: white; font-size: 19px; font-weight: 700; line-height: 1; }

        .metric-container {
            background-color: #161616; border: 1px solid #262626; padding: 20px;
            border-radius: 10px; text-align: center; margin-bottom: 10px;
        }
        .metric-label { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
        .metric-value { color: white; font-size: 22px; font-weight: bold; }
        
        @media (max-width: 768px) {
            [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
            .metric-value { font-size: 18px; }
        }

        @keyframes blinking { 0% { background-color: #440000; } 50% { background-color: #B20000; } 100% { background-color: #440000; } }
        .piscante-erro { padding: 15px; border-radius: 5px; color: white; font-weight: bold; text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000; }
        
        .stButton > button { width: 100%; border-radius: 8px; font-weight: 600; }
        .trade-card { background-color: #161616; border: 1px solid #333; border-radius: 12px; margin-bottom: 20px; overflow: hidden; display: flex; flex-direction: column; min-height: 350px; }
        .img-container { width: 100%; height: 180px; background-color: #000; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid #333; }
        .img-container img { width: 100% !important; height: 100% !important; object-fit: cover !important; }
        .card-footer { padding: 15px; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

    # --- FUNÇÕES DE DADOS ---
    def load_atm():
        if os.path.exists(ATM_FILE):
            try:
                with open(ATM_FILE, 'r') as f: return json.load(f)
            except: pass
        return {"Personalizado": {"lote": 1, "stop": 0.0, "parciais": []}}

    def load_data():
        cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID', 'Prints', 'Notas', 'Usuario']
        if os.path.exists(CSV_FILE):
            try:
                df = pd.read_csv(CSV_FILE)
                for col in cols:
                    if col not in df.columns: df[col] = "admin" if col == 'Usuario' else ""
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

    # --- DIALOG DETALHES ---
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
                current_df.to_csv(CSV_FILE, index=False)
                st.success("Salvo!")
                time.sleep(1); st.rerun()
        with c2:
            st.markdown(f"### Trade Info")
            st.write(f"📅 **Data:** {row['Data']} | 👤 **User:** {row['Usuario']}")
            dir_color = "cyan" if row['Direcao'] == "Compra" else "orange"
            st.markdown(f"↕️ **Direção:** :{dir_color}[{row['Direcao']}]")
            st.divider()
            res_c = "#00FF88" if row['Resultado'] > 0 else "#FF4B4B"
            st.markdown(f"💰 **P&L:** <span style='color:{res_c}; font-weight:bold; font-size:20px'>${row['Resultado']:,.2f}</span>", unsafe_allow_html=True)
            st.write(f"📊 **Média Pts:** {row['Pts_Medio']:.2f}")
            if st.button("🗑️ Deletar Trade", type="primary"):
                st.session_state.to_delete = trade_id; st.rerun()

    # --- SIDEBAR NAV ---
    with st.sidebar:
        st.markdown("""
            <div class="sidebar-logo-box">
                <div class="evo-icon">E</div>
                <div class="evo-text-group">
                    <div class="evo-text-red">EVO</div>
                    <div class="evo-text-white">TRADE</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        pages = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        icons = ["grid-1x2", "currency-dollar", "gear", "clock-history"]
        if st.session_state["logged_user"] == "admin":
            pages.append("Gerenciar Usuários"); icons.append("people")

        selected = option_menu(None, pages, icons=icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        st.write("---")
        if st.button("Sair / Logout"):
            del st.session_state["password_correct"]; st.rerun()

    # --- ABA: GERENCIAR USUÁRIOS ---
    if selected == "Gerenciar Usuários":
        st.title("👥 Cadastro de Usuários")
        users = load_users()
        with st.expander("Cadastrar Novo Usuário", expanded=True):
            nu = st.text_input("Username")
            np = st.text_input("Password", type="password")
            if st.button("Criar Acesso"):
                if nu and np:
                    users[nu] = np; save_users(users)
                    st.success("Cadastrado!"); time.sleep(1); st.rerun()
        
        st.markdown("### Usuários Ativos")
        for u in list(users.keys()):
            c_u, c_d = st.columns([4, 1])
            c_u.write(f"👤 {u}")
            if u != "admin":
                if c_d.button("Remover", key=f"del_{u}"):
                    del users[u]; save_users(users); st.rerun()

    # --- ABA: DASHBOARD ---
    elif selected == "Dashboard":
        st.title("📊 Analytics")
        df_view = df if st.session_state["logged_user"] == "admin" else df[df['Usuario'] == st.session_state["logged_user"]]
        
        if not df_view.empty:
            f_v = st.segmented_control("Visão:", ["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
            df_f = df_view.copy() if f_v == "Capital" else df_view[df_view['Contexto'] == f_v].copy()
            
            if not df_f.empty:
                total = len(df_f); wins = df_f[df_f['Resultado'] > 0]; losses = df_f[df_f['Resultado'] < 0]
                wr = (len(wins)/total*100) if total > 0 else 0
                aw = wins['Resultado'].mean() if not wins.empty else 0
                al = abs(losses['Resultado'].mean()) if not losses.empty else 0
                rr = (aw/al) if al > 0 else 0; total_pl = df_f['Resultado'].sum()
                avg_pts_gain = wins['Pts_Medio'].mean() if not wins.empty else 0
                avg_pts_loss = abs(losses['Pts_Medio'].mean()) if not losses.empty else 0
                avg_lote = df_f['Lote'].mean()

                r1, r2, r3 = st.columns(3)
                with r1: 
                    st.markdown(f'<div class="metric-container"><div class="metric-label">P&L TOTAL</div><div class="metric-value" style="color:{"#00FF88" if total_pl>0 else "#FF4B4B"}">${total_pl:,.2f}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-container"><div class="metric-label">RISCO:RETORNO</div><div class="metric-value">1:{rr:.2f}</div></div>', unsafe_allow_html=True)
                with r2: 
                    st.markdown(f'<div class="metric-container"><div class="metric-label">WIN RATE</div><div class="metric-value" style="color:#B20000">{wr:.1f}%</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-container"><div class="metric-label">LOTE MÉDIO</div><div class="metric-value">{avg_lote:.1f}</div></div>', unsafe_allow_html=True)
                with r3: 
                    st.markdown(f'<div class="metric-container"><div class="metric-label">TRADES TOTAL</div><div class="metric-value">{total}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-container"><div class="metric-label">GAIN MÉDIO</div><div class="metric-value" style="color:#00FF88">${aw:,.2f}</div></div>', unsafe_allow_html=True)
                
                df_g = df_f.sort_values('Data').reset_index(drop=True)
                df_g['Acumulado'] = df_g['Resultado'].cumsum()
                fig = px.area(df_g, x=range(len(df_g)), y='Acumulado', template="plotly_dark", markers=True)
                fig.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)', line_shape='spline')
                st.plotly_chart(fig, use_container_width=True)

    # --- ABA: REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Registro de Trade")
        if 'n_extras' not in st.session_state: st.session_state.n_extras = 0
        if 'last_atm' not in st.session_state: st.session_state.last_atm = None
        
        c1, c2 = st.columns([3, 1])
        with c1:
            atm_sel = st.selectbox("🎯 ATM", list(atm_db.keys())); config = atm_db[atm_sel]
            if st.session_state.last_atm != atm_sel:
                st.session_state.n_extras = 0; st.session_state.last_atm = atm_sel; st.rerun()
        with c2:
            st.write(""); cb1, cb2 = st.columns(2)
            cb1.button("➕", on_click=lambda: st.session_state.update({"n_extras": st.session_state.n_extras + 1}))
            cb2.button("🧹", on_click=lambda: st.rerun())

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            data = st.date_input("Data", datetime.now().date()); ativo = st.selectbox("Ativo", ["MNQ", "NQ"]); contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"]); direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        with f2:
            lote_t = st.number_input("Contratos", min_value=0, value=int(config["lote"]))
            stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]))
            up_files = st.file_uploader("📸 Prints", accept_multiple_files=True)
        with f3:
            st.write("**Saídas**"); saidas = []; alocado = 0
            for i, p_c in enumerate(config["parciais"]):
                sc1, sc2 = st.columns(2)
                p = sc1.number_input(f"Pts P{i+1}", value=float(p_c[0]), key=f"p_{i}"); q = sc2.number_input(f"Qtd P{i+1}", value=int(p_c[1]), key=f"q_{i}")
                saidas.append((p, q)); alocado += q
            for i in range(st.session_state.n_extras):
                sc1, sc2 = st.columns(2)
                p = sc1.number_input(f"Pts Ex {i+1}", key=f"pe_{i}"); q = sc2.number_input(f"Qtd Ex {i+1}", key=f"qe_{i}")
                saidas.append((p, q)); alocado += q
            if lote_t > 0 and lote_t != alocado: st.markdown(f'<div class="piscante-erro">FALTAM {lote_t-alocado} CONTRATOS</div>', unsafe_allow_html=True)
            elif lote_t == alocado and lote_t > 0: st.success("✅ Posição Completa")

        rb1, rb2 = st.columns(2)
        with rb1:
            if st.button("💾 REGISTRAR GAIN", use_container_width=True):
                if lote_t > 0 and alocado == lote_t:
                    res = sum([s[0]*MULTIPLIERS[ativo]*s[1] for s in saidas]); pts_m = sum([s[0]*s[1] for s in saidas]) / lote_t
                    n_id = str(uuid.uuid4()); paths = []
                    for i, f in enumerate(up_files):
                        p_path = os.path.join(IMG_DIR, f"{n_id}_{i}.png"); paths.append(p_path)
                        with open(p_path, "wb") as bf: bf.write(f.getbuffer())
                    n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': (stop_p*MULTIPLIERS[ativo]*lote_t), 'ID': n_id, 'Prints': "|".join(paths), 'Notas': "", 'Usuario': st.session_state["logged_user"]}])
                    df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False); st.success("🎯 Salvo!"); st.rerun()
        with rb2:
            if st.button("🚨 REGISTRAR STOP FULL", type="secondary", use_container_width=True):
                if lote_t > 0 and stop_p > 0:
                    res_s = -(stop_p * MULTIPLIERS[ativo] * lote_t); n_id = str(uuid.uuid4()); paths = []
                    for i, f in enumerate(up_files):
                        p_path = os.path.join(IMG_DIR, f"{n_id}_{i}.png"); paths.append(p_path)
                        with open(p_path, "wb") as bf: bf.write(f.getbuffer())
                    n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res_s, 'Pts_Medio': -stop_p, 'Risco_Fin': abs(res_s), 'ID': n_id, 'Prints': "|".join(paths), 'Notas': "", 'Usuario': st.session_state["logged_user"]}])
                    df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False); st.error("🚨 Stop!"); st.rerun()

    # --- ABA: CONFIGURAR ATM ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Editor de ATM")
        with st.expander("✨ Criar Novo Template", expanded=True):
            n = st.text_input("Nome da Estratégia"); ca1, ca2 = st.columns(2); l_p = ca1.number_input("Lote Total", min_value=1); s_p = ca2.number_input("Stop (Pts)", min_value=0.0); n_p = st.number_input("Alvos", 1, 6, 1); novas_p = []
            for i in range(n_p):
                cp1, cp2 = st.columns(2); novas_p.append([cp1.number_input(f"Pts {i+1}", key=f"ap_{i}"), cp2.number_input(f"Qtd {i+1}", key=f"aq_{i}", min_value=1)])
            if st.button("💾 Salvar ATM"):
                atm_db[n] = {"lote": l_p, "stop": s_p, "parciais": novas_p}
                with open(ATM_FILE, 'w') as f:
                    json.dump(atm_db, f)
                st.rerun()
        for nome, cfg in list(atm_db.items()):
            if nome != "Personalizado":
                c_n, c_d = st.columns([4, 1]); c_n.write(f"**{nome}** (Lote: {cfg['lote']})")
                if c_d.button("Excluir", key=f"del_{nome}"):
                    del atm_db[nome]
                    with open(ATM_FILE, 'w') as f:
                        json.dump(atm_db, f)
                    st.rerun()

    # --- ABA: HISTÓRICO ---
    elif selected == "Histórico":
        st.title("📜 Galeria")
        if 'to_delete' in st.session_state:
            df = df[df['ID'] != st.session_state.to_delete]; df.to_csv(CSV_FILE, index=False); del st.session_state.to_delete; st.rerun()
        
        # Filtros Superiores
        cf1, cf2 = st.columns(2)
        with cf1:
            u_options = ["Todos"] + list(df['Usuario'].unique()) if st.session_state["logged_user"] == "admin" else [st.session_state["logged_user"]]
            f_user = st.selectbox("Operador:", u_options)
        with cf2:
            f_ctx = st.selectbox("Contexto:", ["Todos", "Contexto A", "Contexto B", "Contexto C"])
        
        df_h = df.copy()
        if f_user != "Todos": df_h = df_h[df_h['Usuario'] == f_user]
        if f_ctx != "Todos": df_h = df_h[df_h['Contexto'] == f_ctx]
        
        if not df_h.empty:
            df_disp = df_h.iloc[::-1].copy(); df_disp['Num'] = range(len(df_disp), 0, -1)
            for i in range(0, len(df_disp), 5):
                cols = st.columns(5)
                for j in range(5):
                    if i + j < len(df_disp):
                        row = df_disp.iloc[i + j]; ps = str(row['Prints']).split("|") if row['Prints'] else []
                        with cols[j]:
                            img_html = f'<div class="img-container"><img src="data:image/png;base64,{get_base64(ps[0])}"></div>' if ps and os.path.exists(ps[0]) else '<div class="img-container" style="color:#444">Sem Print</div>'
                            st.markdown(f'<div class="trade-card">{img_html}<div class="card-footer"><div><b style="color:white">{row["Usuario"]}</b><br><small style="color:#888">{row["Contexto"]}</small></div><div style="color:{"#00FF88" if row["Resultado"] > 0 else "#FF4B4B"}; font-weight:bold;">${row["Resultado"]:,.2f}</div>', unsafe_allow_html=True)
                            if st.button("Ver", key=f"v_{row['ID']}"): expand_modal(row['ID'])
                            st.markdown('</div></div>', unsafe_allow_html=True)
