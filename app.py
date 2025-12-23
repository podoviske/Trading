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

# --- CSS CUSTOMIZADO (SEU ORIGINAL INTEGRAL) ---
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
    .metric-container { background-color: #161616; border: 1px solid #262626; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: border-color 0.3s; min-height: 140px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
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
                st.session_state["user_data"] = res.data[0]
            else: st.session_state["password_correct"] = False
        except Exception as e: st.error(f"Erro: {e}")

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.markdown('<div style="text-align:center;"><div style="color:#B20000; font-size:50px; font-weight:900;">EVO</div><div style="color:white; font-size:35px; font-weight:700; margin-top:-15px;">TRADE</div></div>', unsafe_allow_html=True)
            st.write("---")
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
        return False
    return True

if check_password():
    # --- CONSTANTES ---
    USER = st.session_state["logged_user"]
    USER_DATA = st.session_state["user_data"]
    IS_ADMIN = (USER == "admin")
    HAS_MULTICONTAS = USER_DATA.get("permitir_contas", False) or IS_ADMIN
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}

    # --- FUNÇÕES DE DADOS ---
    def load_trades_db():
        res = supabase.table("trades").select("*").eq("usuario", USER).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['created_at'] = pd.to_datetime(df['created_at'])
            if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
            if 'conta_vinculo' not in df.columns: df['conta_vinculo'] = 'Geral'
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
        menu_options = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        menu_icons = ["grid", "currency-dollar", "gear", "clock"]
        
        if HAS_MULTICONTAS:
            menu_options.insert(2, "Contas")
            menu_icons.insert(2, "briefcase")
        
        if IS_ADMIN:
            menu_options.append("Gerenciar Usuários")
            menu_icons.append("people")

        selected = option_menu(None, menu_options, icons=menu_icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair / Logout"): st.session_state.clear(); st.rerun()

    # --- ABA: CONTAS ---
    if selected == "Contas":
        st.title("💼 Gestão de Portfólio de Contas")
        col_c1, col_c2 = st.columns([1, 1.5])
        with col_c1:
            st.subheader("Cadastrar Nova Mesa/Conta")
            with st.form("cad_conta"):
                g_nome = st.text_input("Grupo (Ex: Grupo A, Apex, TakeProfit)")
                c_nome = st.text_input("ID da Conta (Ex: Apex-01, 50k-PRO)")
                if st.form_submit_button("Salvar Vínculo"):
                    supabase.table("contas_config").insert({"usuario": USER, "grupo_nome": g_nome, "conta_identificador": c_nome}).execute()
                    st.success("Conta cadastrada com sucesso!")
                    st.rerun()
        with col_c2:
            st.subheader("Estrutura Atual")
            df_c = load_contas_config()
            if not df_c.empty:
                for grupo in df_c['grupo_nome'].unique():
                    with st.expander(f"📁 {grupo}"):
                        for _, r in df_c[df_c['grupo_nome'] == grupo].iterrows():
                            cc1, cc2 = st.columns([3, 1])
                            cc1.write(f"💳 {r['conta_identificador']}")
                            if cc2.button("🗑️", key=f"del_c_{r['id']}"):
                                supabase.table("contas_config").delete().eq("id", r['id']).execute()
                                st.rerun()
            else: st.info("Nenhuma conta vinculada.")

    # --- ABA: DASHBOARD (SEU ORIGINAL + FILTRO GRUPOS) ---
    elif selected == "Dashboard":
        st.title("📊 Central de Controle")
        df_raw = load_trades_db()
        if not df_raw.empty:
            with st.expander("🔍 Filtros Avançados", expanded=True):
                c_d1, c_d2, c_grp, c_ctx = st.columns([1, 1, 1.2, 1.8])
                d_i = c_d1.date_input("Início", df_raw['data'].min())
                d_f = c_d2.date_input("Fim", df_raw['data'].max())
                
                # FILTRO DE GRUPO (IGUAL AO CONTEXTO)
                if HAS_MULTICONTAS:
                    opcoes_grupo = ["Todos"] + list(df_raw['grupo_vinculo'].unique())
                    sel_grp = c_grp.selectbox("Grupo de Contas", opcoes_grupo)
                else: sel_grp = "Todos"
                
                all_ctx = list(df_raw['contexto'].unique())
                sel_ctx = c_ctx.multiselect("Contextos", all_ctx, default=all_ctx)

            mask = (df_raw['data'] >= d_i) & (df_raw['data'] <= d_f) & (df_raw['contexto'].isin(sel_ctx))
            if sel_grp != "Todos": mask &= (df_raw['grupo_vinculo'] == sel_grp)
            df_f = df_raw[mask].copy()

            if not df_f.empty:
                # KPIs (SEUS CÁLCULOS ORIGINAIS)
                t_tr = len(df_f); net = df_f['resultado'].sum()
                wins = df_f[df_f['resultado'] > 0]; losses = df_f[df_f['resultado'] < 0]
                pf = (wins['resultado'].sum() / abs(losses['resultado'].sum())) if not losses.empty else float('inf')
                wr = (len(wins)/t_tr)*100
                avg_w = wins['resultado'].mean() if not wins.empty else 0
                avg_l = abs(losses['resultado'].mean()) if not losses.empty else 0
                payoff = avg_w / avg_l if avg_l > 0 else 0
                
                c1, c2, c3, c4 = st.columns(4)
                with c1: card_metric("RESULTADO LÍQUIDO", f"${net:,.2f}", f"Trades: {t_tr}", "#00FF88" if net >= 0 else "#FF4B4B")
                with c2: card_metric("FATOR DE LUCRO", f"{pf:.2f}" if pf != float('inf') else "∞", "Ideal > 1.5", "#B20000")
                with c3: card_metric("WIN RATE", f"{wr:.1f}%", f"{len(wins)}W / {len(losses)}L")
                with c4: card_metric("PAYOFF REAL", f"1 : {payoff:.2f}", "Risco:Retorno")

                st.markdown("---")
                df_f = df_f.sort_values('created_at')
                df_f['equity'] = df_f['resultado'].cumsum()
                fig = px.area(df_f, x='created_at', y='equity', title="📈 Curva de Patrimônio", template="plotly_dark")
                fig.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("Sem dados para estes filtros.")

    # --- ABA: REGISTRAR TRADE (SEU ORIGINAL + VÍNCULO) ---
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
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
            # VÍNCULO DE CONTA
            if HAS_MULTICONTAS and not df_c.empty:
                g_dest = st.selectbox("Grupo Destino", df_c['grupo_nome'].unique())
                c_dest = st.selectbox("Conta Destino", df_c[df_c['grupo_nome'] == g_dest]['conta_identificador'])
            else: g_dest, c_dest = "Geral", "Geral"

        with f2:
            lt = st.number_input("Contratos Total", min_value=1, value=lt_def)
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_def, step=0.25)
            if stp > 0: st.markdown(f'<div class="risco-alert">📉 Risco: ${stp * MULTIPLIERS[atv] * lt:,.2f}</div>', unsafe_allow_html=True)
            up = st.file_uploader("📸 Anexar Print", type=['png', 'jpg', 'jpeg'])

        with f3:
            st.write("**Saídas (Alocação)**")
            if "num_parciais" not in st.session_state or atm_sel != st.session_state.get("last_atm"):
                st.session_state.num_parciais = len(parciais_pre) if parciais_pre else 1
                st.session_state.last_atm = atm_sel
            c_b1, c_b2 = st.columns(2)
            if c_b1.button("➕ Add"): st.session_state.num_parciais += 1
            if c_b2.button("🧹 Limpar"): st.session_state.num_parciais = 1; st.rerun()
            saidas, aloc = [], 0
            for i in range(st.session_state.num_parciais):
                cc1, cc2 = st.columns(2)
                v_pts = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
                v_qtd = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
                pts = cc1.number_input(f"Pts {i+1}", value=v_pts, key=f"p_pts_{i}"); qtd = cc2.number_input(f"Qtd {i+1}", value=v_qtd, key=f"p_qtd_{i}")
                saidas.append({"pts": pts, "qtd": qtd}); aloc += qtd
            if lt != aloc: st.markdown(f'<div class="piscante-erro">SALDO: {lt - aloc} CTTS</div>', unsafe_allow_html=True)

        st.divider()
        col_g, col_l = st.columns(2)
        btn_reg = False
        if col_g.button("🟢 REGISTRAR GAIN", use_container_width=True, disabled=(lt!=aloc)): btn_reg = True
        if col_l.button("🔴 STOP FULL", use_container_width=True): saidas = [{"pts": -stp, "qtd": lt}]; btn_reg = True

        if btn_reg:
            res_fin = sum([s["pts"] * MULTIPLIERS[atv] * s["qtd"] for s in saidas])
            pt_med = sum([s["pts"] * s["qtd"] for s in saidas]) / lt
            t_id = str(uuid.uuid4()); img_url = ""
            if up:
                supabase.storage.from_("prints").upload(f"{t_id}.png", up.getvalue())
                img_url = supabase.storage.from_("prints").get_public_url(f"{t_id}.png")
            supabase.table("trades").insert({"id": t_id, "data": str(dt), "ativo": atv, "contexto": ctx, "direcao": dr, "lote": lt, "resultado": res_fin, "pts_medio": pt_med, "prints": img_url, "usuario": USER, "grupo_vinculo": g_dest, "conta_vinculo": c_dest}).execute()
            st.balloons(); time.sleep(1); st.rerun()

    # --- ABA: CONFIGURAR ATM (SEU ORIGINAL) ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")
        if "atm_form_data" not in st.session_state: st.session_state.atm_form_data = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        def reset_atm(): st.session_state.atm_form_data = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        res = supabase.table("atm_configs").select("*").order("nome").execute()
        e_atms = res.data
        c_f, c_l = st.columns([1.5, 1])
        with c_l:
            st.subheader("📋 Salvas")
            if st.button("✨ Criar Nova"): reset_atm(); st.rerun()
            for it in e_atms:
                with st.expander(f"📍 {it['nome']}"):
                    c_e, c_d = st.columns(2)
                    if c_e.button("✏️", key=f"e_{it['id']}"):
                        p_d = it['parciais'] if isinstance(it['parciais'], list) else json.loads(it['parciais'])
                        st.session_state.atm_form_data = {"id": it['id'], "nome": it['nome'], "lote": it['lote'], "stop": it['stop'], "parciais": p_d}; st.rerun()
                    if c_d.button("🗑️", key=f"d_{it['id']}"): supabase.table("atm_configs").delete().eq("id", it['id']).execute(); st.rerun()
        with c_f:
            f_d = st.session_state.atm_form_data; n_n = st.text_input("Nome", value=f_d["nome"])
            n_l = st.number_input("Lote", value=int(f_d["lote"])); n_s = st.number_input("Stop", value=float(f_d["stop"]))
            upd_p = []
            for i, p in enumerate(f_d["parciais"]):
                cc1, cc2 = st.columns(2); p_p = cc1.number_input(f"Alvo {i+1}", value=float(p["pts"]), key=f"ae_p_{i}"); p_q = cc2.number_input(f"Qtd {i+1}", value=int(p["qtd"]), key=f"ae_q_{i}")
                upd_p.append({"pts": p_p, "qtd": p_q})
            if st.button("💾 SALVAR ATM"):
                pay = {"nome": n_n, "lote": n_l, "stop": n_s, "parciais": upd_p}
                if f_d["id"]: supabase.table("atm_configs").update(pay).eq("id", f_d["id"]).execute()
                else: supabase.table("atm_configs").insert(pay).execute()
                reset_atm(); st.rerun()

    # --- ABA: HISTÓRICO (CARD ORIGINAL + FILTRO GRUPO) ---
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        df_h = load_trades_db()
        if not df_h.empty:
            df_h = df_h.sort_values('created_at', ascending=False)
            if HAS_MULTICONTAS:
                g_fil = st.multiselect("Filtrar Grupos", df_h['grupo_vinculo'].unique())
                if g_fil: df_h = df_h[df_h['grupo_vinculo'].isin(g_fil)]
            
            @st.dialog("Detalhes da Operação", width="large")
            def show_trade_details(row):
                if row.get('prints'): st.image(row['prints'], use_container_width=True)
                st.write(f"📅 **{row['data']}** | **Grupo:** {row['grupo_vinculo']} | **Conta:** {row['conta_vinculo']}")
                res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
                st.markdown(f"<h1 style='color:{res_c}; text-align:center;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
                if st.button("🗑️ DELETAR"): supabase.table("trades").delete().eq("id", row['id']).execute(); st.rerun()

            cols = st.columns(4)
            for i, (idx, row) in enumerate(df_h.iterrows()):
                with cols[i % 4]:
                    res_cls = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    img_h = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="height:140px; background:#333; display:flex; align-items:center; justify-content:center;">Sem Foto</div>'
                    st.markdown(f'<div class="trade-card"><div class="card-img-container">{img_h}</div><div class="card-title">{row["ativo"]} - {row["grupo_vinculo"]}</div><div class="card-sub">{row["data"]} • {row["contexto"]}</div><div class="{res_cls}">${row["resultado"]:,.2f}</div></div>', unsafe_allow_html=True)
                    if st.button("👁️ Ver", key=f"btn_{row['id']}", use_container_width=True): show_trade_details(row)

    # --- ABA: GERENCIAR USUÁRIOS (COM PERMISSÃO DE CONTAS) ---
    elif selected == "Gerenciar Usuários":
        st.title("👥 Gestão de Usuários")
        res = supabase.table("users").select("*").execute(); u_list = res.data
        for u in u_list:
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"👤 **{u['username']}**")
                p_c = c2.checkbox("Liberar Multicontas", value=u.get('permitir_contas', False), key=f"per_{u['id']}")
                if c3.button("Salvar", key=f"svu_{u['id']}"):
                    supabase.table("users").update({"permitir_contas": p_c}).eq("id", u['id']).execute()
                    st.toast("Permissão atualizada!")
                st.divider()
