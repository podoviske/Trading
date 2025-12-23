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
    .trade-card { background-color: #161616; border-radius: 8px; padding: 12px; margin-bottom: 15px; border: 1px solid #333; transition: transform 0.2s, border-color 0.2s; }
    .trade-card:hover { transform: translateY(-3px); border-color: #B20000; }
    .card-img-container { width: 100%; height: 140px; background-color: #222; border-radius: 5px; overflow: hidden; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 14px; font-weight: 700; color: white; margin-bottom: 2px; }
    .card-sub { font-size: 11px; color: #888; margin-bottom: 8px; }
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }
    .metric-container { background-color: #161616; border: 1px solid #262626; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: border-color 0.3s, transform 0.3s; position: relative; min-height: 140px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
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

# --- 3. LOGIN ---
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

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.markdown('<div style="text-align:center;"><div style="color:#B20000; font-size:50px; font-weight:900;">EVO</div><div style="color:white; font-size:35px; font-weight:700; margin-top:-15px;">TRADE</div></div>', unsafe_allow_html=True)
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
        return False
    return True

if check_password():
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER = st.session_state["logged_user"]
    ROLE = st.session_state.get("user_role", "user")

    def load_trades_db():
        res = supabase.table("trades").select("*").eq("usuario", USER).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['created_at'] = pd.to_datetime(df['created_at'])
            if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
        return df

    def load_contas_config():
        res = supabase.table("contas_config").select("*").eq("usuario", USER).execute()
        return pd.DataFrame(res.data)

    def load_atms_db():
        res = supabase.table("atm_configs").select("*").execute()
        return {item['nome']: item for item in res.data}

    def card_metric(label, value, sub_value="", color="white", help_text=""):
        sub_html = f'<div class="metric-sub">{sub_value}</div>' if sub_value else '<div class="metric-sub">&nbsp;</div>'
        help_html = f'<span class="help-icon" title="{help_text}">?</span>' if help_text else ""
        st.markdown(f'<div class="metric-container" title="{help_text}"><div class="metric-label">{label} {help_html}</div><div class="metric-value" style="color: {color};">{value}</div>{sub_html}</div>', unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        icons = ["grid", "currency-dollar", "gear", "clock"]
        if ROLE in ["master", "admin"]: menu.insert(2, "Contas"); icons.insert(2, "briefcase")
        if ROLE == "admin": menu.append("Gerenciar Usuários"); icons.append("people")
        selected = option_menu(None, menu, icons=icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair / Logout"): st.session_state.clear(); st.rerun()

    # --- DASHBOARD (RESTAURADO 100%) ---
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df_raw = load_trades_db()
        if not df_raw.empty:
            with st.expander("🔍 Filtros Avançados", expanded=True):
                if ROLE in ["master", "admin"]:
                    col_d1, col_d2, col_grp, col_ctx = st.columns([1, 1, 1.2, 1.8])
                    sel_grupo = col_grp.selectbox("Filtrar Grupo", ["Todos"] + sorted(list(df_raw['grupo_vinculo'].unique())))
                else:
                    col_d1, col_d2, col_ctx = st.columns([1, 1, 2])
                    sel_grupo = "Todos"
                d_inicio = col_d1.date_input("Data Início", df_raw['data'].min())
                d_fim = col_d2.date_input("Data Fim", df_raw['data'].max())
                all_contexts = list(df_raw['contexto'].unique())
                filters_ctx = col_ctx.multiselect("Filtrar Contextos", all_contexts, default=all_contexts)

            mask = (df_raw['data'] >= d_inicio) & (df_raw['data'] <= d_fim) & (df_raw['contexto'].isin(filters_ctx))
            if sel_grupo != "Todos": mask &= (df_raw['grupo_vinculo'] == sel_grupo)
            df_f = df_raw[mask].copy()

            if not df_f.empty:
                # CÁLCULOS TÉCNICOS RESTAURADOS
                total_trades = len(df_f); net_profit = df_f['resultado'].sum()
                wins = df_f[df_f['resultado'] > 0]; losses = df_f[df_f['resultado'] < 0]
                gross_profit = wins['resultado'].sum(); gross_loss = abs(losses['resultado'].sum())
                pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                win_rate = (len(wins) / total_trades) * 100
                avg_win = wins['resultado'].mean() if not wins.empty else 0
                avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0
                payoff = avg_win / avg_loss if avg_loss > 0 else 0
                expectancy = ((win_rate/100) * avg_win) - ((len(losses)/total_trades) * avg_loss)
                df_f = df_f.sort_values('created_at')
                df_f['equity'] = df_f['resultado'].cumsum(); df_f['peak'] = df_f['equity'].cummax()
                df_f['drawdown'] = df_f['equity'] - df_f['peak']; max_dd = df_f['drawdown'].min()

                st.markdown("##### 🏁 Desempenho Geral")
                c1, c2, c3, c4 = st.columns(4)
                with c1: card_metric("RESULTADO LÍQUIDO", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f} / -${gross_loss:,.0f}", "#00FF88" if net_profit >= 0 else "#FF4B4B", "Resultado financeiro total.")
                with c2: card_metric("FATOR DE LUCRO (PF)", f"{pf:.2f}" if pf != float('inf') else "∞", "Ideal > 1.5", "#B20000", "Relação Lucro Bruto / Prejuízo Bruto.")
                with c3: card_metric("WIN RATE", f"{win_rate:.1f}%", f"{len(wins)} Wins / {len(losses)} Loss", "white", "Taxa de acerto.")
                with c4: card_metric("EXPECTATIVA MAT.", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy > 0 else "#FF4B4B", "Valor esperado por operação.")

                st.markdown("##### 💲 Médias & Risco")
                c5, c6, c7, c8 = st.columns(4)
                with c5: card_metric("MÉDIA GAIN ($)", f"${avg_win:,.2f}", "", "#00FF88")
                with c6: card_metric("MÉDIA LOSS ($)", f"-${avg_loss:,.2f}", "", "#FF4B4B")
                with c7: card_metric("RISCO : RETORNO", f"1 : {payoff:.2f}", "Payoff Real", "white")
                with c8: card_metric("DRAWDOWN MÁXIMO", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B")

                st.markdown("---")
                g1, g2 = st.columns([2, 1])
                with g1:
                    view_mode = st.radio("Visualizar Curva por:", ["Sequência de Trades", "Data (Tempo)"], horizontal=True, label_visibility="collapsed")
                    x_axis = 'data' if view_mode == "Data (Tempo)" else range(1, len(df_f)+1)
                    fig_eq = px.area(df_f, x=x_axis, y='equity', title="📈 Curva de Patrimônio", template="plotly_dark")
                    fig_eq.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                    st.plotly_chart(fig_eq, use_container_width=True)
                with g2:
                    ctx_perf = df_f.groupby('contexto')['resultado'].sum().reset_index()
                    st.plotly_chart(px.bar(ctx_perf, x='contexto', y='resultado', title="📊 Resultado por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"]), use_container_width=True)

    # --- REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db(); df_c = load_contas_config()
        atm_sel = st.selectbox("🎯 Escolher Template ATM", ["Manual"] + list(atm_db.keys()))
        if atm_sel != "Manual":
            config = atm_db[atm_sel]; lt_def, stp_def = int(config["lote"]), float(config["stop"])
            parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
        else: lt_def, stp_def, parciais_pre = 1, 0.0, []

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date()); atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True); ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
            grupo_sel = st.selectbox("Vincular ao Grupo", sorted(df_c['grupo_nome'].unique())) if ROLE in ["master", "admin"] and not df_c.empty else "Geral"
        with f2:
            lt = st.number_input("Contratos Total", min_value=1, value=lt_def)
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_def, step=0.25)
            if stp > 0: st.markdown(f'<div class="risco-alert">📉 Risco Estimado: ${stp * MULTIPLIERS[atv] * lt:,.2f}</div>', unsafe_allow_html=True)
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
                pts = c_pts.number_input(f"Pts Alvo {i+1}", value=v_pts, key=f"p_pts_{i}"); qtd = c_qtd.number_input(f"Contratos {i+1}", value=v_qtd, key=f"p_qtd_{i}")
                saidas.append({"pts": pts, "qtd": qtd}); aloc += qtd
            if lt != aloc: st.markdown(f'<div class="piscante-erro">SALDO: {lt - aloc} CTTS</div>', unsafe_allow_html=True)

        col_g, col_l = st.columns(2); btn_reg = False
        if col_g.button("🟢 REGISTRAR GAIN", use_container_width=True, disabled=(lt!=aloc)): btn_reg = True
        if col_l.button("🔴 STOP FULL", use_container_width=True): saidas = [{"pts": -stp, "qtd": lt}]; btn_reg = True
        if btn_reg:
            res_fin = sum([s["pts"] * MULTIPLIERS[atv] * s["qtd"] for s in saidas]); pt_med = sum([s["pts"] * s["qtd"] for s in saidas]) / lt
            t_id = str(uuid.uuid4()); img_url = ""
            if up:
                supabase.storage.from_("prints").upload(f"{t_id}.png", up.getvalue())
                img_url = supabase.storage.from_("prints").get_public_url(f"{t_id}.png")
            supabase.table("trades").insert({"id": t_id, "data": str(dt), "ativo": atv, "contexto": ctx, "direcao": dr, "lote": lt, "resultado": res_fin, "pts_medio": pt_med, "prints": img_url, "usuario": USER, "grupo_vinculo": grupo_sel}).execute()
            st.balloons(); time.sleep(1); st.rerun()

    # --- ABA: CONTAS (MASTER/ADMIN) ---
    elif selected == "Contas":
        st.title("💼 Gestão de Portfólio")
        df_c = load_contas_config()
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("⚙️ Vincular Conta")
            with st.form("f_contas"):
                gn = st.text_input("Nome do Grupo (Ex: Grupo A)"); ci = st.text_input("Conta/Mesa")
                if st.form_submit_button("Salvar"):
                    supabase.table("contas_config").insert({"usuario": USER, "grupo_nome": gn, "conta_identificador": ci}).execute()
                    st.rerun()
        with c2:
            st.subheader("📋 Suas Mesas")
            for grupo in df_c['grupo_nome'].unique() if not df_c.empty else []:
                with st.expander(f"📂 {grupo}"):
                    for _, row in df_c[df_c['grupo_nome'] == grupo].iterrows():
                        cc1, cc2 = st.columns([3, 1])
                        cc1.write(f"💳 {row['conta_identificador']}")
                        if cc2.button("🗑️", key=f"del_c_{row['id']}"): supabase.table("contas_config").delete().eq("id", row['id']).execute(); st.rerun()

    # --- ABA: CONFIGURAR ATM (RESTAURADO) ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")
        if "atm_f_d" not in st.session_state: st.session_state.atm_f_d = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        res = supabase.table("atm_configs").select("*").order("nome").execute(); e_atms = res.data
        c_f, c_l = st.columns([1.5, 1])
        with c_l:
            st.subheader("📋 Salvas")
            if st.button("✨ Criar Nova"): st.session_state.atm_f_d = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}; st.rerun()
            for it in e_atms:
                with st.expander(f"📍 {it['nome']}"):
                    ce, cd = st.columns(2)
                    if ce.button("✏️", key=f"ed_{it['id']}"):
                        p_d = it['parciais'] if isinstance(it['parciais'], list) else json.loads(it['parciais'])
                        st.session_state.atm_f_d = {"id": it['id'], "nome": it['nome'], "lote": it['lote'], "stop": it['stop'], "parciais": p_d}; st.rerun()
                    if cd.button("🗑️", key=f"dl_{it['id']}"): supabase.table("atm_configs").delete().eq("id", it['id']).execute(); st.rerun()
        with c_f:
            fd = st.session_state.atm_f_d; nn = st.text_input("Nome", value=fd["nome"])
            nl = st.number_input("Lote", value=int(fd["lote"])); ns = st.number_input("Stop", value=float(fd["stop"]))
            st.write("🎯 Alvos"); c_add, c_rem = st.columns([1, 4])
            if c_add.button("➕ Adicionar Alvo"): fd["parciais"].append({"pts": 0.0, "qtd": 1}); st.rerun()
            if c_rem.button("➖ Remover") and len(fd["parciais"]) > 1: fd["parciais"].pop(); st.rerun()
            up_p = []
            for i, p in enumerate(fd["parciais"]):
                cc1, cc2 = st.columns(2); pp = cc1.number_input(f"Alvo {i+1}", value=float(p["pts"]), key=f"ae_p_{i}"); pq = cc2.number_input(f"Qtd {i+1}", value=int(p["qtd"]), key=f"ae_q_{i}")
                up_p.append({"pts": pp, "qtd": pq})
            if st.button("💾 SALVAR"):
                pay = {"nome": nn, "lote": nl, "stop": ns, "parciais": up_p}
                if fd["id"]: supabase.table("atm_configs").update(pay).eq("id", fd["id"]).execute()
                else: supabase.table("atm_configs").insert(pay).execute()
                st.rerun()

    # --- ABA: HISTÓRICO (RESTAURADO 100%) ---
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        df_h = load_trades_db()
        if not df_h.empty:
            cf1, cf2, cf3, cf4 = st.columns(4)
            f_atv = cf1.multiselect("Filtrar Ativo", ["NQ", "MNQ"])
            f_res = cf2.selectbox("Filtrar Resultado", ["Todos", "Wins", "Losses"])
            f_ctx = cf3.multiselect("Filtrar Contexto", sorted(df_h['contexto'].unique()))
            f_grp = cf4.multiselect("Filtrar Grupo", sorted(df_h['grupo_vinculo'].unique())) if ROLE in ["master", "admin"] else []

            if f_atv: df_h = df_h[df_h['ativo'].isin(f_atv)]
            if f_ctx: df_h = df_h[df_h['contexto'].isin(f_ctx)]
            if f_grp: df_h = df_h[df_h['grupo_vinculo'].isin(f_grp)]
            if f_res == "Wins": df_h = df_h[df_h['resultado'] > 0]
            if f_res == "Losses": df_h = df_h[df_h['resultado'] < 0]

            @st.dialog("Detalhes", width="large")
            def show_trade(row):
                if row.get('prints'): st.image(row['prints'], use_container_width=True)
                st.write(f"📅 **{row['data']}** | {row['ativo']} | {row['grupo_vinculo']}")
                res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
                st.markdown(f"<h1 style='color:{res_c}; text-align:center;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
                if st.button("🗑️ DELETAR"): supabase.table("trades").delete().eq("id", row['id']).execute(); st.rerun()

            cols = st.columns(4)
            for i, (idx, row) in enumerate(df_h.sort_values('created_at', ascending=False).iterrows()):
                with cols[i % 4]:
                    res_cls = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    img_h = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="height:140px; background:#333; display:flex; align-items:center; justify-content:center;">Sem Foto</div>'
                    st.markdown(f'<div class="trade-card"><div class="card-img-container">{img_h}</div><div class="card-title">{row["ativo"]} - {row["direcao"]}</div><div class="card-sub">{row["data"]} • {row["grupo_vinculo"]}</div><div class="{res_cls}">${row["resultado"]:,.2f}</div></div>', unsafe_allow_html=True)
                    if st.button("👁️ Ver", key=f"btn_{row['id']}", use_container_width=True): show_trade(row)

    # --- ABA: GERENCIAR USUÁRIOS (SÓ ADMIN) ---
    elif selected == "Gerenciar Usuários" and ROLE == "admin":
        st.title("👥 Gestão Suprema")
        res = supabase.table("users").select("*").execute(); u_list = res.data
        for u in u_list:
            with st.container():
                cc1, cc2, cc3 = st.columns([2, 1, 1])
                cc1.write(f"👤 **{u['username']}** | Cargo: `{u.get('role', 'user')}`")
                nr = cc2.selectbox("Cargo", ["user", "master", "admin"], index=["user", "master", "admin"].index(u.get('role', 'user')), key=f"r_{u['id']}")
                if cc3.button("Atualizar", key=f"b_{u['id']}"): supabase.table("users").update({"role": nr}).eq("id", u['id']).execute(); st.rerun()
                st.divider()
