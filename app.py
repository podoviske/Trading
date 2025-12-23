import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import json
import uuid
import time
from supabase import create_client, Client

# --- 1. CONEXÃO SUPABASE ---
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro crítico: Chaves do Supabase não encontradas nos Secrets.")

# --- 2. CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="EvoTrade Terminal", layout="wide", page_icon="📈")

# --- CSS CUSTOMIZADO (MANTIDO 100%) ---
st.markdown("""
    <style>
    .trade-card {
        background-color: #161616; border-radius: 8px; padding: 12px;
        margin-bottom: 15px; border: 1px solid #333; transition: transform 0.2s, border-color 0.2s;
    }
    .trade-card:hover { transform: translateY(-3px); border-color: #B20000; }
    .card-img-container {
        width: 100%; height: 140px; background-color: #222;
        border-radius: 5px; overflow: hidden; display: flex;
        align-items: center; justify-content: center; margin-bottom: 10px;
    }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 14px; font-weight: 700; color: white; margin-bottom: 2px; }
    .card-sub { font-size: 11px; color: #888; margin-bottom: 8px; }
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }

    .metric-container { 
        background-color: #161616; border: 1px solid #262626; padding: 15px; 
        border-radius: 10px; text-align: center; margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: border-color 0.3s, transform 0.3s;
        position: relative; min-height: 140px; display: flex; flex-direction: column;
        justify-content: center; align-items: center;
    }
    .metric-container:hover { border-color: #B20000; transform: translateY(-3px); cursor: help; }
    .metric-label { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; display: flex; justify-content: center; align-items: center; gap: 5px; }
    .metric-value { color: white; font-size: 22px; font-weight: 800; margin-top: 5px; }
    .metric-sub { font-size: 12px; margin-top: 4px; color: #666; }
    .help-icon { color: #555; font-size: 12px; border: 1px solid #444; border-radius: 50%; width: 14px; height: 14px; display: inline-flex; align-items: center; justify-content: center; }
    [data-testid="stSidebar"] { background-color: #0F0F0F !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    .piscante-erro { padding: 15px; border-radius: 5px; color: white; font-weight: bold; text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000; }
    .risco-alert { color: #FF4B4B; font-weight: bold; font-size: 16px; margin-top: 5px; background-color: rgba(255, 75, 75, 0.1); padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #FF4B4B; }
    @keyframes blinking { 0% { background-color: #440000; } 50% { background-color: #B20000; } 100% { background-color: #440000; } }
    </style>
""", unsafe_allow_html=True)

# --- 3. SISTEMA DE LOGIN (MANTIDO) ---
def check_password():
    def password_entered():
        u = st.session_state.get("username_input")
        p = st.session_state.get("password_input")
        try:
            res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data:
                st.session_state["password_correct"] = True
                st.session_state["logged_user"] = u
            else: st.session_state["password_correct"] = False
        except Exception as e: st.error(f"Erro de conexão: {e}")

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown("""<style>.login-container { max-width: 400px; margin: 50px auto; padding: 30px; background-color: #161616; border-radius: 15px; border: 1px solid #B20000; text-align: center; } .logo-main { color: #B20000; font-size: 50px; font-weight: 900; } .logo-sub { color: white; font-size: 35px; font-weight: 700; margin-top: -15px; } </style>""", unsafe_allow_html=True)
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.markdown('<div class="login-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div>', unsafe_allow_html=True)
            st.write("---")
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
            if st.session_state.get("password_correct") == False: st.error("😕 Credenciais incorretas.")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if check_password():
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER_LOGGED = st.session_state["logged_user"]
    IS_ADMIN = (USER_LOGGED == "admin")

    # --- 5. FUNÇÕES DE DADOS (COM SUPORTE A GRUPO) ---
    def load_trades_db():
        try:
            res = supabase.table("trades").select("*").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.date
                df['created_at'] = pd.to_datetime(df['created_at'])
                if 'grupo_conta' not in df.columns: df['grupo_conta'] = 'Geral'
            return df
        except: return pd.DataFrame()

    def load_atms_db():
        try:
            res = supabase.table("atm_configs").select("*").execute()
            return {item['nome']: item for item in res.data}
        except: return {}

    def card_metric(label, value, sub_value="", color="white", help_text=""):
        sub_html = f'<div class="metric-sub">{sub_value}</div>' if sub_value else '<div class="metric-sub">&nbsp;</div>'
        help_html = f'<span class="help-icon" title="{help_text}">?</span>' if help_text else ""
        st.markdown(f'<div class="metric-container" title="{help_text}"><div class="metric-label">{label} {help_html}</div><div class="metric-value" style="color: {color};">{value}</div>{sub_html}</div>', unsafe_allow_html=True)

    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        if IS_ADMIN: menu.append("Gerenciar Usuários")
        selected = option_menu(None, menu, icons=["grid", "currency-dollar", "gear", "clock", "people"], styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair / Logout"): st.session_state.clear(); st.rerun()

    # --- 7. DASHBOARD (COM FILTRO DE GRUPO) ---
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df_raw = load_trades_db()
        if not df_raw.empty:
            df = df_raw[df_raw['usuario'] == USER_LOGGED]
            if not df.empty:
                with st.expander("🔍 Filtros Avançados", expanded=True):
                    # Adicionado seletor de Grupo aqui
                    c_d1, c_d2, c_grp, c_ctx = st.columns([1, 1, 1.2, 1.8])
                    d_inicio = c_d1.date_input("Início", df['data'].min())
                    d_fim = c_d2.date_input("Fim", df['data'].max())
                    
                    if IS_ADMIN:
                        grupos_list = ["Todos"] + sorted(df['grupo_conta'].unique().tolist())
                        sel_grp = c_grp.selectbox("Grupo de Contas", grupos_list)
                    else: sel_grp = "Todos"
                    
                    all_ctx = list(df['contexto'].unique())
                    fil_ctx = c_ctx.multiselect("Contextos", all_ctx, default=all_ctx)

                mask = (df['data'] >= d_inicio) & (df['data'] <= d_fim) & (df['contexto'].isin(fil_ctx))
                if IS_ADMIN and sel_grp != "Todos": mask = mask & (df['grupo_conta'] == sel_grp)
                df_f = df[mask].copy()

                if df_f.empty: st.warning("⚠️ Nenhum trade encontrado.")
                else:
                    # Lógica de KPIs (Sua lógica original mantida)
                    total_trades = len(df_f)
                    net_profit = df_f['resultado'].sum()
                    wins = df_f[df_f['resultado'] > 0]
                    losses = df_f[df_f['resultado'] < 0]
                    gross_p = wins['resultado'].sum()
                    gross_l = abs(losses['resultado'].sum())
                    pf = gross_p / gross_l if gross_l > 0 else float('inf')
                    win_rate = (len(wins) / total_trades) * 100
                    avg_win, avg_loss = wins['resultado'].mean() if not wins.empty else 0, abs(losses['resultado'].mean()) if not losses.empty else 0
                    payoff = avg_win / avg_loss if avg_loss > 0 else 0
                    
                    st.markdown("##### 🏁 Desempenho Geral")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: card_metric("RESULTADO LÍQUIDO", f"${net_profit:,.2f}", f"Bruto: ${gross_p:,.0f}", "#00FF88" if net_profit >= 0 else "#FF4B4B")
                    with c2: card_metric("FATOR DE LUCRO (PF)", f"{pf:.2f}" if pf != float('inf') else "∞", "Ideal > 1.5", "#B20000")
                    with c3: card_metric("WIN RATE", f"{win_rate:.1f}%", f"{len(wins)} Wins / {len(losses)} Loss")
                    with c4: card_metric("PAYOFF", f"1 : {payoff:.2f}", "Risco:Retorno Real")

                    # Gráficos (Seus gráficos originais)
                    df_f = df_f.sort_values('created_at')
                    df_f['equity'] = df_f['resultado'].cumsum()
                    g1, g2 = st.columns([2, 1])
                    with g1:
                        fig_eq = px.area(df_f, x='created_at', y='equity', title="📈 Curva de Patrimônio", template="plotly_dark")
                        fig_eq.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                        st.plotly_chart(fig_eq, use_container_width=True)
                    with g2:
                        ctx_perf = df_f.groupby('contexto')['resultado'].sum().reset_index()
                        fig_bar = px.bar(ctx_perf, x='contexto', y='resultado', title="📊 Por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                        st.plotly_chart(fig_bar, use_container_width=True)
            else: st.info("Sem operações.")
        else: st.warning("Banco vazio.")

    # --- 8. REGISTRAR TRADE (COM SELETOR DE GRUPO) ---
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db()
        
        # Injeção do Grupo
        if IS_ADMIN:
            grupo_trade = st.radio("Selecione o Bloco de Contas:", ["Grupo A", "Grupo B", "Grupo C", "Grupo D", "Geral"], horizontal=True, index=4)
        else: grupo_trade = "Geral"

        atm_sel = st.selectbox("🎯 Escolher Template ATM", ["Manual"] + list(atm_db.keys()))
        # ... (Sua lógica de ATM original 100% igual abaixo) ...
        if atm_sel != "Manual":
            config = atm_db[atm_sel]; lt_default = int(config["lote"]); stp_default = float(config["stop"])
            parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
        else: lt_default, stp_default, parciais_pre = 1, 0.0, []

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date()); atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True); ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
        with f2:
            lt = st.number_input("Contratos Total", min_value=1, value=lt_default)
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_default, step=0.25)
            if stp > 0: st.markdown(f'<div class="risco-alert">📉 Risco: ${stp * MULTIPLIERS[atv] * lt:,.2f}</div>', unsafe_allow_html=True)
            up = st.file_uploader("📸 Anexar Print", type=['png', 'jpg', 'jpeg'])
        with f3:
            st.write("**Saídas (Alocação)**")
            if "num_parciais" not in st.session_state or atm_sel != st.session_state.get("last_atm"):
                st.session_state.num_parciais = len(parciais_pre) if parciais_pre else 1
                st.session_state.last_atm = atm_sel
            c_b1, c_b2 = st.columns(2)
            if c_b1.button("➕ Add Parcial"): st.session_state.num_parciais += 1
            if c_b2.button("🧹 Limpar"): st.session_state.num_parciais = 1; st.rerun()
            saidas, aloc = [], 0
            for i in range(st.session_state.num_parciais):
                c_pts, c_qtd = st.columns(2)
                v_pts = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
                v_qtd = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
                pts = c_pts.number_input(f"Alvo {i+1}", value=v_pts, key=f"p_pts_{i}_{atm_sel}"); qtd = c_qtd.number_input(f"Qtd {i+1}", value=v_qtd, key=f"p_qtd_{i}_{atm_sel}")
                saidas.append({"pts": pts, "qtd": qtd}); aloc += qtd
            if lt != aloc: st.markdown(f'<div class="piscante-erro">SALDO: {lt - aloc} CTTS</div>', unsafe_allow_html=True)
            else: st.success("✅ Sincronizado")

        st.divider()
        col_gain, col_loss = st.columns(2)
        btn_reg = False
        if col_gain.button("🟢 REGISTRAR GAIN", use_container_width=True, disabled=(lt!=aloc)): btn_reg = True
        if col_loss.button("🔴 REGISTRAR STOP FULL", use_container_width=True): saidas = [{"pts": -stp, "qtd": lt}]; btn_reg = True

        if btn_reg:
            with st.spinner("Salvando..."):
                res_fin = sum([s["pts"] * MULTIPLIERS[atv] * s["qtd"] for s in saidas])
                pt_med = sum([s["pts"] * s["qtd"] for s in saidas]) / lt
                t_id = str(uuid.uuid4()); img_url = ""
                if up: 
                    supabase.storage.from_("prints").upload(f"{t_id}.png", up.getvalue())
                    img_url = supabase.storage.from_("prints").get_public_url(f"{t_id}.png")
                supabase.table("trades").insert({"id": t_id, "data": str(dt), "ativo": atv, "contexto": ctx, "direcao": dr, "lote": lt, "resultado": res_fin, "pts_medio": pt_med, "prints": img_url, "usuario": USER_LOGGED, "grupo_conta": grupo_trade}).execute()
                st.balloons(); time.sleep(2); st.rerun()

    # --- 9. CONFIGURAR ATM (SEU CÓDIGO ORIGINAL COMPLETO) ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")
        if "atm_form_data" not in st.session_state: st.session_state.atm_form_data = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        def reset_atm_form(): st.session_state.atm_form_data = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        res = supabase.table("atm_configs").select("*").order("nome").execute()
        existing_atms = res.data
        c_form, c_list = st.columns([1.5, 1])
        with c_list:
            st.subheader("📋 Estratégias Salvas")
            if st.button("✨ Criar Nova", use_container_width=True): reset_atm_form(); st.rerun()
            if existing_atms:
                for item in existing_atms:
                    with st.expander(f"📍 {item['nome']}"):
                        c_edit, c_del = st.columns(2)
                        if c_edit.button("✏️", key=f"ed_{item['id']}"):
                            p_data = item['parciais'] if isinstance(item['parciais'], list) else json.loads(item['parciais'])
                            st.session_state.atm_form_data = {"id": item['id'], "nome": item['nome'], "lote": item['lote'], "stop": item['stop'], "parciais": p_data}; st.rerun()
                        if c_del.button("🗑️", key=f"dl_{item['id']}"): supabase.table("atm_configs").delete().eq("id", item['id']).execute(); st.rerun()
        with c_form:
            f_d = st.session_state.atm_form_data; n_nome = st.text_input("Nome", value=f_d["nome"])
            n_lote = st.number_input("Lote", value=int(f_d["lote"])); n_stop = st.number_input("Stop", value=float(f_d["stop"]))
            upd_p = []
            for i, p in enumerate(f_d["parciais"]):
                c1, c2 = st.columns(2); p_pts = c1.number_input(f"Alvo {i+1}", value=float(p["pts"]), key=f"at_pts_{i}"); p_qtd = c2.number_input(f"Qtd {i+1}", value=int(p["qtd"]), key=f"at_qtd_{i}")
                upd_p.append({"pts": p_pts, "qtd": p_qtd})
            if st.button("💾 SALVAR"):
                pay = {"nome": n_nome, "lote": n_lote, "stop": n_stop, "parciais": upd_p}
                if f_d["id"]: supabase.table("atm_configs").update(pay).eq("id", f_d["id"]).execute()
                else: supabase.table("atm_configs").insert(pay).execute()
                reset_atm_form(); st.rerun()

    # --- 10. HISTÓRICO (COM GRUPO NO CARD) ---
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        df_h = load_trades_db()
        if not df_h.empty:
            df_h = df_h[df_h['usuario'] == USER_LOGGED].sort_values('created_at', ascending=False)
            
            @st.dialog("Detalhes da Operação", width="large")
            def show_trade_details(row):
                if row.get('prints'): st.image(row['prints'], use_container_width=True)
                st.write(f"📅 **Data:** {row['data']} | **Grupo:** {row['grupo_conta']}")
                res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
                st.markdown(f"<h1 style='color:{res_c}; text-align:center;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
                if st.button("🗑️ DELETAR REGISTRO", type="primary"): supabase.table("trades").delete().eq("id", row['id']).execute(); st.rerun()

            cols = st.columns(4)
            for i, (index, row) in enumerate(df_h.iterrows()):
                with cols[i % 4]:
                    res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    img_h = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="height:140px; background:#333; display:flex; align-items:center; justify-content:center;">Sem Foto</div>'
                    st.markdown(f'<div class="trade-card"><div class="card-img-container">{img_h}</div><div class="card-title">{row["ativo"]} - {row["grupo_conta"]}</div><div class="card-sub">{row["data"]} • {row["contexto"]}</div><div class="{res_class}">${row["resultado"]:,.2f}</div></div>', unsafe_allow_html=True)
                    if st.button("👁️ Ver", key=f"btn_{row['id']}", use_container_width=True): show_trade_details(row)

    # --- 11. GERENCIAR USUÁRIOS (SEU CÓDIGO ORIGINAL COMPLETO) ---
    elif selected == "Gerenciar Usuários":
        st.title("👥 Gestão de Usuários")
        if "u_f_d" not in st.session_state: st.session_state.u_f_d = {"id": None, "username": "", "password": ""}
        res = supabase.table("users").select("*").execute(); u_list = res.data
        c_f, c_l = st.columns([1, 1.5])
        with c_l:
            for u in u_list:
                with st.container():
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.write(f"👤 **{u['username']}**")
                    if c2.button("✏️", key=f"ue_{u['id']}"): st.session_state.u_f_d = {"id": u['id'], "username": u['username'], "password": u['password']}; st.rerun()
                    if c3.button("🗑️", key=f"ud_{u['id']}"): supabase.table("users").delete().eq("id", u['id']).execute(); st.rerun()
                    st.divider()
        with c_f:
            u_d = st.session_state.u_f_d; n_u = st.text_input("Login", value=u_d["username"]); n_p = st.text_input("Senha", value=u_d["password"])
            if st.button("💾 SALVAR USUÁRIO"):
                if u_d["id"]: supabase.table("users").update({"username": n_u, "password": n_p}).eq("id", u_d["id"]).execute()
                else: supabase.table("users").insert({"username": n_u, "password": n_p}).execute()
                st.session_state.u_f_d = {"id": None, "username": "", "password": ""}; st.rerun()
