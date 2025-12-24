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

# ==============================================================================
# 1. CONFIGURAÇÃO INICIAL E CONEXÃO
# ==============================================================================
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro crítico: Chaves do Supabase não encontradas nos Secrets.")
    st.stop()

st.set_page_config(page_title="EvoTrade Terminal", layout="wide", page_icon="📈")

# ==============================================================================
# 2. ESTILOS CSS
# ==============================================================================
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

# ==============================================================================
# 3. SISTEMA DE LOGIN
# ==============================================================================
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
            st.error(f"Erro de conexão: {e}")

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown("""
            <style>
            .login-container { max-width: 400px; margin: 50px auto; padding: 30px; background-color: #161616; border-radius: 15px; border: 1px solid #B20000; text-align: center; }
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
            if st.session_state.get("password_correct") == False: st.error("Credenciais inválidas.")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if check_password():
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER = st.session_state["logged_user"]
    ROLE = st.session_state.get("user_role", "user")

    # ==============================================================================
    # 5. FUNÇÕES DE DADOS
    # ==============================================================================
    def load_trades_db():
        try:
            res = supabase.table("trades").select("*").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.date
                df['created_at'] = pd.to_datetime(df['created_at'])
                if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
                if 'comportamento' not in df.columns: df['comportamento'] = 'Normal'
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
            
    def load_grupos_config():
        try:
            res = supabase.table("grupos_config").select("*").eq("usuario", USER).execute()
            return pd.DataFrame(res.data)
        except: return pd.DataFrame()

    def card_metric(label, value, sub="", color="white", help_t=""):
        st.markdown(f'<div class="metric-container" title="{help_t}"><div class="metric-label">{label}</div><div class="metric-value" style="color:{color}">{value}</div><div class="metric-sub">{sub}</div></div>', unsafe_allow_html=True)

    # ==============================================================================
    # 6. SIDEBAR
    # ==============================================================================
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        icons = ["grid", "currency-dollar", "gear", "clock"]
        if ROLE in ['master', 'admin']: menu.insert(2, "Contas"); icons.insert(2, "briefcase")
        if ROLE == 'admin': menu.append("Gerenciar Usuários"); icons.append("people")
        selected = option_menu(None, menu, icons=icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # ==============================================================================
    # 7. DASHBOARD
    # ==============================================================================
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df_raw = load_trades_db()
        
        if not df_raw.empty:
            df = df_raw[df_raw['usuario'] == USER]
            
            if not df.empty:
                with st.expander("🔍 Filtros Avançados", expanded=True):
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
                    # --- PAINEL APEX (DASHBOARD) ---
                    if sel_grp != "Todos" and ROLE in ['master', 'admin']:
                        st.markdown(f"### 🛡️ Monitor Apex: {sel_grp}")
                        df_c = load_contas_config()
                        contas_g = df_c[df_c['grupo_nome'] == sel_grp]
                        if not contas_g.empty:
                            ref = contas_g.iloc[0]; fase = ref['fase']; saldo_cadastrado = float(ref['saldo_inicial'])
                            saldo_cadastrado = 150000.0 if saldo_cadastrado < 1000 else saldo_cadastrado
                            
                            lucro_periodo = df_f['resultado'].sum()
                            saldo_atual_est = saldo_cadastrado + lucro_periodo
                            
                            equity_curve = df_f.sort_values('created_at')['resultado'].cumsum() + saldo_cadastrado
                            hwm = max(saldo_cadastrado, equity_curve.max()) if not equity_curve.empty else saldo_cadastrado
                            
                            trailing_stop = hwm - 5000.0
                            stop_real = 150100.0 if (saldo_cadastrado > 155100 or trailing_stop > 150100) else min(trailing_stop, 150100.0)
                            buffer_vida = saldo_atual_est - stop_real
                            
                            meta_alvo = 0.0; base_prog = 150000.0
                            if "Fase 1" in fase: meta_alvo = 159000.0
                            elif "Fase 2" in fase: meta_alvo = 155100.0
                            elif "Fase 3" in fase: meta_alvo = 160000.0; base_prog = 155100.0
                            
                            k1, k2, k3, k4 = st.columns(4)
                            k1.metric("Contas", f"{len(contas_g)}", fase)
                            k2.metric("Saldo Unitário", f"${saldo_atual_est:,.2f}", f"Stop: ${stop_real:,.0f}")
                            cor_b = "inverse" if buffer_vida < 2500 else "normal"
                            k3.metric("🔥 Buffer", f"${buffer_vida:,.2f}", "Até quebrar", delta_color=cor_b)
                            if meta_alvo > 0:
                                k4.metric("Falta Meta", f"${meta_alvo-saldo_atual_est:,.2f}", f"Alvo: ${meta_alvo:,.0f}")
                                pct = min(1.0, max(0.0, (saldo_atual_est - base_prog) / (meta_alvo - base_prog)))
                                st.progress(pct)
                            else:
                                saque = max(0, saldo_atual_est - 152600) * len(contas_g)
                                k4.metric("💰 Saque Disp.", f"${saque:,.2f}")
                        st.markdown("---")

                    # --- KPIs GERAIS ---
                    t_tr = len(df_f); net = df_f['resultado'].sum()
                    wins = df_f[df_f['resultado'] > 0]; losses = df_f[df_f['resultado'] < 0]
                    pf = (wins['resultado'].sum() / abs(losses['resultado'].sum())) if not losses.empty else float('inf')
                    wr = (len(wins)/t_tr)*100
                    avg_w = wins['resultado'].mean() if not wins.empty else 0
                    avg_l = abs(losses['resultado'].mean()) if not losses.empty else 0
                    payoff = avg_w/avg_l if avg_l > 0 else 0
                    exp = ((wr/100)*avg_w) - ((len(losses)/t_tr)*avg_l)
                    
                    df_f = df_f.sort_values('created_at')
                    df_f['equity'] = df_f['resultado'].cumsum()
                    max_dd = (df_f['equity'] - df_f['equity'].cummax()).min()

                    r1 = st.columns(4)
                    with r1[0]: card_metric("RESULTADO", f"${net:,.2f}", f"Bruto: ${wins['resultado'].sum():,.0f}", "#00FF88" if net>=0 else "#FF4B4B")
                    with r1[1]: card_metric("FATOR DE LUCRO", f"{pf:.2f}", "Ideal > 1.5", "#B20000")
                    with r1[2]: card_metric("WIN RATE", f"{wr:.1f}%", f"{len(wins)}W / {len(losses)}L", "white")
                    with r1[3]: card_metric("EXPECTATIVA", f"${exp:.2f}", "Por Trade", "#00FF88" if exp>0 else "#FF4B4B")

                    r2 = st.columns(4)
                    with r2[0]: card_metric("MÉDIA GAIN", f"${avg_w:,.2f}", "", "#00FF88")
                    with r2[1]: card_metric("MÉDIA LOSS", f"-${avg_l:,.2f}", "", "#FF4B4B")
                    with r2[2]: card_metric("PAYOFF", f"1 : {payoff:.2f}", "Risco:Retorno")
                    with r2[3]: card_metric("DRAWDOWN MÁX", f"${max_dd:,.2f}", "No Período", "#FF4B4B")

                    g1, g2 = st.columns([2, 1])
                    with g1: st.plotly_chart(px.area(df_f, x='created_at', y='equity', title="Curva de Lucro", template="plotly_dark").update_traces(line_color='#B20000', fillcolor='rgba(178,0,0,0.2)'), use_container_width=True)
                    with g2: 
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.plotly_chart(px.pie(df_f, names='contexto', values='lote', title="Contexto", template="plotly_dark", hole=0.4), use_container_width=True)

                else: st.info("Sem dados. Registre operações.")
        else: st.warning("Banco vazio.")

    # ==============================================================================
    # 8. REGISTRAR TRADE
    # ==============================================================================
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db()
        df_grupos = load_grupos_config()
        
        col_atm, col_grp = st.columns([3, 1.5])
        with col_atm: atm_sel = st.selectbox("🎯 ATM", ["Manual"] + list(atm_db.keys()))
        with col_grp:
            grupo_sel_trade = "Geral"
            if ROLE in ["master", "admin"]:
                if not df_grupos.empty:
                    lista_grupos = sorted(list(df_grupos['nome'].unique()))
                    grupo_sel_trade = st.selectbox("📂 Vincular ao Grupo", lista_grupos)
                else: st.caption("⚠️ Crie grupos na aba Contas.")
        
        if atm_sel != "Manual":
            config = atm_db[atm_sel]
            lt_default = int(config["lote"])
            stp_default = float(config["stop"])
            try:
                parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
            except: parciais_pre = []
        else:
            lt_default = 1; stp_default = 0.0; parciais_pre = []

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date())
            atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            ctx = st.selectbox("Contexto", ["Tendência", "Lateralidade", "Rompimento", "Contra-Tendência", "Outro"])
            psi = st.selectbox("Estado Mental", ["Focado/Bem", "Ansioso", "Vingativo", "Cansado", "Fomo", "Neutro"])
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
                saidas.append({"pts": pts, "qtd": qtd}); aloc += qtd
            
            if lt != aloc:
                diff = lt - aloc
                st.markdown(f'<div class="piscante-erro">{"FALTAM" if diff > 0 else "SOBRAM"} {abs(diff)} CONTRATOS</div>', unsafe_allow_html=True)
            else: st.success("✅ Posição Sincronizada")

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
                    trade_id = str(uuid.uuid4()); img_url = ""
                    if up:
                        file_path = f"{trade_id}.png"
                        supabase.storage.from_("prints").upload(file_path, up.getvalue())
                        img_url = supabase.storage.from_("prints").get_public_url(file_path)

                    supabase.table("trades").insert({
                        "id": trade_id, "data": str(dt), "ativo": atv, "contexto": ctx,
                        "direcao": dr, "lote": lt, "resultado": res_fin, "pts_medio": pt_med,
                        "prints": img_url, "usuario": USER, "grupo_vinculo": grupo_sel_trade,
                        "comportamento": psi, "risco_fin": (stp * MULTIPLIERS[atv] * lt)
                    }).execute()
                    st.balloons(); st.success(f"✅ SUCESSO! Resultado: ${res_fin:,.2f}"); time.sleep(2); st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

    # ==============================================================================
    # 9. ABA CONTAS (COM MONITOR CORRIGIDO - GRÁFICO DINÂMICO APEX)
    # ==============================================================================
    elif selected == "Contas":
        st.title("💼 Gestão de Portfólio")
        
        if ROLE not in ['master', 'admin']: st.error("Acesso restrito.")
        else:
            t1, t2, t3, t4 = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📊 Visão Geral", "🚀 Monitor de Performance"])
            
            with t1:
                st.subheader("Nova Estrutura de Contas")
                with st.form("form_grupo"):
                    novo_grupo = st.text_input("Nome do Grupo (Ex: Mesa Apex, Fase 2)")
                    if st.form_submit_button("Criar Grupo"):
                        if novo_grupo:
                            supabase.table("grupos_config").insert({"usuario": USER, "nome": novo_grupo}).execute()
                            st.success(f"Grupo '{novo_grupo}' criado!"); time.sleep(1); st.rerun()
                        else: st.warning("Digite um nome.")
                st.divider(); st.write("Grupos Existentes:")
                df_g = load_grupos_config()
                if not df_g.empty:
                    for idx, r in df_g.iterrows():
                        c1, c2 = st.columns([4,1])
                        c1.info(f"📂 {r['nome']}")
                        if c2.button("X", key=f"dg_{r['id']}"): supabase.table("grupos_config").delete().eq("id", r['id']).execute(); st.rerun()

            with t2:
                st.subheader("Adicionar Conta")
                df_g = load_grupos_config()
                if df_g.empty: st.warning("Crie um grupo antes.")
                else:
                    with st.form("form_conta"):
                        grupo_selecionado = st.selectbox("Selecione o Grupo", sorted(df_g['nome'].unique()))
                        conta_id = st.text_input("ID Conta (Ex: PA-01)")
                        saldo_ini = st.number_input("Saldo ATUAL na Corretora ($)", value=150000.0, step=100.0)
                        fase_atual = st.selectbox("Fase Atual", ["Fase 1 (Teste)", "Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saque)"])
                        
                        if st.form_submit_button("Salvar Conta"):
                            if conta_id:
                                supabase.table("contas_config").insert({
                                    "usuario": USER, "grupo_nome": grupo_selecionado, "conta_identificador": conta_id,
                                    "saldo_inicial": saldo_ini, "fase": fase_atual
                                }).execute()
                                st.success("Conta vinculada com sucesso!"); time.sleep(1); st.rerun()
                            else: st.warning("Preencha o ID da conta.")

            with t3:
                st.subheader("Monitoramento Individual")
                dc = load_contas_config(); dt = load_trades_db()
                if not dt.empty: dt = dt[dt['usuario'] == USER]
                
                if not dc.empty:
                    for g in sorted(dc['grupo_nome'].unique()):
                        with st.expander(f"📂 {g}", expanded=True):
                            tg = dt[dt['grupo_vinculo'] == g] if not dt.empty else pd.DataFrame()
                            lg = tg['resultado'].sum() if not tg.empty else 0.0
                            cg = dc[dc['grupo_nome'] == g]
                            for _, r in cg.iterrows():
                                saldo_base = float(r['saldo_inicial'])
                                if saldo_base < 100: saldo_base = 150000.0
                                atual = saldo_base + lg
                                delta = atual - saldo_base
                                cor = "#00FF88" if delta >= 0 else "#FF4B4B"
                                c1, c2, c3 = st.columns([3, 0.5, 0.5])
                                c1.markdown(f"💳 **{r['conta_identificador']}** | {r['fase']} | Saldo: **${atual:,.2f}** (<span style='color:{cor}'>${delta:+,.2f}</span>)", unsafe_allow_html=True)
                                with c2.popover("⚙️"):
                                    ns = st.number_input("Ajustar Saldo Real", value=saldo_base, key=f"ns_{r['id']}")
                                    nf = st.selectbox("Mudar Fase", ["Fase 1 (Teste)", "Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saque)"], key=f"nf_{r['id']}")
                                    if st.button("Salvar", key=f"sv_{r['id']}"):
                                        supabase.table("contas_config").update({"saldo_inicial": ns, "fase": nf}).eq("id", r['id']).execute(); st.rerun()
                                if c3.button("🗑️", key=f"dl_{r['id']}"):
                                    supabase.table("contas_config").delete().eq("id", r['id']).execute(); st.rerun()
                else: st.info("Vazio.")

            # --- ABA 4: MONITOR DE PERFORMANCE (LÓGICA DO GRÁFICO DINÂMICO DE STOP) ---
            with t4:
                st.subheader("🚀 Monitor de Performance (Apex 150k)")
                df_c = load_contas_config(); df_t = load_trades_db()
                if not df_t.empty: df_t = df_t[df_t['usuario'] == USER]

                if not df_c.empty:
                    grps = sorted(df_c['grupo_nome'].unique())
                    sel_g = st.selectbox("Selecione o Grupo para Analisar", grps)
                    
                    c_d1, c_d2 = st.columns(2)
                    min_d = df_t['data'].min() if not df_t.empty else datetime.now().date()
                    max_d = df_t['data'].max() if not df_t.empty else datetime.now().date()
                    d_ini = c_d1.date_input("De", min_d); d_fim = c_d2.date_input("Até", max_d)

                    contas_g = df_c[df_c['grupo_nome'] == sel_g]
                    trades_g = df_t[df_t['grupo_vinculo'] == sel_g] if not df_t.empty else pd.DataFrame()
                    if not trades_g.empty:
                        trades_g = trades_g[(trades_g['data'] >= d_ini) & (trades_g['data'] <= d_fim)]

                    if not contas_g.empty:
                        ref = contas_g.iloc[0]; fase = ref['fase']
                        saldo_base = float(ref['saldo_inicial'])
                        if saldo_base < 1000: saldo_base = 150000.0 
                        
                        lucro_filt = trades_g['resultado'].sum() if not trades_g.empty else 0.0
                        saldo_atual = saldo_base + lucro_filt

                        meta = 0.0; base_prog = 150000.0
                        if "Fase 1" in fase: meta = 159000.0; base_prog = 150000.0
                        elif "Fase 2" in fase: meta = 155100.0; base_prog = 150000.0
                        elif "Fase 3" in fase: meta = 160000.0; base_prog = 155100.0
                        elif "Fase 4" in fase: meta = 0.0; base_prog = 150100.0

                        # Cálculo do Stop Atual
                        if not trades_g.empty:
                            eq = trades_g.sort_values('created_at')['resultado'].cumsum() + saldo_base
                            hwm = max(saldo_base, eq.max())
                        else: hwm = saldo_base
                        
                        ts = hwm - 5000.0
                        stop_real = 150100.0 if (saldo_base > 155100 or ts > 150100) else min(ts, 150100.0)
                        buff = saldo_atual - stop_real

                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Saldo Unitário", f"${saldo_atual:,.2f}")
                        k2.metric("Lucro Período", f"${lucro_filt:+,.2f}", f"{len(contas_g)} contas")
                        k3.metric("Buffer", f"${buff:,.2f}", "Até quebrar")
                        if meta > 0: k4.metric("Falta", f"${meta-saldo_atual:,.2f}", f"Alvo: ${meta:,.0f}")
                        else: k4.metric("Modo Saque", "Sem Teto")

                        st.divider()
                        cg, cp = st.columns([2, 1])
                        
                        with cg:
                            st.markdown("##### 🌊 Curva de Evolução & Trailing Stop")
                            
                            # --- PREPARAÇÃO DOS DADOS DO GRÁFICO (COM PONTO INICIAL) ---
                            if not trades_g.empty:
                                df_evo = trades_g.sort_values('created_at').copy()
                                df_evo['saldo_acc'] = df_evo['resultado'].cumsum() + saldo_base
                                start_dt = df_evo['created_at'].min() - timedelta(minutes=30)
                            else:
                                df_evo = pd.DataFrame()
                                start_dt = datetime.now()

                            # Cria o ponto inicial artificial em 150k (ou saldo base)
                            start_row = pd.DataFrame([{'created_at': start_dt, 'saldo_acc': saldo_base}])
                            
                            if not df_evo.empty:
                                df_plot = pd.concat([start_row, df_evo[['created_at', 'saldo_acc']]], ignore_index=True)
                            else:
                                df_plot = start_row

                            # --- CÁLCULO DA CURVA DE STOP DINÂMICO ---
                            # Calcula o HWM linha a linha para desenhar o Stop subindo
                            df_plot['hwm'] = df_plot['saldo_acc'].cummax()
                            
                            # Se a conta já começou acima de 155.100, o stop é travado em 150.100 desde o inicio
                            if saldo_base > 155100:
                                df_plot['stop_curve'] = 150100.0
                            else:
                                # Regra: HWM - 5000, mas nunca passa de 150.100
                                df_plot['stop_curve'] = (df_plot['hwm'] - 5000).clip(upper=150100.0)

                            # PLOTAGEM
                            fig = px.line(df_plot, x='created_at', y='saldo_acc', template="plotly_dark")
                            
                            # Linha de Saldo (Azul)
                            fig.update_traces(name='Saldo', line_color='#2E93fA', fill='tozeroy', fillcolor='rgba(46, 147, 250, 0.1)')
                            
                            # Linha de Stop Dinâmico (Vermelha Tracejada)
                            fig.add_scatter(x=df_plot['created_at'], y=df_plot['stop_curve'], mode='lines', 
                                          line=dict(color='#FF4B4B', dash='dash'), name='Trailing Stop')
                            
                            # Linha de Meta (Verde Fixa)
                            if meta > 0: 
                                fig.add_hline(y=meta, line_dash="dot", line_color="#00FF88", annotation_text="Meta")
                            
                            # --- ZOOM AUTOMÁTICO INTELIGENTE ---
                            # Foca apenas na região entre o Stop e a Meta/Saldo (ignora o zero)
                            vals = pd.concat([df_plot['saldo_acc'], df_plot['stop_curve']])
                            min_y = vals.min() - 500
                            max_y = max(meta if meta > 0 else 0, vals.max()) + 500
                            fig.update_layout(yaxis_range=[min_y, max_y], showlegend=True, legend=dict(orientation="h", y=1.02, x=0))
                            
                            st.plotly_chart(fig, use_container_width=True)

                        with cp:
                            st.markdown("##### 🎯 Projeção")
                            if meta > 0:
                                total_p = meta - base_prog
                                done_p = saldo_atual - base_prog
                                pct = min(1.0, max(0.0, done_p / total_p if total_p > 0 else 0))
                                st.write(f"Progresso: {pct*100:.1f}%")
                                st.progress(pct)
                            
                            mg = trades_g['resultado'].mean() if not trades_g.empty else 0
                            if meta > 0 and (meta-saldo_atual) > 0 and mg > 0:
                                tn = int((meta-saldo_atual) / mg) + 1
                                st.info(f"Faltam **{tn} trades** na média (${mg:.0f})")
                            elif meta > 0 and (meta-saldo_atual) <= 0: st.success("Meta Atingida!")
                            
                    else: st.info("Grupo sem contas.")
                else: st.info("Cadastre contas.")

    # ==============================================================================
    # 10. CONFIGURAR ATM (MANTIDO)
    # ==============================================================================
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")
        if "atm_form_data" not in st.session_state: st.session_state.atm_form_data = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        def reset_atm_form(): st.session_state.atm_form_data = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        res = supabase.table("atm_configs").select("*").order("nome").execute(); existing_atms = res.data
        c_form, c_list = st.columns([1.5, 1])
        with c_list:
            st.subheader("📋 Estratégias Salvas")
            if st.button("✨ Criar Nova (Limpar)", use_container_width=True): reset_atm_form(); st.rerun()
            if existing_atms:
                for item in existing_atms:
                    with st.expander(f"📍 {item['nome']}", expanded=False):
                        st.write(f"**Lote:** {item['lote']} | **Stop:** {item['stop']}")
                        c_edit, c_del = st.columns(2)
                        if c_edit.button("✏️ Editar", key=f"edit_{item['id']}"):
                            p_data = item['parciais'] if isinstance(item['parciais'], list) else json.loads(item['parciais'])
                            st.session_state.atm_form_data = {"id": item['id'], "nome": item['nome'], "lote": item['lote'], "stop": item['stop'], "parciais": p_data}; st.rerun()
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
            st.markdown("---"); st.write("🎯 Configuração de Alvos"); c_add, c_rem = st.columns([1, 4])
            if c_add.button("➕ Adicionar Alvo"): st.session_state.atm_form_data["parciais"].append({"pts": 0.0, "qtd": 1}); st.rerun()
            if c_rem.button("➖ Remover Último") and len(form_data["parciais"]) > 1: st.session_state.atm_form_data["parciais"].pop(); st.rerun()
            updated_partials = []; total_aloc = 0
            for i, p in enumerate(form_data["parciais"]):
                c1, c2 = st.columns(2)
                p_pts = c1.number_input(f"Alvo {i+1} (Pts)", value=float(p["pts"]), key=f"edm_pts_{i}", step=0.25)
                p_qtd = c2.number_input(f"Qtd {i+1}", value=int(p["qtd"]), min_value=1, key=f"edm_qtd_{i}")
                updated_partials.append({"pts": p_pts, "qtd": p_qtd}); total_aloc += p_qtd
            if total_aloc != new_lote: st.warning(f"⚠️ Atenção: Soma das parciais ({total_aloc}) difere do Lote Total ({new_lote}).")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 SALVAR ESTRATÉGIA", use_container_width=True):
                payload = {"nome": new_nome, "lote": new_lote, "stop": new_stop, "parciais": updated_partials}
                if form_data["id"]: supabase.table("atm_configs").update(payload).eq("id", form_data["id"]).execute(); st.toast("Atualizado!", icon="✅")
                else: supabase.table("atm_configs").insert(payload).execute(); st.toast("Criado!", icon="✨")
                time.sleep(1); reset_atm_form(); st.rerun()

    # ==============================================================================
    # 11. HISTÓRICO (CORRIGIDO: load_trades_db)
    # ==============================================================================
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        dfh = load_trades_db() # NOME CORRIGIDO AQUI
        if not dfh.empty:
            c1, c2, c3, c4 = st.columns(4)
            fa = c1.multiselect("Ativo", ["NQ", "MNQ"])
            fr = c2.selectbox("Resultado", ["Todos", "Wins", "Losses"])
            fc = c3.multiselect("Contexto", list(dfh['contexto'].unique()))
            fg = c4.multiselect("Grupo", list(dfh['grupo_vinculo'].unique())) if ROLE in ["master", "admin"] else []
            
            if fa: dfh = dfh[dfh['ativo'].isin(fa)]
            if fc: dfh = dfh[dfh['contexto'].isin(fc)]
            if fg: dfh = dfh[dfh['grupo_vinculo'].isin(fg)]
            if fr == "Wins": dfh = dfh[dfh['resultado'] > 0]
            if fr == "Losses": dfh = dfh[dfh['resultado'] < 0]
            df_h = dfh.sort_values('created_at', ascending=False)
            
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
                if ROLE in ['master', 'admin']: st.write(f"📂 **Grupo:** {row['grupo_vinculo']}")
                res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
                st.markdown(f"<h1 style='color:{res_c}; text-align:center; font-size:40px;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
                if st.button("🗑️ DELETAR REGISTRO", type="primary", use_container_width=True):
                    supabase.table("trades").delete().eq("id", row['id']).execute(); st.rerun()

            cols = st.columns(4)
            for i, (index, row) in enumerate(df_h.iterrows()):
                with cols[i % 4]:
                    res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    res_fmt = f"${row['resultado']:,.2f}"
                    img_html = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="width:100%; height:100%; background:#333; display:flex; align-items:center; justify-content:center; color:#555;">Sem Foto</div>'
                    st.markdown(f"""<div class="trade-card"><div class="card-img-container">{img_html}</div><div class="card-title">{row['ativo']} - {row['direcao']}</div><div class="card-sub">{row['data']} • {row['grupo_vinculo']}</div><div class="{res_class}">{res_fmt}</div></div>""", unsafe_allow_html=True)
                    if st.button("👁️ Ver", key=f"btn_{row['id']}", use_container_width=True): show_trade_details(row)

    # ==============================================================================
    # 12. GERENCIAR USUÁRIOS (MANTIDO)
    # ==============================================================================
    elif selected == "Gerenciar Usuários":
        if ROLE != "admin": st.error("Acesso Negado.")
        else:
            st.title("👥 Gestão de Usuários")
            if "user_form_data" not in st.session_state: st.session_state.user_form_data = {"id": None, "username": "", "password": "", "role": "user"}
            def reset_user_form(): st.session_state.user_form_data = {"id": None, "username": "", "password": "", "role": "user"}
            res = supabase.table("users").select("*").execute(); users_list = res.data
            c_form, c_list = st.columns([1, 1.5])
            with c_list:
                st.subheader("📋 Usuários Ativos")
                if st.button("✨ Criar Novo Usuário", use_container_width=True): reset_user_form(); st.rerun()
                if users_list:
                    for u in users_list:
                        with st.container():
                            c1, c2, c3 = st.columns([2, 2, 1])
                            c1.write(f"👤 **{u['username']}**")
                            badge = "👑 Admin" if u.get('role') == 'admin' else ("🛡️ Master" if u.get('role') == 'master' else "👤 User")
                            c2.write(badge)
                            col_edit, col_del = st.columns(2)
                            if col_edit.button("✏️", key=f"u_edit_{u['id']}"): st.session_state.user_form_data = {"id": u['id'], "username": u['username'], "password": u['password'], "role": u.get('role', 'user')}; st.rerun()
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
