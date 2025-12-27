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
# 1. CONFIGURAÇÃO E CONEXÃO
# ==============================================================================
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Erro Crítico de Conexão: {e}")
    st.stop()

st.set_page_config(page_title="EvoTrade Terminal v182", layout="wide", page_icon="🦅")

# ==============================================================================
# 2. ESTILOS CSS (PROFISSIONAL / DARK MODE)
# ==============================================================================
st.markdown("""
    <style>
    /* Global */
    .stApp { background-color: #0e0e0e; }
    [data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #1a1a1a; }
    
    /* Metrics Cards */
    .metric-container { 
        background-color: #141414; 
        border: 1px solid #262626; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center; 
        margin-bottom: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5); 
        position: relative;
        min-height: 140px; 
        display: flex; 
        flex-direction: column; 
        justify-content: center; 
        align-items: center;
        transition: transform 0.2s, border-color 0.2s;
    }
    .metric-container:hover { 
        border-color: #B20000; 
        transform: translateY(-2px); 
    }
    .metric-label { 
        color: #888; 
        font-size: 11px; 
        text-transform: uppercase; 
        font-weight: 700; 
        letter-spacing: 1px; 
    }
    .metric-value { 
        color: white; 
        font-size: 24px; 
        font-weight: 800; 
        margin: 5px 0; 
    }
    .metric-sub { 
        font-size: 12px; 
        color: #666; 
    }

    /* Alerta Pânico (Piscante) */
    .piscante-erro { 
        padding: 20px; 
        border-radius: 8px; 
        color: white; 
        font-weight: 900; 
        text-align: center; 
        animation: blinking 1.0s infinite; 
        border: 2px solid #FF0000; 
        background-color: #3d0000; 
        margin-bottom: 20px;
        font-size: 18px; 
        text-transform: uppercase; 
        letter-spacing: 1.5px;
    }
    @keyframes blinking { 
        0% { border-color: #FF0000; box-shadow: 0 0 5px #FF0000; } 
        50% { border-color: #FFFFFF; box-shadow: 0 0 20px #FF0000; } 
        100% { border-color: #FF0000; box-shadow: 0 0 5px #FF0000; } 
    }

    /* Cards Histórico */
    .trade-card { 
        background-color: #141414; 
        border: 1px solid #333; 
        border-radius: 8px; 
        padding: 10px; 
        transition: 0.2s; 
    }
    .trade-card:hover { border-color: #B20000; }
    
    .card-img-container {
        width: 100%; height: 140px; background-color: #222;
        border-radius: 5px; overflow: hidden; display: flex;
        align-items: center; justify-content: center; margin-bottom: 10px;
    }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. SISTEMA DE AUTENTICAÇÃO
# ==============================================================================
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

def check_password():
    if st.session_state["password_correct"]:
        return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align:center; color:#B20000;'>EVO<span style='color:white'>TRADE</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#666;'>Terminal v182 (Stable)</p>", unsafe_allow_html=True)
        
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        
        if st.button("ACESSAR SISTEMA", use_container_width=True):
            try:
                res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
                if res.data:
                    st.session_state["password_correct"] = True
                    st.session_state["logged_user"] = u
                    st.session_state["user_role"] = res.data[0].get('role', 'user')
                    st.rerun()
                else:
                    st.error("Credenciais Inválidas.")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")
    return False

if check_password():
    MULTIPLIERS = {"NQ": 20, "MNQ": 2, "ES": 50, "MES": 5}
    USER = st.session_state["logged_user"]
    ROLE = st.session_state.get("user_role", "user")

    # ==============================================================================
    # 4. FUNÇÕES DE BANCO DE DADOS (DB)
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

    def load_contas_config():
        try:
            res = supabase.table("contas_config").select("*").eq("usuario", USER).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                # Garante que colunas novas existam
                if 'pico_previo' not in df.columns: df['pico_previo'] = df['saldo_inicial']
                if 'fase_entrada' not in df.columns: df['fase_entrada'] = 'Fase 1'
                if 'status_conta' not in df.columns: df['status_conta'] = 'Ativa'
            return df
        except:
            return pd.DataFrame()

    def load_atms_db():
        try:
            res = supabase.table("atm_configs").select("*").execute()
            return {item['nome']: item for item in res.data}
        except:
            return {}

    def load_grupos_config():
        try:
            res = supabase.table("grupos_config").select("*").eq("usuario", USER).execute()
            return pd.DataFrame(res.data)
        except:
            return pd.DataFrame()

    def card_metric(label, value, sub="", color="white", help_t=""):
        st.markdown(f"""
            <div class="metric-container" title="{help_t}">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color: {color};">{value}</div>
                <div class="metric-sub">{sub}</div>
            </div>
        """, unsafe_allow_html=True)

    # ==============================================================================
    # 5. MENU LATERAL
    # ==============================================================================
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h3 style="color:white; margin-top:-20px;">TERMINAL v182</h3>', unsafe_allow_html=True)
        
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
    # 6. DASHBOARD (LÓGICA BLINDADA v182)
    # ==============================================================================
    if selected == "Dashboard":
        st.title("📊 Central de Controle (v182)")
        df_raw = load_trades_db()
        df_contas = load_contas_config()

        if not df_raw.empty:
            df = df_raw[df_raw['usuario'] == USER]
            
            if not df.empty:
                # --- FILTROS ---
                with st.expander("🔍 Filtros de Análise", expanded=True):
                    c1, c2, c3 = st.columns([1, 1, 2])
                    d_ini = c1.date_input("Data Início", df['data'].min())
                    d_fim = c2.date_input("Data Fim", df['data'].max())
                    
                    grps = ["Todos"] + sorted(list(df['grupo_vinculo'].unique()))
                    if ROLE in ['master', 'admin']:
                        sel_grupo = c3.selectbox("Grupo de Contas", grps)
                    else:
                        sel_grupo = "Todos"
                    
                    # Filtro de Contexto
                    all_ctx = list(df['contexto'].unique())
                    sel_ctx = st.multiselect("Filtrar Contextos", all_ctx, default=all_ctx)

                # Aplica Filtros
                mask = (df['data'] >= d_ini) & (df['data'] <= d_fim) & (df['contexto'].isin(sel_ctx))
                if sel_grupo != "Todos":
                    mask = mask & (df['grupo_vinculo'] == sel_grupo)
                
                df_f = df[mask].copy().sort_values('created_at')

                if df_f.empty:
                    st.warning("⚠️ Nenhum trade encontrado com os filtros atuais.")
                else:
                    # ==============================================================================
                    # CÁLCULO DE SAÚDE GLOBAL (BUFFER E STOP DINÂMICO)
                    # ==============================================================================
                    total_buffer_real = 0.0
                    total_saldo_atual = 0.0
                    contas_ativas = 0
                    
                    if not df_contas.empty:
                        # Seleciona as contas baseadas no filtro do dashboard
                        c_alvo = df_contas if sel_grupo == "Todos" else df_contas[df_contas['grupo_nome'] == sel_grupo]
                        
                        for _, row in c_alvo.iterrows():
                            if row.get('status_conta', 'Ativa') == 'Ativa':
                                s_ini = float(row['saldo_inicial'])
                                p_prev = float(row['pico_previo'])
                                
                                # Busca trades apenas desta conta/grupo para calcular o saldo atual real
                                trades_conta = df[df['grupo_vinculo'] == row['grupo_nome']]
                                lucro_acc = trades_conta['resultado'].sum() if not trades_conta.empty else 0.0
                                
                                saldo_atual = s_ini + lucro_acc
                                
                                # HWM Dinâmico (High Water Mark)
                                equity_curve = (trades_conta['resultado'].cumsum() + s_ini) if not trades_conta.empty else pd.Series([s_ini])
                                hwm_atual = max(p_prev, equity_curve.max(), s_ini)
                                
                                # --- REGRA DINÂMICA DE TRAILING (APEX/PROP) ---
                                # Detecta o tamanho da conta automaticamente
                                if s_ini >= 250000: 
                                    drawdown_limite = 7500.0 # Conta 300k
                                elif s_ini >= 100000: 
                                    drawdown_limite = 5000.0 # Conta 150k ou 100k
                                elif s_ini >= 50000: 
                                    drawdown_limite = 2500.0 # Conta 50k
                                else: 
                                    drawdown_limite = 1500.0 # Conta 25k
                                
                                # Calcula ponto de trava (Saldo Inicial + 100)
                                lock_threshold = s_ini + drawdown_limite + 100.0
                                locked_stop_value = s_ini + 100.0
                                
                                if hwm_atual >= lock_threshold:
                                    trailing_stop = locked_stop_value
                                else:
                                    trailing_stop = hwm_atual - drawdown_limite
                                
                                # Soma ao global
                                total_buffer_real += max(0, saldo_atual - trailing_stop)
                                total_saldo_atual += saldo_atual
                                contas_ativas += 1
                    
                    # Stop Implícito para exibição no card
                    stop_atual_val = total_saldo_atual - total_buffer_real

                    # --- ESTATÍSTICAS FINANCEIRAS ---
                    wins = df_f[df_f['resultado'] > 0]
                    losses = df_f[df_f['resultado'] < 0]
                    
                    n_trades = len(df_f)
                    n_wins = len(wins)
                    n_loss = len(losses)
                    
                    net = df_f['resultado'].sum()
                    gross_win = wins['resultado'].sum()
                    gross_loss = abs(losses['resultado'].sum())
                    
                    pf = gross_win / gross_loss if gross_loss > 0 else float('inf')
                    pf_str = f"{pf:.2f}" if gross_loss > 0 else "∞"
                    
                    # Taxas
                    wr = n_wins / n_trades if n_trades > 0 else 0.0
                    avg_w = wins['resultado'].mean() if n_wins > 0 else 0.0
                    avg_l = abs(losses['resultado'].mean()) if n_loss > 0 else 0.0
                    
                    payoff = avg_w / avg_l if avg_l > 0 else 0.0
                    expectancy = (wr * avg_w) - ((1-wr) * avg_l)
                    
                    # Médias de Execução
                    lote_med = df_f['lote'].mean() if n_trades > 0 else 0
                    ref_ativo = df_f['ativo'].iloc[-1] if n_trades > 0 else "MNQ"
                    pts_loss_med = abs(losses['pts_medio'].mean()) if n_loss > 0 else 15.0
                    
                    # ==============================================================================
                    # MOTOR DE RISCO v182 (BROWNIAN MOTION + KELLY)
                    # ==============================================================================
                    
                    # 1. Risco Base (Comportamental)
                    risco_base = lote_med * pts_loss_med * MULTIPLIERS.get(ref_ativo, 2)
                    if risco_base == 0: risco_base = 100.0
                    
                    # 2. Vidas Reais
                    vidas = total_buffer_real / risco_base if risco_base > 0 else 0
                    
                    # 3. Probabilidade de Ruína (Aproximação de Difusão)
                    # Corrige erro de 100% ruína quando WR=50% mas Payoff é alto
                    q = 1 - wr
                    # Variância dos retornos
                    variancia = (wr * (avg_w - expectancy)**2) + (q * (-avg_l - expectancy)**2)
                    
                    ruina_pct = 0.0
                    msg_risco = "Calculando..."
                    cor_risco = "gray"
                    
                    if n_trades < 5:
                        msg_risco = "Dados Insuficientes"
                        ruina_pct = 0.0
                    elif vidas < 1:
                        ruina_pct = 100.0
                        msg_risco = "LIQUIDAÇÃO IMINENTE"
                        cor_risco = "#FF0000"
                    elif expectancy <= 0:
                        ruina_pct = 100.0
                        msg_risco = "EDGE NEGATIVO"
                        cor_risco = "#FF0000"
                    else:
                        if variancia > 0:
                            # Formula: P = exp(-2 * Mu * Buffer / Sigma^2)
                            arg_exp = -2 * expectancy * total_buffer_real / variancia
                            try:
                                ruina_pct = math.exp(arg_exp) * 100
                            except:
                                ruina_pct = 0.0
                        else:
                            ruina_pct = 0.0
                        
                        ruina_pct = min(max(ruina_pct, 0.0), 100.0)
                        
                        if ruina_pct < 1.0: 
                            cor_risco = "#00FF88"; msg_risco = "Zona Segura"
                        elif ruina_pct < 5.0: 
                            cor_risco = "#FFFF00"; msg_risco = "Atenção"
                        elif ruina_pct < 20.0: 
                            cor_risco = "#FF8800"; msg_risco = "Alto Risco"
                        else: 
                            cor_risco = "#FF4B4B"; msg_risco = "CRÍTICO"

                    # ALERTA DE PÂNICO
                    if ruina_pct > 15.0 and n_trades > 5 and expectancy > 0:
                        st.markdown(f"""
                            <div class="piscante-erro">
                                💀 ALERTA DE RUÍNA: {ruina_pct:.2f}% 💀<br>
                                <span style="font-size:16px;">VOLATILIDADE ALTA. REDUZA O LOTE.</span>
                            </div>
                        """, unsafe_allow_html=True)

                    # --- EXIBIÇÃO ---
                    st.markdown("##### 🏁 Performance Financeira")
                    k1, k2, k3, k4 = st.columns(4)
                    with k1: card_metric("Resultado Líquido", f"${net:,.2f}", f"PF: {pf_str}", "#00FF88" if net>=0 else "#FF4B4B")
                    with k2: card_metric("Win Rate", f"{wr*100:.1f}%", f"{n_wins}W / {n_loss}L", "white")
                    with k3: card_metric("Payoff", f"{payoff:.2f}", f"Exp: ${expectancy:.2f}", "white")
                    
                    dd_max = (df_f['resultado'].cumsum() - df_f['resultado'].cumsum().cummax()).min()
                    with k4: card_metric("Max Drawdown", f"${dd_max:,.2f}", "Histórico", "#FF4B4B")

                    st.markdown("---")
                    st.subheader(f"🛡️ Sobrevivência & Kelly (Base: {sel_grupo})")
                    
                    # Cálculo Kelly
                    if payoff > 0:
                        kelly_f = wr - ((1-wr)/payoff)
                    else: kelly_f = 0
                    
                    kelly_half = max(0.0, kelly_f / 2)
                    
                    # Sugestão de Lote (Com trava de 20 vidas)
                    risco_kelly = total_buffer_real * kelly_half
                    risco_vidas = total_buffer_real / 20.0
                    
                    risco_final = min(risco_kelly, risco_vidas)
                    
                    custo_lote = pts_loss_med * MULTIPLIERS.get(ref_ativo, 2)
                    if costo_lote := custo_lote: # walrus operator check > 0
                        lote_sugerido = int(risco_final / costo_lote)
                    else: lote_sugerido = 0
                    
                    if lote_sugerido > 40: lote_sugerido = 40 # Hard Cap
                    
                    r1, r2, r3, r4 = st.columns(4)
                    with r1: card_metric("Buffer Real", f"${total_buffer_real:,.0f}", f"{contas_ativas} Contas", "#00FF88")
                    with r2: card_metric("Vidas Atuais", f"{vidas:.1f}", f"Risco: ${risco_base:.0f}")
                    with r3: card_metric("Prob. Ruína", f"{ruina_pct:.2f}%", msg_risco, cor_risco)
                    with r4:
                        ck = "#00FF88" if lote_sugerido > 0 else "#FF4B4B"
                        mk = "Aumentar" if lote_sugerido > lote_med else "Reduzir/Manter"
                        st.markdown(f"""
                            <div style="border: 2px solid {ck}; border-radius: 10px; padding: 10px; text-align: center; background: #1a1a1a;">
                                <div style="color: #888; font-size: 10px;">SUGESTÃO DE LOTE</div>
                                <div style="color: {ck}; font-size: 28px; font-weight: 900;">{lote_sugerido} ctrs</div>
                                <div style="font-size: 11px; color: #aaa;">{mk} (Alvo 20 Vidas)</div>
                            </div>
                        """, unsafe_allow_html=True)

                    # --- GRÁFICOS ---
                    st.markdown("---")
                    g1, g2 = st.columns([2, 1])
                    with g1:
                        # Gráfico de Saldo Total (Reverse Engineering Start Balance)
                        # Se temos o Saldo Total Atual e o Lucro Liquido, o Saldo Inicial Base é a diferença
                        start_base_plot = total_saldo_atual - net
                        if start_base_plot < 0: start_base_plot = 0
                        
                        df_f['seq'] = range(1, len(df_f)+1)
                        df_f['saldo_acc'] = df_f['resultado'].cumsum() + start_base_plot
                        
                        fig = px.area(df_f, x='seq', y='saldo_acc', title="📈 Curva de Patrimônio (Saldo Total)", template="plotly_dark")
                        fig.update_traces(line_color='#2E93fA', fillcolor='rgba(46, 147, 250, 0.1)')
                        fig.add_hline(y=start_base_plot, line_dash="dash", line_color="gray", annotation_text="Capital Inicial")
                        
                        # Zoom Automático
                        y_min_z = min(start_base_plot, df_f['saldo_acc'].min()) * 0.99
                        y_max_z = max(start_base_plot, df_f['saldo_acc'].max()) * 1.01
                        fig.update_layout(yaxis_range=[y_min_z, y_max_z], xaxis_title="# Trades", yaxis_title="Saldo ($)")
                        st.plotly_chart(fig, use_container_width=True)
                        
                    with g2:
                        df_f['dia'] = pd.to_datetime(df_f['data']).dt.day_name()
                        res_dia = df_f.groupby('dia')['resultado'].sum().reset_index()
                        fig2 = px.bar(res_dia, x='dia', y='resultado', title="📅 P&L por Dia", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                        st.plotly_chart(fig2, use_container_width=True)

            else: st.info("Nenhuma operação registrada para este usuário.")
        else: st.warning("Banco de dados vazio.")

    # ==============================================================================
    # 7. REGISTRAR TRADE (COMPLETO)
    # ==============================================================================
    elif selected == "Registrar Trade":
        st.title("📝 Registrar Operação")
        atm_db = load_atms_db()
        df_g = load_grupos_config()
        
        c1, c2 = st.columns([2, 1])
        with c1: atm_sel = st.selectbox("Carregar ATM", ["Manual"] + list(atm_db.keys()))
        with c2: 
            grps = sorted(df_g['nome'].unique()) if not df_g.empty else ["Geral"]
            grp_sel = st.selectbox("Vincular ao Grupo", grps)

        # Configuração Inicial do Form
        lote_def = 1; stop_def = 0.0; parciais_pre = []
        if atm_sel != "Manual":
            cfg = atm_db[atm_sel]
            lote_def = int(cfg['lote'])
            stop_def = float(cfg['stop'])
            try: parciais_pre = cfg['parciais'] if isinstance(cfg['parciais'], list) else json.loads(cfg['parciais'])
            except: pass

        with st.form("trade_form"):
            col1, col2, col3 = st.columns(3)
            dt = col1.date_input("Data", datetime.now())
            atv = col2.selectbox("Ativo", ["MNQ", "NQ", "ES", "MES"])
            dr = col3.radio("Direção", ["Compra", "Venda"], horizontal=True)
            
            col4, col5, col6 = st.columns(3)
            lote = col4.number_input("Lote Total", 1, 100, lote_def)
            stop_pts = col5.number_input("Stop (Pts)", 0.0, 500.0, stop_def, step=0.25)
            psi = col6.selectbox("Estado Mental", ["Normal", "Fomo", "Vingativo", "Hesitação", "Cansado"])
            ctx = st.selectbox("Contexto", ["Tendência", "Lateralidade", "Rompimento", "Contra-Tendência"])
            
            st.divider()
            st.markdown("**Saídas / Parciais**")
            
            # Gerador de Campos de Parcial
            saidas = []
            cols_p = st.columns(3)
            
            for i in range(3): # Suporta até 3 parciais no form simples
                with cols_p[i]:
                    dq = int(parciais_pre[i]['qtd']) if i < len(parciais_pre) else (lote if i==0 else 0)
                    dp = float(parciais_pre[i]['pts']) if i < len(parciais_pre) else 0.0
                    
                    q = st.number_input(f"Qtd {i+1}", 0, lote, dq, key=f"qp_{i}")
                    p = st.number_input(f"Pts {i+1}", -500.0, 500.0, dp, step=0.25, key=f"pp_{i}")
                    if q > 0: saidas.append({'q': q, 'p': p})
            
            # Validação
            q_alocada = sum([x['q'] for x in saidas])
            if q_alocada != lote:
                st.caption(f"⚠️ Atenção: Lote alocado ({q_alocada}) difere do total ({lote}).")
            
            # Upload
            foto = st.file_uploader("Evidência (Print)", type=["png", "jpg", "jpeg"])
            
            submitted = st.form_submit_button("💾 SALVAR TRADE", use_container_width=True)
            
            if submitted:
                if q_alocada == lote:
                    # Cálculo Financeiro
                    fin_total = sum([x['q'] * x['p'] * MULTIPLIERS.get(atv, 2) for x in saidas])
                    pts_med = sum([x['q'] * x['p'] for x in saidas]) / lote
                    
                    # Upload
                    path_img = ""
                    t_id = str(uuid.uuid4())
                    if foto:
                        supabase.storage.from_("prints").upload(f"{t_id}.png", foto.getvalue())
                        path_img = supabase.storage.from_("prints").get_public_url(f"{t_id}.png")
                    
                    # Insert
                    supabase.table("trades").insert({
                        "id": t_id, "usuario": USER, "data": str(dt), "ativo": atv,
                        "direcao": dr, "lote": lote, "resultado": fin_total,
                        "pts_medio": pts_med, "grupo_vinculo": grp_sel,
                        "contexto": ctx, "comportamento": psi, "prints": path_img,
                        "risco_fin": stop_pts * lote * MULTIPLIERS.get(atv, 2)
                    }).execute()
                    
                    st.success(f"✅ Trade Registrado! Resultado: ${fin_total:,.2f}")
                    time.sleep(1); st.rerun()
                else:
                    st.error("Erro: A soma das quantidades parciais deve ser igual ao Lote Total.")

    # ==============================================================================
    # 8. GESTÃO DE CONTAS (MONITOR APEX COMPLETO)
    # ==============================================================================
    elif selected == "Contas":
        st.title("💼 Carteira & Monitoramento")
        t1, t2 = st.tabs(["Monitoramento em Tempo Real", "Configurações"])
        
        df_c = load_contas_config()
        df_t = load_trades_db()
        if not df_t.empty: df_t = df_t[df_t['usuario'] == USER]
        
        with t1:
            if not df_c.empty:
                grps = sorted(df_c['grupo_nome'].unique())
                sel_g = st.selectbox("Selecionar Grupo", grps)
                st.markdown("---")
                
                # Filtrar Dados
                contas = df_c[df_c['grupo_nome'] == sel_g]
                trades = df_t[df_t['grupo_vinculo'] == sel_g] if not df_t.empty else pd.DataFrame()
                
                # Cálculos do Grupo
                s_ini_total = contas['saldo_inicial'].sum()
                res_total = trades['resultado'].sum() if not trades.empty else 0.0
                saldo_atual_grupo = s_ini_total + res_total
                
                # --- TRAILING STOP VISUAL (Lógica do Gráfico) ---
                # Precisamos iterar conta a conta para somar o stop correto
                stop_global_grupo = 0.0
                hwm_global_grupo = 0.0
                
                for _, row in contas.iterrows():
                    si = float(row['saldo_inicial'])
                    pp = float(row['pico_previo'])
                    
                    # Trades desta conta
                    # Assumimos distribuição proporcional se não houver ID no trade, mas aqui usamos grupo
                    # Simplificação para visualização de grupo: 
                    # Stop Global = Soma dos Stops individuais
                    
                    # Recalcular HWM individual (Estimado pelo grupo para simplificar visualização ou proporcional)
                    # Melhor abordagem: Trailing Stop é a soma dos trailings individuais.
                    
                    # Tamanho da conta para regra
                    if si >= 250000: dd = 7500.0
                    elif si >= 100000: dd = 5000.0
                    elif si >= 50000: dd = 2500.0
                    else: dd = 1500.0
                    
                    # Para o monitoramento funcionar perfeito, precisamos saber o lucro INDIVIDUAL de cada conta.
                    # Como o trade está vinculado ao GRUPO, assumimos que o lucro do grupo é dividido pelo numero de contas?
                    # Ou que todas as contas operam igual (CopyTrading). Vamos assumir CopyTrading (distribuição igual).
                    
                    lucro_por_conta = res_total / len(contas)
                    saldo_acc_ind = si + lucro_por_conta
                    
                    # HWM Individual Estimado
                    if not trades.empty:
                        # Pega o max drawdown da curva do grupo e aplica proporcionalmente
                        # Curva do grupo
                        curve_grp = trades['resultado'].cumsum()
                        max_runup_grp = curve_grp.max()
                        if max_runup_grp < 0: max_runup_grp = 0
                        
                        hwm_ind = max(pp, si + (max_runup_grp / len(contas)), si)
                    else:
                        hwm_ind = max(pp, si)
                    
                    # Stop Check
                    lock_val = si + dd + 100.0
                    stop_locked = si + 100.0
                    
                    if hwm_ind >= lock_val:
                        stop_ind = stop_locked
                    else:
                        stop_ind = hwm_ind - dd
                    
                    stop_global_grupo += stop_ind
                
                buffer_grupo = saldo_atual_grupo - stop_global_grupo
                
                # Exibição
                m1, m2, m3 = st.columns(3)
                m1.metric("Saldo do Grupo", f"${saldo_atual_grupo:,.0f}", f"Lucro: ${res_total:,.0f}")
                m2.metric("Stop Loss Global", f"${stop_global_grupo:,.0f}", "Trailing Dinâmico")
                m3.metric("Buffer Disponível", f"${buffer_grupo:,.0f}", "Oxigênio", delta_color="normal" if buffer_grupo > 3000 else "inverse")
                
                # Barra de Progresso do Buffer
                # Max buffer possível é soma dos drawdowns iniciais
                max_buff_possivel = 0
                for _, row in contas.iterrows():
                    si = float(row['saldo_inicial'])
                    if si >= 250000: max_buff_possivel += 7500
                    elif si >= 100000: max_buff_possivel += 5000
                    elif si >= 50000: max_buff_possivel += 2500
                    else: max_buff_possivel += 1500
                
                prog = min(1.0, max(0.0, buffer_grupo / max_buff_possivel))
                st.progress(prog)
                st.caption(f"Saúde do Buffer: {prog*100:.1f}% (Total Max: ${max_buff_possivel:,.0f})")
                
                st.markdown("---")
                st.write("📋 Detalhe das Contas Vinculadas")
                st.dataframe(contas[['conta_identificador', 'saldo_inicial', 'status_conta', 'fase_entrada']], use_container_width=True)
                
            else: st.info("Nenhuma conta configurada. Vá na aba Configurações.")

        with t2:
            st.subheader("Adicionar Conta / Grupo")
            c_new_g, c_new_c = st.columns(2)
            
            with c_new_g:
                with st.form("new_grp"):
                    n_g = st.text_input("Novo Nome de Grupo (Ex: Apex 20 Contas)")
                    if st.form_submit_button("Criar Grupo"):
                        supabase.table("grupos_config").insert({"usuario": USER, "nome": n_g}).execute()
                        st.success("Grupo Criado!"); time.sleep(1); st.rerun()
            
            with c_new_c:
                grps_l = load_grupos_config()
                if not grps_l.empty:
                    with st.form("new_acc"):
                        sel_grp_add = st.selectbox("Vincular ao Grupo", grps_l['nome'].unique())
                        nome_acc = st.text_input("ID da Conta (ex: PA-001)")
                        s_ini = st.number_input("Saldo Inicial", value=150000.0, step=1000.0)
                        if st.form_submit_button("Criar Conta"):
                            supabase.table("contas_config").insert({
                                "usuario": USER, "grupo_nome": sel_grp_add, 
                                "conta_identificador": nome_acc, "saldo_inicial": s_ini,
                                "pico_previo": s_ini, "status_conta": "Ativa"
                            }).execute()
                            st.success("Conta Criada!"); time.sleep(1); st.rerun()
                else: st.warning("Crie um grupo primeiro.")

    # ==============================================================================
    # 9. EXTRAS (CONFIG ATM & HISTÓRICO COMPLETO)
    # ==============================================================================
    elif selected == "Configurar ATM":
        st.title("⚙️ Editor de Estratégias (ATM)")
        
        # State para edição
        if "atm_edit" not in st.session_state: st.session_state.atm_edit = None
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("Salvas")
            atms = load_atms_db()
            if st.button("✨ Nova Estratégia", use_container_width=True): 
                st.session_state.atm_edit = None; st.rerun()
            
            for nome, dados in atms.items():
                with st.expander(f"📍 {nome}"):
                    if st.button("Editar", key=f"ed_{dados['id']}"): 
                        st.session_state.atm_edit = dados; st.rerun()
                    if st.button("Excluir", key=f"del_{dados['id']}"): 
                        supabase.table("atm_configs").delete().eq("id", dados['id']).execute(); st.rerun()

        with c2:
            st.subheader("Editar / Criar")
            dados_form = st.session_state.atm_edit if st.session_state.atm_edit else {}
            
            with st.form("atm_full"):
                n = st.text_input("Nome", value=dados_form.get('nome', ''))
                l = st.number_input("Lote Total", 1, 100, int(dados_form.get('lote', 1)))
                s = st.number_input("Stop Loss (Pts)", 0.0, 200.0, float(dados_form.get('stop', 5.0)))
                
                st.markdown("**Saídas Parciais**")
                # Carregar parciais existentes ou criar padrão
                try: p_list = dados_form.get('parciais', []) if isinstance(dados_form.get('parciais'), list) else json.loads(dados_form.get('parciais'))
                except: p_list = []
                
                new_parciais = []
                cols = st.columns(3)
                for i in range(3):
                    with cols[i]:
                        def_q = int(p_list[i]['qtd']) if i < len(p_list) else (l if i==0 else 0)
                        def_p = float(p_list[i]['pts']) if i < len(p_list) else 0.0
                        q = st.number_input(f"Qtd {i+1}", 0, 100, def_q, key=f"pq_{i}")
                        p = st.number_input(f"Pts {i+1}", -100.0, 500.0, def_p, key=f"pp_{i}")
                        if q > 0: new_parciais.append({'qtd': q, 'pts': p})
                
                if st.form_submit_button("SALVAR ESTRATÉGIA"):
                    if sum([x['qtd'] for x in new_parciais]) == l:
                        pay = {"nome": n, "lote": l, "stop": s, "parciais": new_parciais}
                        if dados_form.get('id'):
                            supabase.table("atm_configs").update(pay).eq("id", dados_form['id']).execute()
                        else:
                            supabase.table("atm_configs").insert(pay).execute()
                        st.success("Salvo!"); st.session_state.atm_edit = None; time.sleep(1); st.rerun()
                    else: st.error("Erro: Soma das parciais difere do lote.")

    elif selected == "Histórico":
        st.title("📜 Histórico de Operações")
        df = load_trades_db()
        if not df.empty:
            df = df[df['usuario']==USER].sort_values('created_at', ascending=False)
            
            # Filtros Rápidos
            f_col1, f_col2 = st.columns(2)
            f_atv = f_col1.multiselect("Ativo", df['ativo'].unique())
            f_grp = f_col2.multiselect("Grupo", df['grupo_vinculo'].unique())
            
            if f_atv: df = df[df['ativo'].isin(f_atv)]
            if f_grp: df = df[df['grupo_vinculo'].isin(f_grp)]
            
            for _, r in df.iterrows():
                res = r['resultado']
                c = "card-res-win" if res >= 0 else "card-res-loss"
                c_border = "#00FF88" if res >= 0 else "#FF4B4B"
                
                with st.expander(f"{r['data']} | {r['ativo']} | {r['direcao']} | Resultado: ${res:,.2f}"):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Lote:** {r['lote']}")
                    c2.write(f"**Médio:** {r.get('pts_medio', 0):.2f} pts")
                    c3.write(f"**Grupo:** {r['grupo_vinculo']}")
                    
                    if r['prints']: st.image(r['prints'])
                    else: st.info("Sem print.")
                    
                    if st.button("🗑️ Deletar Registro", key=f"del_h_{r['id']}"):
                        supabase.table("trades").delete().eq("id", r['id']).execute()
                        st.rerun()
        else: st.info("Histórico vazio.")

    elif selected == "Gerenciar Usuários" and ROLE == "admin":
        st.title("Painel Admin")
        u_data = supabase.table("users").select("*").execute().data
        st.dataframe(u_data)
