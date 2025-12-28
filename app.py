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
# 1. INFRAESTRUTURA E CONEXÃO (BLINDADA)
# ==============================================================================
st.set_page_config(
    page_title="EvoTrade Empire v200", 
    layout="wide", 
    page_icon="🦅",
    initial_sidebar_state="expanded"
)

# Tratamento de Erro na Conexão com Supabase
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("🔴 ERRO CRÍTICO DE CONEXÃO:")
    st.error(f"Detalhes: {e}")
    st.warning("Verifique se o arquivo .streamlit/secrets.toml está configurado corretamente.")
    st.stop()

# ==============================================================================
# 2. DESIGN SYSTEM (DARK MODE AGRESSIVO + CSS)
# ==============================================================================
st.markdown("""
    <style>
    /* Reset Geral */
    .stApp { background-color: #0F0F0F; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #222; }
    
    /* Cards do Histórico (Trade Cards) */
    .trade-card {
        background-color: #161616;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid #262626;
        transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
    }
    .trade-card:hover {
        transform: translateY(-4px);
        border-color: #B20000;
        box-shadow: 0 6px 12px rgba(178, 0, 0, 0.15);
    }
    .card-img-container {
        width: 100%; height: 150px; background-color: #222;
        border-radius: 8px; overflow: hidden; display: flex;
        align-items: center; justify-content: center; margin-bottom: 12px;
    }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 15px; font-weight: 700; color: white; margin-bottom: 4px; }
    .card-sub { font-size: 12px; color: #888; margin-bottom: 10px; display: flex; justify-content: space-between; }
    .card-res-win { font-size: 18px; font-weight: 800; color: #00FF88; text-shadow: 0 0 10px rgba(0,255,136,0.3); } 
    .card-res-loss { font-size: 18px; font-weight: 800; color: #FF4B4B; }

    /* Métricas do Dashboard (KPI Cards) */
    .metric-container { 
        background-color: #161616; 
        border: 1px solid #262626; 
        padding: 20px; 
        border-radius: 12px; 
        text-align: center; 
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
        position: relative;
        min-height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .metric-container:hover {
        border-color: #B20000;
        transform: translateY(-3px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.5);
    }
    .metric-label { 
        color: #888; font-size: 12px; text-transform: uppercase; 
        letter-spacing: 1.5px; font-weight: 600; display: flex; 
        justify-content: center; align-items: center; gap: 6px;
    }
    .metric-value { color: white; font-size: 26px; font-weight: 800; margin-top: 8px; }
    .metric-sub { font-size: 13px; margin-top: 6px; color: #666; font-weight: 500; }
    
    .help-icon {
        color: #555; font-size: 12px; border: 1px solid #444;
        border-radius: 50%; width: 16px; height: 16px;
        display: inline-flex; align-items: center; justify-content: center;
        cursor: help;
    }

    /* Alerta de Perigo Imediato (Piscante) */
    .piscante-erro { 
        padding: 25px; 
        border-radius: 10px; 
        color: white; 
        font-weight: 900; 
        text-align: center; 
        animation: blinking 1.2s infinite; 
        border: 2px solid #FF0000;
        background-color: #440000;
        margin-bottom: 25px;
        text-transform: uppercase;
        font-size: 22px;
        letter-spacing: 2px;
        box-shadow: 0 0 20px rgba(255, 0, 0, 0.4);
    }
    
    .risco-alert {
        color: #FF4B4B; font-weight: bold; font-size: 16px; margin-top: 5px;
        background-color: rgba(255, 75, 75, 0.1); padding: 10px; border-radius: 5px; 
        text-align: center; border: 1px solid #FF4B4B;
    }
    
    @keyframes blinking { 
        0% { background-color: #440000; border-color: #FF0000; } 
        50% { background-color: #FF0000; border-color: #FFFFFF; } 
        100% { background-color: #440000; border-color: #FF0000; } 
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: #0F0F0F; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 5px; }
    ::-webkit-scrollbar-thumb:hover { background: #B20000; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. SISTEMA DE LOGIN E SESSÃO
# ==============================================================================
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False
if "login_attempted" not in st.session_state:
    st.session_state["login_attempted"] = False

def check_password():
    """Retorna True se o usuário estiver logado com sucesso."""
    def password_entered():
        st.session_state["login_attempted"] = True
        u = st.session_state.get("username_input")
        p = st.session_state.get("password_input")
        try:
            # Query segura na tabela users
            res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data:
                st.session_state["password_correct"] = True
                st.session_state["logged_user"] = u
                st.session_state["user_role"] = res.data[0].get('role', 'user')
            else:
                st.session_state["password_correct"] = False
        except Exception as e:
            st.error(f"Erro de conexão no login: {e}")

    if not st.session_state["password_correct"]:
        # Layout da Tela de Login
        st.markdown("""
            <style>
            .login-container {
                max-width: 450px; margin: 100px auto; padding: 40px;
                background-color: #161616; border-radius: 15px;
                border: 1px solid #B20000; text-align: center;
                box-shadow: 0 0 30px rgba(178, 0, 0, 0.2);
            }
            .logo-main { color: #B20000; font-size: 60px; font-weight: 900; letter-spacing: -2px; }
            .logo-sub { color: white; font-size: 40px; font-weight: 700; margin-top: -20px; letter-spacing: 5px; }
            </style>
        """, unsafe_allow_html=True)
        
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.markdown('<div class="login-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("ACESSAR TERMINAL", on_click=password_entered, use_container_width=True, type="primary")
            
            if st.session_state["login_attempted"] and not st.session_state["password_correct"]:
                st.error("❌ Credenciais inválidas.")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

# ------------------------------------------------------------------------------
# INÍCIO DO CÓDIGO PRINCIPAL (Só executa se logado)
# ------------------------------------------------------------------------------
if check_password():
    # Variáveis Globais de Sessão
    MULTIPLIERS = {"NQ": 20, "MNQ": 2, "ES": 50, "MES": 5}
    USER = st.session_state["logged_user"]
    ROLE = st.session_state.get("user_role", "user")

    # ==========================================================================
    # 4. FUNÇÕES DE ACESSO A DADOS (DATA ACCESS LAYER)
    # ==========================================================================
    def load_trades_db():
        """Carrega e trata os dados de trades do banco."""
        try:
            res = supabase.table("trades").select("*").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                # Conversão segura de datas
                df['data'] = pd.to_datetime(df['data']).dt.date
                df['created_at'] = pd.to_datetime(df['created_at'])
                
                # Conversão segura de números (caso venha texto)
                df['resultado'] = pd.to_numeric(df['resultado'], errors='coerce').fillna(0.0)
                df['lote'] = pd.to_numeric(df['lote'], errors='coerce').fillna(0)
                
                # Preenchimento de colunas opcionais
                if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
                if 'comportamento' not in df.columns: df['comportamento'] = 'Normal'
            return df
        except Exception as e:
            st.error(f"Erro ao carregar trades: {e}")
            return pd.DataFrame()

    def load_atms_db():
        try:
            res = supabase.table("atm_configs").select("*").execute()
            return {item['nome']: item for item in res.data}
        except: return {}

    def load_contas_config():
        try:
            res = supabase.table("contas_config").select("*").eq("usuario", USER).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                # Garante colunas mínimas
                if 'pico_previo' not in df.columns: df['pico_previo'] = df['saldo_inicial']
                if 'fase_entrada' not in df.columns: df['fase_entrada'] = 'Fase 1'
                if 'status_conta' not in df.columns: df['status_conta'] = 'Ativa'
                
                # Garante numérico
                df['saldo_inicial'] = pd.to_numeric(df['saldo_inicial'], errors='coerce').fillna(0.0)
                df['pico_previo'] = pd.to_numeric(df['pico_previo'], errors='coerce').fillna(0.0)
            return df
        except: return pd.DataFrame()
            
    def load_grupos_config():
        try:
            res = supabase.table("grupos_config").select("*").eq("usuario", USER).execute()
            return pd.DataFrame(res.data)
        except: return pd.DataFrame()

    def card_metric(label, value, sub_value="", color="white", help_text=""):
        """Gera o HTML do Card de Métrica (KPI)."""
        sub_html = f'<div class="metric-sub">{sub_value}</div>' if sub_value else '<div class="metric-sub">&nbsp;</div>'
        help_html = f'<span class="help-icon" title="{help_text}">?</span>' if help_text else ""
        
        st.markdown(f"""
            <div class="metric-container" title="{help_text}">
                <div class="metric-label">{label} {help_html}</div>
                <div class="metric-value" style="color: {color};">{value}</div>
                {sub_html}
            </div>
        """, unsafe_allow_html=True)

    # ==========================================================================
    # 5. LÓGICA DE NEGÓCIO: MOTOR APEX (VERSÃO BLINDADA)
    # ==========================================================================
    def calcular_saude_apex(saldo_inicial, pico_previo, trades_df):
        """
        Motor Apex v200: Calcula Trailing Stop, HWM e Fases.
        BLINDAGEM: Respeita o maior valor entre Saldo, Pico Histórico e Gráfico Atual.
        """
        # 0. Tratamento de Tipos
        try:
            s_ini = float(saldo_inicial)
            p_prev = float(pico_previo) if pico_previo is not None else s_ini
        except:
            s_ini = 150000.0; p_prev = 150000.0 # Fallback

        # 1. Regras Apex (Hardcoded Lookup Table)
        if s_ini >= 250000:   # 300k
            dd_max = 7500.0; meta_trava = s_ini + dd_max + 100.0; meta_f3 = s_ini + 15000.0
        elif s_ini >= 100000: # 150k
            dd_max = 5000.0; meta_trava = 155100.0; meta_f3 = 161000.0
        elif s_ini >= 50000:  # 50k
            dd_max = 2500.0; meta_trava = 52600.0; meta_f3 = 56000.0
        else:                 # 25k
            dd_max = 1500.0; meta_trava = 26600.0; meta_f3 = 28000.0
            
        # 2. Calcular Saldo Atual
        lucro_acc = trades_df['resultado'].sum() if not trades_df.empty else 0.0
        saldo_atual = s_ini + lucro_acc
        
        # 3. Calcular Pico Real (High Water Mark)
        candidatos_pico = [s_ini, p_prev]
        
        if not trades_df.empty:
            trades_sorted = trades_df.sort_values('created_at')
            # Reconstrói a curva de patrimônio dia a dia
            equity_curve = trades_sorted['resultado'].cumsum() + s_ini
            pico_grafico = equity_curve.max()
            candidatos_pico.append(pico_grafico)
            
        pico_real = max(candidatos_pico) # Pega o MAIOR valor já visto na história

        # 4. Lógica da Trava (The Lock)
        stop_travado = s_ini + 100.0
        
        if pico_real >= meta_trava:
            stop_atual = stop_travado
            status_stop = "TRAVADO"
        else:
            stop_atual = pico_real - dd_max
            status_stop = "TRAILING"
            
        buffer = max(0.0, saldo_atual - stop_atual)
        
        # 5. Fases Empire Builder
        if stop_atual == stop_travado:
            # Se travou, já venceu a Fase 2
            if saldo_atual < meta_f3:
                fase_nome = "Fase 3 (Blindagem)"
                status_fase = "Rumo aos 161k"
                meta_global = meta_f3
                distancia_meta = meta_f3 - saldo_atual
            else:
                fase_nome = "Fase 4 (Império)"
                status_fase = "Liberado Saque"
                meta_global = 999999.0
                distancia_meta = 0.0
        else:
            # Ainda em busca da trava
            fase_nome = "Fase 2 (Colchão)"
            status_fase = "Buscando Trava"
            meta_global = meta_trava
            distancia_meta = meta_trava - saldo_atual
        
        return {
            "saldo_atual": saldo_atual,
            "stop_atual": stop_atual,
            "buffer": buffer,
            "hwm": pico_real,
            "meta_global": meta_global,
            "distancia_meta": distancia_meta, 
            "dd_max": dd_max,
            "lock_threshold": meta_trava,
            "stop_travado": stop_travado,
            "fase_nome": fase_nome,
            "status_fase": status_fase
        }

    # ==========================================================================
    # 6. MENU DE NAVEGAÇÃO
    # ==========================================================================
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        st.markdown("---")
        
        menu_options = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico", "Plano de Trading"]
        menu_icons = ["grid", "currency-dollar", "gear", "clock", "file-earmark-text"]
        
        if ROLE in ['master', 'admin']:
            menu_options.insert(2, "Contas")
            menu_icons.insert(2, "briefcase")
            
        if ROLE == 'admin':
            menu_options.append("Gerenciar Usuários")
            menu_icons.append("people")
            
        selected = option_menu(
            menu_title=None, 
            options=menu_options, 
            icons=menu_icons, 
            styles={
                "nav-link-selected": {"background-color": "#B20000"},
                "nav-link": {"font-size": "14px", "margin": "5px"}
            }
        )
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Sair / Logout", use_container_width=True): 
            st.session_state.clear()
            st.rerun()

    # ==============================================================================
    # 7. ABA: DASHBOARD (v201 - COMPLETO COM TODAS AS MÉTRICAS RESTAURADAS)
    # ==============================================================================
    elif selected == "Dashboard":
        st.title(f"📊 Central de Controle ({USER})")
        
        df_raw = load_trades_db()
        df_contas = load_contas_config()
        
        # INICIALIZAÇÃO DE VARIÁVEIS DE SEGURANÇA (Para não quebrar se não tiver dados)
        win_rate_dec = 0.0; loss_rate_dec = 0.0; payoff = 0.0; total_trades = 0
        r_min_show = 0.0; r_max_show = 0.0
        
        if not df_raw.empty:
            # Filtro Crítico: Apenas trades do usuário logado
            df = df_raw[df_raw['usuario'] == USER].copy()
            
            if not df.empty:
                # --- ÁREA DE FILTROS ---
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

                # Aplicação dos Filtros
                mask = (df['data'] >= d_inicio) & (df['data'] <= d_fim) & (df['contexto'].isin(filters_ctx))
                if sel_grupo != "Todos":
                    mask = mask & (df['grupo_vinculo'] == sel_grupo)
                
                df_filtered = df[mask].copy()

                if df_filtered.empty:
                    st.warning("⚠️ Nenhum trade encontrado com os filtros atuais.")
                else:
                    # --- LOOP DE CÁLCULO DE CONTAS (MOTOR APEX) ---
                    total_buffer_real = 0.0
                    soma_saldo_agora = 0.0
                    contas_analisadas = 0
                    
                    if not df_contas.empty:
                        c_alvo = df_contas if sel_grupo == "Todos" else df_contas[df_contas['grupo_nome'] == sel_grupo]
                        for _, row in c_alvo.iterrows():
                            if row.get('status_conta', 'Ativa') == 'Ativa':
                                trades_deste_grupo = df[df['grupo_vinculo'] == row['grupo_nome']]
                                
                                # Chama o Motor Blindado
                                status_conta = calcular_saude_apex(
                                    row['saldo_inicial'], 
                                    row['pico_previo'], 
                                    trades_deste_grupo
                                )
                                
                                total_buffer_real += status_conta['buffer']
                                soma_saldo_agora += status_conta['saldo_atual']
                                contas_analisadas += 1
                    
                    stop_atual_val = soma_saldo_agora - total_buffer_real if contas_analisadas > 0 else 0.0

                    # --- KPIs FINANCEIROS E ESTATÍSTICOS ---
                    total_trades = len(df_filtered)
                    wins = df_filtered[df_filtered['resultado'] > 0]
                    losses = df_filtered[df_filtered['resultado'] < 0]
                    
                    net_profit = df_filtered['resultado'].sum()
                    gross_profit = wins['resultado'].sum()
                    gross_loss = abs(losses['resultado'].sum())
                    
                    pf = gross_profit / gross_loss if gross_loss > 0 else 99.9
                    pf_str = f"{pf:.2f}" if gross_loss > 0 else "∞"
                    
                    win_rate_dec = len(wins) / total_trades if total_trades > 0 else 0
                    loss_rate_dec = len(losses) / total_trades if total_trades > 0 else 0
                    win_rate = win_rate_dec * 100
                    
                    avg_win = wins['resultado'].mean() if not wins.empty else 0
                    avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0
                    payoff = avg_win / avg_loss if avg_loss > 0 else 1.0
                    expectancy = (win_rate_dec * avg_win) - (loss_rate_dec * avg_loss)
                    
                    lote_medio_real = df_filtered['lote'].mean() if not df_filtered.empty else 0
                    pts_loss_medio_real = abs(losses['pts_medio'].mean()) if not losses.empty else 15.0 
                    ativo_referencia = df_filtered['ativo'].iloc[-1] if not df_filtered.empty else "MNQ"
                    
                    avg_pts_gain = wins['pts_medio'].mean() if not wins.empty else 0
                    
                    # Ordenação para Gráfico de Equity e Drawdown
                    df_filtered = df_filtered.sort_values('created_at')
                    df_filtered['equity'] = df_filtered['resultado'].cumsum()
                    max_dd = (df_filtered['equity'] - df_filtered['equity'].cummax()).min()

                    # --- ANÁLISE DE RISCO (BROWNIAN MOTION) ---
                    risco_comportamental = lote_medio_real * pts_loss_medio_real * MULTIPLIERS.get(ativo_referencia, 2)
                    if risco_comportamental == 0: risco_comportamental = 300.0

                    fator_replicacao = contas_analisadas if contas_analisadas > 0 else 1
                    risco_grupo_total = risco_comportamental * fator_replicacao
                    vidas_u = total_buffer_real / risco_grupo_total if risco_grupo_total > 0 else 0

                    p = win_rate_dec
                    q = 1 - p
                    prob_ruina = 0.0
                    msg_alerta = "Calculando..."
                    
                    if total_trades < 5:
                        msg_alerta = "⚠️ Calibrando..."
                        color_r = "gray"
                    elif vidas_u <= 0.5:
                        prob_ruina = 100.0
                        msg_alerta = "LIQUIDAÇÃO IMINENTE"
                        color_r = "#FF0000"
                    elif expectancy <= 0:
                        prob_ruina = 100.0
                        msg_alerta = "EDGE NEGATIVO"
                        color_r = "#FF0000"
                    else:
                        variancia = (p * (avg_win - expectancy)**2) + (q * (-avg_loss - expectancy)**2)
                        if variancia > 0:
                            arg_exp = -2 * expectancy * total_buffer_real / variancia
                            try: prob_ruina = math.exp(arg_exp) * 100
                            except: prob_ruina = 0.0
                        
                        prob_ruina = min(max(prob_ruina, 0.0), 100.0)
                        
                        if prob_ruina < 1.0: color_r = "#00FF88"; msg_alerta = "Zona de Segurança"
                        elif prob_ruina < 5.0: color_r = "#FFFF00"; msg_alerta = "Risco Moderado"
                        else: color_r = "#FF4B4B"; msg_alerta = "RISCO CRÍTICO"

                    if prob_ruina > 10.0 and total_trades >= 5 and expectancy > 0:
                        st.markdown(f"""<div class="piscante-erro">💀 ALERTA DE RUÍNA: {prob_ruina:.2f}% 💀<br><span style="font-size:16px;">REDUZA O LOTE AGORA.</span></div>""", unsafe_allow_html=True)

                    # --- EXIBIÇÃO CARDS (AGORA COMPLETO) ---
                    
                    # LINHA 1: GERAL
                    st.markdown("##### 🏁 Desempenho Geral")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: card_metric("RESULTADO LÍQUIDO", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f} / -${gross_loss:,.0f}", "#00FF88" if net_profit >= 0 else "#FF4B4B", "Dinheiro no bolso.")
                    with c2: card_metric("FATOR DE LUCRO (PF)", pf_str, "Ideal > 1.5", "#B20000", "Eficiência.")
                    with c3: card_metric("WIN RATE", f"{win_rate:.1f}%", f"{len(wins)}W / {len(losses)}L", "white", "Taxa de acerto.")
                    with c4: card_metric("EXPECTATIVA MAT.", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy > 0 else "#FF4B4B", "Edge estatístico.")
                    
                    # LINHA 2: MÉDIAS FINANCEIRAS (RESTAURADA)
                    st.markdown("##### 💲 Médias Financeiras")
                    c5, c6, c7, c8 = st.columns(4)
                    with c5: card_metric("MÉDIA GAIN ($)", f"${avg_win:,.2f}", "", "#00FF88", "Média de lucro nos gains.")
                    with c6: card_metric("MÉDIA LOSS ($)", f"-${avg_loss:,.2f}", "", "#FF4B4B", "Média de prejuízo nos stops.")
                    with c7: card_metric("RISCO : RETORNO", f"1 : {payoff:.2f}", "Payoff Real", "white", "Quanto ganha para cada 1 que perde.")
                    with c8: card_metric("DRAWDOWN MÁXIMO", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B", "Maior queda a partir do topo.")

                    # LINHA 3: PERFORMANCE TÉCNICA (RESTAURADA)
                    st.markdown("##### 🎯 Performance Técnica")
                    c9, c10, c11, c12 = st.columns(4)
                    with c9: card_metric("PTS MÉDIOS (GAIN)", f"{avg_pts_gain:.2f} pts", "", "#00FF88", "Média de pontos nos gains.")
                    with c10: card_metric("STOP MÉDIO (LOSS)", f"{pts_loss_medio_real:.2f} pts", "Base do Risco", "#FF4B4B", "Tamanho médio do stop em pontos.")
                    with c11: card_metric("LOTE MÉDIO", f"{lote_medio_real:.1f}", "Contratos", "white", "Tamanho da mão média.")
                    with c12: card_metric("TOTAL TRADES", str(total_trades), "Executados", "white", "Volume total.")

                    # LINHA 4: SOBREVIVÊNCIA E RISCO
                    st.markdown("---")
                    st.subheader(f"🛡️ Análise de Sobrevivência (Brownian Motion) - {sel_grupo}")
                    k1, k2, k3, k4 = st.columns(4)
                    z_edge = (win_rate_dec * payoff) - loss_rate_dec
                    with k1: card_metric("Z-SCORE (EDGE)", f"{z_edge:.4f}", "Força do Edge", "#00FF88" if z_edge > 0 else "#FF4B4B", "Confiabilidade estatística.")
                    with k2: card_metric("BUFFER REAL", f"${total_buffer_real:,.0f}", f"{contas_analisadas} Contas", "#00FF88", "Oxigênio (Distância pro Stop da Mesa).")
                    with k3: card_metric("VIDAS REAIS (U)", f"{vidas_u:.1f}", f"Risco Base: ${risco_grupo_total:,.0f}", "#FF4B4B" if vidas_u < 6 else "#00FF88", "Quantos stops cheios suporta.")
                    with k4: 
                        st.markdown(f"""<div style="background: #161616; border: 2px solid {color_r}; border-radius: 12px; padding: 10px; text-align: center; height: 150px; display:flex; flex-direction:column; justify-content:center;">
                            <div style="color:#888; font-size:11px; font-weight:bold;">PROB. RUÍNA</div>
                            <div style="color:{color_r}; font-size:24px; font-weight:900;">{prob_ruina:.2f}%</div>
                            <div style="color:#BBB; font-size:11px;">{msg_alerta}</div>
                        </div>""", unsafe_allow_html=True)

                    # --- KELLY CRITERION ---
                    st.markdown("---")
                    st.subheader("🧠 Inteligência de Lote (Kelly)")
                    
                    if payoff > 0 and expectancy > 0 and total_trades > 5:
                        kelly_full = win_rate_dec - ((1 - win_rate_dec) / payoff)
                        kelly_half = max(0.0, kelly_full / 2)
                        
                        VIDAS_IDEAL = 20.0
                        risco_teto_kelly = total_buffer_real * kelly_half
                        risco_vidas_20 = total_buffer_real / VIDAS_IDEAL
                        
                        risco_piso_final = min(risco_vidas_20, risco_teto_kelly)
                        
                        risco_por_lote = pts_loss_medio_real * MULTIPLIERS.get(ativo_referencia, 2)
                        
                        if risco_por_lote > 0:
                            lote_sug = math.floor(risco_piso_final / risco_por_lote)
                        else: lote_sug = 0
                        
                        HARD_CAP = 40
                        if lote_sug > HARD_CAP: lote_sug = HARD_CAP
                        
                        r_min_show = lote_sug * risco_por_lote
                        r_max_show = r_min_show # Simplificado
                        
                        cor_k = "#00FF88" if lote_sug > 0 else "#FF4B4B"
                        status_k = "ZONA DE ACELERAÇÃO" if lote_sug > 0 else "SEM GORDURA"
                    else:
                        lote_sug = 0; kelly_half = 0.0
                        # CORREÇÃO: Definindo variaveis para não quebrar
                        r_min_show = 0.0; r_max_show = 0.0
                        cor_k = "#888"; status_k = "DADOS INSUFICIENTES"

                    ka, kb, kc = st.columns(3)
                    with ka: card_metric("HALF-KELLY", f"{kelly_half*100:.1f}%", "Teto Matemático", "#888")
                    with kb: card_metric("RISCO FINANCEIRO", f"${r_min_show:,.0f}", "Sugerido", cor_k)
                    with kc: 
                        st.markdown(f"""<div style="background: #161616; border: 2px solid {cor_k}; border-radius: 12px; padding: 10px; text-align: center;">
                            <div style="color:#888; font-size:11px; font-weight:bold;">SUGESTÃO DE LOTE</div>
                            <div style="color:{cor_k}; font-size:26px; font-weight:900;">{lote_sug} ctrs</div>
                            <div style="color:#BBB; font-size:11px;">{status_k}</div>
                        </div>""", unsafe_allow_html=True)

                    # --- GRÁFICOS ---
                    st.markdown("---")
                    g1, g2 = st.columns([2, 1])
                    
                    # Gráfico 1: Curva de Patrimônio
                    with g1:
                        view_mode = st.radio("Eixo X:", ["Trade", "Data"], horizontal=True, label_visibility="collapsed")
                        
                        saldo_inicial_plot = soma_saldo_agora - net_profit if soma_saldo_agora > 0 else 0
                        if saldo_inicial_plot == 0 and not df_contas.empty:
                             # Fallback se não calculou no loop
                             saldo_inicial_plot = df_contas[df_contas['status_conta'] == 'Ativa']['saldo_inicial'].sum()

                        df_filtered['equity_real'] = df_filtered['resultado'].cumsum() + saldo_inicial_plot
                        
                        x_axis = 'data' if view_mode == "Data" else 'trade_seq'
                        if view_mode == "Trade": df_filtered['trade_seq'] = range(1, len(df_filtered)+1)
                        
                        fig_eq = px.area(df_filtered, x=x_axis, y='equity_real', title=f"📈 Curva de Patrimônio (Base: ${saldo_inicial_plot:,.0f})", template="plotly_dark")
                        fig_eq.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                        fig_eq.add_hline(y=saldo_inicial_plot, line_dash="dash", line_color="gray", annotation_text="Break Even")
                        st.plotly_chart(fig_eq, use_container_width=True)

                    # Gráfico 2: Contexto
                    with g2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        ctx_perf = df_filtered.groupby('contexto')['resultado'].sum().reset_index()
                        fig_bar = px.bar(ctx_perf, x='contexto', y='resultado', title="📊 Resultado por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                        st.plotly_chart(fig_bar, use_container_width=True)

                    # ==========================================================
                    # GRÁFICO DIAS DA SEMANA (VERSÃO ATÔMICA v201 - CORRIGIDA)
                    # ==========================================================
                    st.markdown("### 📅 Performance por Dia da Semana")
                    
                    # 1. Cópia limpa
                    df_clean = df_filtered.copy()
                    
                    # 2. Conversões Forçadas
                    df_clean['data_dt'] = pd.to_datetime(df_clean['data'], errors='coerce')
                    df_clean['res_num'] = pd.to_numeric(df_clean['resultado'], errors='coerce').fillna(0.0)
                    df_clean = df_clean.dropna(subset=['data_dt'])

                    if not df_clean.empty:
                        # 3. Extração Numérica do Dia (0=Segunda)
                        # ISSO CORRIGE O PROBLEMA DE IDIOMA (Monday vs Segunda)
                        df_clean['dia_idx'] = df_clean['data_dt'].dt.dayofweek
                        
                        # 4. Mapeamento Manual
                        mapa_dias = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sab', 6: 'Dom'}
                        df_clean['dia_nome'] = df_clean['dia_idx'].map(mapa_dias)
                        
                        # 5. Agrupamento e Soma
                        df_agrupado = df_clean.groupby('dia_nome')['res_num'].sum()
                        
                        # 6. Reindexação (Garante ordem e preenche zeros)
                        dias_ordem = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex']
                        df_final = df_agrupado.reindex(dias_ordem, fill_value=0.0).reset_index()
                        df_final.columns = ['Dia', 'Resultado ($)']
                        
                        # 7. Plotagem
                        fig_day = px.bar(
                            df_final, 
                            x='Dia', 
                            y='Resultado ($)',
                            text_auto='.2s',
                            template="plotly_dark",
                            color='Resultado ($)',
                            color_continuous_scale=["#FF4B4B", "#00FF88"]
                        )
                        fig_day.update_layout(xaxis_title=None, yaxis_title="Resultado ($)", showlegend=False, coloraxis_showscale=False)
                        st.plotly_chart(fig_day, use_container_width=True)
                    else:
                        st.info("Aguardando dados para gráfico semanal.")

            else: st.info("Sem trades registrados para este usuário.")
        else: st.warning("Banco de dados vazio.")

    # ==========================================================================
    # 8. ABA: REGISTRAR TRADE (CORRIGIDA COMPLETA)
    # ==========================================================================
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
            atv = st.selectbox("Ativo", ["MNQ", "NQ", "ES", "MES"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            
            # --- CONTEXTOS RESTAURADOS (A/B/C) ---
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
            psi = st.selectbox("Estado Mental", ["Focado/Bem", "Ansioso", "Vingativo", "Cansado", "Fomo", "Neutro"])
        with f2:
            lt = st.number_input("Contratos Total", min_value=1, value=lt_default)
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_default, step=0.25)
            if stp > 0:
                risco_calc = stp * MULTIPLIERS.get(atv, 2) * lt
                st.markdown(f'<div class="risco-alert">📉 Risco Estimado: ${risco_calc:,.2f}</div>', unsafe_allow_html=True)
            
            # --- UPLOAD MÚLTIPLO ATIVADO ---
            up = st.file_uploader("📸 Anexar Prints (O primeiro será a capa)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

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
                    # Cálculos Matemáticos
                    res_fin = sum([s["pts"] * MULTIPLIERS.get(atv, 2) * s["qtd"] for s in saidas])
                    pt_med = sum([s["pts"] * s["qtd"] for s in saidas]) / lt
                    
                    trade_id = str(uuid.uuid4())
                    img_url = ""
                    
                    # --- LÓGICA DE UPLOAD MÚLTIPLO (ATÔMICA) ---
                    if up:
                        # Se for lista (multiplos), pega o primeiro. Se for unico, usa ele.
                        # Isso garante que o DB receba string, mas a UI aceita varios
                        arquivo_final = up[0] if isinstance(up, list) else up
                        file_path = f"{trade_id}.png"
                        supabase.storage.from_("prints").upload(file_path, arquivo_final.getvalue())
                        img_url = supabase.storage.from_("prints").get_public_url(file_path)

                    # --- INSERT CORRIGIDO (Nomes de variáveis + Usuário) ---
                    supabase.table("trades").insert({
                        "id": trade_id, 
                        "usuario": USER,                  # <--- OBRIGATÓRIO PARA O DASHBOARD
                        "data": str(dt), 
                        "ativo": atv, 
                        "contexto": ctx,
                        "direcao": dr, 
                        "lote": lt, 
                        "resultado": res_fin,             # Corrigido (era 'fin')
                        "pts_medio": pt_med,
                        "grupo_vinculo": grupo_sel_trade, # Corrigido (era 'grp_sel')
                        "comportamento": psi,
                        "prints": img_url, 
                        "risco_fin": (stp * MULTIPLIERS.get(atv, 2) * lt)
                    }).execute()

                    st.balloons() 
                    st.success(f"✅ SUCESSO! Resultado: ${res_fin:,.2f}")
                    time.sleep(2); st.rerun()
                except Exception as e: st.error(f"Erro ao salvar: {e}")

    # ==========================================================================
    # 9. ABA: CONTAS (GESTAO DE PORTFOLIO)
    # ==========================================================================
    elif selected == "Contas" and ROLE in ['master', 'admin']:
        st.title("💼 Gestão de Portfólio (v200)")
        t1, t2, t3, t4 = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📋 Visão Geral", "🚀 Monitor"])
        
        with t1:
            st.subheader("Nova Estrutura")
            with st.form("form_grupo"):
                novo_grupo = st.text_input("Nome do Grupo (Ex: Apex 5 Contas - A)")
                if st.form_submit_button("Criar Grupo"):
                    if novo_grupo:
                        supabase.table("grupos_config").insert({"usuario": USER, "nome": novo_grupo}).execute(); st.rerun()
                    else: st.warning("Digite um nome.")
            st.divider(); st.write("Grupos Existentes:")
            df_g = load_grupos_config()
            if not df_g.empty:
                for idx, row in df_g.iterrows():
                    c1, c2 = st.columns([4, 1])
                    c1.info(f"📂 {row['nome']}")
                    if c2.button("Excluir", key=f"del_g_{row['id']}"):
                        supabase.table("grupos_config").delete().eq("id", row['id']).execute(); st.rerun()

        with t2:
            st.subheader("Vincular Conta")
            df_g = load_grupos_config()
            if not df_g.empty:
                with st.form("form_conta"):
                    col_a, col_b = st.columns(2)
                    g_sel = col_a.selectbox("Grupo", sorted(df_g['nome'].unique()))
                    c_id = col_b.text_input("Identificador (Ex: PA-001)")
                    s_ini = col_a.number_input("Saldo Inicial", value=150000.0, step=100.0)
                    p_pre = col_b.number_input("Pico Máximo (HWM - Histórico)", value=150000.0, step=100.0, help="Se sua conta já lucrou antes, coloque o maior saldo já atingido aqui.")
                    fase_ini = col_a.selectbox("Fase", ["Fase 1", "Fase 2", "Fase 3", "Fase 4"])
                    
                    if st.form_submit_button("Cadastrar Conta"):
                        if c_id:
                            supabase.table("contas_config").insert({
                                "usuario": USER, "grupo_nome": g_sel, "conta_identificador": c_id,
                                "saldo_inicial": s_ini, "pico_previo": p_pre,
                                "fase_entrada": fase_ini, "status_conta": "Ativa"
                            }).execute()
                            st.success("Conta cadastrada!"); time.sleep(1); st.rerun()
            else: st.warning("Crie um grupo primeiro.")

        with t3:
            st.subheader("📋 Visão Geral")
            df_c = load_contas_config(); df_t = load_trades_db()
            if not df_t.empty: df_t = df_t[df_t['usuario'] == USER]
            lista_grupos = sorted(load_grupos_config()['nome'].unique()) if not load_grupos_config().empty else []
            
            if not df_c.empty:
                for grp in sorted(df_c['grupo_nome'].unique()):
                    with st.expander(f"📂 {grp}", expanded=True):
                        trades_grp = df_t[df_t['grupo_vinculo'] == grp] if not df_t.empty else pd.DataFrame()
                        lucro_grupo = trades_grp['resultado'].sum() if not trades_grp.empty else 0.0
                        contas_g = df_c[df_c['grupo_nome'] == grp]
                        
                        for _, row in contas_g.iterrows():
                            st_icon = "🟢" if row['status_conta'] == "Ativa" else "🔴"
                            saldo_atual = float(row['saldo_inicial']) + lucro_grupo
                            c_info, c_edit, c_del = st.columns([3, 0.5, 0.5])
                            c_info.markdown(f"**{row['conta_identificador']}** | Saldo: ${saldo_atual:,.2f} | Status: {st_icon}")
                            with c_edit.popover("⚙️"):
                                n_grp = st.selectbox("Mover", lista_grupos, key=f"mv_{row['id']}")
                                n_st = st.selectbox("Status", ["Ativa", "Pausada", "Quebrada"], key=f"st_{row['id']}")
                                if st.button("Salvar", key=f"sv_{row['id']}"):
                                    supabase.table("contas_config").update({"grupo_nome": n_grp, "status_conta": n_st}).eq("id", row['id']).execute(); st.rerun()
                            if c_del.button("🗑️", key=f"dl_{row['id']}"):
                                supabase.table("contas_config").delete().eq("id", row['id']).execute(); st.rerun()

        with t4:
            st.subheader("🚀 Monitor Apex")
            df_c = load_contas_config(); df_t = load_trades_db()
            if not df_c.empty:
                sel_g_mon = st.selectbox("Grupo", sorted(df_c['grupo_nome'].unique()), key="mon_sel")
                contas_g = df_c[df_c['grupo_nome'] == sel_g_mon]
                trades_g = df_t[(df_t['usuario']==USER) & (df_t['grupo_vinculo']==sel_g_mon)] if not df_t.empty else pd.DataFrame()
                
                if not contas_g.empty:
                    c_ref = contas_g.iloc[0]
                    # MOTOR APEX CHAMADO AQUI
                    saude = calcular_saude_apex(c_ref['saldo_inicial'], c_ref['pico_previo'], trades_g)
                    
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Saldo", f"${saude['saldo_atual']:,.2f}")
                    k2.metric("Stop Atual", f"${saude['stop_atual']:,.0f}", saude['status_stop'])
                    k3.metric("Buffer (Vida)", f"${saude['buffer']:,.2f}")
                    st.progress(min(1.0, max(0.0, saude['buffer'] / saude['dd_max'])))
                else: st.warning("Grupo vazio.")

    # ==========================================================================
    # 10. ABA: CONFIGURAR ATM
    # ==========================================================================
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")
        if "atm_form" not in st.session_state: st.session_state.atm_form = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        
        def reset_form(): st.session_state.atm_form = {"id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]}
        
        c_list, c_form = st.columns([1, 1.5])
        with c_list:
            st.subheader("Salvas")
            if st.button("Nova Estratégia"): reset_form(); st.rerun()
            atms = supabase.table("atm_configs").select("*").execute().data
            for item in atms:
                with st.expander(f"📍 {item['nome']}"):
                    if st.button("Editar", key=f"ed_{item['id']}"):
                        p_data = item['parciais'] if isinstance(item['parciais'], list) else json.loads(item['parciais'])
                        st.session_state.atm_form = {"id": item['id'], "nome": item['nome'], "lote": item['lote'], "stop": item['stop'], "parciais": p_data}
                        st.rerun()
                    if st.button("Excluir", key=f"dl_atm_{item['id']}"):
                        supabase.table("atm_configs").delete().eq("id", item['id']).execute(); st.rerun()
        
        with c_form:
            f = st.session_state.atm_form
            st.subheader(f"Editando: {f['nome']}" if f['id'] else "Nova")
            new_nome = st.text_input("Nome", value=f['nome'])
            c1, c2 = st.columns(2)
            new_lote = c1.number_input("Lote", value=int(f['lote']), min_value=1)
            new_stop = c2.number_input("Stop Padrão", value=float(f['stop']))
            
            st.write("Parciais:")
            for i, p in enumerate(f['parciais']):
                cc1, cc2 = st.columns(2)
                p['pts'] = cc1.number_input(f"Pts {i+1}", value=float(p['pts']), key=f"pp_{i}")
                p['qtd'] = cc2.number_input(f"Qtd {i+1}", value=int(p['qtd']), key=f"pq_{i}")
            
            if st.button("Adicionar Parcial"): f['parciais'].append({"pts": 0.0, "qtd": 1}); st.rerun()
            if st.button("Salvar ATM", type="primary"):
                pay = {"nome": new_nome, "lote": new_lote, "stop": new_stop, "parciais": f['parciais']}
                if f['id']: supabase.table("atm_configs").update(pay).eq("id", f['id']).execute()
                else: supabase.table("atm_configs").insert(pay).execute()
                st.success("Salvo!"); time.sleep(1); reset_form(); st.rerun()

    # ==========================================================================
    # 11. ABA: HISTÓRICO
    # ==========================================================================
    elif selected == "Histórico":
        st.title("📜 Histórico de Trades")
        dfh = load_trades_db()
        if not dfh.empty:
            dfh = dfh[dfh['usuario'] == USER].sort_values('created_at', ascending=False)
            
            @st.dialog("Detalhes do Trade", width="large")
            def show_details(row):
                if row.get('prints'): st.image(row['prints'])
                c1, c2 = st.columns(2)
                c1.metric("Resultado", f"${row['resultado']:,.2f}")
                c2.metric("Lote", row['lote'])
                st.write(f"Contexto: {row['contexto']} | Mental: {row['comportamento']}")
                if st.button("Excluir Registro", type="primary"):
                    supabase.table("trades").delete().eq("id", row['id']).execute(); st.rerun()

            cols = st.columns(4)
            for i, (idx, row) in enumerate(dfh.iterrows()):
                with cols[i % 4]:
                    res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    img_html = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="height:100px; background:#222;"></div>'
                    st.markdown(f"""
                        <div class="trade-card">
                            <div class="card-img-container">{img_html}</div>
                            <div class="card-title">{row['ativo']} - {row['direcao']}</div>
                            <div class="{res_class}">${row['resultado']:,.2f}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("Ver", key=f"v_{row['id']}"): show_details(row)
        else: st.info("Histórico vazio.")

    # ==========================================================================
    # 12. ABA: PLANO DE TRADING
    # ==========================================================================
    elif selected == "Plano de Trading":
        st.title("📜 Plano Operacional")
        st.markdown("""
        ### Regras de Ouro
        1. **Respeitar o Stop Diário** por grupo de contas.
        2. **Não operar** com "Vidas" abaixo de 6 no Dashboard.
        3. **Alvo:** $500/semana por conta até atingir a trava.
        """)
        st.text_area("Anotações Pessoais", height=400)

    # ==========================================================================
    # 13. ADMINISTRAÇÃO DE USUÁRIOS
    # ==========================================================================
    elif selected == "Gerenciar Usuários" and ROLE == "admin":
        st.title("👥 Admin Panel")
        users = supabase.table("users").select("*").execute().data
        for u in users:
            c1, c2, c3 = st.columns([1, 1, 1])
            c1.write(u['username'])
            c2.write(u['role'])
            if c3.button("Editar", key=f"ued_{u['id']}"):
                st.session_state.editing_user = u
        
        if "editing_user" in st.session_state:
            with st.form("edit_user"):
                eu = st.session_state.editing_user
                nu = st.text_input("User", value=eu['username'])
                np = st.text_input("Pass", value=eu['password'])
                nr = st.selectbox("Role", ["user", "master", "admin"], index=["user", "master", "admin"].index(eu['role']))
                if st.form_submit_button("Salvar"):
                    supabase.table("users").update({"username": nu, "password": np, "role": nr}).eq("id", eu['id']).execute()
                    del st.session_state.editing_user
                    st.rerun()
