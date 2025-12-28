import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from supabase import create_client

# Importando seus motores matemáticos
from modules.logic import ApexEngine, RiskEngine, PositionSizing

# --- 1. CONFIGURAÇÕES E CONEXÃO ---
MULTIPLIERS = {"NQ": 20, "MNQ": 2, "ES": 50, "MES": 5}

def get_supabase():
    try:
        if "supabase" in st.session_state: return st.session_state["supabase"]
        else:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
    except: return None

def load_trades_db():
    try:
        sb = get_supabase()
        res = sb.table("trades").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['created_at'] = pd.to_datetime(df['created_at'])
            if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
            # Garante float
            df['resultado'] = df['resultado'].astype(float)
            df['lote'] = df['lote'].astype(float)
            df['pts_medio'] = df['pts_medio'].astype(float)
        return df
    except: return pd.DataFrame()

def load_contas_config(user):
    try:
        sb = get_supabase()
        res = sb.table("contas_config").select("*").eq("usuario", user).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            if 'pico_previo' not in df.columns: df['pico_previo'] = df['saldo_inicial']
            if 'status_conta' not in df.columns: df['status_conta'] = 'Ativa'
            df['saldo_inicial'] = df['saldo_inicial'].astype(float)
            df['pico_previo'] = df['pico_previo'].astype(float)
        return df
    except: return pd.DataFrame()

# --- 2. COMPONENTE VISUAL (CARD v300) ---
def card(label, value, sub_text, color="white", border_color="#333333"):
    st.markdown(
        f"""
        <div style="
            background-color: #161616; 
            padding: 15px; 
            border-radius: 8px; 
            border: 1px solid {border_color}; 
            text-align: center; 
            margin-bottom: 10px;
            height: 100px; 
            display: flex; flex-direction: column; justify-content: center;
        ">
            <div style="color: #888; font-size: 10px; text-transform: uppercase; margin-bottom: 4px; display: flex; justify-content: center; align-items: center; gap: 5px;">
                {label} <span style="font-size:9px; border: 1px solid #444; border-radius: 50%; width: 10px; height: 10px; display: inline-flex; justify-content: center; align-items: center;">?</span>
            </div>
            <h2 style="color: {color}; margin: 0; font-size: 20px; font-weight: 600;">{value}</h2>
            <p style="color: #666; font-size: 10px; margin-top: 4px;">{sub_text}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- 3. DASHBOARD LOGIC ---
def show(user, role):
    
    # Carrega dados
    df_trades_all = load_trades_db()
    df_contas_all = load_contas_config(user)
    
    if not df_trades_all.empty:
        df_trades_all = df_trades_all[df_trades_all['usuario'] == user]

    # --- TOP BAR: SELEÇÃO E FILTROS ---
    st.markdown("### 🔭 Visão do Operacional")
    
    # 1. Grupo
    grupos_disponiveis = ["Todos"]
    if not df_contas_all.empty:
        grupos_disponiveis = sorted(list(df_contas_all['grupo_nome'].unique()))
    
    c_sel1, c_sel2, c_date1, c_date2 = st.columns([1.5, 1.5, 1, 1])
    
    with c_sel1:
        grupo_sel = st.selectbox("📂 Grupo", grupos_disponiveis)
    
    # 2. Conta/Detalhe
    contas_do_grupo = []
    if not df_contas_all.empty:
        if grupo_sel != "Todos":
            contas_do_grupo = df_contas_all[df_contas_all['grupo_nome'] == grupo_sel]
        else:
            contas_do_grupo = df_contas_all
            
    lista_contas_view = ["📊 VISÃO GERAL (Agregado)"] + sorted(list(contas_do_grupo['conta_identificador'].unique()))
    
    with c_sel2:
        view_mode = st.selectbox("🔎 Detalhe", lista_contas_view)

    # 3. Datas
    with c_date1:
        d_inicio = st.date_input("De", datetime.now().date() - timedelta(days=30))
    with c_date2:
        d_fim = st.date_input("Até", datetime.now().date())

    st.markdown("---")

    # --- FILTRAGEM DE DADOS ---
    
    trades_filtered = df_trades_all.copy()
    if grupo_sel != "Todos":
        trades_filtered = trades_filtered[trades_filtered['grupo_vinculo'] == grupo_sel]
        
    trades_filtered = trades_filtered[
        (trades_filtered['data'] >= d_inicio) & 
        (trades_filtered['data'] <= d_fim)
    ]
    
    if "VISÃO GERAL" in view_mode:
        contas_alvo = contas_do_grupo
    else:
        contas_alvo = contas_do_grupo[contas_do_grupo['conta_identificador'] == view_mode]

    # --- LOOP DO MOTOR APEX (Calcula Buffer) ---
    total_buffer = 0.0
    contas_ativas = 0
    
    if not contas_alvo.empty:
        # Se for visão geral, precisamos estimar o lucro por conta para saber o saldo atual
        lucro_total_periodo = trades_filtered['resultado'].sum() if not trades_filtered.empty else 0.0
        num_contas_no_filtro = len(contas_alvo) if len(contas_alvo) > 0 else 1
        
        # Assume distribuição igualitária (CopyTrading) para cálculo de risco macro
        lucro_por_conta_est = lucro_total_periodo / num_contas_no_filtro

        for _, conta in contas_alvo.iterrows():
            if conta['status_conta'] == 'Ativa':
                saldo_ini = float(conta['saldo_inicial'])
                hwm_prev = float(conta['pico_previo'])
                
                # Saldo estimado atual = Inicial + (Lucro Total / N Contas)
                saldo_atual_est = saldo_ini + lucro_por_conta_est
                
                # CHAMA O MOTOR APEX
                saude = ApexEngine.calculate_health(saldo_atual_est, hwm_prev)
                
                total_buffer += saude['buffer']
                contas_ativas += 1

    # --- CÁLCULOS ESTATÍSTICOS (Todos os KPI do v250) ---
    wins = trades_filtered[trades_filtered['resultado'] > 0]
    losses = trades_filtered[trades_filtered['resultado'] < 0]
    
    net_profit = trades_filtered['resultado'].sum() if not trades_filtered.empty else 0.0
    gross_profit = wins['resultado'].sum() if not wins.empty else 0.0
    gross_loss = abs(losses['resultado'].sum()) if not losses.empty else 0.0
    
    pf = gross_profit / gross_loss if gross_loss > 0 else 99.99
    total_trades = len(trades_filtered)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
    
    avg_win = wins['resultado'].mean() if not wins.empty else 0.0
    avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0.0
    payoff = avg_win / avg_loss if avg_loss > 0 else 0.0
    
    # Expectativa
    expectancy = ( (win_rate/100) * avg_win ) - ( (1 - (win_rate/100)) * avg_loss )
    
    # Médias Técnicas
    avg_pts_gain = wins['pts_medio'].mean() if not wins.empty else 0.0
    avg_pts_loss = abs(losses['pts_medio'].mean()) if not losses.empty else 0.0
    
    # Risco Comportamental (Stop Médio em Pontos)
    pts_loss_medio_real = avg_pts_loss if avg_pts_loss > 0 else 15.0 # fallback
    
    lote_medio = trades_filtered['lote'].mean() if not trades_filtered.empty else 0.0
    ativo_ref = trades_filtered['ativo'].iloc[-1] if not trades_filtered.empty else "MNQ"
    
    # Drawdown Máximo (do Período Visualizado)
    max_dd = 0.0
    if not trades_filtered.empty:
        df_sorted = trades_filtered.sort_values('created_at')
        equity = df_sorted['resultado'].cumsum()
        max_dd = (equity - equity.cummax()).min()

    # --- CÁLCULOS DOS MOTORES (Risco e Lote) ---
    custo_stop_padrao = pts_loss_medio_real * MULTIPLIERS.get(ativo_ref, 2)
    risco_impacto_grupo = custo_stop_padrao * (contas_ativas if contas_ativas > 0 else 1)
    
    # Vidas
    vidas_u = total_buffer / risco_impacto_grupo if risco_impacto_grupo > 0 else 0.0
    
    # Ruína
    prob_ruina = RiskEngine.calculate_ruin(win_rate, avg_win, avg_loss, total_buffer)
    
    # Edge (Z-Score Simplificado v250)
    loss_rate_dec = (len(losses)/total_trades) if total_trades > 0 else 0
    edge_calc = ((win_rate/100) * payoff) - loss_rate_dec
    
    # Lote Sugerido
    lote_min, lote_max, kelly_pct = PositionSizing.calculate_limits(win_rate, payoff, total_buffer, risco_impacto_grupo)

    # ==============================================================================
    # RENDERIZAÇÃO VISUAL (RESTAURANDO O LAYOUT COMPLETO)
    # ==============================================================================

    # 1. DESEMPENHO GERAL
    st.markdown("### 🏁 Desempenho Geral")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card("Resultado Líquido", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f} / -${gross_loss:,.0f}", "#00FF88" if net_profit>=0 else "#FF4B4B")
    with c2: card("Fator de Lucro (PF)", f"{pf:.2f}", "Ideal > 1.5", "#FF4B4B" if pf < 1.5 else "#00FF88")
    with c3: card("Win Rate", f"{win_rate:.1f}%", f"{len(wins)}W / {len(losses)}L", "white")
    with c4: card("Expectativa Mat.", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy>0 else "#FF4B4B")

    # 2. MÉDIAS FINANCEIRAS (RESTAURADO)
    st.markdown("### 💲 Médias Financeiras")
    m1, m2, m3, m4 = st.columns(4)
    with m1: card("Média Gain ($)", f"${avg_win:,.2f}", "", "#00FF88")
    with m2: card("Média Loss ($)", f"-${avg_loss:,.2f}", "", "#FF4B4B")
    with m3: card("Risco : Retorno", f"1 : {payoff:.2f}", "Payoff Real", "white")
    with m4: card("Drawdown Máximo", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B")

    # 3. PERFORMANCE TÉCNICA (RESTAURADO)
    st.markdown("### 🎯 Performance Técnica")
    t1, t2, t3, t4 = st.columns(4)
    with t1: card("Pts Médios (Gain)", f"{avg_pts_gain:.2f} pts", "", "#00FF88")
    with t2: card("Stop Médio (Loss)", f"{avg_pts_loss:.2f} pts", "Base do Risco", "#FF4B4B")
    with t3: card("Lote Médio", f"{lote_medio:.1f}", "Contratos", "white")
    with t4: card("Total Trades", f"{total_trades}", "Executados", "white")

    st.markdown("---")

    # 4. ANÁLISE DE SOBREVIVÊNCIA
    st.markdown(f"### 🛡️ Análise de Sobrevivência ({view_mode})")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        cor_edge = "#00FF88" if edge_calc > 0 else "#FF4B4B"
        card("Z-Score (Edge)", f"{edge_calc:.4f}", "Edge Matemático", cor_edge)
    with k2:
        cor_buf = "#00FF88" if total_buffer > 2000 else "#FF4B4B"
        card("Buffer Real (Hoje)", f"${total_buffer:,.0f}", f"{contas_ativas} Contas Ativas", cor_buf)
    with k3:
        cor_v = "#FF4B4B" if vidas_u < 10 else ("#FFFF00" if vidas_u < 20 else "#00FF88")
        card("Vidas Reais (U)", f"{vidas_u:.1f}", f"Risco Impacto: ${risco_impacto_grupo:,.0f}", cor_v)
    with k4:
        cor_r = "#00FF88" if prob_ruina < 1 else ("#FF4B4B" if prob_ruina > 5 else "#FFFF00")
        card("Prob. Ruína (Real)", f"{prob_ruina:.2f}%", "Risco Moderado", cor_r, border_color=cor_r)

    # 5. INTELIGÊNCIA DE LOTE (SEPARADO COMO NO ORIGINAL)
    st.markdown("### 🧠 Inteligência de Lote (Faixa de Operação)")
    l1, l2, l3, l4 = st.columns(4)
    with l1:
        card("Buffer Disponível", f"${total_buffer:,.0f}", "Capital de Risco", "#00FF88")
    with l2:
        card("Half-Kelly (Math)", f"{kelly_pct*100:.1f}%", "Teto Teórico", "#888")
    with l3:
        r_fin_min = lote_min * (custo_stop_padrao/contas_ativas) # Aproximação unitária para exibição
        r_fin_max = lote_max * (custo_stop_padrao/contas_ativas)
        card("Risco Financeiro", f"${total_buffer * kelly_pct:,.0f}", "Alocação Global", "#00FF88")
    with l4:
        card("Sugestão de Lote", f"{lote_min} a {lote_max} ctrs", "ZONA DE ACELERAÇÃO", "#00FF88", border_color="#00FF88")

    # 6. GRÁFICOS
    st.markdown("### 📈 Evolução Financeira")
    
    g1, g2 = st.columns([2.5, 1])
    
    with g1:
        if not trades_filtered.empty:
            trades_plot = trades_filtered.sort_values('created_at').copy()
            
            # Ajuste do Eixo Y (Saldo Base)
            # Se for Geral: Soma dos Saldos Iniciais
            # Se for Individual: Saldo Inicial da conta
            saldo_inicial_base = contas_alvo['saldo_inicial'].sum() if not contas_alvo.empty else 0.0
            
            trades_plot['saldo_acumulado'] = trades_plot['resultado'].cumsum() + saldo_inicial_base
            
            fig = px.area(trades_plot, x='created_at', y='saldo_acumulado', title=f"Curva de Patrimônio ({view_mode})", template="plotly_dark")
            fig.update_traces(line_color='#00FF88', fillcolor='rgba(0, 255, 136, 0.1)')
            
            # Linha de Referência (Saldo Inicial)
            fig.add_hline(y=saldo_inicial_base, line_dash="dash", line_color="gray", annotation_text="Capital Inicial")
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para exibir gráfico.")
            
    with g2:
        if not trades_filtered.empty:
            ctx_perf = trades_filtered.groupby('contexto')['resultado'].sum().reset_index()
            fig_bar = px.bar(ctx_perf, x='contexto', y='resultado', title="Resultado por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
            st.plotly_chart(fig_bar, use_container_width=True)
