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

# --- CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    /* Cards do Histórico */
    .trade-card {
        background-color: #161616;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 15px;
        border: 1px solid #333;
        transition: transform 0.2s, border-color 0.2s;
    }
    .trade-card:hover {
        transform: translateY(-3px);
        border-color: #B20000;
    }
    .card-img-container {
        width: 100%; height: 140px; background-color: #222;
        border-radius: 5px; overflow: hidden; display: flex;
        align-items: center; justify-content: center; margin-bottom: 10px;
    }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 14px; font-weight: 700; color: white; margin-bottom: 2px; }
    .card-sub { font-size: 11px; color: #888; margin-bottom: 8px; }
    
    /* Cores de Resultado nos Cards (CORRIGIDO: Gain Verde) */
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }

    /* Métricas do Dashboard (FIXED HEIGHT) */
    .metric-container { 
        background-color: #161616; 
        border: 1px solid #262626; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center; 
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: border-color 0.3s, transform 0.3s;
        position: relative;
        min-height: 140px; 
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .metric-container:hover {
        border-color: #B20000;
        transform: translateY(-3px);
        cursor: help;
    }
    .metric-label { 
        color: #888; font-size: 11px; text-transform: uppercase; 
        letter-spacing: 1px; font-weight: 600; display: flex; 
        justify-content: center; align-items: center; gap: 5px;
    }
    .metric-value { color: white; font-size: 22px; font-weight: 800; margin-top: 5px; }
    .metric-sub { font-size: 12px; margin-top: 4px; color: #666; }
    
    .help-icon {
        color: #555; font-size: 12px; border: 1px solid #444;
        border-radius: 50%; width: 14px; height: 14px;
        display: inline-flex; align-items: center; justify-content: center;
    }

    /* Geral */
    [data-testid="stSidebar"] { background-color: #0F0F0F !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    
    .piscante-erro { 
        padding: 15px; border-radius: 5px; color: white; font-weight: bold; 
        text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000; 
    }
    .risco-alert {
        color: #FF4B4B; font-weight: bold; font-size: 16px; margin-top: 5px;
        background-color: rgba(255, 75, 75, 0.1); padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #FF4B4B;
    }
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
            else:
                st.session_state["password_correct"] = False
        except Exception as e:
            st.error(f"Erro de conexão: {e}")

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
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
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
            if st.session_state.get("password_correct") == False:
                st.error("😕 Credenciais incorretas.")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if check_password():
    # --- 4. CONSTANTES ---
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER_LOGGED = st.session_state["logged_user"]
    IS_ADMIN = (USER_LOGGED == "admin")

    # --- 5. FUNÇÕES DE DADOS ---
    def load_trades_db():
        try:
            res = supabase.table("trades").select("*").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.date
                df['created_at'] = pd.to_datetime(df['created_at'])
                if 'grupo_conta' not in df.columns: df['grupo_conta'] = 'Geral'
            return df
        except:
            return pd.DataFrame()

    def load_atms_db():
        try:
            res = supabase.table("atm_configs").select("*").execute()
            return {item['nome']: item for item in res.data}
        except:
            return {}

    def card_metric(label, value, sub_value="", color="white", help_text=""):
        sub_html = f'<div class="metric-sub">{sub_value}</div>' if sub_value else '<div class="metric-sub">&nbsp;</div>'
        help_html = f'<span class="help-icon" title="{help_text}">?</span>' if help_text else ""
        st.markdown(f"""
            <div class="metric-container" title="{help_text}">
                <div class="metric-label">{label} {help_html}</div>
                <div class="metric-value" style="color: {color};">{value}</div>
                {sub_html}
            </div>
        """, unsafe_allow_html=True)

    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        if IS_ADMIN: menu.append("Gerenciar Usuários")
        selected = option_menu(None, menu, icons=["grid", "currency-dollar", "gear", "clock", "people"], styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair / Logout"): 
            st.session_state.clear()
            st.rerun()

    # --- 7. ABA: DASHBOARD ---
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df_raw = load_trades_db()
        
        if not df_raw.empty:
            df = df_raw[df_raw['usuario'] == USER_LOGGED]
            
            if not df.empty:
                with st.expander("🔍 Filtros e Grupos", expanded=True):
                    col_d1, col_d2, col_grp, col_ctx = st.columns([1, 1, 1.5, 2])
                    
                    min_date = df['data'].min()
                    max_date = df['data'].max()
                    d_inicio = col_d1.date_input("Início", min_date)
                    d_fim = col_d2.date_input("Fim", max_date)
                    
                    # FILTRO DE GRUPO (SÓ ADMIN VÊ)
                    if IS_ADMIN:
                        grupos_disp = ["Todos"] + sorted(list(df['grupo_conta'].unique()))
                        sel_grupo = col_grp.selectbox("Grupo de Contas", grupos_disp)
                    else:
                        sel_grupo = "Todos"
                    
                    all_contexts = list(df['contexto'].unique())
                    filters_ctx = col_ctx.multiselect("Contextos", all_contexts, default=all_contexts)

                # Aplica Filtros
                mask = (df['data'] >= d_inicio) & (df['data'] <= d_fim) & (df['contexto'].isin(filters_ctx))
                if IS_ADMIN and sel_grupo != "Todos":
                    mask = mask & (df['grupo_conta'] == sel_grupo)
                
                df_filtered = df[mask].copy()

                if df_filtered.empty:
                    st.warning("⚠️ Nenhum trade encontrado.")
                else:
                    total_trades = len(df_filtered)
                    net_profit = df_filtered['resultado'].sum()
                    wins = df_filtered[df_filtered['resultado'] > 0]
                    losses = df_filtered[df_filtered['resultado'] < 0]
                    gross_profit = wins['resultado'].sum()
                    gross_loss = abs(losses['resultado'].sum())
                    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                    pf_str = f"{pf:.2f}" if gross_loss > 0 else "∞"
                    win_rate = (len(wins) / total_trades) * 100
                    avg_win = wins['resultado'].mean() if not wins.empty else 0
                    avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0
                    payoff = avg_win / avg_loss if avg_loss > 0 else 0
                    expectancy = ((win_rate/100) * avg_win) - ((len(losses)/total_trades) * avg_loss)
                    
                    df_filtered = df_filtered.sort_values('created_at')
                    df_filtered['equity'] = df_filtered['resultado'].cumsum()
                    df_filtered['peak'] = df_filtered['equity'].cummax()
                    max_dd = (df_filtered['equity'] - df_filtered['peak']).min()

                    st.markdown("##### 🏁 Desempenho Geral")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: card_metric("RESULTADO LÍQUIDO", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f}", "#00FF88" if net_profit >= 0 else "#FF4B4B")
                    with c2: card_metric("FATOR DE LUCRO", pf_str, "Ideal > 1.5", "#B20000")
                    with c3: card_metric("WIN RATE", f"{win_rate:.1f}%", f"{len(wins)}W / {len(losses)}L")
                    with c4: card_metric("EXPECTATIVA", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy > 0 else "#FF4B4B")
                    
                    st.markdown("##### 💲 Médias e Risco")
                    c5, c6, c7, c8 = st.columns(4)
                    with c5: card_metric("MÉDIA GAIN", f"${avg_win:,.2f}", "", "#00FF88")
                    with c6: card_metric("MÉDIA LOSS", f"-${avg_loss:,.2f}", "", "#FF4B4B")
                    with c7: card_metric("PAYOFF REAL", f"1 : {payoff:.2f}")
                    with c8: card_metric("DRAWDOWN MÁX", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B")

                    st.markdown("---")
                    g1, g2 = st.columns([2, 1])
                    with g1:
                        fig_eq = px.area(df_filtered, x='created_at', y='equity', title="📈 Curva de Patrimônio", template="plotly_dark")
                        fig_eq.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                        st.plotly_chart(fig_eq, use_container_width=True)
                    with g2:
                        ctx_perf = df_filtered.groupby('contexto')['resultado'].sum().reset_index()
                        fig_bar = px.bar(ctx_perf, x='contexto', y='resultado', title="📊 Por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                        st.plotly_chart(fig_bar, use_container_width=True)

            else: st.info("Sem operações registradas.")
        else: st.warning("Banco de dados vazio.")

    # --- 8. REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db()
        
        # SÓ ADMIN VÊ SELEÇÃO DE GRUPO
        if IS_ADMIN:
            grupo_sel = st.segmented_control("Selecionar Grupo de Contas", ["Grupo A", "Grupo B", "Grupo C", "Grupo D", "Geral"], default="Geral")
        else:
            grupo_sel = "Geral"

        st.divider()
        atm_sel = st.selectbox("🎯 Escolher Template ATM", ["Manual"] + list(atm_db.keys()))
        
        if atm_sel != "Manual":
            config = atm_db[atm_sel]
            lt_default, stp_default = int(config["lote"]), float(config["stop"])
            parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
        else:
            lt_default, stp_default, parciais_pre = 1, 0.0, []

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date())
            atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
        with f2:
            lt = st.number_input("Contratos Total", min_value=1, value=lt_default)
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_default, step=0.25)
            if stp > 0:
                risco_calc = stp * MULTIPLIERS[atv] * lt
                st.markdown(f'<div class="risco-alert">📉 Risco Estimado: ${risco_calc:,.2f}</div>', unsafe_allow_html=True)
            up = st.file_uploader("📸 Anexar Print", type=['png', 'jpg', 'jpeg'])

        with f3:
            st.write("**Saídas (Alocação)**")
            if "num_parciais" not in st.session_state or atm_sel != st.session_state.get("last_atm"):
                st.session_state.num_parciais = len(parciais_pre) if parciais_pre else 1
                st.session_state.last_atm = atm_sel

            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("➕ Add Parcial"): st.session_state.num_parciais += 1
            if col_btn2.button("🧹 Limpar"): st.session_state.num_parciais = 1; st.rerun()

            saidas, aloc = [], 0
            for i in range(st.session_state.num_parciais):
                c_pts, c_qtd = st.columns(2)
                val_pts = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
                val_qtd = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
                pts = c_pts.number_input(f"Pts Alvo {i+1}", value=val_pts, key=f"p_pts_{i}_{atm_sel}", step=0.25)
                qtd = c_qtd.number_input(f"Contratos {i+1}", value=val_qtd, key=f"p_qtd_{i}_{atm_sel}", min_value=0)
                saidas.append({"pts": pts, "qtd": qtd})
                aloc += qtd
            
            if lt != aloc:
                st.markdown(f'<div class="piscante-erro">DESEQUILÍBRIO: {lt - aloc} CTTS</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Posição Sincronizada")

        st.divider()
        col_gain, col_loss = st.columns(2)
        btn_registrar = False
        if col_gain.button("🟢 REGISTRAR GAIN", use_container_width=True, disabled=(lt != aloc)): btn_registrar = True
        if col_loss.button("🔴 REGISTRAR STOP FULL", use_container_width=True): saidas = [{"pts": -stp, "qtd": lt}]; btn_registrar = True

        if btn_registrar:
            with st.spinner("Salvando..."):
                try:
                    res_fin = sum([s["pts"] * MULTIPLIERS[atv] * s["qtd"] for s in saidas])
                    pt_med = sum([s["pts"] * s["qtd"] for s in saidas]) / lt
                    trade_id = str(uuid.uuid4())
                    img_url = ""
                    if up:
                        file_path = f"{trade_id}.png"
                        supabase.storage.from_("prints").upload(file_path, up.getvalue())
                        img_url = supabase.storage.from_("prints").get_public_url(file_path)

                    supabase.table("trades").insert({
                        "id": trade_id, "data": str(dt), "ativo": atv, "contexto": ctx,
                        "direcao": dr, "lote": lt, "resultado": res_fin, "pts_medio": pt_med,
                        "prints": img_url, "usuario": USER_LOGGED, "grupo_conta": grupo_sel,
                        "risco_fin": (stp * MULTIPLIERS[atv] * lt)
                    }).execute()
                    st.balloons()
                    st.success(f"✅ REGISTRADO NO {grupo_sel.upper()}!")
                    time.sleep(2); st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    # --- 9. CONFIGURAR ATM (Sem alterações, mantendo original) ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")
        if "atm_form_data" not in st.session_state:
            st.session_state.atm_form_data = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}

        def reset_atm_form():
            st.session_state.atm_form_data = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}

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
                        if c_edit.button("✏️", key=f"edit_{item['id']}"):
                            p_data = item['parciais'] if isinstance(item['parciais'], list) else json.loads(item['parciais'])
                            st.session_state.atm_form_data = {"id": item['id'], "nome": item['nome'], "lote": item['lote'], "stop": item['stop'], "parciais": p_data}
                            st.rerun()
                        if c_del.button("🗑️", key=f"del_{item['id']}"):
                            supabase.table("atm_configs").delete().eq("id", item['id']).execute()
                            st.rerun()

        with c_form:
            form_data = st.session_state.atm_form_data
            new_nome = st.text_input("Nome", value=form_data["nome"])
            new_lote = st.number_input("Lote", value=int(form_data["lote"]))
            new_stop = st.number_input("Stop", value=float(form_data["stop"]))
            
            updated_partials = []
            for i, p in enumerate(form_data["parciais"]):
                c1, c2 = st.columns(2)
                p_pts = c1.number_input(f"Alvo {i+1}", value=float(p["pts"]), key=f"edm_pts_{i}")
                p_qtd = c2.number_input(f"Qtd {i+1}", value=int(p["qtd"]), key=f"edm_qtd_{i}")
                updated_partials.append({"pts": p_pts, "qtd": p_qtd})
            
            if st.button("💾 SALVAR"):
                payload = {"nome": new_nome, "lote": new_lote, "stop": new_stop, "parciais": updated_partials}
                if form_data["id"]: supabase.table("atm_configs").update(payload).eq("id", form_data["id"]).execute()
                else: supabase.table("atm_configs").insert(payload).execute()
                reset_atm_form(); st.rerun()

    # --- 10. HISTÓRICO ---
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        df = load_trades_db()
        if not df.empty:
            df_h = df[df['usuario'] == USER_LOGGED]
            c_f1, c_f2, c_f3 = st.columns(3)
            filtro_ativo = c_f1.multiselect("Ativo", ["NQ", "MNQ"])
            filtro_res = c_f2.selectbox("Resultado", ["Todos", "Wins", "Losses"])
            # ADICIONADO FILTRO DE GRUPO NO HISTÓRICO
            filtro_grupo_h = c_f3.multiselect("Filtrar Grupos", sorted(list(df_h['grupo_conta'].unique())))

            if filtro_ativo: df_h = df_h[df_h['ativo'].isin(filtro_ativo)]
            if filtro_grupo_h: df_h = df_h[df_h['grupo_conta'].isin(filtro_grupo_h)]
            if filtro_res == "Wins": df_h = df_h[df_h['resultado'] > 0]
            if filtro_res == "Losses": df_h = df_h[df_h['resultado'] < 0]
            
            df_h = df_h.sort_values('created_at', ascending=False)
            
            @st.dialog("Detalhes da Operação", width="large")
            def show_trade_details(row):
                if row.get('prints'): st.image(row['prints'], use_container_width=True)
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.write(f"📅 **Data:** {row['data']}")
                c1.write(f"📈 **Grupo:** {row['grupo_conta']}")
                c2.write(f"⚖️ **Lote:** {row['lote']}")
                c2.write(f"🎯 **Médio:** {row['pts_medio']:.2f} pts")
                res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
                st.markdown(f"<h1 style='color:{res_c}; text-align:center;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
                if st.button("🗑️ DELETAR REGISTRO", type="primary"):
                    supabase.table("trades").delete().eq("id", row['id']).execute()
                    st.rerun()

            cols = st.columns(4)
            for i, (index, row) in enumerate(df_h.iterrows()):
                with cols[i % 4]:
                    res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    img_html = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="height:140px; background:#333; display:flex; align-items:center; justify-content:center;">Sem Foto</div>'
                    st.markdown(f"""
                        <div class="trade-card">
                            <div class="card-img-container">{img_html}</div>
                            <div class="card-title">{row['ativo']} - {row['grupo_conta']}</div>
                            <div class="card-sub">{row['data']} • {row['contexto']}</div>
                            <div class="{res_class}">${row['resultado']:,.2f}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("👁️ Ver", key=f"btn_{row['id']}", use_container_width=True): show_trade_details(row)

    # --- 11. GERENCIAR USUÁRIOS (Sem alterações) ---
    elif selected == "Gerenciar Usuários":
        st.title("👥 Gestão de Usuários")
        res = supabase.table("users").select("*").execute()
        users_list = res.data
        for u in users_list:
            st.write(f"👤 {u['username']}")
            st.divider()
