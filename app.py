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
    /* Cards */
    .trade-card { background-color: #161616; border-radius: 8px; padding: 12px; margin-bottom: 15px; border: 1px solid #333; transition: transform 0.2s; }
    .trade-card:hover { transform: translateY(-3px); border-color: #B20000; }
    .card-img-container { width: 100%; height: 140px; background-color: #222; border-radius: 5px; overflow: hidden; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 14px; font-weight: 700; color: white; margin-bottom: 2px; }
    .card-sub { font-size: 11px; color: #888; margin-bottom: 8px; }
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }
    
    /* Métricas */
    .metric-container { background-color: #161616; border: 1px solid #262626; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); min-height: 140px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    .metric-label { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; display: flex; justify-content: center; align-items: center; gap: 5px; }
    .metric-value { color: white; font-size: 22px; font-weight: 800; margin-top: 5px; }
    .metric-sub { font-size: 12px; margin-top: 4px; color: #666; }
    .help-icon { color: #555; font-size: 12px; border: 1px solid #444; border-radius: 50%; width: 14px; height: 14px; display: inline-flex; align-items: center; justify-content: center; }
    
    /* Geral */
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
    def load_trades():
        try:
            res = supabase.table("trades").select("*").eq("usuario", USER).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.date
                df['created_at'] = pd.to_datetime(df['created_at'])
                if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
                if 'comportamento' not in df.columns: df['comportamento'] = 'Normal'
            return df
        except: return pd.DataFrame()

    def load_contas_config():
        try:
            res = supabase.table("contas_config").select("*").eq("usuario", USER).execute()
            return pd.DataFrame(res.data)
        except: return pd.DataFrame()
            
    def load_grupos_config():
        try:
            res = supabase.table("grupos_config").select("*").eq("usuario", USER).execute()
            return pd.DataFrame(res.data)
        except: return pd.DataFrame()

    def load_atms():
        res = supabase.table("atm_configs").select("*").execute()
        return {item['nome']: item for item in res.data}

    def card_metric(label, value, sub="", color="white", help_t=""):
        st.markdown(f'<div class="metric-container" title="{help_t}"><div class="metric-label">{label}</div><div class="metric-value" style="color:{color}">{value}</div><div class="metric-sub">{sub}</div></div>', unsafe_allow_html=True)

    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        icons = ["grid", "currency-dollar", "gear", "clock"]
        if ROLE in ['master', 'admin']: menu.insert(2, "Contas"); icons.insert(2, "briefcase")
        if ROLE == 'admin': menu.append("Gerenciar Usuários"); icons.append("people")
        selected = option_menu(None, menu, icons=icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- 7. DASHBOARD (COMPLETO + APEX) ---
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df = load_trades()
        if not df.empty:
            with st.expander("🔍 Filtros", expanded=True):
                if ROLE in ['master', 'admin']:
                    c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1.8])
                    df_c_load = load_contas_config()
                    grupos_disp = sorted(list(df_c_load['grupo_nome'].unique())) if not df_c_load.empty else []
                    grupos_trades = list(df['grupo_vinculo'].unique())
                    todos_grupos = sorted(list(set(grupos_disp + grupos_trades)))
                    sel_grp = c3.selectbox("Grupo", ["Todos"] + todos_grupos)
                else:
                    c1, c2, c4 = st.columns([1, 1, 2]); sel_grp = "Todos"
                
                d_i = c1.date_input("Início", df['data'].min())
                d_f = c2.date_input("Fim", df['data'].max())
                f_ctx = c4.multiselect("Contextos", list(df['contexto'].unique()), default=list(df['contexto'].unique()))

            mask = (df['data'] >= d_i) & (df['data'] <= d_f) & (df['contexto'].isin(f_ctx))
            if sel_grp != "Todos": mask &= (df['grupo_vinculo'] == sel_grp)
            df_f = df[mask].copy()

            if not df_f.empty:
                # -----------------------------------------------------------
                # 🛡️ PAINEL APEX 150K (TRAVA STOP 150.100)
                # -----------------------------------------------------------
                if sel_grp != "Todos" and ROLE in ['master', 'admin']:
                    st.markdown(f"### 🛡️ Gestão Apex: {sel_grp}")
                    df_c = load_contas_config()
                    contas_g = df_c[df_c['grupo_nome'] == sel_grp]
                    
                    if not contas_g.empty:
                        ref = contas_g.iloc[0]
                        fase = ref['fase']
                        saldo_inicial_cadastro = float(ref['saldo_inicial'])
                        lucro_periodo = df_f['resultado'].sum()
                        
                        saldo_atual_est = saldo_inicial_cadastro + lucro_periodo
                        
                        # Cálculo Trailing Stop Apex 150k
                        equity_curve = df_f.sort_values('created_at')['resultado'].cumsum() + saldo_inicial_cadastro
                        high_water_mark = max(saldo_inicial_cadastro, equity_curve.max()) if not equity_curve.empty else saldo_inicial_cadastro
                        
                        trailing_stop_teorico = high_water_mark - 5000
                        # Trava em 150.100 se o saldo inicial ou HWM permitir
                        stop_loss_real = 150100.0 if (saldo_inicial_cadastro > 155100 or trailing_stop_teorico > 150100) else min(trailing_stop_teorico, 150100.0)
                        
                        buffer_vida = saldo_atual_est - stop_loss_real
                        
                        # Metas
                        meta_alvo = 0.0
                        if "Fase 1" in fase: meta_alvo = 159000.0
                        elif "Fase 2" in fase: meta_alvo = 155100.0
                        elif "Fase 3" in fase: meta_alvo = 160000.0
                        
                        falta_meta = meta_alvo - saldo_atual_est
                        media_trade = df_f['resultado'].mean()

                        # Visualização
                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Contas Replicadas", f"{len(contas_g)}", f"{len(contas_g)}x Alavancagem")
                        k2.metric("Saldo Unitário", f"${saldo_atual_est:,.2f}", f"Stop: ${stop_loss_real:,.0f}")
                        cor_b = "inverse" if buffer_vida < 2500 else "normal"
                        k3.metric("🔥 Buffer (Vida)", f"${buffer_vida:,.2f}", "Até o Stop", delta_color=cor_b)
                        
                        if meta_alvo > 0 and falta_meta > 0:
                            k4.metric("🎯 Falta p/ Meta", f"${falta_meta:,.2f}", f"Alvo: ${meta_alvo:,.0f}")
                        elif "Fase 4" in fase or (meta_alvo > 0 and falta_meta <= 0):
                            saque_disp = max(0, saldo_atual_est - 152600) * len(contas_g)
                            k4.metric("💰 Saque Disponível", f"${saque_disp:,.2f}", "Total do Grupo")

                        # Projeção Neuro-Friendly
                        st.write("")
                        if meta_alvo > 0 and falta_meta > 0 and media_trade > 0:
                            trades_nec = int(falta_meta / media_trade) + 1
                            st.info(f"🧠 **Foco:** Faltam cerca de **{trades_nec} trades bem feitos** (média ${media_trade:.0f}) para o objetivo.")
                        elif "Fase 4" in fase:
                            st.success("🚀 **Modo Renda:** Mantenha o buffer seguro e solicite saques quinzenais.")
                    st.markdown("---")

                # -----------------------------------------------------------
                # DASHBOARD COMPLETO - MEIO
                # -----------------------------------------------------------
                t_tr, net = len(df_f), df_f['resultado'].sum()
                wins = df_f[df_f['resultado'] > 0]; losses = df_f[df_f['resultado'] < 0]
                pf = (wins['resultado'].sum() / abs(losses['resultado'].sum())) if not losses.empty else float('inf')
                wr = (len(wins)/t_tr)*100
                avg_w = wins['resultado'].mean() if not wins.empty else 0
                avg_l = abs(losses['resultado'].mean()) if not losses.empty else 0
                payoff = avg_w/avg_l if avg_l > 0 else 0
                exp = ((wr/100)*avg_w) - ((len(losses)/t_tr)*avg_l)
                
                df_f = df_f.sort_values('created_at')
                df_f['equity'] = df_f['resultado'].cumsum()
                df_f['peak'] = df_f['equity'].cummax()
                df_f['drawdown'] = df_f['equity'] - df_f['peak']
                max_dd = df_f['drawdown'].min()

                st.markdown("##### 🏁 KPIs Globais")
                r1 = st.columns(4)
                with r1[0]: card_metric("RESULTADO", f"${net:,.2f}", f"Bruto: ${wins['resultado'].sum():,.0f}", "#00FF88" if net>=0 else "#FF4B4B")
                with r1[1]: card_metric("FATOR DE LUCRO", f"{pf:.2f}", "Ideal > 1.5", "#B20000")
                with r1[2]: card_metric("WIN RATE", f"{wr:.1f}%", f"{len(wins)}W / {len(losses)}L", "white")
                with r1[3]: card_metric("EXPECTATIVA", f"${exp:.2f}", "Por Trade", "#00FF88" if exp>0 else "#FF4B4B")

                r2 = st.columns(4)
                with r2[0]: card_metric("MÉDIA GAIN", f"${avg_w:,.2f}", "", "#00FF88")
                with r2[1]: card_metric("MÉDIA LOSS", f"-${avg_l:,.2f}", "", "#FF4B4B")
                with r2[2]: card_metric("PAYOFF", f"1 : {payoff:.2f}", "Risco:Retorno")
                with r2[3]: card_metric("DRAWDOWN MÁX", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B")

                r3 = st.columns(4)
                with r3[0]: card_metric("PTS (GAIN)", f"{wins['pts_medio'].mean():.2f}", "", "#00FF88")
                with r3[1]: card_metric("PTS (LOSS)", f"{abs(losses['pts_medio'].mean()):.2f}", "", "#FF4B4B")
                with r3[2]: card_metric("LOTE MÉDIO", f"{df_f['lote'].mean():.1f}", "Ctos")
                with r3[3]: card_metric("TRADES", str(t_tr), "Total")

                st.divider()
                
                # -----------------------------------------------------------
                # GRÁFICOS - FUNDO
                # -----------------------------------------------------------
                g1, g2 = st.columns([2, 1])
                with g1:
                    tab_eq, tab_dd = st.tabs(["📈 Patrimônio", "🌊 Drawdown"])
                    with tab_eq:
                        st.plotly_chart(px.area(df_f, x='created_at', y='equity', title="Curva de Capital", template="plotly_dark").update_traces(line_color='#B20000', fillcolor='rgba(178,0,0,0.2)'), use_container_width=True)
                    with tab_dd:
                        st.plotly_chart(px.area(df_f, x='created_at', y='drawdown', title="Curva de Drawdown", template="plotly_dark").update_traces(line_color='#FF4B4B', fillcolor='rgba(255,75,75,0.2)'), use_container_width=True)
                
                with g2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    ctx_perf = df_f.groupby('contexto')['resultado'].sum().reset_index()
                    st.plotly_chart(px.bar(ctx_perf, x='contexto', y='resultado', title="Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"]), use_container_width=True)

                st.markdown("### 🕒 Análise Temporal")
                df_f['hora'] = df_f['created_at'].dt.hour
                df_f['dia'] = pd.to_datetime(df_f['data']).dt.day_name()
                
                t1, t2 = st.columns(2)
                with t1:
                    hp = df_f.groupby('hora')['resultado'].sum().reset_index()
                    st.plotly_chart(px.bar(hp, x='hora', y='resultado', title="Por Hora", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"]), use_container_width=True)
                with t2:
                    d_map = {'Monday':0, 'Tuesday':1, 'Wednesday':2, 'Thursday':3, 'Friday':4}
                    df_f['d_idx'] = df_f['dia'].map(d_map)
                    dp = df_f.groupby('dia')['resultado'].sum().reset_index()
                    dp['d_idx'] = dp['dia'].map(d_map); dp = dp.sort_values('d_idx')
                    st.plotly_chart(px.bar(dp, x='dia', y='resultado', title="Por Dia da Semana", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"]), use_container_width=True)

            else: st.info("Sem dados.")
        else: st.warning("Vazio.")

    # --- 8. REGISTRAR TRADE (AGORA COM CONTEXTO A, B, C) ---
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms(); df_c = load_grupos_config()
        
        c_atm, c_grp = st.columns([3, 1.5])
        with c_atm: atm_sel = st.selectbox("🎯 ATM", ["Manual"] + list(atm_db.keys()))
        with c_grp:
            g_sel = "Geral"
            if ROLE in ["master", "admin"]:
                if not df_c.empty:
                    g_sel = st.selectbox("📂 Grupo", sorted(df_c['nome'].unique()))
                else: st.caption("Crie grupos em 'Contas'")

        if atm_sel != "Manual":
            cf = atm_db[atm_sel]; lt_d, stp_d = int(cf["lote"]), float(cf["stop"])
            parc = json.loads(cf["parciais"]) if isinstance(cf["parciais"], str) else cf["parciais"]
        else: lt_d, stp_d, parc = 1, 0.0, []

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date())
            atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            # CORRIGIDO: SUAS OPÇÕES ORIGINAIS
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
            # PSICOLOGIA
            psi = st.selectbox("Estado Mental", ["Focado/Bem", "Ansioso", "Vingativo", "Cansado", "Fomo", "Neutro"])
        with f2:
            lt = st.number_input("Lote", min_value=1, value=lt_d); stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_d, step=0.25)
            if stp > 0: st.markdown(f'<div class="risco-alert">📉 Risco: ${stp * MULTIPLIERS[atv] * lt:,.2f}</div>', unsafe_allow_html=True)
            up = st.file_uploader("📸 Print", type=['png', 'jpg'])
        with f3:
            st.write("**Saídas**")
            if "np" not in st.session_state or st.session_state.get("la") != atm_sel:
                st.session_state.np = len(parc) if parc else 1
                st.session_state.la = atm_sel
            cb1, cb2 = st.columns(2)
            if cb1.button("➕ Add"): st.session_state.np += 1; st.rerun()
            if cb2.button("🧹 Reset"): st.session_state.np = 1; st.rerun()
            saidas, aloc = [], 0
            for i in range(st.session_state.np):
                cp, cq = st.columns(2)
                vp = float(parc[i]["pts"]) if i < len(parc) else 0.0
                vq = int(parc[i]["qtd"]) if i < len(parc) else (lt if i == 0 else 0)
                p = cp.number_input(f"Pts {i+1}", value=vp, key=f"p_{i}_{atm_sel}"); q = cq.number_input(f"Qtd {i+1}", value=vq, key=f"q_{i}_{atm_sel}")
                saidas.append({"pts": p, "qtd": q}); aloc += q
            if lt != aloc: st.markdown(f'<div class="piscante-erro">SALDO: {lt - aloc} CTTS</div>', unsafe_allow_html=True)

        cg, cl = st.columns(2); br = False
        if cg.button("🟢 GAIN", use_container_width=True, disabled=(lt!=aloc)): br = True
        if cl.button("🔴 STOP", use_container_width=True): saidas = [{"pts": -stp, "qtd": lt}]; br = True
        
        if br:
            with st.spinner("Salvando..."):
                fin = sum([s["pts"] * MULTIPLIERS[atv] * s["qtd"] for s in saidas])
                pm = sum([s["pts"] * s["qtd"] for s in saidas]) / lt
                tid = str(uuid.uuid4()); iurl = ""
                if up:
                    supabase.storage.from_("prints").upload(f"{tid}.png", up.getvalue())
                    iurl = supabase.storage.from_("prints").get_public_url(f"{tid}.png")
                supabase.table("trades").insert({
                    "id": tid, "data": str(dt), "ativo": atv, "contexto": ctx, "direcao": dr, "lote": lt, 
                    "resultado": fin, "pts_medio": pm, "prints": iurl, "usuario": USER, 
                    "grupo_vinculo": g_sel, "comportamento": psi, "risco_fin": (stp * MULTIPLIERS[atv] * lt)
                }).execute()
                st.balloons(); time.sleep(1); st.rerun()

    # --- 9. ABA CONTAS (COM MONITOR DE PERFORMANCE NA ABA 4) ---
    elif selected == "Contas":
        st.title("💼 Gestão de Portfólio")
        
        if ROLE not in ['master', 'admin']:
            st.error("Acesso restrito.")
        else:
            # --- ATUALIZAÇÃO AQUI: ADICIONADA A ABA "Monitor de Performance" ---
            tab_grupo, tab_conta, tab_visao, tab_monitor = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📊 Visão Geral", "🚀 Monitor de Performance"])
            
            # --- ABA 1: CRIAR GRUPO ---
            with tab_grupo:
                st.subheader("Nova Estrutura de Contas")
                with st.form("form_grupo"):
                    novo_grupo = st.text_input("Nome do Grupo (Ex: Mesa Apex, Fase 2)")
                    if st.form_submit_button("Criar Grupo"):
                        if novo_grupo:
                            supabase.table("grupos_config").insert({"usuario": USER, "nome": novo_grupo}).execute()
                            st.success(f"Grupo '{novo_grupo}' criado!")
                            time.sleep(1); st.rerun()
                        else:
                            st.warning("Digite um nome.")
                            
                st.divider()
                st.write("Grupos Existentes:")
                df_g = load_grupos_config()
                if not df_g.empty:
                    for idx, row in df_g.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.info(f"📂 {row['nome']}")
                        if c2.button("Excluir", key=f"del_g_{row['id']}"):
                            supabase.table("grupos_config").delete().eq("id", row['id']).execute()
                            st.rerun()

            # --- ABA 2: CADASTRAR CONTA ---
            with tab_conta:
                st.subheader("Adicionar Conta ao Grupo")
                df_g = load_grupos_config()
                if df_g.empty: st.warning("Crie um grupo primeiro.")
                else:
                    with st.form("form_conta"):
                        grupo_selecionado = st.selectbox("Selecione o Grupo", sorted(df_g['nome'].unique()))
                        conta_id = st.text_input("ID da Conta (Ex: PA-001)")
                        # MUDANÇA APEX: SALDO ATUAL
                        saldo_ini = st.number_input("Saldo ATUAL na Corretora ($)", value=150000.0, step=100.0)
                        fase_atual = st.selectbox("Fase Atual", ["Fase 1 (Teste)", "Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saques)"])
                        
                        if st.form_submit_button("Salvar Conta"):
                            if conta_id:
                                supabase.table("contas_config").insert({
                                    "usuario": USER, "grupo_nome": grupo_selecionado, 
                                    "conta_identificador": conta_id, "saldo_inicial": saldo_ini, "fase": fase_atual
                                }).execute()
                                st.success("Conta salva!"); time.sleep(1); st.rerun()
                            else: st.warning("Preencha o ID.")

            # --- ABA 3: VISÃO GERAL (SALDO INTELIGENTE) ---
            with tab_visao:
                st.subheader("📋 Acompanhamento de Saldo Individual")
                df_c = load_contas_config()
                df_t = load_trades_db()
                if not df_t.empty: df_t = df_t[df_t['usuario'] == USER]
                
                if not df_c.empty:
                    grupos_unicos = sorted(df_c['grupo_nome'].unique())
                    
                    for grp in grupos_unicos:
                        with st.expander(f"📂 {grp}", expanded=True):
                            # Calcula lucro total do grupo
                            trades_grp = df_t[df_t['grupo_vinculo'] == grp] if not df_t.empty else pd.DataFrame()
                            lucro_grupo = trades_grp['resultado'].sum() if not trades_grp.empty else 0.0
                            
                            # Filtra contas deste grupo
                            contas_g = df_c[df_c['grupo_nome'] == grp]
                            
                            for _, row in contas_g.iterrows():
                                # Lógica: Saldo Atual = Saldo Cadastrado + Lucro do Grupo
                                saldo_atual = float(row['saldo_inicial']) + lucro_grupo
                                delta = saldo_atual - float(row['saldo_inicial'])
                                cor_delta = "#00FF88" if delta >= 0 else "#FF4B4B"
                                
                                c_info, c_edit, c_del = st.columns([3, 0.5, 0.5])
                                
                                # HTML corrigido para o bug visual
                                c_info.markdown(
                                    f"""
                                    <div style='background-color: #222; padding: 10px; border-radius: 5px; margin-bottom: 5px;'>
                                        <div>💳 <b>{row['conta_identificador']}</b> <span style='color: #888; font-size: 0.9em;'>| {row['fase']}</span></div>
                                        <div style='font-size: 1.2em; margin-top: 5px;'>
                                            💰 Saldo: <b>${saldo_atual:,.2f}</b> 
                                            (<span style='color:{cor_delta}'>${delta:+,.2f}</span>)
                                        </div>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )
                                
                                # Botão de Editar com Popover
                                with c_edit.popover("⚙️"):
                                    st.write(f"Editar {row['conta_identificador']}")
                                    n_fase = st.selectbox("Nova Fase", ["Fase 1 (Teste)", "Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saques)"], key=f"nf_{row['id']}")
                                    n_saldo = st.number_input("Ajustar Saldo Real", value=float(row['saldo_inicial']), key=f"ns_{row['id']}")
                                    if st.button("Salvar Alterações", key=f"save_{row['id']}"):
                                        supabase.table("contas_config").update({"fase": n_fase, "saldo_inicial": n_saldo}).eq("id", row['id']).execute()
                                        st.rerun()

                                if c_del.button("🗑️", key=f"del_acc_{row['id']}"):
                                    supabase.table("contas_config").delete().eq("id", row['id']).execute()
                                    st.rerun()
                else:
                    st.info("Nenhuma conta configurada.")

            # --- ABA 4: MONITOR DE PERFORMANCE (NOVA CORREÇÃO) ---
            with tab_monitor:
                st.subheader("📈 Análise de Performance por Grupo")
                df_c = load_contas_config()
                df_t = load_trades_db()
                if not df_t.empty: df_t = df_t[df_t['usuario'] == USER]

                if not df_c.empty:
                    grps = sorted(df_c['grupo_nome'].unique())
                    sel_g = st.selectbox("Selecione o Grupo para Analisar", grps)

                    # Filtra dados
                    contas_g = df_c[df_c['grupo_nome'] == sel_g]
                    trades_g = df_t[df_t['grupo_vinculo'] == sel_g] if not df_t.empty else pd.DataFrame()

                    if not contas_g.empty:
                        # Pega a primeira conta como referência para a fase e saldo base
                        ref_conta = contas_g.iloc[0]
                        fase = ref_conta['fase']
                        saldo_base = float(ref_conta['saldo_inicial']) # Saldo cadastrado
                        lucro_total_grupo = trades_g['resultado'].sum() if not trades_g.empty else 0.0
                        
                        # Saldo Unitário Estimado
                        saldo_atual_unitario = saldo_base + lucro_total_grupo

                        # Regras Apex
                        meta_alvo = 0.0
                        base_progresso = 150000.0
                        
                        if "Fase 1" in fase: meta_alvo = 159000.0; base_progresso = 150000.0
                        elif "Fase 2" in fase: meta_alvo = 155100.0; base_progresso = 150000.0
                        elif "Fase 3" in fase: meta_alvo = 160000.0; base_progresso = 155100.0
                        elif "Fase 4" in fase: meta_alvo = 0.0; base_progresso = 150100.0

                        # Cálculo do Stop (Trailing Apex 150k)
                        if not trades_g.empty:
                            equity_curve = trades_g.sort_values('created_at')['resultado'].cumsum() + saldo_base
                            hwm = max(saldo_base, equity_curve.max())
                        else:
                            hwm = saldo_base
                        
                        trailing_stop = hwm - 5000.0
                        stop_real = 150100.0 if (saldo_base > 155100 or trailing_stop > 150100) else min(trailing_stop, 150100.0)
                        buffer_vida = saldo_atual_unitario - stop_real

                        # Métricas do Grupo
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Saldo Unitário", f"${saldo_atual_unitario:,.2f}")
                        col2.metric("Lucro Total (Unitário)", f"${lucro_total_grupo:+,.2f}", f"{len(contas_g)} contas")
                        col3.metric("Buffer de Vida", f"${buffer_vida:,.2f}", "Até quebrar")
                        
                        falta = meta_alvo - saldo_atual_unitario
                        if meta_alvo > 0:
                            col4.metric("Falta para Meta", f"${falta:,.2f}", f"Alvo: ${meta_alvo:,.0f}")
                        else:
                            col4.metric("Modo Saque", "Sem Teto")

                        st.divider()

                        # Gráfico de Evolução e Projeção
                        c_graf, c_proj = st.columns([2, 1])
                        
                        with c_graf:
                            st.markdown("##### 🌊 Curva de Evolução")
                            if not trades_g.empty:
                                df_evo = trades_g.sort_values('created_at').copy()
                                df_evo['saldo_acc'] = df_evo['resultado'].cumsum() + saldo_base
                                
                                # --- CORREÇÃO: Adicionar ponto de partida (Saldo Inicial) ---
                                # Cria uma linha artificial com a data do primeiro trade menos 30 min, valendo o saldo inicial
                                start_date = df_evo['created_at'].min() - timedelta(minutes=30)
                                start_row = pd.DataFrame({'created_at': [start_date], 'saldo_acc': [saldo_base]})
                                # Concatena o inicio com os dados reais
                                df_plot = pd.concat([start_row, df_evo[['created_at', 'saldo_acc']]], ignore_index=True)
                                # -----------------------------------------------------------

                                fig = px.area(df_plot, x='created_at', y='saldo_acc', template="plotly_dark")
                                if meta_alvo > 0:
                                    fig.add_hline(y=meta_alvo, line_dash="dot", line_color="green", annotation_text="Meta")
                                fig.add_hline(y=stop_real, line_dash="dash", line_color="red", annotation_text="Stop")
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("Sem trades registrados neste grupo para gerar gráfico.")

                        with c_proj:
                            st.markdown("##### 🎯 Projeção")
                            # Barra de Progresso
                            if meta_alvo > 0:
                                total_path = meta_alvo - base_progresso
                                done_path = saldo_atual_unitario - base_progresso
                                pct = min(1.0, max(0.0, done_path / total_path)) if total_path > 0 else 0
                                st.write(f"Progresso da Fase: {pct*100:.1f}%")
                                st.progress(pct)
                            
                            # Faltam X Trades
                            media_grupo = trades_g['resultado'].mean() if not trades_g.empty else 0
                            if meta_alvo > 0 and falta > 0 and media_grupo > 0:
                                trades_nec = int(falta / media_grupo) + 1
                                st.info(f"Faltam **{trades_nec} trades** na média do grupo (${media_grupo:.0f})")
                            elif meta_alvo > 0 and falta <= 0:
                                st.success("Meta Atingida!")
                            elif meta_alvo == 0:
                                st.success("Fase de Renda (Saque Livre)")
                            else:
                                st.warning("Opere mais para projetar.")

                    else:
                        st.info("Este grupo não possui contas vinculadas.")
                else:
                    st.info("Cadastre contas para ver o monitor.")

    # --- 10. CONFIGURAR ATM ---
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
            st.subheader("📋 Estratégias Salvas")
            if st.button("✨ Criar Nova (Limpar)", use_container_width=True):
                reset_atm_form(); st.rerun()
            if existing_atms:
                for item in existing_atms:
                    with st.expander(f"📍 {item['nome']}", expanded=False):
                        st.write(f"**Lote:** {item['lote']} | **Stop:** {item['stop']}")
                        c_edit, c_del = st.columns(2)
                        if c_edit.button("✏️ Editar", key=f"edit_{item['id']}"):
                            p_data = item['parciais'] if isinstance(item['parciais'], list) else json.loads(item['parciais'])
                            st.session_state.atm_form_data = {
                                "id": item['id'], "nome": item['nome'], "lote": item['lote'],
                                "stop": item['stop'], "parciais": p_data
                            }
                            st.rerun()
                        if c_del.button("🗑️ Excluir", key=f"del_{item['id']}"):
                            supabase.table("atm_configs").delete().eq("id", item['id']).execute()
                            if st.session_state.atm_form_data["id"] == item['id']: reset_atm_form()
                            st.rerun()
            else: st.info("Nenhuma estratégia salva.")

        with c_form:
            form_data = st.session_state.atm_form_data
            titulo = f"✏️ Editando: {form_data['nome']}" if form_data["id"] else "✨ Nova Estratégia"
            st.subheader(titulo)
            
            new_nome = st.text_input("Nome da Estratégia", value=form_data["nome"])
            c_l, c_s = st.columns(2)
            new_lote = c_l.number_input("Lote Total", min_value=1, value=int(form_data["lote"]))
            new_stop = c_s.number_input("Stop Padrão (Pts)", min_value=0.0, value=float(form_data["stop"]), step=0.25)
            
            st.markdown("---")
            st.write("🎯 Configuração de Alvos")
            c_add, c_rem = st.columns([1, 4])
            
            if c_add.button("➕ Adicionar Alvo"): 
                st.session_state.atm_form_data["parciais"].append({"pts": 0.0, "qtd": 1})
                st.rerun()
            if c_rem.button("➖ Remover Último") and len(form_data["parciais"]) > 1: 
                st.session_state.atm_form_data["parciais"].pop()
                st.rerun()
            
            updated_partials = []
            total_aloc = 0
            for i, p in enumerate(form_data["parciais"]):
                c1, c2 = st.columns(2)
                p_pts = c1.number_input(f"Alvo {i+1} (Pts)", value=float(p["pts"]), key=f"edm_pts_{i}", step=0.25)
                p_qtd = c2.number_input(f"Qtd {i+1}", value=int(p["qtd"]), min_value=1, key=f"edm_qtd_{i}")
                updated_partials.append({"pts": p_pts, "qtd": p_qtd})
                total_aloc += p_qtd
            
            if total_aloc != new_lote: st.warning(f"⚠️ Atenção: Soma das parciais ({total_aloc}) difere do Lote Total ({new_lote}).")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("💾 SALVAR ESTRATÉGIA", use_container_width=True):
                payload = {"nome": new_nome, "lote": new_lote, "stop": new_stop, "parciais": updated_partials}
                if form_data["id"]:
                    supabase.table("atm_configs").update(payload).eq("id", form_data["id"]).execute()
                    st.toast("Atualizado!", icon="✅")
                else:
                    supabase.table("atm_configs").insert(payload).execute()
                    st.toast("Criado!", icon="✨")
                time.sleep(1); reset_atm_form(); st.rerun()

    # --- 11. HISTÓRICO ---
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
                
                # Filtro de Grupo (Master/Admin)
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
                else: st.info("Sem Print disponível.")
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.write(f"📅 **Data:** {row['data']}")
                c1.write(f"📈 **Ativo:** {row['ativo']}")
                c2.write(f"⚖️ **Lote:** {row['lote']}")
                c2.write(f"🎯 **Médio:** {row['pts_medio']:.2f} pts")
                c3.write(f"🔄 **Direção:** {row['direcao']}")
                c3.write(f"🧠 **Contexto:** {row['contexto']}")
                c3.write(f"🧠 **Estado:** {row.get('comportamento', '-')}")
                
                if ROLE in ['master', 'admin']:
                    st.write(f"📂 **Grupo:** {row['grupo_vinculo']}")
                
                res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
                st.markdown(f"<h1 style='color:{res_c}; text-align:center; font-size:40px;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
                
                if st.button("🗑️ DELETAR REGISTRO", type="primary", use_container_width=True):
                    supabase.table("trades").delete().eq("id", row['id']).execute()
                    st.rerun()

            cols = st.columns(4)
            for i, (index, row) in enumerate(df_h.iterrows()):
                with cols[i % 4]:
                    res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    res_fmt = f"${row['resultado']:,.2f}"
                    img_html = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="width:100%; height:100%; background:#333; display:flex; align-items:center; justify-content:center; color:#555;">Sem Foto</div>'
                    
                    st.markdown(f"""
                        <div class="trade-card">
                            <div class="card-img-container">{img_html}</div>
                            <div class="card-title">{row['ativo']} - {row['direcao']}</div>
                            <div class="card-sub">{row['data']} • {row['grupo_vinculo']}</div>
                            <div class="{res_class}">{res_fmt}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("👁️ Ver", key=f"btn_{row['id']}", use_container_width=True):
                        show_trade_details(row)

    # --- 12. GERENCIAR USUÁRIOS (SÓ ADMIN) ---
    elif selected == "Gerenciar Usuários":
        if ROLE != "admin":
            st.error("Acesso Negado.")
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
                st.subheader("📋 Usuários Ativos")
                if st.button("✨ Criar Novo Usuário", use_container_width=True):
                    reset_user_form(); st.rerun()
                
                if users_list:
                    for u in users_list:
                        with st.container():
                            c1, c2, c3 = st.columns([2, 2, 1])
                            c1.write(f"👤 **{u['username']}**")
                            
                            # Ícone do Cargo
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
                else: st.info("Nenhum usuário encontrado.")

            with c_form:
                u_data = st.session_state.user_form_data
                titulo = f"✏️ Editando: {u_data['username']}" if u_data["id"] else "✨ Novo Usuário"
                st.subheader(titulo)
                
                form_user = st.text_input("Login (Username)", value=u_data["username"])
                form_pass = st.text_input("Senha (Password)", value=u_data["password"], type="default")
                
                role_opts = ["user", "master", "admin"]
                curr_role = u_data["role"] if u_data["role"] in role_opts else "user"
                form_role = st.selectbox("Nível de Acesso", role_opts, index=role_opts.index(curr_role))
                
                if st.button("💾 SALVAR USUÁRIO", use_container_width=True):
                    if u_data["id"]:
                        supabase.table("users").update({"username": form_user, "password": form_pass, "role": form_role}).eq("id", u_data["id"]).execute()
                        st.toast("Usuário atualizado!", icon="✅")
                    else:
                        supabase.table("users").insert({"username": form_user, "password": form_pass, "role": form_role}).execute()
                        st.toast("Usuário criado!", icon="✨")
                    
                    time.sleep(1); reset_user_form(); st.rerun()
