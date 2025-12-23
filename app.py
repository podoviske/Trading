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
    st.error("Erro crítico: Chaves do Supabase não encontradas.")

# --- 2. CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="EvoTrade Terminal", layout="wide", page_icon="📈")

# --- CSS CUSTOMIZADO (INTEGRAL) ---
st.markdown("""
    <style>
    .trade-card { background-color: #161616; border-radius: 8px; padding: 12px; margin-bottom: 15px; border: 1px solid #333; transition: transform 0.2s; }
    .trade-card:hover { transform: translateY(-3px); border-color: #B20000; }
    .card-img-container { width: 100%; height: 140px; background-color: #222; border-radius: 5px; overflow: hidden; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 14px; font-weight: 700; color: white; }
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }
    .metric-container { background-color: #161616; border: 1px solid #262626; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); min-height: 140px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    .metric-label { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; display: flex; align-items: center; gap: 5px; }
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
        u, p = st.session_state.get("username_input"), st.session_state.get("password_input")
        res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
        if res.data:
            st.session_state["password_correct"] = True
            st.session_state["logged_user"] = u
            st.session_state["user_role"] = res.data[0].get('role', 'user')
        else: st.session_state["password_correct"] = False

    if not st.session_state.get("password_correct"):
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.markdown('<div style="text-align:center; padding: 20px;"><h1 style="color:#B20000; font-size:50px;">EVO</h1><h2 style="color:white; margin-top:-20px;">TRADE</h2></div>', unsafe_allow_html=True)
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
            if st.session_state.get("password_correct") == False: st.error("Credenciais inválidas.")
        return False
    return True

if check_password():
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER, ROLE = st.session_state["logged_user"], st.session_state.get("user_role", "user")

    def load_trades():
        res = supabase.table("trades").select("*").eq("usuario", USER).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['created_at'] = pd.to_datetime(df['created_at'])
            if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
        return df

    def card_metric(label, value, sub="", color="white", help_t=""):
        st.markdown(f'<div class="metric-container" title="{help_t}"><div class="metric-label">{label} <span class="help-icon">?</span></div><div class="metric-value" style="color:{color}">{value}</div><div class="metric-sub">{sub}</div></div>', unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        icons = ["grid", "currency-dollar", "gear", "clock"]
        if ROLE in ["master", "admin"]: menu.insert(2, "Contas"); icons.insert(2, "briefcase")
        if ROLE == "admin": menu.append("Gerenciar Usuários"); icons.append("people")
        selected = option_menu(None, menu, icons=icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Logout"): st.session_state.clear(); st.rerun()

    # --- DASHBOARD (METRICAS COMPLETAS) ---
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df = load_trades()
        if not df.empty:
            with st.expander("🔍 Filtros Avançados", expanded=True):
                c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1.8])
                d_i = c1.date_input("Início", df['data'].min())
                d_f = c2.date_input("Fim", df['data'].max())
                sel_grp = c3.selectbox("Filtrar Grupo", ["Todos"] + sorted(list(df['grupo_vinculo'].unique()))) if ROLE in ["master", "admin"] else "Todos"
                f_ctx = c4.multiselect("Contextos", list(df['contexto'].unique()), default=list(df['contexto'].unique()))

            mask = (df['data'] >= d_i) & (df['data'] <= d_f) & (df['contexto'].isin(f_ctx))
            if sel_grp != "Todos": mask &= (df['grupo_vinculo'] == sel_grp)
            df_f = df[mask].copy()

            if not df_f.empty:
                # CÁLCULOS
                wins, losses = df_f[df_f['resultado'] > 0], df_f[df_f['resultado'] < 0]
                t_tr, net = len(df_f), df_f['resultado'].sum()
                pf = (wins['resultado'].sum() / abs(losses['resultado'].sum())) if not losses.empty else float('inf')
                wr = (len(wins)/t_tr)*100
                avg_win, avg_loss = wins['resultado'].mean() if not wins.empty else 0, abs(losses['resultado'].mean()) if not losses.empty else 0
                payoff = avg_win/avg_loss if avg_loss > 0 else 0
                expectancy = ((wr/100)*avg_win) - ((len(losses)/t_tr)*avg_loss)
                df_f = df_f.sort_values('created_at')
                df_f['equity'] = df_f['resultado'].cumsum()
                max_dd = (df_f['equity'] - df_f['equity'].cummax()).min()

                st.markdown("##### 🏁 Geral")
                r1 = st.columns(4)
                with r1[0]: card_metric("RESULTADO LÍQUIDO", f"${net:,.2f}", f"Bruto: ${wins['resultado'].sum():,.0f}", "#00FF88" if net>=0 else "#FF4B4B")
                with r1[1]: card_metric("FATOR DE LUCRO", f"{pf:.2f}", "Ideal > 1.5", "#B20000")
                with r1[2]: card_metric("WIN RATE", f"{wr:.1f}%", f"{len(wins)}W / {len(losses)}L")
                with r1[3]: card_metric("EXPECTATIVA MAT.", f"${expectancy:.2f}", "Por Operação", "#00FF88" if expectancy>0 else "#FF4B4B")

                st.markdown("##### 💲 Financeiro & Risco")
                r2 = st.columns(4)
                with r2[0]: card_metric("MÉDIA GAIN ($)", f"${avg_win:,.2f}", "", "#00FF88")
                with r2[1]: card_metric("MÉDIA LOSS ($)", f"-${avg_loss:,.2f}", "", "#FF4B4B")
                with r2[2]: card_metric("RISCO : RETORNO", f"1 : {payoff:.2f}", "Payoff Real")
                with r2[3]: card_metric("DRAWDOWN MÁXIMO", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B")

                st.markdown("##### 🎯 Técnica")
                r3 = st.columns(4)
                with r3[0]: card_metric("PTS MÉDIOS (GAIN)", f"{wins['pts_medio'].mean():.2f} pts", "", "#00FF88")
                with r3[1]: card_metric("PTS MÉDIOS (LOSS)", f"{abs(losses['pts_medio'].mean()):.2f} pts", "", "#FF4B4B")
                with r3[2]: card_metric("LOTE MÉDIO", f"{df_f['lote'].mean():.1f}", "Contratos")
                with r3[3]: card_metric("TOTAL TRADES", str(t_tr), "Executados")

                st.divider()
                st.plotly_chart(px.area(df_f, x='created_at', y='equity', title="📈 Curva de Patrimônio", template="plotly_dark").update_traces(line_color='#B20000', fillcolor='rgba(178,0,0,0.2)'), use_container_width=True)
            else: st.warning("Nenhum trade encontrado.")

    # --- REGISTRAR TRADE (ATM FIX) ---
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = supabase.table("atm_configs").select("*").execute().data
        atm_dict = {item['nome']: item for item in atm_db}
        
        atm_sel = st.selectbox("🎯 Template ATM", ["Manual"] + list(atm_dict.keys()))
        
        if atm_sel != "Manual":
            config = atm_dict[atm_sel]
            lt_def, stp_def = int(config["lote"]), float(config["stop"])
            parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
        else: lt_def, stp_def, parciais_pre = 1, 0.0, []

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date()); atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
            df_c = supabase.table("contas_config").select("*").eq("usuario", USER).execute().data
            g_sel = st.selectbox("Vincular ao Grupo", [c['grupo_nome'] for c in df_c]) if (ROLE in ["master", "admin"] and df_c) else "Geral"
        with f2:
            lt = st.number_input("Contratos Total", min_value=1, value=lt_def)
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_def)
            up = st.file_uploader("📸 Print", type=['png', 'jpg'])
        with f3:
            st.write("**Saídas**")
            if "n_parc" not in st.session_state or st.session_state.get("last_atm_reg") != atm_sel:
                st.session_state.n_parc = len(parciais_pre) if parciais_pre else 1
                st.session_state.last_atm_reg = atm_sel

            saidas, aloc = [], 0
            for i in range(st.session_state.n_parc):
                c_p, c_q = st.columns(2)
                v_p = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
                v_q = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
                p = c_p.number_input(f"Pts {i+1}", value=v_p, key=f"r_p_{i}")
                q = c_q.number_input(f"Qtd {i+1}", value=v_q, key=f"r_q_{i}")
                saidas.append({"pts": p, "qtd": q}); aloc += q
            
            if lt != aloc: st.markdown(f'<div class="piscante-erro">SALDO: {lt - aloc} CTTS</div>', unsafe_allow_html=True)
            if st.button("💾 SALVAR TRADE", use_container_width=True, disabled=(lt!=aloc)):
                res_fin = sum([s["pts"] * MULTIPLIERS[atv] * s["qtd"] for s in saidas])
                pt_m = sum([s["pts"] * s["qtd"] for s in saidas]) / lt
                t_id = str(uuid.uuid4()); img_url = ""
                if up:
                    supabase.storage.from_("prints").upload(f"{t_id}.png", up.getvalue())
                    img_url = supabase.storage.from_("prints").get_public_url(f"{t_id}.png")
                supabase.table("trades").insert({"id": t_id, "data": str(dt), "ativo": atv, "contexto": ctx, "direcao": dr, "lote": lt, "resultado": res_fin, "pts_medio": pt_m, "prints": img_url, "usuario": USER, "grupo_vinculo": g_sel}).execute()
                st.balloons(); time.sleep(1); st.rerun()

    # --- CONFIGURAR ATM (RESTAURADO E BUG FIXED) ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")
        if "atm_edit" not in st.session_state: 
            st.session_state.atm_edit = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        
        e_atms = supabase.table("atm_configs").select("*").order("nome").execute().data
        c_f, c_l = st.columns([1.5, 1])
        
        with c_l:
            st.subheader("📋 Salvas")
            if st.button("✨ Nova ATM"): st.session_state.atm_edit = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}; st.rerun()
            for it in e_atms:
                with st.expander(f"📍 {it['nome']}"):
                    ce, cd = st.columns(2)
                    if ce.button("✏️", key=f"e_{it['id']}"):
                        st.session_state.atm_edit = {"id": it['id'], "nome": it['nome'], "lote": it['lote'], "stop": it['stop'], "parciais": it['parciais'] if isinstance(it['parciais'], list) else json.loads(it['parciais'])}
                        st.rerun()
                    if cd.button("🗑️", key=f"d_{it['id']}"): supabase.table("atm_configs").delete().eq("id", it['id']).execute(); st.rerun()

        with c_f:
            ae = st.session_state.atm_edit
            nn = st.text_input("Nome", value=ae["nome"]); nl = st.number_input("Lote", value=int(ae["lote"])); ns = st.number_input("Stop", value=float(ae["stop"]))
            st.write("🎯 Alvos")
            ca, cr = st.columns(2)
            if ca.button("➕ Adicionar"): ae["parciais"].append({"pts": 0.0, "qtd": 1}); st.rerun()
            if cr.button("➖ Remover") and len(ae["parciais"]) > 1: ae["parciais"].pop(); st.rerun()
            
            upd_p = []
            for i, p in enumerate(ae["parciais"]):
                cc1, cc2 = st.columns(2)
                upd_p.append({"pts": cc1.number_input(f"Pts {i+1}", value=float(p["pts"]), key=f"a_p_{i}"), "qtd": cc2.number_input(f"Qtd {i+1}", value=int(p["qtd"]), key=f"a_q_{i}")})
            
            if st.button("💾 SALVAR ATM"):
                pay = {"nome": nn, "lote": nl, "stop": ns, "parciais": upd_p}
                if ae["id"]: supabase.table("atm_configs").update(pay).eq("id", ae["id"]).execute()
                else: supabase.table("atm_configs").insert(pay).execute()
                st.rerun()

    # --- HISTÓRICO (RESTAURADO) ---
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        df_h = load_trades()
        if not df_h.empty:
            c_f = st.columns(4)
            f_atv = c_f[0].multiselect("Ativo", ["NQ", "MNQ"])
            f_res = c_f[1].selectbox("Resultado", ["Todos", "Wins", "Losses"])
            f_ctx = c_f[2].multiselect("Contexto", sorted(df_h['contexto'].unique()))
            f_grp = c_f[3].multiselect("Grupo", sorted(df_h['grupo_vinculo'].unique())) if ROLE in ["master", "admin"] else []

            if f_atv: df_h = df_h[df_h['ativo'].isin(f_atv)]
            if f_ctx: df_h = df_h[df_h['contexto'].isin(f_ctx)]
            if f_grp: df_h = df_h[df_h['grupo_vinculo'].isin(f_grp)]
            if f_res == "Wins": df_h = df_h[df_h['resultado'] > 0]
            if f_res == "Losses": df_h = df_h[df_h['resultado'] < 0]

            @st.dialog("Detalhes")
            def show_tr(row):
                if row.get('prints'): st.image(row['prints'], use_container_width=True)
                st.write(f"📅 **{row['data']}** | {row['ativo']} | {row['grupo_vinculo']}")
                res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
                st.markdown(f"<h1 style='color:{res_c}; text-align:center;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
                if st.button("🗑️ DELETAR"): supabase.table("trades").delete().eq("id", row['id']).execute(); st.rerun()

            cols = st.columns(4)
            for i, (idx, row) in enumerate(df_h.sort_values('created_at', ascending=False).iterrows()):
                with cols[i % 4]:
                    res_cls = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    img = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="height:140px; background:#333; display:flex; align-items:center; justify-content:center;">Sem Foto</div>'
                    st.markdown(f'<div class="trade-card"><div class="card-img-container">{img}</div><div class="card-title">{row["ativo"]} - {row["direcao"]}</div><div class="card-sub">{row["data"]} • {row["grupo_vinculo"]}</div><div class="{res_cls}">${row["resultado"]:,.2f}</div></div>', unsafe_allow_html=True)
                    if st.button("👁️ Ver", key=f"b_h_{row['id']}", use_container_width=True): show_tr(row)

    # --- CONTAS (SÓ MASTER/ADMIN) ---
    elif selected == "Contas":
        st.title("💼 Gestão de Portfólio")
        df_c = supabase.table("contas_config").select("*").eq("usuario", USER).execute().data
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("⚙️ Vincular")
            with st.form("f_c"):
                gn, ci = st.text_input("Grupo"), st.text_input("ID Conta")
                if st.form_submit_button("Salvar"):
                    supabase.table("contas_config").insert({"usuario": USER, "grupo_nome": gn, "conta_identificador": ci}).execute()
                    st.rerun()
        with c2:
            st.subheader("📋 Suas Mesas")
            for g in list(set([c['grupo_nome'] for c in df_c])) if df_c else []:
                with st.expander(f"📂 {g}"):
                    for c in [i for i in df_c if i['grupo_nome'] == g]:
                        cc1, cc2 = st.columns([3, 1])
                        cc1.write(f"💳 {c['conta_identificador']}")
                        if cc2.button("🗑️", key=f"d_c_{c['id']}"): supabase.table("contas_config").delete().eq("id", c['id']).execute(); st.rerun()

    # --- GERENCIAR USUÁRIOS (SÓ ADMIN) ---
    elif selected == "Gerenciar Usuários" and ROLE == "admin":
        st.title("👥 Gestão Suprema")
        users = supabase.table("users").select("*").execute().data
        for u in users:
            with st.container():
                cc1, cc2, cc3 = st.columns([2, 1, 1])
                cc1.write(f"👤 **{u['username']}** | Cargo: `{u.get('role', 'user')}`")
                nr = cc2.selectbox("Cargo", ["user", "master", "admin"], index=["user", "master", "admin"].index(u.get('role', 'user')), key=f"r_{u['id']}")
                if cc3.button("Atualizar", key=f"u_{u['id']}"): supabase.table("users").update({"role": nr}).eq("id", u['id']).execute(); st.rerun()
                st.divider()
