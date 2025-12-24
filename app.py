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
# 2. ESTILOS CSS (Visual Profissional)
# ==============================================================================
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
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }
    
    /* Métricas do Dashboard */
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
        st.markdown('<div class="login-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div>', unsafe_allow_html=True)
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.write("---")
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
            if st.session_state.get("password_correct") == False:
                st.error("Credenciais inválidas.")
        return False
    return True

if check_password():
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER = st.session_state["logged_user"]
    ROLE = st.session_state.get("user_role", "user")

    # ==============================================================================
    # 5. FUNÇÕES DE DADOS (Expandidas e Claras)
    # ==============================================================================
    def load_trades_db():
        try:
            res = supabase.table("trades").select("*").eq("usuario", USER).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.date
                df['created_at'] = pd.to_datetime(df['created_at'])
                if 'grupo_vinculo' not in df.columns:
                    df['grupo_vinculo'] = 'Geral'
                if 'comportamento' not in df.columns:
                    df['comportamento'] = 'Normal'
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

    def card_metric(label, value, sub="", color="white", help_t=""):
        st.markdown(f'<div class="metric-container" title="{help_t}"><div class="metric-label">{label}</div><div class="metric-value" style="color:{color}">{value}</div><div class="metric-sub">{sub}</div></div>', unsafe_allow_html=True)

    # ==============================================================================
    # 6. SIDEBAR
    # ==============================================================================
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
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()

    # ==============================================================================
    # 7. DASHBOARD (Visão Geral)
    # ==============================================================================
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df = load_trades_db()
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
                    c1, c2, c4 = st.columns([1, 1, 2])
                    sel_grp = "Todos"
                
                d_i = c1.date_input("Início", df['data'].min())
                d_f = c2.date_input("Fim", df['data'].max())
                f_ctx = c4.multiselect("Contextos", list(df['contexto'].unique()), default=list(df['contexto'].unique()))

            mask = (df['data'] >= d_i) & (df['data'] <= d_f) & (df['contexto'].isin(f_ctx))
            if sel_grp != "Todos":
                mask &= (df['grupo_vinculo'] == sel_grp)
            df_f = df[mask].copy()

            if not df_f.empty:
                # --- KPI CARDS ---
                t_tr = len(df_f)
                net = df_f['resultado'].sum()
                wins = df_f[df_f['resultado'] > 0]
                losses = df_f[df_f['resultado'] < 0]
                
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
                with g1:
                    st.plotly_chart(px.area(df_f, x='created_at', y='equity', title="Curva de Lucro (Geral)", template="plotly_dark").update_traces(line_color='#B20000', fillcolor='rgba(178,0,0,0.2)'), use_container_width=True)
                with g2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.plotly_chart(px.pie(df_f, names='contexto', values='lote', title="Contexto", template="plotly_dark", hole=0.4), use_container_width=True)
            else:
                st.info("Sem dados para o filtro.")
        else:
            st.warning("Banco de dados vazio.")

    # ==============================================================================
    # 8. REGISTRAR TRADE (CONTEXTO A, B, C + ESTADO MENTAL)
    # ==============================================================================
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db()
        df_grupos = load_grupos_config()
        
        c_atm, c_grp = st.columns([3, 1.5])
        with c_atm:
            atm_sel = st.selectbox("🎯 ATM", ["Manual"] + list(atm_db.keys()))
        with c_grp:
            g_sel = "Geral"
            if ROLE in ["master", "admin"]:
                if not df_grupos.empty:
                    g_sel = st.selectbox("📂 Grupo", sorted(df_grupos['nome'].unique()))
                else:
                    st.caption("Crie grupos em 'Contas'")

        if atm_sel != "Manual":
            cf = atm_db[atm_sel]
            lt_d = int(cf["lote"])
            stp_d = float(cf["stop"])
            parc = json.loads(cf["parciais"]) if isinstance(cf["parciais"], str) else cf["parciais"]
        else:
            lt_d, stp_d, parc = 1, 0.0, []

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date())
            atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
            psi = st.selectbox("Estado Mental", ["Focado/Bem", "Ansioso", "Vingativo", "Cansado", "Fomo", "Neutro"])
        with f2:
            lt = st.number_input("Lote", min_value=1, value=lt_d)
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_d, step=0.25)
            if stp > 0:
                st.markdown(f'<div class="risco-alert">📉 Risco: ${stp * MULTIPLIERS[atv] * lt:,.2f}</div>', unsafe_allow_html=True)
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
                p = cp.number_input(f"Pts {i+1}", value=vp, key=f"p_{i}_{atm_sel}")
                q = cq.number_input(f"Qtd {i+1}", value=vq, key=f"q_{i}_{atm_sel}")
                saidas.append({"pts": p, "qtd": q})
                aloc += q
            if lt != aloc:
                st.markdown(f'<div class="piscante-erro">SALDO: {lt - aloc} CTTS</div>', unsafe_allow_html=True)

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

    # ==============================================================================
    # 9. ABA CONTAS (COM MONITOR DE PERFORMANCE NA 4ª ABA - VERIFIQUE AQUI!)
    # ==============================================================================
    elif selected == "Contas":
        st.title("💼 Gestão de Portfólio")
        if ROLE not in ['master', 'admin']:
            st.error("Restrito.")
        else:
            # === AQUI ESTÃO AS ABAS, INCLUINDO A NOVA ===
            t1, t2, t3, t4 = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📊 Visão Geral", "🚀 Monitor de Performance"])
            
            with t1:
                st.subheader("Novo Grupo")
                with st.form("form_grupo"):
                    gn = st.text_input("Nome")
                    if st.form_submit_button("Criar"):
                        if gn:
                            supabase.table("grupos_config").insert({"usuario": USER, "nome": gn}).execute()
                            st.success("Criado!"); time.sleep(1); st.rerun()
                st.divider(); st.write("Grupos:"); df_g = load_grupos_config()
                for i, r in df_g.iterrows():
                    c1, c2 = st.columns([4,1]); c1.info(f"📂 {r['nome']}")
                    if c2.button("X", key=f"dg_{r['id']}"): supabase.table("grupos_config").delete().eq("id", r['id']).execute(); st.rerun()

            with t2:
                st.subheader("Adicionar Conta")
                df_g = load_grupos_config()
                if df_g.empty: st.warning("Crie grupo.")
                else:
                    with st.form("form_conta"):
                        gs = st.selectbox("Grupo", sorted(df_g['nome'].unique()))
                        ci = st.text_input("ID")
                        si = st.number_input("Saldo ATUAL", value=150000.0, step=100.0)
                        fa = st.selectbox("Fase", ["Fase 1 (Teste)", "Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saque)"])
                        if st.form_submit_button("Salvar"):
                            if ci:
                                supabase.table("contas_config").insert({"usuario": USER, "grupo_nome": gs, "conta_identificador": ci, "saldo_inicial": si, "fase": fa}).execute()
                                st.success("Salvo!"); time.sleep(1); st.rerun()

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
                                sb = float(r['saldo_inicial']); sb = 150000.0 if sb < 1000 else sb
                                sat = sb + lg
                                c1, c2, c3 = st.columns([3, 0.5, 0.5])
                                c1.markdown(f"💳 **{r['conta_identificador']}** | {r['fase']} | Saldo: **${sat:,.2f}** (<span style='color:{'#00FF88' if (sat-sb)>=0 else '#FF4B4B'}'>${sat-sb:+,.2f}</span>)", unsafe_allow_html=True)
                                with c2.popover("⚙️"):
                                    ns = st.number_input("Saldo Real", value=sb, key=f"ns_{r['id']}")
                                    nf = st.selectbox("Fase", ["Fase 1 (Teste)", "Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saque)"], key=f"nf_{r['id']}")
                                    if st.button("Salvar", key=f"sv_{r['id']}"):
                                        supabase.table("contas_config").update({"saldo_inicial": ns, "fase": nf}).eq("id", r['id']).execute(); st.rerun()
                                if c3.button("🗑️", key=f"dl_{r['id']}"):
                                    supabase.table("contas_config").delete().eq("id", r['id']).execute(); st.rerun()
                else: st.info("Vazio.")

            # --- MONITOR DE PERFORMANCE (AQUI ESTÃO AS NOVAS FUNÇÕES) ---
            with t4:
                st.subheader("🚀 Monitor de Performance (Apex 150k)")
                df_c = load_contas_config(); df_t = load_trades_db()
                if not df_t.empty: df_t = df_t[df_t['usuario'] == USER]

                if not df_c.empty:
                    grps = sorted(df_c['grupo_nome'].unique())
                    
                    # --- FILTRO 1: SELETOR DE GRUPO E VISUALIZAÇÃO ---
                    col_sel, col_vis = st.columns([2, 1])
                    sel_g = col_sel.selectbox("Grupo", grps)
                    vis_mode = col_vis.radio("Visualização", ["Trade a Trade", "Diário"], horizontal=True)

                    # --- FILTRO 2: DATAS ---
                    c_d1, c_d2 = st.columns(2)
                    min_d = df_t['data'].min() if not df_t.empty else datetime.now().date()
                    max_d = df_t['data'].max() if not df_t.empty else datetime.now().date()
                    d_ini = c_d1.date_input("De", min_d)
                    d_fim = c_d2.date_input("Até", max_d)

                    contas_g = df_c[df_c['grupo_nome'] == sel_g]
                    trades_g = df_t[df_t['grupo_vinculo'] == sel_g] if not df_t.empty else pd.DataFrame()
                    
                    if not trades_g.empty:
                        trades_g = trades_g[(trades_g['data'] >= d_ini) & (trades_g['data'] <= d_fim)]

                    if not contas_g.empty:
                        ref = contas_g.iloc[0]; fase = ref['fase']
                        saldo_base_db = float(ref['saldo_inicial'])
                        # Proteção: Se saldo for 0, assume 150k
                        saldo_base = 150000.0 if saldo_base_db < 1000 else saldo_base_db 
                        
                        lucro_filt = trades_g['resultado'].sum() if not trades_g.empty else 0.0
                        saldo_atual = saldo_base + lucro_filt

                        meta = 0.0; base_prog = 150000.0
                        if "Fase 1" in fase: meta = 159000.0
                        elif "Fase 2" in fase: meta = 155100.0
                        elif "Fase 3" in fase: meta = 160000.0; base_prog = 155100.0
                        elif "Fase 4" in fase: meta = 0.0; base_prog = 150100.0

                        # Métricas do Topo
                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Saldo Atual", f"${saldo_atual:,.2f}")
                        k2.metric("Lucro Período", f"${lucro_filt:+,.2f}")
                        
                        # Se não tem trades, o buffer é calculado no saldo base
                        k3.metric("Contas", f"{len(contas_g)}")
                        k4.metric("Fase", f"{fase}")

                        st.divider()
                        cg, cp = st.columns([2, 1])
                        
                        with cg:
                            st.markdown("##### 🌊 Curva de Saldo & Trailing Stop")
                            
                            # --- PREPARAÇÃO DOS DADOS PARA O GRÁFICO ---
                            if not trades_g.empty:
                                if vis_mode == "Diário":
                                    # Agrupamento Diário
                                    trades_g['data'] = pd.to_datetime(trades_g['data'])
                                    df_plot = trades_g.groupby('data')['resultado'].sum().reset_index()
                                    # O saldo acumulado deve somar ao Saldo Base
                                    df_plot['saldo_acc'] = df_plot['resultado'].cumsum() + saldo_base
                                    df_plot.rename(columns={'data': 'eixo_x'}, inplace=True)
                                else:
                                    # Trade a Trade
                                    df_plot = trades_g.sort_values('created_at').copy()
                                    df_plot['saldo_acc'] = df_plot['resultado'].cumsum() + saldo_base
                                    df_plot.rename(columns={'created_at': 'eixo_x'}, inplace=True)
                                
                                # Adiciona Ponto Inicial (Antes do primeiro trade, vale o Saldo Base)
                                start_x = df_plot['eixo_x'].min() - (timedelta(days=1) if vis_mode == "Diário" else timedelta(minutes=30))
                                start_row = pd.DataFrame([{'eixo_x': start_x, 'saldo_acc': saldo_base}])
                                df_plot = pd.concat([start_row, df_plot], ignore_index=True)
                            else:
                                # Gráfico Vazio com linha reta no Saldo Base
                                df_plot = pd.DataFrame([
                                    {'eixo_x': datetime.now() - timedelta(hours=1), 'saldo_acc': saldo_base},
                                    {'eixo_x': datetime.now(), 'saldo_acc': saldo_base}
                                ])

                            # --- CÁLCULO DO TRAILING STOP DINÂMICO ---
                            # 1. Calcula o HWM (Maior saldo atingido até o momento)
                            df_plot['hwm'] = df_plot['saldo_acc'].cummax()
                            
                            # 2. Define o limite do stop (150.100 ou customizado)
                            limit_stop = 150100.0
                            
                            # 3. Regra: Stop = HWM - 5000
                            # Se o saldo inicial já é maior que 155.100, o stop nasce travado em 150.100
                            if saldo_base > 155100: 
                                df_plot['stop_line'] = 150100.0
                            else:
                                df_plot['stop_raw'] = df_plot['hwm'] - 5000.0
                                # O stop nunca pode descer, mas o HWM garante isso.
                                # O stop nunca pode passar de 150.100.
                                df_plot['stop_line'] = df_plot['stop_raw'].clip(upper=limit_stop)

                            # PLOTAGEM
                            fig = px.line(df_plot, x='eixo_x', y='saldo_acc', template="plotly_dark")
                            fig.update_traces(name='Saldo', line_color='#2E93fA', fill='tozeroy', fillcolor='rgba(46, 147, 250, 0.1)')
                            
                            # Adiciona a linha de Stop (Vermelha, Degrau)
                            fig.add_scatter(x=df_plot['eixo_x'], y=df_plot['stop_line'], mode='lines', 
                                          line=dict(color='#FF4B4B', dash='dash', shape='hv'), name='Trailing Stop')
                            
                            if meta > 0: 
                                fig.add_hline(y=meta, line_dash="dot", line_color="#00FF88", annotation_text="Meta")
                            
                            # Zoom Inteligente (Ignora o Zero)
                            # Foca entre o Menor Stop e a Maior Meta/Saldo
                            min_y = min(df_plot['stop_line'].min(), df_plot['saldo_acc'].min()) - 1000
                            max_y = max(meta if meta > 0 else saldo_atual, df_plot['saldo_acc'].max()) + 1000
                            fig.update_layout(yaxis_range=[min_y, max_y], showlegend=True, legend=dict(orientation="h", y=1.02))
                            
                            st.plotly_chart(fig, use_container_width=True)

                        with cp:
                            st.markdown("##### 🎯 Status")
                            
                            # Cálculo do Buffer atual (Último ponto)
                            ultimo_stop = df_plot['stop_line'].iloc[-1]
                            buffer_atual = saldo_atual - ultimo_stop
                            
                            cor_buff = "inverse" if buffer_atual < 2500 else "normal"
                            st.metric("Buffer Real", f"${buffer_atual:,.2f}", "Distância do Stop", delta_color=cor_buff)

                            if meta > 0:
                                total = meta - base_prog
                                feito = saldo_atual - base_prog
                                pct = min(1.0, max(0.0, feito / total if total > 0 else 0))
                                st.write(f"Progresso: {pct*100:.1f}%"); st.progress(pct)
                            
                            mg = trades_g['resultado'].mean() if not trades_g.empty else 0
                            if meta > 0 and (meta-saldo_atual) > 0 and mg > 0:
                                tn = int((meta-saldo_atual) / mg) + 1
                                st.info(f"Faltam **{tn} trades** na média (${mg:.0f})")
                            elif meta > 0 and (meta-saldo_atual) <= 0: st.success("Meta Atingida!")
                    else: st.info("Grupo sem contas.")
                else: st.info("Cadastre contas.")

    # ==============================================================================
    # 10. CONFIGURAR ATM
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
    # 11. HISTÓRICO
    # ==============================================================================
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        dfh = load_trades_db()
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
            
            @st.dialog("Detalhes")
            def show_trade_details(row):
                if row.get('prints'): st.image(row['prints'])
                c1, c2 = st.columns(2)
                c1.write(f"📅 {row['data']} | {row['ativo']}")
                c2.write(f"💰 ${row['resultado']:,.2f}")
                if st.button("🗑️ Deletar"): supabase.table("trades").delete().eq("id", row['id']).execute(); st.rerun()

            cols = st.columns(4)
            for i, r in enumerate(dfh.iterrows()):
                row = r[1]
                cls = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                img = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="height:100px;background:#222"></div>'
                with cols[i % 4]:
                    st.markdown(f"""<div class="trade-card"><div class="card-img-container">{img}</div><div class="{cls}">${row['resultado']:,.2f}</div></div>""", unsafe_allow_html=True)
                    if st.button("Ver", key=f"v_{row['id']}"): show_trade_details(row)

    # ==============================================================================
    # 12. GERENCIAR USUÁRIOS
    # ==============================================================================
    elif selected == "Gerenciar Usuários" and ROLE == "admin":
        st.title("👥 Usuários")
        us = supabase.table("users").select("*").execute().data
        c1, c2 = st.columns([1, 1.5])
        with c2:
            for u in us:
                st.write(f"👤 {u['username']} ({u.get('role','user')})")
                if st.button("Edit", key=f"e_{u['id']}"): st.session_state.uf = u; st.rerun()
        with c1:
            ud = st.session_state.get("uf", {"id": None, "username": "", "password": "", "role": "user"})
            nu = st.text_input("User", value=ud["username"]); np = st.text_input("Pass", value=ud["password"]); nr = st.selectbox("Role", ["user", "master", "admin"])
            if st.button("Salvar"):
                pay = {"username": nu, "password": np, "role": nr}
                if ud["id"]: supabase.table("users").update(pay).eq("id", ud["id"]).execute()
                else: supabase.table("users").insert(pay).execute()
                st.rerun()
