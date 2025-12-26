import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import json
import uuid
import time
import math
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

st.set_page_config(page_title="EvoTrade Terminal v151", layout="wide", page_icon="📈")

# ==============================================================================
# 2. ESTILOS CSS
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
    
    /* Cores de Resultado */
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

# ==============================================================================
# 3. SISTEMA DE LOGIN
# ==============================================================================
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

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
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER = st.session_state["logged_user"]
    ROLE = st.session_state.get("user_role", "user")

    # ==============================================================================
    # 5. FUNÇÕES DE DADOS (ROBUSTAS)
    # ==============================================================================
    def load_trades_db():
        try:
            res = supabase.table("trades").select("*").execute()
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
            df = pd.DataFrame(res.data)
            # Garantir colunas novas v151
            if not df.empty and 'pico_previo' not in df.columns:
                df['pico_previo'] = df['saldo_inicial']
            return df
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

    # ==============================================================================
    # 6. MENU LATERAL
    # ==============================================================================
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Contas", "Histórico"]
        icons = ["grid", "currency-dollar", "gear", "briefcase", "clock"]
        
        if ROLE in ['master', 'admin']:
            menu.insert(2, "Contas")
            icons.insert(2, "briefcase")
            
        if ROLE == 'admin':
            menu.append("Gerenciar Usuários")
            icons.append("people")
            
        selected = option_menu(None, menu, icons=icons, styles={"nav-link-selected": {"background-color": "#B20000"}})
        
        if st.button("Sair / Logout"): 
            st.session_state.clear()
            st.rerun()

    # ==============================================================================
    # 7. ABA: DASHBOARD (v151 - MOTOR DE PRECISÃO BASEADO EM COMPORTAMENTO)
    # ==============================================================================
    if selected == "Dashboard":
        st.title("📊 Central de Controle (v151)")
        df_raw = load_trades_db()
        df_contas = load_contas_config()
        
        if not df_raw.empty:
            df = df_raw[df_raw['usuario'] == USER]
            
            if not df.empty:
                # --- FILTROS (Afetam Métricas de Performance e Comportamento) ---
                with st.expander("🔍 Filtros Avançados", expanded=True):
                    if ROLE in ['master', 'admin']:
                        col_d1, col_d2, col_grp, col_ctx = st.columns([1, 1, 1.2, 1.8])
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

                # Aplica Filtros no DF_FILTERED (Para Métricas de Desempenho)
                mask = (df['data'] >= d_inicio) & (df['data'] <= d_fim) & (df['contexto'].isin(filters_ctx))
                if sel_grupo != "Todos":
                    mask = mask & (df['grupo_vinculo'] == sel_grupo)
                
                df_filtered = df[mask].copy()

                if df_filtered.empty:
                    st.warning("⚠️ Nenhum trade encontrado para o período/filtro selecionado.")
                else:
                    # --- KPIs FINANCEIROS (BASEADOS NO FILTRO) ---
                    total_trades = len(df_filtered)
                    wins = df_filtered[df_filtered['resultado'] > 0]
                    losses = df_filtered[df_filtered['resultado'] < 0]
                    
                    net_profit = df_filtered['resultado'].sum()
                    gross_profit = wins['resultado'].sum()
                    gross_loss = abs(losses['resultado'].sum())
                    
                    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                    pf_str = f"{pf:.2f}" if gross_loss > 0 else "∞"
                    
                    # Taxas
                    win_rate_dec = len(wins) / total_trades
                    loss_rate_dec = len(losses) / total_trades
                    win_rate = win_rate_dec * 100
                    
                    avg_win = wins['resultado'].mean() if not wins.empty else 0
                    avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0
                    payoff = avg_win / avg_loss if avg_loss > 0 else 1.0
                    
                    expectancy = ( win_rate_dec * avg_win ) - ( loss_rate_dec * avg_loss )
                    
                    # MÉDIAS COMPORTAMENTAIS (v151 - A Verdade do Período)
                    lote_medio_real = df_filtered['lote'].mean()
                    pts_loss_medio_real = abs(losses['pts_medio'].mean()) if not losses.empty else 15.0 # Fallback 15 pts se nao tiver loss
                    ativo_referencia = df_filtered['ativo'].iloc[-1] # Pega o ativo mais recente pra saber multiplicador
                    
                    # Médias Técnicas
                    avg_pts_gain = wins['pts_medio'].mean() if not wins.empty else 0
                    avg_pts_loss = abs(losses['pts_medio'].mean()) if not losses.empty else 0
                    
                    # --- EXIBIÇÃO DE CARDS (3 LINHAS) ---
                    st.markdown("##### 🏁 Desempenho no Período Selecionado")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: card_metric("RESULTADO LÍQUIDO", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f} / -${gross_loss:,.0f}", "#00FF88" if net_profit >= 0 else "#FF4B4B")
                    with c2: card_metric("FATOR DE LUCRO (PF)", pf_str, "Ideal > 1.5", "#B20000")
                    with c3: card_metric("WIN RATE", f"{win_rate:.1f}%", f"{len(wins)}W / {len(losses)}L", "white")
                    with c4: card_metric("EXPECTATIVA MAT.", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy > 0 else "#FF4B4B")
                    
                    st.markdown("##### 🎯 Comportamento Operacional (Base para Ruína)")
                    c5, c6, c7, c8 = st.columns(4)
                    with c5: card_metric("LOTE MÉDIO", f"{lote_medio_real:.1f}", "Contratos", "#00FF88")
                    with c6: card_metric("STOP MÉDIO (PTS)", f"{pts_loss_medio_real:.2f} pts", "Loss Técnico Real", "#FF4B4B")
                    with c7: card_metric("RISCO : RETORNO", f"1 : {payoff:.2f}", "Payoff Real", "white")
                    
                    # Drawdown do período filtrado
                    df_filtered = df_filtered.sort_values('created_at')
                    df_filtered['equity'] = df_filtered['resultado'].cumsum()
                    max_dd = (df_filtered['equity'] - df_filtered['equity'].cummax()).min()
                    with c8: card_metric("DRAWDOWN PERÍODO", f"${max_dd:,.2f}", "Pior Queda Filtrada", "#FF4B4B")

                    # ==============================================================================
                    # 🛡️ MOTOR DE CÁLCULO: RISCO DE RUÍNA v151 (COMPORTAMENTO x REALIDADE APEX)
                    # ==============================================================================
                    st.markdown("---")
                    st.subheader(f"🛡️ Sobrevivência Apex ({sel_grupo})")

                    # 1. RISCO UNITÁRIO (Baseado no seu comportamento no filtro de data)
                    # SEM GORDURA DE 20% - USA O REAL
                    risco_comportamental = lote_medio_real * pts_loss_medio_real * MULTIPLIERS[ativo_referencia]

                    # 2. BUFFER REAL DO GRUPO (Baseado no HISTÓRICO TOTAL, independente do filtro de data)
                    # O Buffer não pode depender do filtro de data, ele é o estado atual da conta.
                    total_buffer_real = 0.0
                    contas_analisadas = 0
                    
                    if not df_contas.empty:
                        contas_alvo = df_contas if sel_grupo == "Todos" else df_contas[df_contas['grupo_nome'] == sel_grupo]
                        for _, row in contas_alvo.iterrows():
                            saldo_entrada = float(row['saldo_inicial'])
                            pico_previo = float(row.get('pico_previo', saldo_entrada))
                            
                            # Para saber o buffer real, precisamos de TODOS os trades deste grupo, não só os filtrados
                            trades_grp_total = df[df['grupo_vinculo'] == row['grupo_nome']].sort_values('created_at')
                            
                            if not trades_grp_total.empty:
                                lucro_atual_total = trades_grp_total['resultado'].sum()
                                saldo_agora = saldo_entrada + lucro_atual_total
                                
                                # HWM Global (Pico Real)
                                pico_acumulado = (trades_grp_total['resultado'].cumsum()).max()
                                # O pico é o maior entre (Check-in Inicial) OU (Saldo Inicial + Lucro Máximo)
                                pico_real = max(pico_previo, saldo_entrada + max(0, pico_acumulado))
                            else:
                                saldo_agora = saldo_entrada
                                pico_real = pico_previo
                            
                            # REGRA APEX: Trava em 150.100 se pico >= 155.100
                            if pico_real >= 155100.0:
                                trailing_stop = 150100.0
                                status_fase = "Stop Travado"
                            else:
                                trailing_stop = pico_real - 5000.0
                                status_fase = "Trailing Ativo"
                            
                            buffer_disponivel = max(0, saldo_agora - trailing_stop)
                            total_buffer_real += buffer_disponivel
                            contas_analisadas += 1
                    
                    if total_buffer_real == 0 and contas_analisadas == 0: total_buffer_real = 0.0

                    # 3. CÁLCULO DAS VIDAS (Buffer Total / Risco do Comportamento Atual x Contas)
                    fator_replicacao = contas_analisadas if contas_analisadas > 0 else 1
                    risco_total_grupo = risco_comportamental * fator_replicacao
                    
                    vidas_u = total_buffer_real / risco_total_grupo if risco_total_grupo > 0 else 0

                    # 4. Z-SCORE E RUÍNA
                    z_edge = (win_rate_dec * payoff) - loss_rate_dec

                    if total_trades < 5:
                        msg_alerta = "⚠️ Poucos dados"
                        display_ror = "---"
                        color_r = "gray"
                    elif z_edge <= 0:
                        ror_final = 100.0
                        display_ror = "100.00000%"
                        color_r = "#FF4B4B"
                        msg_alerta = "Edge Negativo"
                    else:
                        # Fórmula ajustada para alavancagem
                        base_calc = max(0.0, (1 - z_edge) / (1 + z_edge))
                        ror_val = (base_calc ** vidas_u) * 100
                        ror_final = min(max(ror_val, 0.0), 100.0)
                        
                        display_ror = f"{ror_final:.5f}%"
                        
                        if ror_final < 0.1: color_r = "#00FF88"
                        elif ror_final < 5: color_r = "#FFFF00"
                        else: color_r = "#FF4B4B"
                        msg_alerta = "Calculado s/ Lote Médio"

                    # --- EXIBIÇÃO VISUAL (4 CARDS) ---
                    k1, k2, k3, k4 = st.columns(4)
                    
                    with k1:
                        lbl_z = "EDGE POSITIVO" if z_edge > 0 else "EDGE NEGATIVO"
                        cor_z = "#00FF88" if z_edge > 0 else "#FF4B4B"
                        card_metric("Z-SCORE (VANTAGEM)", f"{z_edge:.5f}", lbl_z, cor_z, "Vantagem Matemática.")
                    
                    with k2:
                        card_metric("BUFFER REAL (HOJE)", f"${total_buffer_real:,.0f}", f"{contas_analisadas} Contas Somadas", "#00FF88", "Distância real do Stop Apex HOJE.")

                    with k3:
                        cor_v = "#FF4B4B" if vidas_u < 4 else ("#FFFF00" if vidas_u < 8 else "white")
                        card_metric("VIDAS REAIS (U)", f"{vidas_u:.1f}", f"Custo Vida: ${risco_total_grupo:,.0f}", cor_v, f"Baseado no Lote: {lote_medio_real:.1f}")

                    with k4:
                        st.markdown(f"""
                            <div style="background: #101010; border: 2px solid {color_r}; border-radius: 12px; padding: 10px; text-align: center; display: flex; flex-direction: column; justify-content: center; height: 140px;">
                                <div style="color: #888; font-size: 11px; font-weight: bold; text-transform: uppercase;">Risco de Ruína</div>
                                <div style="color: {color_r}; font-size: 24px; font-weight: 900; margin: 2px 0;">{display_ror}</div>
                                <div style="font-size: 10px; color: #666; margin-top:5px;">{msg_alerta}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---")

                    # --- GRÁFICOS ---
                    g1, g2 = st.columns([2, 1])
                    with g1:
                        view_mode = st.radio("Visualizar Curva por:", ["Sequência de Trades", "Data (Tempo)"], horizontal=True, label_visibility="collapsed")
                        if view_mode == "Sequência de Trades":
                            df_filtered['trade_seq'] = range(1, len(df_filtered) + 1)
                            x_axis = 'trade_seq'; x_title = "Quantidade de Trades"
                        else:
                            x_axis = 'data'; x_title = "Data"

                        fig_eq = px.area(df_filtered, x=x_axis, y='equity', title="📈 Curva de Patrimônio (Filtrada)", template="plotly_dark")
                        fig_eq.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                        fig_eq.add_hline(y=0, line_dash="dash", line_color="gray")
                        st.plotly_chart(fig_eq, use_container_width=True, config={'displayModeBar': False})
                        
                    with g2:
                        st.markdown("<br>", unsafe_allow_html=True) 
                        ctx_perf = df_filtered.groupby('contexto')['resultado'].sum().reset_index()
                        fig_bar = px.bar(ctx_perf, x='contexto', y='resultado', title="📊 Resultado por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
                    
                    # Performance por Dia da Semana (Restaurado)
                    st.markdown("### 📅 Performance por Dia da Semana")
                    df_filtered['dia_semana'] = pd.to_datetime(df_filtered['data']).dt.day_name()
                    dias_pt = {'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua', 'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sab', 'Sunday': 'Dom'}
                    df_filtered['dia_pt'] = df_filtered['dia_semana'].map(dias_pt)
                    day_perf = df_filtered.groupby('dia_pt')['resultado'].sum().reindex(['Seg', 'Ter', 'Qua', 'Qui', 'Sex']).reset_index()
                    fig_day = px.bar(day_perf, x='dia_pt', y='resultado', template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                    st.plotly_chart(fig_day, use_container_width=True)

            else: st.info("Sem operações registradas para este usuário.")
        else: st.warning("Banco de dados vazio.")

    # ==============================================================================
    # 8. REGISTRAR TRADE (COMPLETO COM PARCIAIS)
    # ==============================================================================
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db()
        df_grupos = load_grupos_config()
        
        # Topo Otimizado: ATM e Grupo
        col_atm, col_grp = st.columns([3, 1.5])
        
        with col_atm:
            atm_sel = st.selectbox("🎯 Escolher Template ATM", ["Manual"] + list(atm_db.keys()))
        
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
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
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
                saidas.append({"pts": pts, "qtd": qtd})
                aloc += qtd
            
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
                        "comportamento": psi, "risco_fin": (stp * MULTIPLIERS[atv] * lt)
                    }).execute()

                    st.balloons() 
                    st.success(f"✅ SUCESSO! Resultado: ${res_fin:,.2f}")
                    time.sleep(2); st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

    # ==============================================================================
    # 9. ABA CONTAS (v151 - CHECK-IN E MONITOR DE PERFORMANCE COMPLETO)
    # ==============================================================================
    elif selected == "Contas":
        st.title("💼 Gestão de Portfólio (v151)")
        
        if ROLE not in ['master', 'admin']:
            st.error("Acesso restrito.")
        else:
            t1, t2, t3, t4 = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta (Check-in)", "📋 Visão Geral", "🚀 Monitor de Performance"])
            
            # --- ABA 1: GRUPOS ---
            with t1:
                with st.form("form_grupo"):
                    novo_grupo = st.text_input("Nome do Grupo (Ex: Apex 5 Contas - A)")
                    if st.form_submit_button("Criar Grupo"):
                        if novo_grupo:
                            supabase.table("grupos_config").insert({"usuario": USER, "nome": novo_grupo}).execute(); st.rerun()
                st.divider()
                df_g = load_grupos_config()
                if not df_g.empty:
                    for _, row in df_g.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.info(f"📂 {row['nome']}")
                        if c2.button("X", key=f"del_g_{row['id']}"):
                            supabase.table("grupos_config").delete().eq("id", row['id']).execute(); st.rerun()

            # --- ABA 2: CADASTRAR CONTA (COM CHECK-IN v151) ---
            with t2:
                st.subheader("Vincular Conta com Histórico")
                df_g = load_grupos_config()
                if not df_g.empty:
                    with st.form("form_conta"):
                        col_a, col_b = st.columns(2)
                        g_sel = col_a.selectbox("Grupo", sorted(df_g['nome'].unique()))
                        c_id = col_b.text_input("Identificador (Ex: PA-001)")
                        s_ini = col_a.number_input("Saldo ATUAL na Corretora ($)", value=150000.0, step=100.0)
                        p_pre = col_b.number_input("Pico Máximo já Atingido (HWM)", value=150000.0, step=100.0, help="Importante: Define se o stop já travou")
                        
                        if st.form_submit_button("Cadastrar Conta"):
                            if c_id:
                                try:
                                    supabase.table("contas_config").insert({
                                        "usuario": USER, "grupo_nome": g_sel, "conta_identificador": c_id,
                                        "saldo_inicial": s_ini, "pico_previo": p_pre
                                    }).execute()
                                    st.success("Conta cadastrada com Check-in!"); time.sleep(1); st.rerun()
                                except Exception as e: st.error(f"Erro: {e}")
                else: st.warning("Crie um grupo antes.")

            # --- ABA 3: VISÃO GERAL ---
            with t3:
                df_c = load_contas_config()
                if not df_c.empty:
                    st.dataframe(df_c[["grupo_nome", "conta_identificador", "saldo_inicial", "pico_previo"]], use_container_width=True)
                    st.divider()
                    for _, row in df_c.iterrows():
                        with st.expander(f"{row['conta_identificador']} ({row['grupo_nome']})"):
                            if st.button("Excluir Conta", key=f"del_c_{row['id']}"):
                                supabase.table("contas_config").delete().eq("id", row['id']).execute(); st.rerun()
                else: st.info("Nenhuma conta cadastrada.")

            # --- ABA 4: MONITOR DE PERFORMANCE (RESTAURADO E ATUALIZADO v151) ---
            with t4:
                st.subheader("🚀 Monitor de Performance Apex")
                df_c = load_contas_config()
                df_t = load_trades_db()
                if not df_t.empty: df_t = df_t[df_t['usuario'] == USER]

                if not df_c.empty:
                    grps = sorted(df_c['grupo_nome'].unique())
                    sel_g = st.selectbox("Selecione o Grupo para Análise", grps)
                    
                    contas_g = df_c[df_c['grupo_nome'] == sel_g]
                    trades_g = df_t[df_t['grupo_vinculo'] == sel_g] if not df_t.empty else pd.DataFrame()
                    
                    if not contas_g.empty:
                        # Base de Cálculo: Pega a conta com menor saldo para ser conservador
                        saldo_inicial_base = contas_g['saldo_inicial'].min()
                        # IMPORTANTE v151: Usa o pico prévio para saber onde a conta "já esteve"
                        pico_previo_base = contas_g['pico_previo'].min() if 'pico_previo' in contas_g.columns else saldo_inicial_base
                        
                        lucro_total_grupo = trades_g['resultado'].sum() if not trades_g.empty else 0.0
                        saldo_atual_base = saldo_inicial_base + lucro_total_grupo
                        
                        # Definição de Fases (LÓGICA DETALHADA)
                        if saldo_atual_base < 159000.0:
                            meta = 159000.0; fase = "Fase 1: Passar no Teste"; idx_f = 1
                        elif saldo_atual_base < 155100.0:
                            meta = 155100.0; fase = "Fase 2: Colchão"; idx_f = 2
                        elif saldo_atual_base < 161000.0:
                            meta = 161000.0; fase = "Fase 3: Escalada"; idx_f = 3
                        else:
                            meta = 162000.0; fase = "Fase 4: Saque"; idx_f = 4

                        k1, k2, k3 = st.columns(3)
                        k1.metric("Saldo Base Atual", f"${saldo_atual_base:,.2f}")
                        k2.metric("Fase Atual", fase)
                        k3.metric("Meta Próxima", f"${meta:,.0f}", f"Falta: ${max(0, meta - saldo_atual_base):,.2f}")
                        
                        st.markdown("---")
                        
                        # Barra de Progresso da Fase
                        base_prog = 150000.0
                        if idx_f == 3: base_prog = 155100.0
                        elif idx_f == 4: base_prog = 160000.0
                        
                        prog = min(1.0, max(0.0, (saldo_atual_base - base_prog) / (meta - base_prog))) if meta > base_prog else 1.0
                        st.write(f"Progresso da Fase: {prog*100:.1f}%")
                        st.progress(prog)
                        
                        # Cálculo EV para Trades Restantes
                        if not trades_g.empty:
                            ev_por_trade = trades_g['resultado'].mean()
                            falta = meta - saldo_atual_base
                            if falta > 0 and ev_por_trade > 0:
                                trades_restantes = math.ceil(falta / ev_por_trade)
                                st.info(f"💡 Estimativa: Faltam ~{trades_restantes} trades para a meta (EV: ${ev_por_trade:.2f})")
                        
                        # Gráfico de Evolução (Global do Grupo com HWM)
                        if not trades_g.empty:
                            trades_g = trades_g.sort_values('created_at')
                            trades_g['seq'] = range(1, len(trades_g)+1)
                            trades_g['saldo_acc'] = trades_g['resultado'].cumsum() + saldo_inicial_base
                            
                            # Calcula o HWM dinâmico para o gráfico
                            max_hwm_grafico = max(pico_previo_base, trades_g['saldo_acc'].max())
                            stop_grafico = 150100.0 if max_hwm_grafico >= 155100.0 else max_hwm_grafico - 5000.0

                            fig = px.line(trades_g, x='seq', y='saldo_acc', title="Evolução do Grupo", template="plotly_dark")
                            fig.add_hline(y=meta, line_dash="dot", line_color="#00FF88", annotation_text="Meta")
                            fig.add_hline(y=stop_grafico, line_dash="dash", line_color="#FF4B4B", annotation_text="Trailing Stop Real")
                            st.plotly_chart(fig, use_container_width=True)
                        else: st.info("Sem trades.")
                        
                    else: st.warning("Grupo sem contas.")
                else: st.warning("Cadastre contas primeiro.")

    # ==============================================================================
    # 10. CONFIGURAR ATM (COMPLETO)
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
    # 11. HISTÓRICO (COMPLETO)
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
            dfh = dfh.sort_values('created_at', ascending=False)
            
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
            for i, (index, row) in enumerate(dfh.iterrows()):
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
                    if st.button("👁️ Ver", key=f"btn_{row['id']}", use_container_width=True): show_trade_details(row)

    # ==============================================================================
    # 12. GERENCIAR USUÁRIOS (COMPLETO)
    # ==============================================================================
    elif selected == "Gerenciar Usuários" and ROLE == "admin":
        st.title("👥 Usuários")
        us = supabase.table("users").select("*").execute().data
        c1, c2 = st.columns([1, 1.5])
        with c2:
            for u in us:
                with st.container():
                    st.write(f"👤 **{u['username']}** ({u.get('role','user')})")
                    if st.button("Edit", key=f"ue_{u['id']}"): st.session_state.uf = u; st.rerun()
                    st.divider()
        with c1:
            ud = st.session_state.get("uf", {"id": None, "username": "", "password": "", "role": "user"})
            nu = st.text_input("User", value=ud["username"]); np = st.text_input("Pass", value=ud["password"]); nr = st.selectbox("Role", ["user", "master", "admin"])
            if st.button("Salvar"):
                pay = {"username": nu, "password": np, "role": nr}
                if ud["id"]: supabase.table("users").update(pay).eq("id", ud["id"]).execute()
                else: supabase.table("users").insert(pay).execute()
                st.session_state.uf = {"id": None, "username": "", "password": "", "role": "user"}; st.rerun()
