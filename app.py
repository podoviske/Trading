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
import numpy as np

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

    # --- ESTILO CSS PREMIUM ---
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #0F0F0F !important; border-right: 1px solid #1E1E1E; }
        .stApp { background-color: #0F0F0F; }
        .sidebar-brand-container { display: flex; align-items: center; gap: 12px; padding: 10px 5px 25px 5px; }
        .evo-logo-box { background-color: #B20000; color: white; padding: 5px 12px; border-radius: 8px; font-weight: 900; font-size: 24px; }
        .evo-text-red { color: #B20000; font-size: 22px; font-weight: 900; line-height: 1; }
        .evo-text-white { color: white; font-size: 19px; font-weight: 700; line-height: 1; }
        
        .metric-container { 
            background-color: #161616; border: 1px solid #262626; padding: 15px; 
            border-radius: 10px; text-align: center; margin-bottom: 12px; min-height: 100px;
        }
        .metric-label { color: #888; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; display: flex; justify-content: center; align-items: center; gap: 5px; }
        .metric-value { color: white; font-size: 20px; font-weight: bold; margin-top: 5px; }
        .help-icon { color: #B20000; font-size: 12px; cursor: help; font-weight: bold; border: 1px solid #B20000; border-radius: 50%; width: 16px; height: 16px; display: inline-flex; align-items: center; justify-content: center; }
        
        .trade-card { background-color: #161616; border: 1px solid #333; border-radius: 12px; margin-bottom: 20px; overflow: hidden; display: flex; flex-direction: column; min-height: 350px; }
        .img-container { width: 100%; height: 160px; background-color: #000; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid #333; }
        .img-container img { width: 100% !important; height: 100% !important; object-fit: cover !important; }
        .piscante-erro { padding: 15px; border-radius: 5px; color: white; font-weight: bold; text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000; }
        @keyframes blinking { 0% { background-color: #440000; } 50% { background-color: #B20000; } 100% { background-color: #440000; } }
        </style>
    """, unsafe_allow_html=True)

    # --- FUNÇÕES DE DADOS ---
    def load_data():
        cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID', 'Prints', 'Notas', 'Usuario']
        if os.path.exists(CSV_FILE):
            try:
                df = pd.read_csv(CSV_FILE)
                for c in cols:
                    if c not in df.columns: df[c] = "admin" if c == 'Usuario' else ""
                df['Data'] = pd.to_datetime(df['Data']).dt.date
                return df
            except: return pd.DataFrame(columns=cols)
        return pd.DataFrame(columns=cols)

    def card_metric(label, value, help_text, color="white"):
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">
                    {label} <div class="help-icon" title="{help_text}">?</div>
                </div>
                <div class="metric-value" style="color: {color};">{value}</div>
            </div>
        """, unsafe_allow_html=True)

    def get_base64(path):
        try:
            with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
        except: return None

    # --- CÁLCULOS ESTATÍSTICOS ---
    def calculate_advanced_stats(results):
        if not results: return 0, 0, 0
        max_win = max_loss = cur_w = cur_l = peak = cur_acc = mdd = 0
        for r in results:
            if r > 0:
                cur_w += 1; cur_l = 0; max_win = max(max_win, cur_w)
            elif r < 0:
                cur_l += 1; cur_w = 0; max_loss = max(max_loss, cur_l)
            cur_acc += r
            peak = max(peak, cur_acc)
            mdd = max(mdd, peak - cur_acc)
        return max_win, max_loss, mdd

    # --- MODAL ---
    @st.dialog("Detalhes do Trade", width="large")
    def expand_modal(trade_id):
        curr_df = load_data()
        row = curr_df[curr_df['ID'] == trade_id].iloc[0]
        c1, c2 = st.columns([1.5, 1])
        with c1:
            ps = [p.strip() for p in str(row['Prints']).split("|") if p.strip() and os.path.exists(p.strip())]
            if ps:
                tabs = st.tabs([f"Print {i+1}" for i in range(len(ps))])
                for i, tab in enumerate(tabs):
                    with tab: st.image(ps[i], use_container_width=True)
            st.markdown("---")
            notas = st.text_area("Notas:", value=str(row['Notas']) if pd.notna(row['Notas']) else "", height=150)
            if st.button("💾 Salvar Notas"):
                curr_df.loc[curr_df['ID'] == trade_id, 'Notas'] = notas
                curr_df.to_csv(CSV_FILE, index=False); st.success("Salvo!"); time.sleep(1); st.rerun()
        with c2:
            st.markdown("### Info")
            st.write(f"📅 **Data:** {row['Data']} | 👤 **User:** {row['Usuario']}")
            dir_c = "cyan" if row['Direcao'] == "Compra" else "orange"
            st.markdown(f"↕️ **Direção:** :{dir_c}[{row['Direcao']}]")
            st.divider()
            res_c = "#00FF88" if row['Resultado'] > 0 else "#FF4B4B"
            st.markdown(f"💰 **P&L:** <span style='color:{res_c}; font-weight:bold; font-size:20px'>${row['Resultado']:,.2f}</span>", unsafe_allow_html=True)
            if st.button("🗑️ Deletar Trade", type="primary"):
                st.session_state.to_delete = trade_id; st.rerun()

    # --- INICIALIZAÇÃO ---
    atm_db = json.load(open(ATM_FILE, 'r')) if os.path.exists(ATM_FILE) else {"Personalizado": {"lote": 1, "stop": 0.0, "parciais": []}}
    df = load_data()

    with st.sidebar:
        st.markdown('<div class="sidebar-brand-container"><div class="evo-logo-box">E</div><div class="evo-text-group"><div class="evo-text-red">EVO</div><div class="evo-text-white">TRADE</div></div></div>', unsafe_allow_html=True)
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        icons = ["grid-1x2", "currency-dollar", "gear", "clock-history"]
        if st.session_state["logged_user"] == "admin": menu.append("Gerenciar Usuários"); icons.append("people")
        selected = option_menu(None, menu, icons=icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair / Logout"): del st.session_state["password_correct"]; st.rerun()

    # --- ABA: DASHBOARD (PRIVACIDADE + 9 MÉTRICAS) ---
    if selected == "Dashboard":
        st.title("📊 Analytics Pessoal")
        df_u = df[df['Usuario'] == st.session_state["logged_user"]]
        
        if not df_u.empty:
            vis = st.segmented_control("Contexto:", ["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
            df_f = df_u if vis == "Capital" else df_u[df_u['Contexto'] == vis]
            
            if not df_f.empty:
                total = len(df_f); wins = df_f[df_f['Resultado'] > 0]; losses = df_f[df_f['Resultado'] < 0]
                wr = (len(wins)/total*100) if total > 0 else 0
                aw = wins['Resultado'].mean() if not wins.empty else 0
                al = abs(losses['Resultado'].mean()) if not losses.empty else 0
                rr = (aw/al) if al > 0 else 0; t_pl = df_f['Resultado'].sum()
                
                # Cálculos Profissionais
                pf = wins['Resultado'].sum() / abs(losses['Resultado'].sum()) if not losses.empty else wins['Resultado'].sum()
                exp = (wr/100 * aw) - ((1 - wr/100) * al)
                m_win, m_loss, mdd = calculate_advanced_stats(df_f['Resultado'].tolist())

                # Grid de Métricas 3x3
                c1, c2, c3 = st.columns(3)
                with c1: 
                    card_metric("P&L TOTAL", f"${t_pl:,.2f}", "Saldo líquido acumulado.", "#00FF88" if t_pl > 0 else "#FF4B4B")
                    card_metric("PROFIT FACTOR", f"{pf:.2f}", "Sustentabilidade: Ganho bruto vs Perda bruta.")
                    card_metric("EXPECTATIVA", f"${exp:,.2f}", "Média esperada de ganho por trade no longo prazo.")
                with c2: 
                    card_metric("WIN RATE", f"{wr:.1f}%", "Aproveitamento de operações vitoriosas.", "#B20000")
                    card_metric("RISCO:RETORNO", f"1:{rr:.2f}", "Proporção entre Gain Médio e Loss Médio.")
                    card_metric("MAX DRAWDOWN", f"${mdd:,.2f}", "Maior queda da conta a partir de um topo anterior.", "#FF4B4B")
                with c3: 
                    card_metric("TRADES TOTAL", str(total), "Número total de registros.")
                    card_metric("MAX SEQ GAIN", f"{m_win} Trades", "Sua maior sequência de vitórias consecutivas.", "#00FF88")
                    card_metric("MAX SEQ LOSS", f"{m_loss} Trades", "Sua maior sequência de stops consecutivos.", "#FF4B4B")
                
                st.markdown("---")
                df_g = df_f.sort_values('Data').reset_index(drop=True)
                df_g['Acumulado'] = df_g['Resultado'].cumsum()
                fig = px.area(df_g, x=df_g.index + 1, y='Acumulado', template="plotly_dark", markers=True)
                fig.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)', line_shape='spline')
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("Sem dados para este contexto.")
        else: st.info("Você ainda não possui trades.")

    # --- ABA: REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Registro de Trade")
        if 'n_ex' not in st.session_state: st.session_state.n_ex = 0
        if 'last_atm' not in st.session_state: st.session_state.last_atm = None
        col1, col2 = st.columns([3, 1])
        with col1:
            atm_sel = st.selectbox("🎯 ATM", list(atm_db.keys())); config = atm_db[atm_sel]
            if st.session_state.last_atm != atm_sel: st.session_state.n_ex = 0; st.session_state.last_atm = atm_sel; st.rerun()
        with col2:
            st.write(""); cb1, cb2 = st.columns(2)
            cb1.button("➕", on_click=lambda: st.session_state.update({"n_ex": st.session_state.n_ex + 1}))
            cb2.button("🧹", on_click=lambda: st.rerun())

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date()); atv = st.selectbox("Ativo", ["MNQ", "NQ"]); ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"]); dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        with f2:
            lt = st.number_input("Contratos", min_value=0, value=int(config["lote"])); stp = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]))
            up = st.file_uploader("📸 Prints", accept_multiple_files=True)
        with f3:
            st.write("**Saídas**"); saídas = []; aloc = 0
            for i, p_c in enumerate(config["parciais"]):
                sc1, sc2 = st.columns(2); p = sc1.number_input(f"Pts P{i+1}", value=float(p_c[0]), key=f"p_{i}"); q = sc2.number_input(f"Qtd P{i+1}", value=int(p_c[1]), key=f"q_{i}"); saídas.append((p, q)); aloc += q
            for i in range(st.session_state.n_ex):
                sc1, sc2 = st.columns(2); p = sc1.number_input(f"Pts Ex {i+1}", key=f"pe_{i}"); q = sc2.number_input(f"Qtd Ex {i+1}", key=f"qe_{i}"); saídas.append((p, q)); aloc += q
            if lt > 0 and lt != aloc: st.markdown(f'<div class="piscante-erro">FALTAM {lt-aloc} CONTRATOS</div>', unsafe_allow_html=True)
            elif lt == aloc and lt > 0: st.success("✅ Posição Completa")

        rb1, rb2 = st.columns(2)
        with rb1:
            if st.button("💾 REGISTRAR GAIN", use_container_width=True) and lt == aloc:
                res = sum([s[0]*MULTIPLIERS[atv]*s[1] for s in saídas]); pt_m = sum([s[0]*s[1] for s in saídas])/lt; nid = str(uuid.uuid4()); paths = []
                for i, f in enumerate(up):
                    p_path = os.path.join(IMG_DIR, f"{nid}_{i}.png"); open(p_path, "wb").write(f.getbuffer()); paths.append(p_path)
                nt = pd.DataFrame([{'Data': dt, 'Ativo': atv, 'Contexto': ctx, 'Direcao': dr, 'Lote': lt, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': pt_m, 'Risco_Fin': (stp*MULTIPLIERS[atv]*lt), 'ID': nid, 'Prints': "|".join(paths), 'Notas': "", 'Usuario': st.session_state["logged_user"]}])
                df = pd.concat([df, nt], ignore_index=True); df.to_csv(CSV_FILE, index=False); st.success("🎯 Registrado!"); st.rerun()
        with rb2:
            if st.button("🚨 REGISTRAR STOP FULL", type="secondary", use_container_width=True) and lt > 0:
                res_s = -(stp*MULTIPLIERS[atv]*lt); nid = str(uuid.uuid4()); paths = []
                for i, f in enumerate(up):
                    p_path = os.path.join(IMG_DIR, f"{nid}_{i}.png"); open(p_path, "wb").write(f.getbuffer()); paths.append(p_path)
                nt = pd.DataFrame([{'Data': dt, 'Ativo': atv, 'Contexto': ctx, 'Direcao': dr, 'Lote': lt, 'ATM': atm_sel, 'Resultado': res_s, 'Pts_Medio': -stp, 'Risco_Fin': abs(res_s), 'ID': nid, 'Prints': "|".join(paths), 'Notas': "", 'Usuario': st.session_state["logged_user"]}])
                df = pd.concat([df, nt], ignore_index=True); df.to_csv(CSV_FILE, index=False); st.error("🚨 Stop!"); st.rerun()

    # --- ABA: CONFIGURAR ATM ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Editor de ATM")
        with st.expander("✨ Criar Template", expanded=True):
            n = st.text_input("Nome"); ca1, ca2 = st.columns(2); l_p = ca1.number_input("Lote Total", min_value=1); s_p = ca2.number_input("Stop (Pts)", min_value=0.0); n_p = st.number_input("Alvos", 1, 6, 1); n_p_list = []
            for i in range(n_p):
                cp1, cp2 = st.columns(2); n_p_list.append([cp1.number_input(f"Pts {i+1}", key=f"ap_{i}"), cp2.number_input(f"Qtd {i+1}", key=f"aq_{i}", min_value=1)])
            if st.button("💾 Salvar ATM"):
                atm_db[n] = {"lote": l_p, "stop": s_p, "parciais": n_p_list}
                with open(ATM_FILE, 'w') as f: json.dump(atm_db, f)
                st.rerun()
        for nome, cfg in list(atm_db.items()):
            if nome != "Personalizado":
                c_n, c_d = st.columns([4, 1]); c_n.write(f"**{nome}** (Lote: {cfg['lote']})")
                if c_d.button("Excluir", key=f"del_{nome}"):
                    del atm_db[nome]
                    with open(ATM_FILE, 'w') as f: json.dump(atm_db, f)
                    st.rerun()

    # --- ABA: HISTÓRICO ---
    elif selected == "Histórico":
        st.title("📜 Galeria")
        if 'to_delete' in st.session_state:
            df = df[df['ID'] != st.session_state.to_delete]; df.to_csv(CSV_FILE, index=False); del st.session_state.to_delete; st.rerun()
        cf1, cf2 = st.columns(2)
        with cf1:
            u_opt = ["Todos"] + list(df['Usuario'].unique()) if st.session_state["logged_user"] == "admin" else [st.session_state["logged_user"]]
            f_u = st.selectbox("Operador:", u_opt)
        with cf2: f_cx = st.selectbox("Contexto:", ["Todos", "Contexto A", "Contexto B", "Contexto C"])
        df_h = df.copy()
        if f_u != "Todos": df_h = df_h[df_h['Usuario'] == f_u]
        if f_cx != "Todos": df_h = df_h[df_h['Contexto'] == f_cx]
        if not df_h.empty:
            df_disp = df_h.iloc[::-1].copy(); df_disp['Num'] = range(len(df_disp), 0, -1)
            for i in range(0, len(df_disp), 5):
                cols = st.columns(5)
                for j in range(5):
                    if i + j < len(df_disp):
                        row = df_disp.iloc[i + j]; p_s = str(row['Prints']).split("|") if row['Prints'] else []
                        with cols[j]:
                            img_h = f'<div class="img-container"><img src="data:image/png;base64,{get_base64(p_s[0])}"></div>' if p_s and os.path.exists(p_s[0]) else '<div class="img-container">Sem Print</div>'
                            st.markdown(f'<div class="trade-card">{img_h}<div class="card-footer"><div><b style="color:white">{row["Usuario"]}</b><br><small style="color:#888">{row["Contexto"]}</small></div><div style="color:{"#00FF88" if row["Resultado"] > 0 else "#FF4B4B"}; font-weight:bold;">${row["Resultado"]:,.2f}</div>', unsafe_allow_html=True)
                            if st.button("Ver", key=f"v_{row['ID']}"): expand_modal(row['ID'])
                            st.markdown('</div></div>', unsafe_allow_html=True)

    # --- ABA: GERENCIAR USUÁRIOS (ADM) ---
    elif st.session_state["logged_user"] == "admin" and selected == "Gerenciar Usuários":
        st.title("👥 Gestão")
        u_db = load_users()
        with st.expander("Novo Acesso"):
            nu = st.text_input("User"); np = st.text_input("Senha", type="password")
            if st.button("Criar"): u_db[nu] = np; save_users(u_db); st.rerun()
        for u in list(u_db.keys()):
            c_u, c_d = st.columns([4, 1]); c_u.write(f"👤 {u}")
            if u != "admin" and c_d.button("Remover", key=f"rm_{u}"): del u_db[u]; save_users(u_db); st.rerun()
