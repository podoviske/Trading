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
    .trade-card { background-color: #161616; border-radius: 8px; padding: 12px; margin-bottom: 15px; border: 1px solid #333; transition: transform 0.2s; }
    .trade-card:hover { transform: translateY(-3px); border-color: #B20000; }
    .card-img-container { width: 100%; height: 140px; background-color: #222; border-radius: 5px; overflow: hidden; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 14px; font-weight: 700; color: white; margin-bottom: 2px; }
    .card-sub { font-size: 11px; color: #888; margin-bottom: 8px; }
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }
    .metric-container { background-color: #161616; border: 1px solid #262626; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); min-height: 140px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
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

# --- 3. SISTEMA DE LOGIN ---
def check_password():
    def password_entered():
        u = st.session_state.get("username_input")
        p = st.session_state.get("password_input")
        try:
            res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data:
                st.session_state["password_correct"] = True
                st.session_state["logged_user"] = u
                st.session_state["user_role"] = res.data[0].get('role', 'user')
            else: st.session_state["password_correct"] = False
        except Exception as e: st.error(f"Erro: {e}")

    if not st.session_state.get("password_correct"):
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.markdown('<div class="login-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div>', unsafe_allow_html=True)
            st.write("---")
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
            if st.session_state.get("password_correct") == False: st.error("Credenciais inválidas.")
        return False
    return True

if check_password():
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER = st.session_state["logged_user"]
    ROLE = st.session_state.get("user_role", "user")

    # --- 5. FUNÇÕES DE DADOS ---
    def load_trades_db():
        try:
            res = supabase.table("trades").select("*").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.date
                df['created_at'] = pd.to_datetime(df['created_at'])
                if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
                if 'conta_vinculo' not in df.columns: df['conta_vinculo'] = 'Geral'
            return df
        except: return pd.DataFrame()

    def load_atms_db():
        try:
            res = supabase.table("atm_configs").select("*").execute()
            return {item['nome']: item for item in res.data}
        except: return {}

    def load_contas_config():
        try:
            res = supabase.table("contas_config").select("*").eq("usuario", USER).execute()
            return pd.DataFrame(res.data)
        except: return pd.DataFrame()

    def card_metric(label, value, sub_value="", color="white", help_text=""):
        sub_html = f'<div class="metric-sub">{sub_value}</div>' if sub_value else '<div class="metric-sub">&nbsp;</div>'
        st.markdown(f'<div class="metric-container" title="{help_text}"><div class="metric-label">{label}</div><div class="metric-value" style="color: {color};">{value}</div>{sub_html}</div>', unsafe_allow_html=True)

    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        icons = ["grid", "currency-dollar", "gear", "clock"]
        
        if ROLE in ['master', 'admin']:
            menu.insert(2, "Contas")
            icons.insert(2, "briefcase")
        if ROLE == 'admin':
            menu.append("Gerenciar Usuários")
            icons.append("people")
            
        selected = option_menu(None, menu, icons=icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair / Logout"): st.session_state.clear(); st.rerun()

    # --- 7. ABA: DASHBOARD ---
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df_raw = load_trades_db()
        if not df_raw.empty:
            df = df_raw[df_raw['usuario'] == USER]
            if not df.empty:
                with st.expander("🔍 Filtros Avançados", expanded=True):
                    if ROLE in ['master', 'admin']:
                        c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1.8])
                        sel_grp = c3.selectbox("Grupo", ["Todos"] + sorted(list(df['grupo_vinculo'].unique())))
                    else:
                        c1, c2, c4 = st.columns([1, 1, 2]); sel_grp = "Todos"
                    
                    d_i = c1.date_input("Início", df['data'].min())
                    d_f = c2.date_input("Fim", df['data'].max())
                    f_ctx = c4.multiselect("Contextos", list(df['contexto'].unique()), default=list(df['contexto'].unique()))

                mask = (df['data'] >= d_i) & (df['data'] <= d_f) & (df['contexto'].isin(f_ctx))
                if sel_grp != "Todos": mask &= (df['grupo_vinculo'] == sel_grp)
                df_f = df[mask].copy()

                if not df_f.empty:
                    # KPIs
                    t_tr = len(df_f); net = df_f['resultado'].sum()
                    wins, losses = df_f[df_f['resultado'] > 0], df_f[df_f['resultado'] < 0]
                    pf = (wins['resultado'].sum() / abs(losses['resultado'].sum())) if not losses.empty else float('inf')
                    wr = (len(wins)/t_tr)*100
                    avg_w, avg_l = wins['resultado'].mean() if not wins.empty else 0, abs(losses['resultado'].mean()) if not losses.empty else 0
                    payoff = avg_w/avg_l if avg_l > 0 else 0
                    exp = ((wr/100)*avg_w) - ((len(losses)/t_tr)*avg_l)
                    
                    df_f = df_f.sort_values('created_at'); df_f['equity'] = df_f['resultado'].cumsum()
                    max_dd = (df_f['equity'] - df_f['equity'].cummax()).min()

                    # DISPLAY
                    r1 = st.columns(4)
                    with r1[0]: card_metric("RESULTADO LÍQUIDO", f"${net:,.2f}", f"Bruto: ${wins['resultado'].sum():,.0f}", "#00FF88" if net>=0 else "#FF4B4B")
                    with r1[1]: card_metric("FATOR DE LUCRO", f"{pf:.2f}", "Ideal > 1.5", "#B20000")
                    with r1[2]: card_metric("WIN RATE", f"{wr:.1f}%", f"{len(wins)}W / {len(losses)}L", "white")
                    with r1[3]: card_metric("EXPECTATIVA", f"${exp:.2f}", "Por Trade", "#00FF88" if exp>0 else "#FF4B4B")

                    r2 = st.columns(4)
                    with r2[0]: card_metric("MÉDIA GAIN", f"${avg_w:,.2f}", "", "#00FF88")
                    with r2[1]: card_metric("MÉDIA LOSS", f"-${avg_l:,.2f}", "", "#FF4B4B")
                    with r2[2]: card_metric("PAYOFF", f"1 : {payoff:.2f}", "Risco:Retorno")
                    with r2[3]: card_metric("DRAWDOWN MÁX", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B")

                    r3 = st.columns(4)
                    with r3[0]: card_metric("PTS MÉDIOS (GAIN)", f"{wins['pts_medio'].mean():.2f}", "", "#00FF88")
                    with r3[1]: card_metric("PTS MÉDIOS (LOSS)", f"{abs(losses['pts_medio'].mean()):.2f}", "", "#FF4B4B")
                    with r3[2]: card_metric("LOTE MÉDIO", f"{df_f['lote'].mean():.1f}", "Contratos")
                    with r3[3]: card_metric("TRADES", str(t_tr), "Total")

                    st.divider()
                    g1, g2 = st.columns([2, 1])
                    with g1:
                        st.plotly_chart(px.area(df_f, x='created_at', y='equity', title="📈 Curva de Patrimônio", template="plotly_dark").update_traces(line_color='#B20000', fillcolor='rgba(178,0,0,0.2)'), use_container_width=True)
                    with g2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        ctx_perf = df_f.groupby('contexto')['resultado'].sum().reset_index()
                        st.plotly_chart(px.bar(ctx_perf, x='contexto', y='resultado', title="📊 Resultado por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"]), use_container_width=True)
            else: st.info("Sem trades.")
        else: st.warning("Banco vazio.")

    # --- 8. REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db(); df_c = load_contas_config()
        
        c_atm, c_grp = st.columns([3, 1.5])
        with c_atm: atm_sel = st.selectbox("🎯 Template ATM", ["Manual"] + list(atm_db.keys()))
        with c_grp:
            grupo_sel = st.selectbox("📂 Grupo", sorted(df_c['grupo_nome'].unique())) if (ROLE in ["master", "admin"] and not df_c.empty) else "Geral"

        if atm_sel != "Manual":
            conf = atm_db[atm_sel]; lt_d, stp_d = int(conf["lote"]), float(conf["stop"])
            parc_pre = json.loads(conf["parciais"]) if isinstance(conf["parciais"], str) else conf["parciais"]
        else: lt_d, stp_d, parc_pre = 1, 0.0, []

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date()); atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True); ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
        with f2:
            lt = st.number_input("Lote", min_value=1, value=lt_d); stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_d, step=0.25)
            if stp > 0: st.markdown(f'<div class="risco-alert">📉 Risco: ${stp * MULTIPLIERS[atv] * lt:,.2f}</div>', unsafe_allow_html=True)
            up = st.file_uploader("📸 Print", type=['png', 'jpg'])
        with f3:
            st.write("**Saídas**")
            if "n_parc" not in st.session_state or st.session_state.get("last_atm") != atm_sel:
                st.session_state.n_parc = len(parc_pre) if parc_pre else 1
                st.session_state.last_atm = atm_sel
            
            cb1, cb2 = st.columns(2)
            if cb1.button("➕ Add"): st.session_state.n_parc += 1; st.rerun()
            if cb2.button("🧹 Reset"): st.session_state.n_parc = 1; st.rerun()
            
            saidas, aloc = [], 0
            for i in range(st.session_state.n_parc):
                cp, cq = st.columns(2)
                vp = float(parc_pre[i]["pts"]) if i < len(parc_pre) else 0.0
                vq = int(parc_pre[i]["qtd"]) if i < len(parc_pre) else (lt if i == 0 else 0)
                p = cp.number_input(f"Pts {i+1}", value=vp, key=f"p_{i}_{atm_sel}"); q = cq.number_input(f"Qtd {i+1}", value=vq, key=f"q_{i}_{atm_sel}")
                saidas.append({"pts": p, "qtd": q}); aloc += q
            if lt != aloc: st.markdown(f'<div class="piscante-erro">SALDO: {lt - aloc} CTTS</div>', unsafe_allow_html=True)

        cg, cl = st.columns(2); b_reg = False
        if cg.button("🟢 GAIN", use_container_width=True, disabled=(lt!=aloc)): b_reg = True
        if cl.button("🔴 STOP", use_container_width=True): saidas = [{"pts": -stp, "qtd": lt}]; b_reg = True
        
        if b_reg:
            with st.spinner("Salvando..."):
                res_fin = sum([s["pts"] * MULTIPLIERS[atv] * s["qtd"] for s in saidas])
                pt_m = sum([s["pts"] * s["qtd"] for s in saidas]) / lt
                tid = str(uuid.uuid4()); i_url = ""
                if up:
                    supabase.storage.from_("prints").upload(f"{tid}.png", up.getvalue())
                    i_url = supabase.storage.from_("prints").get_public_url(f"{tid}.png")
                supabase.table("trades").insert({"id": tid, "data": str(dt), "ativo": atv, "contexto": ctx, "direcao": dr, "lote": lt, "resultado": res_fin, "pts_medio": pt_m, "prints": i_url, "usuario": USER, "grupo_vinculo": grupo_sel}).execute()
                st.balloons(); time.sleep(1); st.rerun()

    # --- 9. ABA CONTAS (EVOLUÇÃO DO SALDO) ---
    elif selected == "Contas":
        st.title("💼 Gestão de Portfólio")
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("⚙️ Nova Conta")
            with st.form("f_cta"):
                gn = st.text_input("Grupo (Ex: Fase 2 - Apex)")
                ci = st.text_input("Conta (Ex: PA-01)")
                si = st.number_input("Saldo Inicial ($)", value=50000.0, step=100.0)
                fa = st.selectbox("Fase Atual", ["Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saques)"])
                if st.form_submit_button("Salvar Conta"):
                    supabase.table("contas_config").insert({"usuario": USER, "grupo_nome": gn, "conta_identificador": ci, "saldo_inicial": si, "fase": fa}).execute()
                    st.success("Conta criada!"); st.rerun()
        
        with c2:
            st.subheader("📋 Acompanhamento")
            df_c = load_contas_config()
            df_t = load_trades_db() # Carrega trades para calcular saldo
            
            if not df_c.empty:
                # Se não for User, filtra os trades dele. Se for Master, já carregou os dele.
                df_t = df_t[df_t['usuario'] == USER]
                
                for grp in sorted(df_c['grupo_nome'].unique()):
                    with st.expander(f"📂 {grp}", expanded=True):
                        # Pega trades desse grupo
                        trades_grupo = df_t[df_t['grupo_vinculo'] == grp]
                        lucro_grupo = trades_grupo['resultado'].sum()
                        
                        contas_g = df_c[df_c['grupo_nome'] == grp]
                        for _, row in contas_g.iterrows():
                            # Se tivéssemos filtro por conta individual no trade, usariamos aqui.
                            # Como o trade é por GRUPO, dividimos o lucro do grupo pelo nº de contas (Simulação de Copy)
                            # OU assumimos que o trade registrado impacta todas. 
                            # Para simplificar e seguir a lógica de "Grupo", mostramos o saldo do grupo ou individual?
                            # O usuário pediu "saldo da conta". Vamos mostrar o Saldo Inicial + Lucro do Grupo (Considerando que opera copy igual).
                            
                            saldo_atual = row['saldo_inicial'] + lucro_grupo 
                            delta = saldo_atual - row['saldo_inicial']
                            cor_delta = "#00FF88" if delta >= 0 else "#FF4B4B"
                            
                            c_info, c_del = st.columns([4, 1])
                            c_info.markdown(f"""
                                **{row['conta_identificador']}** | {row['fase']}  
                                💰 Saldo: **${saldo_atual:,.2f}** (<span style='color:{cor_delta}'>${delta:+,.2f}</span>)
                            """, unsafe_allow_html=True)
                            
                            if c_del.button("🗑️", key=f"del_c_{row['id']}"):
                                supabase.table("contas_config").delete().eq("id", row['id']).execute(); st.rerun()
                        
                        st.progress(min(1.0, max(0.0, (lucro_grupo + 5000)/10000))) # Barra de progresso visual genérica (Ex: meta 5k)
            else: st.info("Nenhuma conta cadastrada.")

    # --- 10. CONFIGURAR ATM ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")
        if "ae" not in st.session_state: st.session_state.ae = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        
        atms = supabase.table("atm_configs").select("*").order("nome").execute().data
        cf, cl = st.columns([1.5, 1])
        with cl:
            st.subheader("Salvas")
            if st.button("✨ Nova"): st.session_state.ae = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}; st.rerun()
            for a in atms:
                with st.expander(f"📍 {a['nome']}"):
                    ce, cd = st.columns(2)
                    if ce.button("✏️", key=f"e_{a['id']}"):
                        pd_ = a['parciais'] if isinstance(a['parciais'], list) else json.loads(a['parciais'])
                        st.session_state.ae = {"id": a['id'], "nome": a['nome'], "lote": a['lote'], "stop": a['stop'], "parciais": pd_}; st.rerun()
                    if cd.button("🗑️", key=f"d_{a['id']}"): supabase.table("atm_configs").delete().eq("id", a['id']).execute(); st.rerun()
        with cf:
            fd = st.session_state.ae; nn = st.text_input("Nome", value=fd["nome"])
            nl = st.number_input("Lote", value=int(fd["lote"])); ns = st.number_input("Stop", value=float(fd["stop"]))
            ca, cr = st.columns(2)
            if ca.button("➕ Alvo"): fd["parciais"].append({"pts": 0.0, "qtd": 1}); st.rerun()
            if cr.button("➖ Alvo"): fd["parciais"].pop(); st.rerun()
            upp = []
            for i, p in enumerate(fd["parciais"]):
                c1, c2 = st.columns(2); pp = c1.number_input(f"Pts {i+1}", value=float(p["pts"]), key=f"ap_{i}"); pq = c2.number_input(f"Qtd {i+1}", value=int(p["qtd"]), key=f"aq_{i}")
                upp.append({"pts": pp, "qtd": pq})
            if st.button("💾 SALVAR"):
                pay = {"nome": nn, "lote": nl, "stop": ns, "parciais": upp}
                if fd["id"]: supabase.table("atm_configs").update(pay).eq("id", fd["id"]).execute()
                else: supabase.table("atm_configs").insert(pay).execute()
                st.rerun()

    # --- 11. HISTÓRICO ---
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        df = load_trades_db()
        if not df.empty:
            df_h = df[df['usuario'] == USER]
            with st.expander("🔍 Filtros", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                fa = c1.multiselect("Ativo", ["NQ", "MNQ"])
                fr = c2.selectbox("Resultado", ["Todos", "Wins", "Losses"])
                fc = c3.multiselect("Contexto", list(df_h['contexto'].unique()))
                fg = c4.multiselect("Grupo", list(df_h['grupo_vinculo'].unique())) if ROLE in ["master", "admin"] else []
            
            if fa: df_h = df_h[df_h['ativo'].isin(fa)]
            if fc: df_h = df_h[df_h['contexto'].isin(fc)]
            if fg: df_h = df_h[df_h['grupo_vinculo'].isin(fg)]
            if fr == "Wins": df_h = df_h[df_h['resultado'] > 0]
            if fr == "Losses": df_h = df_h[df_h['resultado'] < 0]

            @st.dialog("Detalhes")
            def show_t(row):
                if row.get('prints'): st.image(row['prints'], use_container_width=True)
                st.write(f"📅 **{row['data']}** | {row['ativo']} | {row['grupo_vinculo']}")
                st.markdown(f"<h1 style='color:{'#00FF88' if row['resultado']>=0 else '#FF4B4B'}; text-align:center;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
                if st.button("🗑️ DELETAR"): supabase.table("trades").delete().eq("id", row['id']).execute(); st.rerun()

            cols = st.columns(4)
            for i, (idx, row) in enumerate(df_h.sort_values('created_at', ascending=False).iterrows()):
                with cols[i % 4]:
                    cls = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    img = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="height:100px; background:#222;"></div>'
                    st.markdown(f'<div class="trade-card"><div class="card-img-container">{img}</div><div class="card-title">{row["ativo"]} - {row["direcao"]}</div><div class="card-sub">{row["grupo_vinculo"]}</div><div class="{cls}">${row["resultado"]:,.2f}</div></div>', unsafe_allow_html=True)
                    if st.button("👁️", key=f"v_{row['id']}", use_container_width=True): show_t(row)

    # --- 12. GERENCIAR USUÁRIOS ---
    elif selected == "Gerenciar Usuários" and ROLE == "admin":
        st.title("👥 Gestão de Usuários")
        users = supabase.table("users").select("*").execute().data
        
        c1, c2 = st.columns([1, 1.5])
        with c2:
            for u in users:
                with st.container():
                    cc1, cc2, cc3 = st.columns([2, 2, 1])
                    cc1.write(f"👤 **{u['username']}**")
                    cc2.write(f"Cargo: `{u.get('role', 'user')}`")
                    if cc3.button("🗑️", key=f"du_{u['id']}"): supabase.table("users").delete().eq("id", u['id']).execute(); st.rerun()
                    st.divider()
        with c1:
            st.subheader("Novo / Editar")
            nu = st.text_input("User"); np = st.text_input("Pass", type="password")
            nr = st.selectbox("Cargo", ["user", "master", "admin"])
            if st.button("Salvar"):
                supabase.table("users").insert({"username": nu, "password": np, "role": nr}).execute()
                st.success("Salvo!"); st.rerun()
