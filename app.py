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
        with open(USER_FILE, 'r') as f: return json.load(f)
    return {"admin": "1234"}

def save_users(users):
    with open(USER_FILE, 'w') as f: json.dump(users, f)

# --- SISTEMA DE LOGIN SEGURO ---
def check_password():
    users = load_users()
    def password_entered():
        u = st.session_state["username"]
        p = st.session_state["password"]
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

# --- INÍCIO DO APP ---
if check_password():
    IMG_DIR = "trade_prints"
    if not os.path.exists(IMG_DIR): os.makedirs(IMG_DIR)

    CSV_FILE = 'evotrade_data.csv'
    ATM_FILE = 'atm_configs.json'
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}

    # --- ESTILO CSS GERAL PREMIUM & RESPONSIVO ---
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #0F0F0F !important; border-right: 1px solid #1E1E1E; }
        .stApp { background-color: #0F0F0F; }
        
        /* Sidebar Logo Branding */
        .sidebar-logo-box { padding: 10px 0px 30px 5px; display: flex; align-items: center; gap: 12px; }
        .evo-icon { background-color: #B20000; color: white; padding: 5px 12px; border-radius: 8px; font-weight: 900; font-size: 22px; }
        .evo-text-group { display: flex; flex-direction: column; }
        .evo-text-red { color: #B20000; font-size: 20px; font-weight: 900; line-height: 1; }
        .evo-text-white { color: white; font-size: 18px; font-weight: 700; line-height: 1; }

        /* Metric Cards */
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

        .trade-card {
            background-color: #161616; border: 1px solid #333; border-radius: 12px;
            margin-bottom: 20px; overflow: hidden; display: flex; flex-direction: column; height: auto; min-height: 360px;
        }
        .img-container { width: 100%; height: 170px; background-color: #000; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid #333; }
        .img-container img { width: 100% !important; height: 100% !important; object-fit: cover !important; }
        .card-footer { padding: 12px; text-align: center; }
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
            pages.append("Gerenciar Usuários")
            icons.append("people")

        selected = option_menu(None, pages, icons=icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        st.write("---")
        if st.button("Sair / Logout"):
            del st.session_state["password_correct"]; st.rerun()

    # --- LOGICA: GERENCIAR USUÁRIOS ---
    if selected == "Gerenciar Usuários":
        st.title("👥 Cadastro de Usuários")
        users = load_users()
        with st.expander("Novo Usuário", expanded=True):
            nu = st.text_input("Username")
            np = st.text_input("Password", type="password")
            if st.button("Salvar Acesso"):
                if nu and np:
                    users[nu] = np; save_users(users)
                    st.success("Cadastrado!"); time.sleep(1); st.rerun()
        
        st.markdown("### Usuários Ativos")
        for u in list(users.keys()):
            c_u, c_d = st.columns([4, 1])
            c_u.write(f"👤 {u}")
            if u != "admin" and c_d.button("Remover", key=f"del_{u}"):
                del users[u]; save_users(users); st.rerun()

    # --- LOGICA: DASHBOARD ---
    elif selected == "Dashboard":
        st.title("📊 Analytics")
        # Admin vê tudo, usuário comum vê só o dele
        df_view = df if st.session_state["logged_user"] == "admin" else df[df['Usuario'] == st.session_state["logged_user"]]
        
        if not df_view.empty:
            f_v = st.segmented_control("Contexto:", ["Todos", "Contexto A", "Contexto B", "Contexto C"], default="Todos")
            df_f = df_view if f_v == "Todos" else df_view[df_view['Contexto'] == f_v]
            
            if not df_f.empty:
                res = df_f['Resultado'].sum()
                wr = (len(df_f[df_f['Resultado']>0])/len(df_f)*100)
                
                c1, c2, c3 = st.columns(3)
                with c1: st.markdown(f'<div class="metric-container"><div class="metric-label">P&L TOTAL</div><div class="metric-value" style="color:{"#00FF88" if res>0 else "#FF4B4B"}">${res:,.2f}</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="metric-container"><div class="metric-label">WIN RATE</div><div class="metric-value">{wr:.1f}%</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="metric-container"><div class="metric-label">TRADES</div><div class="metric-value">{len(df_f)}</div></div>', unsafe_allow_html=True)
                
                df_f = df_f.sort_values('Data')
                df_f['Acumulado'] = df_f['Resultado'].cumsum()
                fig = px.area(df_f, x=range(len(df_f)), y='Acumulado', template="plotly_dark")
                fig.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                st.plotly_chart(fig, use_container_width=True)

    # --- LOGICA: REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Novo Registro")
        atm_sel = st.selectbox("🎯 ATM", list(atm_db.keys()))
        config = atm_db[atm_sel]
        
        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            data = st.date_input("Data", datetime.now().date())
            ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
            contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
            direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        with f2:
            lote_t = st.number_input("Lote", min_value=1, value=int(config["lote"]))
            stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]))
            up_files = st.file_uploader("📸 Prints", accept_multiple_files=True)
        with f3:
            st.write("**Saídas**"); saidas = []; alocado = 0
            for i, p_c in enumerate(config["parciais"]):
                sc1, sc2 = st.columns(2)
                p = sc1.number_input(f"Pts P{i+1}", value=float(p_c[0]), key=f"p_{i}")
                q = sc2.number_input(f"Qtd P{i+1}", value=int(p_c[1]), key=f"q_{i}")
                saidas.append((p, q)); alocado += q
            if lote_t != alocado: st.warning(f"Lote incompleto: {alocado}/{lote_t}")

        if st.button("💾 SALVAR OPERAÇÃO", use_container_width=True):
            res = sum([s[0]*MULTIPLIERS[ativo]*s[1] for s in saidas])
            n_id = str(uuid.uuid4()); paths = []
            for i, f in enumerate(up_files):
                p = os.path.join(IMG_DIR, f"{n_id}_{i}.png"); paths.append(p)
                with open(p, "wb") as bf: bf.write(f.getbuffer())
            
            n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': (res/(lote_t*MULTIPLIERS[ativo])), 'Risco_Fin': (stop_p*MULTIPLIERS[ativo]*lote_t), 'ID': n_id, 'Prints': "|".join(paths), 'Notas': "", 'Usuario': st.session_state["logged_user"]}])
            df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
            st.success("Registrado!"); time.sleep(1); st.rerun()

    # --- LOGICA: CONFIGURAR ATM ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Editor de ATM")
        with st.expander("Novo Template"):
            n = st.text_input("Nome")
            ca1, ca2 = st.columns(2)
            l_p = ca1.number_input("Lote Total", min_value=1)
            s_p = ca2.number_input("Stop", min_value=0.0)
            n_p = st.number_input("Alvos", 1, 6, 1); novas_p = []
            for i in range(n_p):
                cp1, cp2 = st.columns(2)
                novas_p.append([cp1.number_input(f"Pts {i+1}", key=f"ap_{i}"), cp2.number_input(f"Qtd {i+1}", key=f"aq_{i}", min_value=1)])
            if st.button("Salvar ATM"):
                atm_db[n] = {"lote": l_p, "stop": s_p, "parciais": novas_p}
                with open(ATM_FILE, 'w') as f: json.dump(atm_db, f)
                st.rerun()

    # --- LOGICA: HISTÓRICO (FILTROS POR USER E CONTEXTO) ---
    elif selected == "Histórico":
        st.title("📜 Galeria")
        
        # Filtros Superiores
        cf1, cf2 = st.columns(2)
        with cf1:
            users_list = ["Todos"] + list(df['Usuario'].unique()) if st.session_state["logged_user"] == "admin" else [st.session_state["logged_user"]]
            f_user = st.selectbox("Operador:", users_list)
        with cf2:
            f_ctx = st.selectbox("Contexto:", ["Todos", "Contexto A", "Contexto B", "Contexto C"])
        
        # Aplicar Filtros
        df_h = df.copy()
        if f_user != "Todos": df_h = df_h[df_h['Usuario'] == f_user]
        if f_ctx != "Todos": df_h = df_h[df_h['Contexto'] == f_ctx]
        
        if not df_h.empty:
            df_disp = df_h.iloc[::-1]
            for i in range(0, len(df_disp), 5):
                cols = st.columns(5)
                for j in range(5):
                    if i + j < len(df_disp):
                        row = df_disp.iloc[i + j]
                        with cols[j]:
                            ps = str(row['Prints']).split("|") if row['Prints'] else []
                            img = f'<div class="img-container"><img src="data:image/png;base64,{get_base64(ps[0])}"></div>' if ps and os.path.exists(ps[0]) else '<div class="img-container">Sem Print</div>'
                            res_color = "#00FF88" if row['Resultado'] > 0 else "#FF4B4B"
                            st.markdown(f'<div class="trade-card">{img}<div class="card-footer"><b style="color:white">{row["Usuario"]}</b><br><small>{row["Contexto"]}</small><div style="color:{res_color}; font-weight:bold;">${row["Resultado"]:,.2f}</div>', unsafe_allow_html=True)
                            if st.button("Ver", key=f"btn_{row['ID']}"): 
                                st.info(f"Notas: {row['Notas']}") # Modal simplificado para o exemplo
                            st.markdown('</div></div>', unsafe_allow_html=True)
