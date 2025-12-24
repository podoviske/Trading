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

# --- 1. SUPABASE CONNECTION ---
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Critical Error: Supabase keys not found in Secrets.")

# --- 2. PAGE CONFIGURATION ---
st.set_page_config(page_title="EvoTrade Terminal", layout="wide", page_icon="📈")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    /* History Cards */
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
    
    /* Result Colors in Cards */
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }

    /* Dashboard Metrics (FIXED HEIGHT) */
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
        min-height: 140px; /* Ensures uniform height */
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
    
    /* Help Icon */
    .help-icon {
        color: #555; font-size: 12px; border: 1px solid #444;
        border-radius: 50%; width: 14px; height: 14px;
        display: inline-flex; align-items: center; justify-content: center;
    }

    /* General */
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

# --- 3. LOGIN SYSTEM ---
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
            else:
                st.session_state["password_correct"] = False
        except Exception as e:
            st.error(f"Connection error: {e}")

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
            st.text_input("Username", key="username_input")
            st.text_input("Password", type="password", key="password_input")
            st.button("Access Terminal", on_click=password_entered, use_container_width=True)
            if st.session_state.get("password_correct") == False:
                st.error("😕 Incorrect credentials.")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if check_password():
    # --- 4. CONSTANTS AND USER ---
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER = st.session_state["logged_user"]
    ROLE = st.session_state.get("user_role", "user")

    # --- 5. DATA FUNCTIONS ---
    def load_trades_db():
        try:
            res = supabase.table("trades").select("*").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.date
                df['created_at'] = pd.to_datetime(df['created_at'])
                if 'grupo_vinculo' not in df.columns: 
                    df['grupo_vinculo'] = 'Geral'
            return df
        except:
            return pd.DataFrame()

    def load_atms_db():
        try:
            res = supabase.table("atm_configs").select("*").execute()
            return {item['nome']: item for item in res.data}
        except:
            return {}

    def load_contas_config():
        try:
            res = supabase.table("contas_config").select("*").eq("usuario", USER).execute()
            return pd.DataFrame(res.data)
        except:
            return pd.DataFrame()
            
    def load_grupos_config():
        try:
            res = supabase.table("grupos_config").select("*").eq("usuario", USER).execute()
            return pd.DataFrame(res.data)
        except:
            return pd.DataFrame()

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
        icons = ["grid", "currency-dollar", "gear", "clock"]
        
        if ROLE in ['master', 'admin']:
            menu.insert(2, "Contas")
            icons.insert(2, "briefcase")
            
        if ROLE == 'admin':
            menu.append("Gerenciar Usuários")
            icons.append("people")
            
        selected = option_menu(None, menu, icons=icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        
        if st.button("Logout / Sair"): 
            st.session_state.clear()
            st.rerun()

    # --- 7. TAB: DASHBOARD ---
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df_raw = load_trades_db()
        
        if not df_raw.empty:
            df = df_raw[df_raw['usuario'] == USER]
            
            if not df.empty:
                # --- FILTERS ---
                with st.expander("🔍 Filtros Avançados", expanded=True):
                    if ROLE in ['master', 'admin']:
                        col_d1, col_d2, col_grp, col_ctx = st.columns([1, 1, 1.2, 1.8])
                        
                        # Load unique groups
                        grupos_disp = ["Todos"] + sorted(list(df['grupo_vinculo'].unique()))
                        sel_grupo = col_grp.selectbox("Grupo de Contas", grupos_disp)
                    else:
                        col_d1, col_d2, col_ctx = st.columns([1, 1, 2])
                        sel_grupo = "Todos"
                    
                    min_date = df['data'].min()
                    max_date = df['data'].max()
                    d_inicio = col_d1.date_input("Data Início", min_date)
                    d_fim = col_d2.date_input("Data Fim", max_date)
                    
                    all_contexts = list(df['contexto'].unique())
                    filters_ctx = col_ctx.multiselect("Filtrar Contextos", all_contexts, default=all_contexts)

                # Apply Filters
                mask = (df['data'] >= d_inicio) & (df['data'] <= d_fim) & (df['contexto'].isin(filters_ctx))
                if sel_grupo != "Todos":
                    mask = mask & (df['grupo_vinculo'] == sel_grupo)
                
                df_filtered = df[mask].copy()

                if df_filtered.empty:
                    st.warning("⚠️ No trades found with selected filters.")
                else:
                    # --- KPI CALCULATION (COMPLETE) ---
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
                    loss_rate = (len(losses) / total_trades)
                    expectancy = ( (win_rate/100) * avg_win ) - ( loss_rate * avg_loss )
                    
                    avg_pts_gain = wins['pts_medio'].mean() if not wins.empty else 0
                    avg_pts_loss = abs(losses['pts_medio'].mean()) if not losses.empty else 0
                    avg_lot = df_filtered['lote'].mean() if not df_filtered.empty else 0

                    df_filtered = df_filtered.sort_values('created_at')
                    df_filtered['equity'] = df_filtered['resultado'].cumsum()
                    df_filtered['peak'] = df_filtered['equity'].cummax()
                    df_filtered['drawdown'] = df_filtered['equity'] - df_filtered['peak']
                    max_dd = df_filtered['drawdown'].min()

                    # --- KPI DISPLAY (12 CARDS) ---
                    st.markdown("##### 🏁 Desempenho Geral")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: card_metric("RESULTADO LÍQUIDO", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f} / -${gross_loss:,.0f}", "#00FF88" if net_profit >= 0 else "#FF4B4B", "Total financial result (Profit - Loss).")
                    with c2: card_metric("FATOR DE LUCRO (PF)", pf_str, "Ideal > 1.5", "#B20000", "Gross Profit / Gross Loss Ratio.")
                    with c3: card_metric("WIN RATE", f"{win_rate:.1f}%", f"{len(wins)} Wins / {len(losses)} Loss", "white", "Trade win rate.")
                    with c4: card_metric("EXPECTATIVA MAT.", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy > 0 else "#FF4B4B", "Expected value per trade long term.")
                    
                    st.markdown("##### 💲 Médias Financeiras & Risco")
                    c5, c6, c7, c8 = st.columns(4)
                    with c5: card_metric("MÉDIA GAIN ($)", f"${avg_win:,.2f}", "", "#00FF88", "Average win value.")
                    with c6: card_metric("MÉDIA LOSS ($)", f"-${avg_loss:,.2f}", "", "#FF4B4B", "Average loss value.")
                    with c7: card_metric("RISCO : RETORNO", f"1 : {payoff:.2f}", "Payoff Real", "white", "How many times your average gain is bigger than your average loss.")
                    with c8: card_metric("DRAWDOWN MÁXIMO", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B", "Maximum account drawdown from a peak.")

                    st.markdown("##### 🎯 Performance Técnica")
                    c9, c10, c11, c12 = st.columns(4)
                    with c9: card_metric("PTS MÉDIOS (GAIN)", f"{avg_pts_gain:.2f} pts", "", "#00FF88", "Average points captured in winning trades.")
                    with c10: card_metric("PTS MÉDIOS (LOSS)", f"{avg_pts_loss:.2f} pts", "", "#FF4B4B", "Average points lost in losing trades.")
                    with c11: card_metric("LOTE MÉDIO", f"{avg_lot:.1f}", "Contratos", "white", "Average trade size.")
                    with c12: card_metric("TOTAL TRADES", str(total_trades), "Executados", "white", "Total trade volume in period.")

                    st.markdown("---")

                    # --- CHARTS (3 CHARTS) ---
                    g1, g2 = st.columns([2, 1])
                    with g1:
                        view_mode = st.radio("Visualize Curve by:", ["Sequence of Trades", "Date (Time)"], horizontal=True, label_visibility="collapsed")
                        if view_mode == "Sequence of Trades":
                            df_filtered['trade_seq'] = range(1, len(df_filtered) + 1)
                            x_axis = 'trade_seq'
                            x_title = "Number of Trades"
                        else:
                            x_axis = 'data'
                            x_title = "Date"

                        fig_eq = px.area(df_filtered, x=x_axis, y='equity', title="📈 Curva de Patrimônio", template="plotly_dark")
                        fig_eq.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                        fig_eq.add_hline(y=0, line_dash="dash", line_color="gray")
                        fig_eq.update_layout(xaxis_title=x_title, yaxis_title="Equity ($)")
                        st.plotly_chart(fig_eq, use_container_width=True, config={'displayModeBar': False})
                        
                    with g2:
                        st.markdown("<br>", unsafe_allow_html=True) 
                        ctx_perf = df_filtered.groupby('contexto')['resultado'].sum().reset_index()
                        fig_bar = px.bar(ctx_perf, x='contexto', y='resultado', title="📊 Resultado por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

                    st.markdown("### 📅 Performance por Dia da Semana")
                    df_filtered['dia_semana'] = pd.to_datetime(df_filtered['data']).dt.day_name()
                    dias_pt = {'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua', 'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sab', 'Sunday': 'Dom'}
                    df_filtered['dia_pt'] = df_filtered['dia_semana'].map(dias_pt)
                    
                    day_perf = df_filtered.groupby('dia_pt')['resultado'].sum().reindex(['Seg', 'Ter', 'Qua', 'Qui', 'Sex']).reset_index()
                    fig_day = px.bar(day_perf, x='dia_pt', y='resultado', template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                    fig_day.update_layout(xaxis_title="Day of Week", yaxis_title="Result ($)")
                    st.plotly_chart(fig_day, use_container_width=True, config={'displayModeBar': False})

            else: st.info("No trades registered for this user.")
        else: st.warning("Database empty.")

    # --- 8. REGISTRAR TRADE (OPTIMIZED LAYOUT) ---
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db()
        df_grupos = load_grupos_config()
        
        # Optimized Top: ATM and Group
        col_atm, col_grp = st.columns([3, 1.5])
        
        with col_atm:
            atm_sel = st.selectbox("🎯 Escolher Template ATM", ["Manual"] + list(atm_db.keys()))
        
        with col_grp:
            grupo_sel_trade = "Geral"
            if ROLE in ["master", "admin"]:
                if not df_grupos.empty:
                    # List of groups registered in the new table
                    lista_grupos = sorted(list(df_grupos['nome'].unique()))
                    grupo_sel_trade = st.selectbox("📂 Vincular ao Grupo", lista_grupos)
                else:
                    st.caption("⚠️ Create groups in 'Contas' tab.")
        
        if atm_sel != "Manual":
            config = atm_db[atm_sel]
            lt_default = int(config["lote"])
            stp_default = float(config["stop"])
            try:
                parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
            except:
                parciais_pre = []
        else:
            lt_default = 1
            stp_default = 0.0
            parciais_pre = []

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

            saidas = []
            aloc = 0
            for i in range(st.session_state.num_parciais):
                c_pts, c_qtd = st.columns(2)
                val_pts = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
                val_qtd = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
                
                pts = c_pts.number_input(f"Pts Alvo {i+1}", value=val_pts, key=f"p_pts_{i}_{atm_sel}", step=0.25)
                qtd = c_qtd.number_input(f"Contratos {i+1}", value=val_qtd, key=f"p_qtd_{i}_{atm_sel}", min_value=0)
                saidas.append({"pts": pts, "qtd": qtd})
                aloc += qtd
            
            if lt != aloc:
                diff = lt - aloc
                st.markdown(f'<div class="piscante-erro">{"FALTAM" if diff > 0 else "SOBRAM"} {abs(diff)} CONTRATOS</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Posição Sincronizada")

        st.divider()
        col_gain, col_loss = st.columns(2)
        btn_registrar = False
        if col_gain.button("🟢 REGISTRAR GAIN", use_container_width=True, disabled=(lt != aloc)): btn_registrar = True
        if col_loss.button("🔴 REGISTRAR STOP FULL", use_container_width=True): saidas = [{"pts": -stp, "qtd": lt}]; btn_registrar = True

        if btn_registrar:
            with st.spinner("Saving..."):
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
                        "prints": img_url, "usuario": USER, "grupo_vinculo": grupo_sel_trade,
                        "risco_fin": (stp * MULTIPLIERS[atv] * lt)
                    }).execute()
                    st.balloons() 
                    st.success(f"✅ SUCCESS! Result: ${res_fin:,.2f}")
                    time.sleep(2); st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- 9. TAB CONTAS (COMPLETE SEPARATION: GROUP vs ACCOUNT) ---
    elif selected == "Contas":
        st.title("💼 Gestão de Portfólio")
        
        if ROLE not in ['master', 'admin']:
            st.error("Access Restricted.")
        else:
            # Internal tabs for organizing
            tab_grupo, tab_conta, tab_visao = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📊 Visão Geral"])
            
            # --- TAB 1: CREATE GROUP ---
            with tab_grupo:
                st.subheader("Nova Estrutura de Contas")
                with st.form("form_grupo"):
                    novo_grupo = st.text_input("Nome do Grupo (Ex: Mesa Apex, Fase 2)")
                    if st.form_submit_button("Criar Grupo"):
                        if novo_grupo:
                            supabase.table("grupos_config").insert({"usuario": USER, "nome": novo_grupo}).execute()
                            st.success(f"Group '{novo_grupo}' created!")
                            time.sleep(1); st.rerun()
                        else:
                            st.warning("Enter a name.")
                            
                st.divider()
                st.write("Existing Groups:")
                df_g = load_grupos_config()
                if not df_g.empty:
                    for idx, row in df_g.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.info(f"📂 {row['nome']}")
                        if c2.button("Delete", key=f"del_g_{row['id']}"):
                            supabase.table("grupos_config").delete().eq("id", row['id']).execute()
                            st.rerun()

            # --- TAB 2: REGISTER ACCOUNT ---
            with tab_conta:
                st.subheader("Vincular Conta a um Grupo")
                df_g = load_grupos_config()
                
                if df_g.empty:
                    st.warning("⚠️ Create a Group first in the previous tab.")
                else:
                    with st.form("form_conta"):
                        # Selectbox pulling from groups table
                        grupo_selecionado = st.selectbox("Select Group", sorted(df_g['nome'].unique()))
                        
                        conta_id = st.text_input("Account Identifier (Ex: PA-001, 50k-01)")
                        saldo_ini = st.number_input("Initial Balance ($)", value=50000.0, step=100.0)
                        fase_atual = st.selectbox("Current Phase", ["Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saques)"])
                        
                        if st.form_submit_button("Save Account"):
                            if conta_id:
                                supabase.table("contas_config").insert({
                                    "usuario": USER,
                                    "grupo_nome": grupo_selecionado,
                                    "conta_identificador": conta_id,
                                    "saldo_inicial": saldo_ini,
                                    "fase": fase_atual
                                }).execute()
                                st.success("Account linked successfully!")
                                time.sleep(1); st.rerun()
                            else:
                                st.warning("Fill in the Account ID.")

            # --- TAB 3: OVERVIEW (SMART BALANCE) ---
            with tab_visao:
                st.subheader("📋 Acompanhamento de Saldo em Tempo Real")
                df_c = load_contas_config()
                df_t = load_trades_db()
                
                if not df_t.empty: df_t = df_t[df_t['usuario'] == USER]
                
                if not df_c.empty:
                    grupos_unicos = sorted(df_c['grupo_nome'].unique())
                    
                    for grp in grupos_unicos:
                        with st.expander(f"📂 {grp}", expanded=True):
                            # Calculate total profit for the group
                            trades_grp = df_t[df_t['grupo_vinculo'] == grp] if not df_t.empty else pd.DataFrame()
                            lucro_grupo = trades_grp['resultado'].sum() if not trades_grp.empty else 0.0
                            
                            # Filter accounts for this group
                            contas_g = df_c[df_c['grupo_nome'] == grp]
                            
                            for _, row in contas_g.iterrows():
                                # Logic: Balance = Initial + Group Profit
                                saldo_atual = float(row['saldo_inicial']) + lucro_grupo
                                delta = saldo_atual - float(row['saldo_inicial'])
                                cor_delta = "#00FF88" if delta >= 0 else "#FF4B4B"
                                
                                c_info, c_edit, c_del = st.columns([3, 0.5, 0.5])
                                
                                # HTML corrected for visual bug
                                c_info.markdown(
                                    f"""
                                    <div style='background-color: #222; padding: 10px; border-radius: 5px; margin-bottom: 5px;'>
                                        <div>💳 <b>{row['conta_identificador']}</b> <span style='color: #888; font-size: 0.9em;'>| {row['fase']}</span></div>
                                        <div style='font-size: 1.2em; margin-top: 5px;'>
                                            💰 Balance: <b>${saldo_atual:,.2f}</b> 
                                            (<span style='color:{cor_delta}'>${delta:+,.2f}</span>)
                                        </div>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )
                                
                                # Edit Button with Popover
                                with c_edit.popover("⚙️"):
                                    st.write(f"Edit {row['conta_identificador']}")
                                    n_fase = st.selectbox("New Phase", ["Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saques)"], key=f"nf_{row['id']}")
                                    n_saldo = st.number_input("New Initial Balance", value=float(row['saldo_inicial']), key=f"ns_{row['id']}")
                                    if st.button("Save Changes", key=f"save_{row['id']}"):
                                        supabase.table("contas_config").update({"fase": n_fase, "saldo_inicial": n_saldo}).eq("id", row['id']).execute()
                                        st.rerun()

                                if c_del.button("🗑️", key=f"del_acc_{row['id']}"):
                                    supabase.table("contas_config").delete().eq("id", row['id']).execute()
                                    st.rerun()
                            
                            # Visual Progress Bar (Visual target of +$3000 profit)
                            if lucro_grupo > 0:
                                prog = min(1.0, lucro_grupo / 3000)
                                st.progress(prog)
                                st.caption(f"Cushion Target ($3k): {prog*100:.1f}%")
                            else:
                                st.progress(0.0)
                else:
                    st.info("No accounts configured.")

    # --- 10. CONFIGURE ATM ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")

        if "atm_form_data" not in st.session_state:
            st.session_state.atm_form_data = {
                "id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]
            }

        def reset_atm_form():
            st.session_state.atm_form_data = {
                "id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]
            }

        res = supabase.table("atm_configs").select("*").order("nome").execute()
        existing_atms = res.data

        c_form, c_list = st.columns([1.5, 1])

        with c_list:
            st.subheader("📋 Saved Strategies")
            if st.button("✨ Create New (Clear)", use_container_width=True):
                reset_atm_form(); st.rerun()
            if existing_atms:
                for item in existing_atms:
                    with st.expander(f"📍 {item['nome']}", expanded=False):
                        st.write(f"**Lot:** {item['lote']} | **Stop:** {item['stop']}")
                        c_edit, c_del = st.columns(2)
                        if c_edit.button("✏️ Edit", key=f"edit_{item['id']}"):
                            p_data = item['parciais'] if isinstance(item['parciais'], list) else json.loads(item['parciais'])
                            st.session_state.atm_form_data = {
                                "id": item['id'], "nome": item['nome'], "lote": item['lote'],
                                "stop": item['stop'], "parciais": p_data
                            }
                            st.rerun()
                        if c_del.button("🗑️ Delete", key=f"del_{item['id']}"):
                            supabase.table("atm_configs").delete().eq("id", item['id']).execute()
                            if st.session_state.atm_form_data["id"] == item['id']: reset_atm_form()
                            st.rerun()
            else: st.info("No saved strategies.")

        with c_form:
            form_data = st.session_state.atm_form_data
            titulo = f"✏️ Editing: {form_data['nome']}" if form_data["id"] else "✨ New Strategy"
            st.subheader(titulo)
            
            new_nome = st.text_input("Strategy Name", value=form_data["nome"])
            c_l, c_s = st.columns(2)
            new_lote = c_l.number_input("Total Lot", min_value=1, value=int(form_data["lote"]))
            new_stop = c_s.number_input("Default Stop (Pts)", min_value=0.0, value=float(form_data["stop"]), step=0.25)
            
            st.markdown("---")
            st.write("🎯 Target Configuration")
            c_add, c_rem = st.columns([1, 4])
            
            if c_add.button("➕ Add Target"): 
                st.session_state.atm_form_data["parciais"].append({"pts": 0.0, "qtd": 1})
                st.rerun()
            if c_rem.button("➖ Remove Last") and len(form_data["parciais"]) > 1: 
                st.session_state.atm_form_data["parciais"].pop()
                st.rerun()
            
            updated_partials = []
            total_aloc = 0
            for i, p in enumerate(form_data["parciais"]):
                c1, c2 = st.columns(2)
                p_pts = c1.number_input(f"Target {i+1} (Pts)", value=float(p["pts"]), key=f"edm_pts_{i}", step=0.25)
                p_qtd = c2.number_input(f"Qty {i+1}", value=int(p["qtd"]), min_value=1, key=f"edm_qtd_{i}")
                updated_partials.append({"pts": p_pts, "qtd": p_qtd})
                total_aloc += p_qtd
            
            if total_aloc != new_lote: st.warning(f"⚠️ Warning: Sum of partials ({total_aloc}) differs from Total Lot ({new_lote}).")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("💾 SAVE STRATEGY", use_container_width=True):
                payload = {"nome": new_nome, "lote": new_lote, "stop": new_stop, "parciais": updated_partials}
                if form_data["id"]:
                    supabase.table("atm_configs").update(payload).eq("id", form_data["id"]).execute()
                    st.toast("Updated!", icon="✅")
                else:
                    supabase.table("atm_configs").insert(payload).execute()
                    st.toast("Created!", icon="✨")
                time.sleep(1); reset_atm_form(); st.rerun()

    # --- 11. HISTORY ---
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        df = load_trades_db()
        if not df.empty:
            df_h = df[df['usuario'] == USER]
            with st.expander("🔍 Filtros", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                filtro_ativo = c1.multiselect("Filtrar Ativo", ["NQ", "MNQ"])
                filtro_res = c2.selectbox("Filtrar Resultado", ["Todos", "Wins", "Losses"])
                filtro_ctx = c3.multiselect("Filtrar Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
                
                # Group Filter (Master/Admin)
                if ROLE in ['master', 'admin']:
                    opcoes_grupo = sorted(list(df_h['grupo_vinculo'].unique()))
                    filtro_grp = c4.multiselect("Filtrar Grupo", opcoes_grupo)
                else:
                    filtro_grp = []

            if filtro_ativo: df_h = df_h[df_h['ativo'].isin(filtro_ativo)]
            if filtro_ctx: df_h = df_h[df_h['contexto'].isin(filtro_ctx)]
            if filtro_grp: df_h = df_h[df_h['grupo_vinculo'].isin(filtro_grp)]
            if filtro_res == "Wins": df_h = df_h[df_h['resultado'] > 0]
            if filtro_res == "Losses": df_h = df_h[df_h['resultado'] < 0]
            
            df_h = df_h.sort_values('created_at', ascending=False)
            
            @st.dialog("Detalhes da Operação", width="large")
            def show_trade_details(row):
                if row.get('prints'): st.image(row['prints'], use_container_width=True)
                else: st.info("No Print available.")
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.write(f"📅 **Date:** {row['data']}")
                c1.write(f"📈 **Asset:** {row['ativo']}")
                c2.write(f"⚖️ **Lot:** {row['lote']}")
                c2.write(f"🎯 **Avg Pts:** {row['pts_medio']:.2f} pts")
                c3.write(f"🔄 **Direction:** {row['direcao']}")
                c3.write(f"🧠 **Context:** {row['contexto']}")
                
                if ROLE in ['master', 'admin']:
                    st.write(f"📂 **Group:** {row['grupo_vinculo']}")
                
                res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
                st.markdown(f"<h1 style='color:{res_c}; text-align:center; font-size:40px;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
                
                if st.button("🗑️ DELETE RECORD", type="primary", use_container_width=True):
                    supabase.table("trades").delete().eq("id", row['id']).execute()
                    st.rerun()

            cols = st.columns(4)
            for i, (index, row) in enumerate(df_h.iterrows()):
                with cols[i % 4]:
                    res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    res_fmt = f"${row['resultado']:,.2f}"
                    img_html = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="width:100%; height:100%; background:#333; display:flex; align-items:center; justify-content:center; color:#555;">No Photo</div>'
                    
                    st.markdown(f"""
                        <div class="trade-card">
                            <div class="card-img-container">{img_html}</div>
                            <div class="card-title">{row['ativo']} - {row['direcao']}</div>
                            <div class="card-sub">{row['data']} • {row['grupo_vinculo']}</div>
                            <div class="{res_class}">{res_fmt}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("👁️ View", key=f"btn_{row['id']}", use_container_width=True):
                        show_trade_details(row)

    # --- 12. MANAGE USERS (ADMIN ONLY) ---
    elif selected == "Gerenciar Usuários":
        if ROLE != "admin":
            st.error("Access Denied.")
        else:
            st.title("👥 Gestão de Usuários")

            if "user_form_data" not in st.session_state:
                st.session_state.user_form_data = {"id": None, "username": "", "password": "", "role": "user"}

            def reset_user_form():
                st.session_state.user_form_data = {"id": None, "username": "", "password": "", "role": "user"}

            res = supabase.table("users").select("*").execute()
            users_list = res.data

            c_form, c_list = st.columns([1, 1.5])

            with c_list:
                st.subheader("📋 Active Users")
                if st.button("✨ Create New User", use_container_width=True):
                    reset_user_form(); st.rerun()
                
                if users_list:
                    for u in users_list:
                        with st.container():
                            c1, c2, c3 = st.columns([2, 2, 1])
                            c1.write(f"👤 **{u['username']}**")
                            
                            # Role Icon
                            badge = "👑 Admin" if u.get('role') == 'admin' else ("🛡️ Master" if u.get('role') == 'master' else "👤 User")
                            c2.write(badge)
                            
                            col_edit, col_del = st.columns(2)
                            if col_edit.button("✏️", key=f"u_edit_{u['id']}"):
                                st.session_state.user_form_data = {"id": u['id'], "username": u['username'], "password": u['password'], "role": u.get('role', 'user')}
                                st.rerun()
                            if col_del.button("🗑️", key=f"u_del_{u['id']}"):
                                supabase.table("users").delete().eq("id", u['id']).execute()
                                if st.session_state.user_form_data["id"] == u['id']: reset_user_form()
                                st.rerun()
                            st.divider()
                else: st.info("No users found.")

            with c_form:
                u_data = st.session_state.user_form_data
                titulo = f"✏️ Editing: {u_data['username']}" if u_data["id"] else "✨ New User"
                st.subheader(titulo)
                
                form_user = st.text_input("Login (Username)", value=u_data["username"])
                form_pass = st.text_input("Password", value=u_data["password"], type="default")
                
                role_opts = ["user", "master", "admin"]
                curr_role = u_data["role"] if u_data["role"] in role_opts else "user"
                form_role = st.selectbox("Access Level", role_opts, index=role_opts.index(curr_role))
                
                if st.button("💾 SAVE USER", use_container_width=True):
                    if u_data["id"]:
                        supabase.table("users").update({"username": form_user, "password": form_pass, "role": form_role}).eq("id", u_data["id"]).execute()
                        st.toast("User updated!", icon="✅")
                    else:
                        supabase.table("users").insert({"username": form_user, "password": form_pass, "role": form_role}).execute()
                        st.toast("User created!", icon="✨")
                    
                    time.sleep(1); reset_user_form(); st.rerun()
