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

st.set_page_config(page_title="EvoTrade Terminal v156", layout="wide", page_icon="📈")

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

    /* Alerta de Perigo Imediato (v152/155) */
    .piscante-erro { 
        padding: 20px; 
        border-radius: 8px; 
        color: white; 
        font-weight: 900; 
        text-align: center; 
        animation: blinking 1.0s infinite; 
        border: 2px solid #FF0000;
        background-color: #440000;
        margin-bottom: 20px;
        text-transform: uppercase;
        font-size: 20px;
        letter-spacing: 1px;
    }
    
    .risco-alert {
        color: #FF4B4B; font-weight: bold; font-size: 16px; margin-top: 5px;
        background-color: rgba(255, 75, 75, 0.1); padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #FF4B4B;
    }
    
    @keyframes blinking { 0% { background-color: #440000; border-color: #FF0000; } 50% { background-color: #FF0000; border-color: #FFFFFF; } 100% { background-color: #440000; border-color: #FF0000; } }

    /* Geral */
    [data-testid="stSidebar"] { background-color: #0F0F0F !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. SISTEMA DE LOGIN
# ==============================================================================
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False
if "login_attempted" not in st.session_state:
    st.session_state["login_attempted"] = False

def check_password():
    def password_entered():
        st.session_state["login_attempted"] = True
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

    if not st.session_state["password_correct"]:
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
            if st.session_state["login_attempted"] and not st.session_state["password_correct"]:
                st.error("😕 Credenciais incorretas.")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if check_password():
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    USER = st.session_state["logged_user"]
    ROLE = st.session_state.get("user_role", "user")

    # ==============================================================================
    # 5. FUNÇÕES DE DADOS (ATUALIZADAS v156)
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
            # Garantias v156
            if not df.empty:
                if 'pico_previo' not in df.columns: df['pico_previo'] = df['saldo_inicial']
                if 'fase_entrada' not in df.columns: df['fase_entrada'] = 'Fase 1'
                if 'status_conta' not in df.columns: df['status_conta'] = 'Ativa'
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
        
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        icons = ["grid", "currency-dollar", "gear", "clock"]
        
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
    # 7. ABA: DASHBOARD (v165 - RISCO DE RUÍNA REAL / GAMBLER'S RUIN)
    # ==============================================================================
    if selected == "Dashboard":
        st.title("📊 Central de Controle (v165)")
        df_raw = load_trades_db()
        df_contas = load_contas_config()
        
        if not df_raw.empty:
            df = df_raw[df_raw['usuario'] == USER]
            
            if not df.empty:
                # --- FILTROS ---
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

                # Aplica Filtros
                mask = (df['data'] >= d_inicio) & (df['data'] <= d_fim) & (df['contexto'].isin(filters_ctx))
                if sel_grupo != "Todos":
                    mask = mask & (df['grupo_vinculo'] == sel_grupo)
                
                df_filtered = df[mask].copy()

                if df_filtered.empty:
                    st.warning("⚠️ Nenhum trade encontrado com os filtros.")
                else:
                    # --- KPIs FINANCEIROS ---
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
                    
                    # --- MÉDIAS COMPORTAMENTAIS ---
                    lote_medio_real = df_filtered['lote'].mean() if not df_filtered.empty else 0
                    pts_loss_medio_real = abs(losses['pts_medio'].mean()) if not losses.empty else 15.0 
                    ativo_referencia = df_filtered['ativo'].iloc[-1] if not df_filtered.empty else "MNQ"
                    
                    avg_pts_gain = wins['pts_medio'].mean() if not wins.empty else 0
                    avg_pts_loss = abs(losses['pts_medio'].mean()) if not losses.empty else 0

                    df_filtered = df_filtered.sort_values('created_at')
                    df_filtered['equity'] = df_filtered['resultado'].cumsum()
                    max_dd = (df_filtered['equity'] - df_filtered['equity'].cummax()).min()

                    # ==============================================================================
                    # 🛡️ MOTOR DE CÁLCULO v165 - A FÓRMULA DA REALIDADE
                    # ==============================================================================
                    
                    # 1. RISCO UNITÁRIO REAL (Baseado na dor média do histórico)
                    risco_comportamental = lote_medio_real * pts_loss_medio_real * MULTIPLIERS[ativo_referencia]
                    if risco_comportamental == 0: risco_comportamental = 300.0

                    # 2. BUFFER REAL DO GRUPO (Oxigênio disponível até o Stop)
                    total_buffer_real = 0.0
                    contas_analisadas = 0
                    
                    if not df_contas.empty:
                        contas_alvo = df_contas if sel_grupo == "Todos" else df_contas[df_contas['grupo_nome'] == sel_grupo]
                        for _, row in contas_alvo.iterrows():
                            if row.get('status_conta', 'Ativa') == 'Ativa':
                                saldo_entrada = float(row['saldo_inicial'])
                                pico_previo = float(row.get('pico_previo', saldo_entrada))
                                
                                trades_deste_grupo = df[df['grupo_vinculo'] == row['grupo_nome']].sort_values('created_at')
                                
                                if not trades_deste_grupo.empty:
                                    lucro_atual = trades_deste_grupo['resultado'].sum()
                                    saldo_agora = saldo_entrada + lucro_atual
                                    # Recalcula o HWM baseado no histórico + pico manual
                                    equity_curve = trades_deste_grupo['resultado'].cumsum() + saldo_entrada
                                    pico_real = max(pico_previo, equity_curve.max(), saldo_entrada)
                                else:
                                    saldo_agora = saldo_entrada
                                    pico_real = pico_previo
                                
                                # Regra Apex 150k
                                if pico_real >= 155100.0: trailing_stop = 150100.0
                                else: trailing_stop = pico_real - 5000.0
                                
                                total_buffer_real += max(0, saldo_agora - trailing_stop)
                                contas_analisadas += 1
                    
                    if total_buffer_real == 0 and contas_analisadas == 0: total_buffer_real = 0.0

                    # 3. VIDAS REAIS (U)
                    # Quantas vezes eu posso errar antes de morrer?
                    fator_replicacao = contas_analisadas if contas_analisadas > 0 else 1
                    risco_grupo_total = risco_comportamental * fator_replicacao
                    
                    vidas_u = total_buffer_real / risco_grupo_total if risco_grupo_total > 0 else 0

                    # 4. FÓRMULA DE RUÍNA DO JOGADOR (Gambler's Ruin)
                    # P = (q / p) ^ U
                    
                    p = win_rate_dec
                    q = 1 - p
                    prob_ruina = 0.0
                    msg_alerta = ""
                    
                    if total_trades < 5:
                        msg_alerta = "⚠️ Calibrando..."
                        prob_ruina = 0.0
                        color_r = "gray"
                    elif vidas_u <= 0.5:
                        prob_ruina = 100.0
                        msg_alerta = "LIQUIDAÇÃO IMINENTE"
                        color_r = "#FF0000"
                    elif p <= q:
                        # Se você perde mais do que ganha (ou igual), a ruína é 100% certa no longo prazo
                        prob_ruina = 100.0
                        msg_alerta = "EDGE NEGATIVO (PARE)"
                        color_r = "#FF0000"
                    else:
                        # Fórmula Discreta (A Verdade)
                        raw_ruin = (q / p) ** vidas_u
                        prob_ruina = raw_ruin * 100
                        prob_ruina = min(max(prob_ruina, 0.0), 100.0)
                        
                        if prob_ruina < 1.0: 
                            color_r = "#00FF88" # Seguro
                            msg_alerta = "Zona de Segurança"
                        elif prob_ruina < 5.0: 
                            color_r = "#FFFF00" # Atenção
                            msg_alerta = "Risco Moderado"
                        else: 
                            color_r = "#FF4B4B" # Perigo
                            msg_alerta = "RISCO CRÍTICO"

                    # --- TRAVA DE SEGURANÇA VISUAL (ALERTA DE PÂNICO) ---
                    # Se o risco real for maior que 10%, o sistema grita.
                    if prob_ruina > 10.0 and total_trades >= 5:
                        st.markdown(f"""
                            <div class="piscante-erro">
                                💀 ALERTA DE RUÍNA: {prob_ruina:.2f}% 💀<br>
                                <span style="font-size:16px; font-weight:normal; text-transform:none;">
                                    Você tem apenas <b>{vidas_u:.1f} Vidas</b>. A estatística está contra você.<br>
                                    A probabilidade de quebrar sua conta em breve é ALTÍSSIMA.<br>
                                    <b>AÇÃO IMEDIATA: REDUZA O LOTE PELA METADE.</b>
                                </span>
                            </div>
                        """, unsafe_allow_html=True)

                    # --- EXIBIÇÃO DE CARDS ---
                    st.markdown("##### 🏁 Desempenho Geral")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: card_metric("RESULTADO LÍQUIDO", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f} / -${gross_loss:,.0f}", "#00FF88" if net_profit >= 0 else "#FF4B4B", "Soma total dos lucros e prejuízos no período.")
                    with c2: card_metric("FATOR DE LUCRO (PF)", pf_str, "Ideal > 1.5", "#B20000", "Razão entre lucro bruto e prejuízo bruto.")
                    with c3: card_metric("WIN RATE", f"{win_rate:.1f}%", f"{len(wins)}W / {len(losses)}L", "white", "Percentual de operações vencedoras.")
                    with c4: card_metric("EXPECTATIVA MAT.", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy > 0 else "#FF4B4B", "Valor financeiro esperado por operação no longo prazo.")
                    
                    st.markdown("##### 💲 Médias Financeiras")
                    c5, c6, c7, c8 = st.columns(4)
                    with c5: card_metric("MÉDIA GAIN ($)", f"${avg_win:,.2f}", "", "#00FF88", "Média financeira dos trades positivos.")
                    with c6: card_metric("MÉDIA LOSS ($)", f"-${avg_loss:,.2f}", "", "#FF4B4B", "Média financeira dos trades negativos.")
                    with c7: card_metric("RISCO : RETORNO", f"1 : {payoff:.2f}", "Payoff Real", "white", "Relação média entre risco assumido e retorno obtido.")
                    with c8: card_metric("DRAWDOWN MÁXIMO", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B", "Maior queda de capital a partir de um topo.")

                    st.markdown("##### 🎯 Performance Técnica")
                    c9, c10, c11, c12 = st.columns(4)
                    with c9: card_metric("PTS MÉDIOS (GAIN)", f"{avg_pts_gain:.2f} pts", "", "#00FF88", "Média de pontos capturados nos gains.")
                    with c10: card_metric("STOP MÉDIO (LOSS)", f"{pts_loss_medio_real:.2f} pts", "Base do Risco", "#FF4B4B", "Média de pontos perdidos nos stops (define seu risco).")
                    with c11: card_metric("LOTE MÉDIO", f"{lote_medio_real:.1f}", "Contratos", "white", "Tamanho médio da mão utilizada.")
                    with c12: card_metric("TOTAL TRADES", str(total_trades), "Executados", "white", "Volume total de operações.")

                    # --- CARD DO MOTOR v165 (NOVO) ---
                    st.markdown("---")
                    st.subheader(f"🛡️ Análise de Sobrevivência (Gambler's Ruin) - {sel_grupo}")
                    
                    z_edge = (win_rate_dec * payoff) - loss_rate_dec

                    k1, k2, k3, k4 = st.columns(4)
                    with k1:
                        lbl_z = "EDGE POSITIVO" if z_edge > 0 else "EDGE NEGATIVO"
                        cor_z = "#00FF88" if z_edge > 0 else "#FF4B4B"
                        card_metric("Z-SCORE (EDGE)", f"{z_edge:.4f}", lbl_z, cor_z, "Força estatística da sua estratégia.")
                    
                    with k2:
                        card_metric("BUFFER REAL (HOJE)", f"${total_buffer_real:,.0f}", f"{contas_analisadas} Contas Ativas", "#00FF88", "Oxigênio real: Distância do Saldo Atual para o Stop Apex.")

                    with k3:
                        # Cores de Vidas baseadas na realidade discreta
                        cor_v = "#FF4B4B" if vidas_u < 6 else ("#FFFF00" if vidas_u < 10 else "#00FF88")
                        lbl_v = "CRÍTICO" if vidas_u < 6 else "OK"
                        card_metric("VIDAS REAIS (U)", f"{vidas_u:.1f}", f"Risco Base: ${risco_grupo_total:,.0f}", cor_v, "Quantos stops cheios você suporta AGORA.")

                    with k4:
                        st.markdown(f"""
                            <div style="background: #101010; border: 2px solid {color_r}; border-radius: 12px; padding: 10px; text-align: center; display: flex; flex-direction: column; justify-content: center; height: 140px;">
                                <div style="color: #888; font-size: 11px; font-weight: bold; text-transform: uppercase;">PROB. RUÍNA (REAL)</div>
                                <div style="color: {color_r}; font-size: 28px; font-weight: 900; margin: 2px 0;">{prob_ruina:.2f}%</div>
                                <div style="font-size: 11px; color: #BBB; margin-top:5px; font-weight:bold;">{msg_alerta}</div>
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

                        fig_eq = px.area(df_filtered, x=x_axis, y='equity', title="📈 Curva de Patrimônio", template="plotly_dark")
                        fig_eq.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                        fig_eq.add_hline(y=0, line_dash="dash", line_color="gray")
                        fig_eq.update_layout(xaxis_title=x_title, yaxis_title="Patrimônio ($)")
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
                    fig_day.update_layout(xaxis_title="Dia da Semana", yaxis_title="Resultado ($)")
                    st.plotly_chart(fig_day, use_container_width=True, config={'displayModeBar': False})

            else: st.info("Sem operações registradas para este usuário.")
        else: st.warning("Banco de dados vazio.")
        
    # ==============================================================================
    # 8. REGISTRAR TRADE
    # ==============================================================================
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db()
        df_grupos = load_grupos_config()
        
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
            try: parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
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
            if col_btn1.button("➕ Add Parcial"): st.session_state.num_parciais += 1; st.rerun()
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
    # 9. ABA CONTAS (v157 FINAL - SEM ERROS DE INDENTAÇÃO + ZOOM + AUTO-FASE)
    # ==============================================================================
    elif selected == "Contas":
        st.title("💼 Gestão de Portfólio (v159)")
        
        if ROLE not in ['master', 'admin']:
            st.error("Acesso restrito.")
        else:
            t1, t2, t3, t4 = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📋 Visão Geral", "🚀 Monitor de Performance"])
            
            # --- ABA 1: GRUPOS ---
            with t1:
                st.subheader("Nova Estrutura de Contas")
                with st.form("form_grupo"):
                    novo_grupo = st.text_input("Nome do Grupo (Ex: Apex 5 Contas - A)")
                    if st.form_submit_button("Criar Grupo"):
                        if novo_grupo:
                            supabase.table("grupos_config").insert({"usuario": USER, "nome": novo_grupo}).execute(); st.rerun()
                        else: st.warning("Digite um nome.")
                st.divider()
                st.write("Grupos Existentes:")
                df_g = load_grupos_config()
                if not df_g.empty:
                    for idx, row in df_g.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.info(f"📂 {row['nome']}")
                        if c2.button("Excluir", key=f"del_g_{row['id']}"):
                            supabase.table("grupos_config").delete().eq("id", row['id']).execute(); st.rerun()

            # --- ABA 2: CADASTRAR CONTA ---
            with t2:
                st.subheader("Vincular Conta")
                df_g = load_grupos_config()
                if not df_g.empty:
                    with st.form("form_conta"):
                        col_a, col_b = st.columns(2)
                        g_sel = col_a.selectbox("Grupo", sorted(df_g['nome'].unique()))
                        c_id = col_b.text_input("Identificador (Ex: PA-001)")
                        s_ini = col_a.number_input("Saldo ATUAL na Corretora ($)", value=150000.0, step=100.0)
                        p_pre = col_b.number_input("Pico Máximo (HWM)", value=150000.0, step=100.0)
                        fase_ini = col_a.selectbox("Fase Inicial (Referência)", ["Fase 1", "Fase 2", "Fase 3", "Fase 4"])
                        
                        if st.form_submit_button("Cadastrar Conta"):
                            if c_id:
                                try:
                                    supabase.table("contas_config").insert({
                                        "usuario": USER, "grupo_nome": g_sel, "conta_identificador": c_id,
                                        "saldo_inicial": s_ini, "pico_previo": p_pre,
                                        "fase_entrada": fase_ini, "status_conta": "Ativa"
                                    }).execute()
                                    st.success("Conta cadastrada!"); time.sleep(1); st.rerun()
                                except Exception as e: st.error(f"Erro: {e}")
                else: st.warning("Crie um grupo antes.")

            # --- ABA 3: VISÃO GERAL ---
            with t3:
                st.subheader("📋 Gestão e Mobilidade")
                df_c = load_contas_config()
                df_g_list = load_grupos_config()
                df_t = load_trades_db()
                if not df_t.empty: df_t = df_t[df_t['usuario'] == USER]
                
                lista_grupos_existentes = sorted(df_g_list['nome'].unique()) if not df_g_list.empty else []

                if not df_c.empty:
                    grupos_unicos = sorted(df_c['grupo_nome'].unique())
                    for grp in grupos_unicos:
                        with st.expander(f"📂 {grp}", expanded=True):
                            trades_grp = df_t[df_t['grupo_vinculo'] == grp] if not df_t.empty else pd.DataFrame()
                            lucro_grupo = trades_grp['resultado'].sum() if not trades_grp.empty else 0.0
                            contas_g = df_c[df_c['grupo_nome'] == grp]
                            
                            for _, row in contas_g.iterrows():
                                st_icon = "🟢" if row['status_conta'] == "Ativa" else "🔴"
                                saldo_atual = float(row['saldo_inicial']) + lucro_grupo
                                delta = saldo_atual - float(row['saldo_inicial'])
                                cor_delta = "#00FF88" if delta >= 0 else "#FF4B4B"
                                
                                c_info, c_edit, c_del = st.columns([3, 0.5, 0.5])
                                c_info.markdown(f"""
                                    <div style='background-color: #222; padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 3px solid {"#00FF88" if row['status_conta']=="Ativa" else "#FF4B4B"}'>
                                        <div style="display:flex; justify-content:space-between;">
                                            <span>💳 <b>{row['conta_identificador']}</b> <small>({row['fase_entrada']})</small></span>
                                            <span>{st_icon} {row['status_conta']}</span>
                                        </div>
                                        <div style='font-size: 1.1em; margin-top: 5px;'>💰 Saldo: <b>${saldo_atual:,.2f}</b> (<span style='color:{cor_delta}'>${delta:+,.2f}</span>)</div>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                with c_edit.popover("⚙️"):
                                    idx_grp = lista_grupos_existentes.index(row['grupo_nome']) if row['grupo_nome'] in lista_grupos_existentes else 0
                                    novo_grp = st.selectbox("Mover para Grupo", lista_grupos_existentes, index=idx_grp, key=f"mv_g_{row['id']}")
                                    
                                    status_ops = ["Ativa", "Pausada", "Quebrada"]
                                    idx_st = status_ops.index(row['status_conta']) if row['status_conta'] in status_ops else 0
                                    novo_status = st.selectbox("Status", status_ops, index=idx_st, key=f"mv_s_{row['id']}")
                                    
                                    novo_saldo_ini = st.number_input("Corrigir Saldo Inicial", value=float(row['saldo_inicial']), key=f"mv_si_{row['id']}")
                                    
                                    if st.button("💾 Salvar", key=f"btn_sv_{row['id']}"):
                                        supabase.table("contas_config").update({"grupo_nome": novo_grp, "status_conta": novo_status, "saldo_inicial": novo_saldo_ini}).eq("id", row['id']).execute()
                                        st.rerun()

                                if c_del.button("🗑️", key=f"del_acc_{row['id']}"):
                                    supabase.table("contas_config").delete().eq("id", row['id']).execute(); st.rerun()
                else: st.info("Nenhuma conta configurada.")

            # ==============================================================================
            # ABA 4: MONITOR DE PERFORMANCE (v160 - TRAILING STOP CORRIGIDO)
            # ==============================================================================
            with t4:
                st.subheader("🚀 Monitor de Performance (Apex 150k)")
                df_c = load_contas_config()
                df_t = load_trades_db()
                if not df_t.empty: df_t = df_t[df_t['usuario'] == USER]

                if not df_c.empty:
                    grps = sorted(df_c['grupo_nome'].unique())
                    col_sel, col_vis = st.columns([2, 1])
                    sel_g = col_sel.selectbox("Escolher Grupo para Monitorar", grps)
                    vis_mode = col_vis.radio("Eixo X", ["Trade a Trade", "Diário"], horizontal=True)
                    st.markdown("---")
                    
                    contas_g = df_c[df_c['grupo_nome'] == sel_g]
                    trades_g = df_t[df_t['grupo_vinculo'] == sel_g] if not df_t.empty else pd.DataFrame()
                    
                    if not contas_g.empty:
                        # 1. SETUP DE DADOS - RESPEITO AO BANCO
                        conta_ref = contas_g.iloc[0]
                        saldo_inicial_base = float(conta_ref['saldo_inicial'])
                        pico_manual = float(conta_ref.get('pico_previo', saldo_inicial_base))
                        fase_str_db = str(conta_ref.get('fase_entrada', 'Fase 1'))
                        
                        # Define a fase base do banco (não rebaixa)
                        if "Fase 4" in fase_str_db: fase_base = 4
                        elif "Fase 3" in fase_str_db: fase_base = 3
                        elif "Fase 2" in fase_str_db: fase_base = 2
                        else: fase_base = 1

                        lucro_total_grupo = trades_g['resultado'].sum() if not trades_g.empty else 0.0
                        saldo_atual_base = saldo_inicial_base + lucro_total_grupo
                        
                        # Promoção automática (SÓ SOBE)
                        fase_final = fase_base
                        if fase_base == 1 and saldo_atual_base >= 159000.0: fase_final = 2
                        if fase_final == 2 and saldo_atual_base >= 155100.0: fase_final = 3
                        if fase_final == 3 and saldo_atual_base >= 161000.0: fase_final = 4

                        # Definição de Metas
                        if fase_final == 1: meta_dinamica = 159000.0; status_lbl = "Fase 1: Teste (Alvo 9k)"
                        elif fase_final == 2: meta_dinamica = 155100.0; status_lbl = "Fase 2: Colchão PA (Alvo 5.1k)"
                        elif fase_final == 3: meta_dinamica = 161000.0; status_lbl = "Fase 3: Escalada (Rumo aos 161k)"
                        else: meta_dinamica = 162000.0; status_lbl = "Fase 4: MODO SAQUE"

                        # 2. CÁLCULO DE STOP E HWM ATUAL
                        if not trades_g.empty:
                            temp = trades_g.sort_values('created_at').copy()
                            temp['equity'] = temp['resultado'].cumsum() + saldo_inicial_base
                            max_equity = temp['equity'].max()
                        else: max_equity = saldo_inicial_base
                        
                        hwm_real_atual = max(pico_manual, max_equity, saldo_inicial_base)
                        stop_atual_val = 150100.0 if hwm_real_atual >= 155100.0 else hwm_real_atual - 5000.0

                        # 3. CARDS DE INFORMAÇÃO
                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Saldo Atual", f"${saldo_atual_base:,.2f}", f"Lucro: ${lucro_total_grupo:+,.2f}")
                        k2.metric("HWM (Topo)", f"${hwm_real_atual:,.2f}")
                        
                        dist_stop = saldo_atual_base - stop_atual_val
                        k3.metric("Dist. Stop", f"${dist_stop:,.2f}", f"Stop: ${stop_atual_val:,.0f}", delta_color="inverse" if dist_stop < 1500 else "normal")
                        k4.metric("Fase Atual", status_lbl)

                        cg, cp = st.columns([2, 1])

                        # 4. GRÁFICO (LINHA SÓLIDA)
                        with cg:
                            st.markdown("##### 🌊 Curva do Grupo")
                            if not trades_g.empty:
                                if vis_mode == "Diário":
                                    trades_g['data'] = pd.to_datetime(trades_g['data'])
                                    df_plot = trades_g.groupby('data')['resultado'].sum().reset_index()
                                    df_plot['saldo_acc'] = df_plot['resultado'].cumsum() + saldo_inicial_base
                                    df_plot.rename(columns={'data': 'eixo_x'}, inplace=True)
                                    start_x = df_plot['eixo_x'].min() - timedelta(days=1)
                                    df_plot = pd.concat([pd.DataFrame([{'eixo_x': start_x, 'saldo_acc': saldo_inicial_base}]), df_plot], ignore_index=True)
                                    x_col = 'eixo_x'
                                else:
                                    df_sorted = trades_g.sort_values('created_at').copy()
                                    df_sorted['seq'] = range(1, len(df_sorted)+1)
                                    df_plot = df_sorted
                                    df_plot['saldo_acc'] = df_plot['resultado'].cumsum() + saldo_inicial_base
                                    df_plot.rename(columns={'seq': 'eixo_x'}, inplace=True)
                                    x_col = 'eixo_x'

                                hwm_start = max(saldo_inicial_base, pico_manual)
                                df_plot['hwm_hist'] = df_plot['saldo_acc'].cummax().clip(lower=hwm_start)
                                df_plot['stop_hist'] = df_plot['hwm_hist'].apply(lambda x: 150100.0 if x >= 155100.0 else x - 5000.0)

                                fig = px.line(df_plot, x=x_col, y='saldo_acc', template="plotly_dark")
                                fig.update_traces(line_color='#2E93fA', fill='tozeroy', fillcolor='rgba(46, 147, 250, 0.1)', name="Saldo")
                                
                                fig.add_scatter(x=df_plot[x_col], y=df_plot['stop_hist'], mode='lines', 
                                              line=dict(color='#FF4B4B', width=2), name='Trailing Stop',
                                              hovertemplate='Stop: $%{y:,.2f}<extra></extra>')
                                
                                fig.add_hline(y=meta_dinamica, line_dash="dot", line_color="#00FF88", annotation_text="Meta")
                                fig.add_hline(y=161000, line_color="gold", line_width=1, opacity=0.3)
                                
                                y_min = min(df_plot['stop_hist'].min(), df_plot['saldo_acc'].min()) - 1000
                                y_max = max(df_plot['saldo_acc'].max(), meta_dinamica) + 1000
                                fig.update_layout(yaxis_range=[y_min, y_max], showlegend=True, legend=dict(orientation="h", y=1.1))
                                st.plotly_chart(fig, use_container_width=True)
                            else: st.info("Sem trades registrados.")

                        # 5. PROGRESSO DA FASE + EV
                        with cp:
                            st.markdown("##### 🎯 Progresso da Fase")
                            if fase_final <= 2: p_zero = 150000.0
                            elif fase_final == 3: p_zero = 155100.0
                            else: p_zero = 161000.0
                            
                            total_fase = meta_dinamica - p_zero
                            ganho_real = saldo_atual_base - p_zero
                            
                            percent = min(1.0, max(0.0, ganho_real / total_fase)) if total_fase > 0 else 1.0
                            st.write(f"Conclusão: {percent*100:.1f}%")
                            st.progress(percent)
                            
                            falta_money = meta_dinamica - saldo_atual_base
                            
                            # Cálculo EV e Trades Restantes
                            ev_por_trade = trades_g['resultado'].mean() if not trades_g.empty else 0.0
                            
                            if falta_money > 0:
                                if ev_por_trade > 0:
                                    trades_restantes = math.ceil(falta_money / ev_por_trade)
                                    st.write(f"Faltam **~{trades_restantes} trades** (EV: ${ev_por_trade:,.2f})")
                                else:
                                    st.write(f"Faltam: **${falta_money:,.2f}**")
                            else:
                                st.success("Meta Batida! 🚀")

                    else: st.warning("Grupo vazio.")
                    
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
