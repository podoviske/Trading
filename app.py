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

# --- CSS CUSTOMIZADO (MANTIDO) ---
st.markdown("""
    <style>
    .trade-card {
        background-color: #161616; border-radius: 8px; padding: 12px; margin-bottom: 15px; border: 1px solid #333; transition: transform 0.2s, border-color 0.2s;
    }
    .trade-card:hover { transform: translateY(-3px); border-color: #B20000; }
    .card-img-container {
        width: 100%; height: 140px; background-color: #222; border-radius: 5px; overflow: hidden; display: flex; align-items: center; justify-content: center; margin-bottom: 10px;
    }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 14px; font-weight: 700; color: white; margin-bottom: 2px; }
    .card-sub { font-size: 11px; color: #888; margin-bottom: 8px; }
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }
    .metric-container { 
        background-color: #161616; border: 1px solid #262626; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: border-color 0.3s, transform 0.3s; position: relative; min-height: 140px; display: flex; flex-direction: column; justify-content: center; align-items: center;
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

# --- 3. SISTEMA DE LOGIN COM ROLES ---
def check_password():
    def password_entered():
        u = st.session_state.get("username_input")
        p = st.session_state.get("password_input")
        try:
            res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data:
                st.session_state["password_correct"] = True
                st.session_state["logged_user"] = u
                # Salva o cargo (role) do usuário na sessão
                st.session_state["user_role"] = res.data[0].get('role', 'user')
            else:
                st.session_state["password_correct"] = False
        except Exception as e:
            st.error(f"Erro de conexão: {e}")

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.markdown('<div class="login-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div>', unsafe_allow_html=True)
            st.write("---")
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
            if st.session_state.get("password_correct") == False:
                st.error("😕 Credenciais incorretas.")
        return False
    return True

if check_password():
    # --- CONSTANTES ---
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER_ROLE = st.session_state.get("user_role", 'user')
    LOGGED_USER = st.session_state["logged_user"]

    # --- FUNÇÕES DE DADOS ---
    def load_trades_db():
        try:
            res = supabase.table("trades").select("*").eq("usuario", LOGGED_USER).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.date
                df['created_at'] = pd.to_datetime(df['created_at'])
                if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
            return df
        except: return pd.DataFrame()

    def load_atms_db():
        try:
            res = supabase.table("atm_configs").select("*").execute()
            return {item['nome']: item for item in res.data}
        except: return {}

    def load_contas_config():
        try:
            res = supabase.table("contas_config").select("*").eq("usuario", LOGGED_USER).execute()
            return pd.DataFrame(res.data)
        except: return pd.DataFrame()

    def card_metric(label, value, sub_value="", color="white", help_text=""):
        sub_html = f'<div class="metric-sub">{sub_value}</div>' if sub_value else '<div class="metric-sub">&nbsp;</div>'
        help_html = f'<span class="help-icon" title="{help_text}">?</span>' if help_text else ""
        st.markdown(f'<div class="metric-container" title="{help_text}"><div class="metric-label">{label} {help_html}</div><div class="metric-value" style="color: {color};">{value}</div>{sub_html}</div>', unsafe_allow_html=True)

    # --- 6. SIDEBAR COM HIERARQUIA ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        
        # Define itens do menu baseado no cargo
        menu_items = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        menu_icons = ["grid", "currency-dollar", "gear", "clock"]
        
        # MASTER e ADMIN veem aba de Contas
        if USER_ROLE in ['master', 'admin']:
            menu_items.insert(2, "Contas")
            menu_icons.insert(2, "briefcase")
            
        # Apenas ADMIN vê aba de Usuários
        if USER_ROLE == "admin":
            menu_items.append("Gerenciar Usuários")
            menu_icons.append("people")

        selected = option_menu(None, menu_items, icons=menu_icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair / Logout"): 
            st.session_state.clear()
            st.rerun()

    # --- 7. ABA: DASHBOARD ---
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df = load_trades_db()
        if not df.empty:
            with st.expander("🔍 Filtros Avançados", expanded=True):
                # MASTER e ADMIN veem filtro de Grupo
                if USER_ROLE in ['master', 'admin']:
                    col_d1, col_d2, col_grp, col_ctx = st.columns([1, 1, 1.2, 1.8])
                else:
                    col_d1, col_d2, col_ctx = st.columns([1, 1, 2])
                
                d_inicio = col_d1.date_input("Início", df['data'].min())
                d_fim = col_d2.date_input("Fim", df['data'].max())
                
                sel_grupo = "Todos"
                if USER_ROLE in ['master', 'admin']:
                    grps = ["Todos"] + sorted(list(df['grupo_vinculo'].unique()))
                    sel_grupo = col_grp.selectbox("Filtrar Grupo", grps)
                
                all_ctx = list(df['contexto'].unique())
                filters_ctx = col_ctx.multiselect("Contextos", all_ctx, default=all_ctx)

            mask = (df['data'] >= d_inicio) & (df['data'] <= d_fim) & (df['contexto'].isin(filters_ctx))
            if sel_grupo != "Todos": mask &= (df['grupo_vinculo'] == sel_grupo)
            df_f = df[mask].copy()

            if not df_f.empty:
                # KPIs (Cálculos originais mantidos)
                total_trades = len(df_f)
                net_profit = df_f['resultado'].sum()
                wins = df_f[df_f['resultado'] > 0]
                losses = df_f[df_f['resultado'] < 0]
                pf = (wins['resultado'].sum() / abs(losses['resultado'].sum())) if not losses.empty else float('inf')
                wr = (len(wins) / total_trades) * 100
                
                st.markdown("##### 🏁 Desempenho Geral")
                c1, c2, c3, c4 = st.columns(4)
                with c1: card_metric("RESULTADO LÍQUIDO", f"${net_profit:,.2f}", f"Bruto: ${wins['resultado'].sum():,.0f}", "#00FF88" if net_profit >= 0 else "#FF4B4B")
                with c2: card_metric("FATOR DE LUCRO", f"{pf:.2f}" if pf != float('inf') else "∞", "Ideal > 1.5", "#B20000")
                with c3: card_metric("WIN RATE", f"{wr:.1f}%", f"{len(wins)} W / {len(losses)} L")
                with c4: card_metric("TOTAL TRADES", str(total_trades))

                df_f = df_f.sort_values('created_at')
                df_f['equity'] = df_f['resultado'].cumsum()
                fig_eq = px.area(df_f, x='created_at', y='equity', title="📈 Curva de Patrimônio", template="plotly_dark")
                fig_eq.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                st.plotly_chart(fig_eq, use_container_width=True)
            else: st.warning("Sem dados.")
        else: st.info("Nenhum trade registrado.")

    # --- 8. REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db()
        df_contas = load_contas_config()
        
        atm_sel = st.selectbox("🎯 Escolher Template ATM", ["Manual"] + list(atm_db.keys()))
        if atm_sel != "Manual":
            config = atm_db[atm_sel]
            lt_def, stp_def = int(config["lote"]), float(config["stop"])
            parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
        else: lt_def, stp_def, parciais_pre = 1, 0.0, []

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date())
            atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
            
            # MASTER/ADMIN seleciona Grupo
            grupo_sel = "Geral"
            if USER_ROLE in ['master', 'admin'] and not df_contas.empty:
                grupo_sel = st.selectbox("🎯 Vincular ao Grupo", sorted(list(df_contas['grupo_nome'].unique())))

        with f2:
            lt = st.number_input("Contratos Total", min_value=1, value=lt_def)
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_def, step=0.25)
            if stp > 0: st.markdown(f'<div class="risco-alert">📉 Risco: ${stp * MULTIPLIERS[atv] * lt:,.2f}</div>', unsafe_allow_html=True)
            up = st.file_uploader("📸 Print", type=['png', 'jpg', 'jpeg'])

        with f3:
            st.write("**Saídas (Alocação)**")
            if "num_parciais" not in st.session_state or atm_sel != st.session_state.get("last_atm"):
                st.session_state.num_parciais = len(parciais_pre) if parciais_pre else 1
                st.session_state.last_atm = atm_sel
            
            cb1, cb2 = st.columns(2)
            if cb1.button("➕ Add Parcial"): st.session_state.num_parciais += 1
            if cb2.button("🧹 Limpar"): st.session_state.num_parciais = 1; st.rerun()

            saidas, aloc = [], 0
            for i in range(st.session_state.num_parciais):
                cc1, cc2 = st.columns(2)
                v_pts = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
                v_qtd = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
                pts = cc1.number_input(f"Pts {i+1}", value=v_pts, key=f"p_pts_{i}"); qtd = cc2.number_input(f"Qtd {i+1}", value=v_qtd, key=f"p_qtd_{i}")
                saidas.append({"pts": pts, "qtd": qtd}); aloc += qtd
            if lt != aloc: st.markdown(f'<div class="piscante-erro">SALDO: {lt - aloc} CTTS</div>', unsafe_allow_html=True)

        if st.button("💾 REGISTRAR TRADE", use_container_width=True, disabled=(lt != aloc)):
            res_fin = sum([s["pts"] * MULTIPLIERS[atv] * s["qtd"] for s in saidas])
            pt_med = sum([s["pts"] * s["qtd"] for s in saidas]) / lt
            t_id = str(uuid.uuid4()); img_url = ""
            if up:
                supabase.storage.from_("prints").upload(f"{t_id}.png", up.getvalue())
                img_url = supabase.storage.from_("prints").get_public_url(f"{t_id}.png")
            supabase.table("trades").insert({
                "id": t_id, "data": str(dt), "ativo": atv, "contexto": ctx, "direcao": dr, "lote": lt, "resultado": res_fin, "pts_medio": pt_med, "prints": img_url, "usuario": LOGGED_USER, "grupo_vinculo": grupo_sel
            }).execute()
            st.balloons(); time.sleep(1); st.rerun()

    # --- 9. ABA: CONTAS (MASTER/ADMIN) ---
    elif selected == "Contas":
        st.title("💼 Gestão de Grupos e Contas")
        df_c = load_contas_config()
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("⚙️ Cadastrar Grupo")
            with st.form("f_contas"):
                gn = st.text_input("Nome do Grupo (Ex: Mesa Apex)")
                ci = st.text_input("Número da Conta")
                if st.form_submit_button("Salvar"):
                    supabase.table("contas_config").insert({"usuario": LOGGED_USER, "grupo_nome": gn, "conta_identificador": ci}).execute()
                    st.success("Salvo!"); st.rerun()
        with c2:
            st.subheader("📋 Seus Grupos")
            if not df_c.empty:
                for grupo in df_c['grupo_nome'].unique():
                    with st.expander(f"📂 {grupo}"):
                        for _, row in df_c[df_c['grupo_nome'] == grupo].iterrows():
                            st.write(f"💳 {row['conta_identificador']}")

    # --- 10. ABA: HISTÓRICO ---
    elif selected == "Histórico":
        st.title("📜 Histórico de Trades")
        df = load_trades_db()
        if not df.empty:
            if USER_ROLE in ['master', 'admin']:
                f_grp = st.multiselect("Filtrar Grupos", sorted(list(df['grupo_vinculo'].unique())))
                if f_grp: df = df[df['grupo_vinculo'].isin(f_grp)]
            
            for _, row in df.sort_values('created_at', ascending=False).iterrows():
                with st.container():
                    st.write(f"**{row['data']}** | {row['ativo']} | {row['grupo_vinculo']}")
                    st.divider()

    # --- 11. ABA: GERENCIAR USUÁRIOS (SÓ ADMIN) ---
    elif selected == "Gerenciar Usuários" and USER_ROLE == "admin":
        st.title("👥 Gestão de Usuários")
        res = supabase.table("users").select("*").execute()
        for u in res.data:
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f"👤 {u['username']}")
            new_role = c2.selectbox("Cargo", ["user", "master", "admin"], index=["user", "master", "admin"].index(u.get('role', 'user')), key=f"role_{u['id']}")
            if c3.button("Atualizar", key=f"btn_{u['id']}"):
                supabase.table("users").update({"role": new_role}).eq("id", u['id']).execute()
                st.toast("Atualizado!")
