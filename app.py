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

    # --- 7. DASHBOARD (LÓGICA APEX 150K) ---
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df = load_trades()
        if not df.empty:
            with st.expander("🔍 Filtros", expanded=True):
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
                # --- PAINEL INTELIGENTE APEX ---
                if sel_grp != "Todos" and ROLE in ['master', 'admin']:
                    st.markdown(f"### 🛡️ Gestão: {sel_grp}")
                    df_c = load_contas_config()
                    contas_g = df_c[df_c['grupo_nome'] == sel_grp]
                    
                    if not contas_g.empty:
                        # Referência (Modelo da 1ª conta do grupo)
                        ref_conta = contas_g.iloc[0]
                        fase = ref_conta['fase']
                        saldo_inicial_corretora = float(ref_conta['saldo_inicial']) # O valor que você cadastrou
                        lucro_acumulado_app = df_f['resultado'].sum() # O lucro registrado no APP
                        
                        # Saldo Real Estimado = O que tava na corretora + O que fez no app
                        saldo_atual_estimado = saldo_inicial_corretora + lucro_acumulado_app
                        
                        # --- REGRAS DE NEGÓCIO APEX 150K ---
                        # Tamanho conta: 150k | Trailing Max: 5k | Trailing Para em: 150.100
                        tamanho_conta = 150000.0
                        limite_trailing_stop = 150100.0
                        
                        # Definição de Metas e Limites por Fase
                        meta_fase = 0.0
                        drawdown_atual = 0.0
                        buffer_vida = 0.0
                        
                        if "Fase 1" in fase: # Teste: 150k -> 159k
                            meta_fase = 159000.0
                            # No teste o trailing sobe. Vamos assumir pior caso: High Water Mark - 5000
                            # Simplificação: Buffer = (Saldo Atual) - (High Water Mark - 5000)
                            # Se saldo atual é o topo, buffer é 5000.
                            # Para simplificar visualização:
                            falta_meta = meta_fase - saldo_atual_estimado
                            buffer_vida = 5000.0 # Aproximado para teste
                            
                        elif "Fase 2" in fase: # PA Colchão: Foco chegar em 155.100
                            meta_fase = 155100.0 # Meta para ter o colchão completo
                            falta_meta = meta_fase - saldo_atual_estimado
                            
                            # Logica do Trailing PA: Ele para em 150.100
                            # Se meu saldo > 150.100, meu stop é fixo em 150.100
                            if saldo_atual_estimado > 150100:
                                nivel_quebra = 150100.0
                            else:
                                # Se ainda to baixo, o stop ta atras
                                nivel_quebra = saldo_atual_estimado - 5000 # (Estimativa, pois depende do High Water Mark real)
                                
                            buffer_vida = saldo_atual_estimado - nivel_quebra
                            
                        elif "Fase 3" in fase or "Fase 4" in fase: # Dobro ou Saque
                            meta_fase = 0 # Sem teto
                            nivel_quebra = 150100.0 # Fixo
                            buffer_vida = saldo_atual_estimado - nivel_quebra
                            
                        # VISUALIZAÇÃO
                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Contas no Grupo", f"{len(contas_g)}", f"Alavancagem: {len(contas_g)}x")
                        k2.metric("Saldo Atual (Est.)", f"${saldo_atual_estimado:,.2f}", f"App P&L: ${lucro_acumulado_app:+,.2f}")
                        
                        cor_b = "inverse" if buffer_vida < 2000 else "normal"
                        k3.metric("🔥 Buffer (Vida)", f"${buffer_vida:,.2f}", f"Até Quebrar", delta_color=cor_b)
                        
                        if meta_fase > 0:
                            k4.metric("🎯 Falta p/ Meta", f"${falta_meta:,.2f}", f"Alvo: ${meta_fase:,.0f}")
                        else:
                            # Fase de Saque: Tudo acima de 150.100 + Buffer Segurança é saque
                            saque_pot = (saldo_atual_estimado - 152600) * len(contas_g) # Deixa 2.5k de buffer e saca o resto
                            val_saque = max(0, saque_pot)
                            k4.metric("💰 Saque Potencial", f"${val_saque:,.2f}", "Mantendo $2.5k Buffer")

                        # Barra de Progresso Mental
                        media_trade = df_f['resultado'].mean()
                        if meta_fase > 0 and media_trade > 0:
                            trades_restantes = int(falta_meta / media_trade)
                            st.info(f"🧠 **Mentalidade:** Faltam cerca de **{trades_restantes} trades bem executados** (na sua média) para o próximo nível.")
                        elif "Fase 4" in fase:
                            st.success(f"🚀 **Modo Saque:** Mantenha o buffer acima de $2.500 e solicite saques a cada 15 dias.")
                            
                    st.markdown("---")

                # --- KPIs GERAIS (MANTIDOS) ---
                t_tr, net = len(df_f), df_f['resultado'].sum()
                wins = df_f[df_f['resultado'] > 0]; losses = df_f[df_f['resultado'] < 0]
                pf = (wins['resultado'].sum() / abs(losses['resultado'].sum())) if not losses.empty else float('inf')
                wr = (len(wins)/t_tr)*100
                avg_w = wins['resultado'].mean() if not wins.empty else 0
                avg_l = abs(losses['resultado'].mean()) if not losses.empty else 0
                payoff = avg_w/avg_l if avg_l > 0 else 0
                exp = ((wr/100)*avg_w) - ((len(losses)/t_tr)*avg_l)
                
                df_f = df_f.sort_values('created_at'); df_f['equity'] = df_f['resultado'].cumsum()
                max_dd = (df_f['equity'] - df_f['equity'].cummax()).min()

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

                st.divider()
                
                # GRÁFICOS (MANTIDOS)
                g1, g2 = st.columns([2, 1])
                with g1:
                    st.plotly_chart(px.area(df_f, x='created_at', y='equity', title="📈 Curva de Patrimônio", template="plotly_dark").update_traces(line_color='#B20000', fillcolor='rgba(178,0,0,0.2)'), use_container_width=True)
                with g2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.plotly_chart(px.bar(df_f.groupby('contexto')['resultado'].sum().reset_index(), x='contexto', y='resultado', title="Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"]), use_container_width=True)

                st.markdown("### 📅 Performance Semanal")
                df_f['dia'] = pd.to_datetime(df_f['data']).dt.day_name()
                d_map = {'Monday':0, 'Tuesday':1, 'Wednesday':2, 'Thursday':3, 'Friday':4}
                df_f['d_idx'] = df_f['dia'].map(d_map)
                dp = df_f.groupby('dia')['resultado'].sum().reset_index()
                dp['d_idx'] = dp['dia'].map(d_map); dp = dp.sort_values('d_idx')
                st.plotly_chart(px.bar(dp, x='dia', y='resultado', template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"]), use_container_width=True)

            else: st.info("Sem dados.")
        else: st.warning("Vazio.")

    # --- 8. REGISTRAR TRADE ---
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
            ctx = st.selectbox("Contexto", ["Tendência", "Lateralidade", "Rompimento", "Contra-Tendência"])
            psi = st.selectbox("🧠 Estado Mental", ["Focado", "Ansioso", "Vingativo", "Cansado", "Fomo"])
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
                    "grupo_vinculo": g_sel, "comportamento": psi
                }).execute()
                st.balloons(); time.sleep(1); st.rerun()

    # --- 9. ABA CONTAS (AJUSTADA PARA SALDO ATUAL) ---
    elif selected == "Contas":
        st.title("💼 Gestão de Portfólio")
        if ROLE not in ['master', 'admin']: st.error("Restrito.")
        else:
            t1, t2, t3 = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📊 Visão Geral"])
            
            with t1:
                st.subheader("Novo Grupo")
                gn = st.text_input("Nome do Grupo")
                if st.button("Criar"):
                    supabase.table("grupos_config").insert({"usuario": USER, "nome": gn}).execute()
                    st.success("Criado!"); time.sleep(1); st.rerun()
                st.divider()
                dg = load_grupos_config()
                for i, r in dg.iterrows():
                    c1, c2 = st.columns([4,1])
                    c1.info(f"📂 {r['nome']}")
                    if c2.button("X", key=f"dg_{r['id']}"): supabase.table("grupos_config").delete().eq("id", r['id']).execute(); st.rerun()

            with t2:
                st.subheader("Adicionar Conta")
                dg = load_grupos_config()
                if dg.empty: st.warning("Crie um grupo antes.")
                else:
                    gs = st.selectbox("Grupo", sorted(dg['nome'].unique()))
                    ci = st.text_input("ID Conta (Ex: PA-01)")
                    si = st.number_input("Saldo ATUAL na Corretora ($)", value=150000.0, step=100.0)
                    fa = st.selectbox("Fase", ["Fase 1 (Teste)", "Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saque)"])
                    if st.button("Salvar Conta"):
                        supabase.table("contas_config").insert({"usuario": USER, "grupo_nome": gs, "conta_identificador": ci, "saldo_inicial": si, "fase": fa}).execute()
                        st.success("Salvo!"); time.sleep(1); st.rerun()

            with t3:
                st.subheader("Monitoramento")
                dc = load_contas_config(); dt = load_trades()
                if not dt.empty: dt = dt[dt['usuario'] == USER]
                
                if not dc.empty:
                    for g in sorted(dc['grupo_nome'].unique()):
                        with st.expander(f"📂 {g}", expanded=True):
                            tg = dt[dt['grupo_vinculo'] == g] if not dt.empty else pd.DataFrame()
                            lg = tg['resultado'].sum() if not tg.empty else 0.0
                            
                            cg = dc[dc['grupo_nome'] == g]
                            for _, r in cg.iterrows():
                                # Lógica: Saldo Atual = Saldo Cadastrado + Lucro (Assumindo que cadastrou o saldo HOJE)
                                # Se cadastrou hoje com 151k e operou +500, saldo = 151.500
                                atual = float(r['saldo_inicial']) + lg
                                delta = atual - float(r['saldo_inicial'])
                                cor = "#00FF88" if delta >= 0 else "#FF4B4B"
                                
                                c1, c2, c3 = st.columns([3, 0.5, 0.5])
                                c1.markdown(f"💳 **{r['conta_identificador']}** | {r['fase']} | Saldo: **${atual:,.2f}** (<span style='color:{cor}'>${delta:+,.2f}</span>)", unsafe_allow_html=True)
                                
                                with c2.popover("⚙️"):
                                    ns = st.number_input("Ajustar Saldo Real", value=float(r['saldo_inicial']), key=f"ns_{r['id']}")
                                    nf = st.selectbox("Mudar Fase", ["Fase 1 (Teste)", "Fase 2 (Colchão)", "Fase 3 (Dobro)", "Fase 4 (Saque)"], key=f"nf_{r['id']}")
                                    if st.button("Salvar", key=f"sv_{r['id']}"):
                                        supabase.table("contas_config").update({"saldo_inicial": ns, "fase": nf}).eq("id", r['id']).execute()
                                        st.rerun()
                                
                                if c3.button("🗑️", key=f"dl_{r['id']}"):
                                    supabase.table("contas_config").delete().eq("id", r['id']).execute(); st.rerun()
                else: st.info("Vazio.")

    # --- 10. CONFIGURAR ATM (MANTIDO) ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")
        if "ae" not in st.session_state: st.session_state.ae = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        atms = supabase.table("atm_configs").select("*").order("nome").execute().data
        cf, cl = st.columns([1.5, 1])
        with cl:
            if st.button("✨ Nova"): st.session_state.ae = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}; st.rerun()
            for a in atms:
                with st.expander(f"📍 {a['nome']}"):
                    ce, cd = st.columns(2)
                    if ce.button("✏️", key=f"e_{a['id']}"): st.session_state.ae = {"id": a['id'], "nome": a['nome'], "lote": a['lote'], "stop": a['stop'], "parciais": a['parciais'] if isinstance(a['parciais'], list) else json.loads(a['parciais'])}; st.rerun()
                    if cd.button("🗑️", key=f"d_{a['id']}"): supabase.table("atm_configs").delete().eq("id", a['id']).execute(); st.rerun()
        with cf:
            fd = st.session_state.ae; nn = st.text_input("Nome", value=fd["nome"]); nl = st.number_input("Lote", value=int(fd["lote"])); ns = st.number_input("Stop", value=float(fd["stop"]))
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

    # --- 11. HISTÓRICO (MANTIDO) ---
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        dfh = load_trades()
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
            
            for i, r in enumerate(dfh.sort_values('created_at', ascending=False).iterrows()):
                row = r[1]
                cls = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                with st.expander(f"{row['data']} | {row['ativo']} | {row['resultado']:,.2f}"):
                    if row.get('prints'): st.image(row['prints'])
                    st.markdown(f"**Grupo:** {row['grupo_vinculo']} | **Lote:** {row['lote']}")
                    st.markdown(f"<h3 style='color:{'#00FF88' if row['resultado']>=0 else '#FF4B4B'}'>${row['resultado']:,.2f}</h3>", unsafe_allow_html=True)
                    if st.button("🗑️ Deletar", key=f"dh_{row['id']}"): supabase.table("trades").delete().eq("id", row['id']).execute(); st.rerun()

    # --- 12. GERENCIAR USUÁRIOS (MANTIDO) ---
    elif selected == "Gerenciar Usuários" and ROLE == "admin":
        st.title("👥 Usuários")
        us = supabase.table("users").select("*").execute().data
        c1, c2 = st.columns([1, 1.5])
        with c2:
            for u in us:
                with st.container():
                    st.write(f"👤 **{u['username']}** ({u.get('role', 'user')})")
                    if st.button("✏️", key=f"ue_{u['id']}"): st.session_state.user_form_data = {"id": u['id'], "username": u['username'], "password": u['password'], "role": u.get('role', 'user')}; st.rerun()
                    st.divider()
        with c1:
            ud = st.session_state.get("user_form_data", {"id": None, "username": "", "password": "", "role": "user"})
            nu = st.text_input("User", value=ud["username"]); np = st.text_input("Pass", value=ud["password"]); nr = st.selectbox("Role", ["user", "master", "admin"], index=["user", "master", "admin"].index(ud["role"]))
            if st.button("Salvar"):
                pay = {"username": nu, "password": np, "role": nr}
                if ud["id"]: supabase.table("users").update(pay).eq("id", ud["id"]).execute()
                else: supabase.table("users").insert(pay).execute()
                st.session_state.user_form_data = {"id": None, "username": "", "password": "", "role": "user"}; st.rerun()
