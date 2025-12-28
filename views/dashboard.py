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
            
            cols_float = ['resultado', 'lote', 'pts_medio']
            for c in cols_float:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
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

    # --- TOP BAR ---
    st.markdown("### 🔭 Visão do Operacional")
    
    grupos_disponiveis = ["Todos"]
    if not df_contas_all.empty:
        grupos_disponiveis += sorted(list(df_contas_all['grupo_nome'].unique()))
    
    c_sel1, c_sel2, c_date1, c_date2 = st.columns([1.5, 1.5, 1, 1])
    
    with c_sel1:
        grupo_sel = st.selectbox("📂 Grupo", grupos_disponiveis)
    
    contas_do_grupo = pd.DataFrame()
    if not df_contas_all.empty:
        if grupo_sel != "Todos":
            contas_do_grupo = df_contas_all[df_contas_all['grupo_nome'] == grupo_sel]
        else:
            contas_do_grupo = df_contas_all
            
    lista_opcoes = []
    if not contas_do_grupo.empty:
        lista_opcoes = sorted(list(contas_do_grupo['conta_identificador'].unique()))
        
    lista_contas_view = ["📊 VISÃO GERAL (Agregado)"] + lista_opcoes
    
    with c_sel2:
        view_mode = st.selectbox("🔎 Detalhe", lista_contas_view)

    with c_date1:
        d_inicio = st.date_input("De", datetime.now().date() - timedelta(days=30))
    with c_date2:
        d_fim = st.date_input("Até", datetime.now().date())

    st.markdown("---")

    # --- FILTRAGEM ---
    trades_filtered = pd.DataFrame()
    if not df_trades_all.empty:
        trades_filtered = df_trades_all.copy()
        if grupo_sel != "Todos":
            trades_filtered = trades_filtered[trades_filtered['grupo_vinculo'] == grupo_sel]
        
        if 'data' in trades_filtered.columns:
            trades_filtered = trades_filtered[
                (trades_filtered['data'] >= d_inicio) & 
                (trades_filtered['data'] <= d_fim)
            ]
    
    if "VISÃO GERAL" in view_mode:
        contas_alvo = contas_do_grupo
    else:
        if not contas_do_grupo.empty:
            contas_alvo = contas_do_grupo[contas_do_grupo['conta_identificador'] == view_mode]
        else:
            contas_alvo = pd.DataFrame()

    # --- ENGINE (BUFFER) ---
    total_buffer = 0.0
    contas_ativas = 0
    
    if not contas_alvo.empty:
        lucro_total_periodo = trades_filtered['resultado'].sum() if not trades_filtered.empty else 0.0
        num_contas_no_filtro = len(contas_alvo) if len(contas_alvo) > 0 else 1
        lucro_por_conta_est = lucro_total_periodo / num_contas_no_filtro

        for _, conta in contas_alvo.iterrows():
            if conta['status_conta'] == 'Ativa':
                saldo_ini = float(conta['saldo_inicial'])
                hwm_prev = float(conta['pico_previo'])
                saldo_atual_est = saldo_ini + lucro_por_conta_est
                saude = ApexEngine.calculate_health(saldo_atual_est, hwm_prev)
                total_buffer += saude['buffer']
                contas_ativas += 1

    # --- KPI CALCULATIONS ---
    if not trades_filtered.empty:
        wins = trades_filtered[trades_filtered['resultado'] > 0]
        losses = trades_filtered[trades_filtered['resultado'] < 0]
        
        net_profit = trades_filtered['resultado'].sum()
        gross_profit = wins['resultado'].sum() if not wins.empty else 0.0
        gross_loss = abs(losses['resultado'].sum()) if not losses.empty else 0.0
        
        pf = gross_profit / gross_loss if gross_loss > 0 else 99.99
        total_trades = len(trades_filtered)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
        
        avg_win = wins['resultado'].mean() if not wins.empty else 0.0
        avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0.0
        payoff = avg_win / avg_loss if avg_loss > 0 else 0.0
        expectancy = ( (win_rate/100) * avg_win ) - ( (1 - (win_rate/100)) * avg_loss )
        
        avg_pts_gain = wins['pts_medio'].mean() if not wins.empty else 0.0
        avg_pts_loss = abs(losses['pts_medio'].mean()) if not losses.empty else 0.0
        pts_loss_medio_real = avg_pts_loss if avg_pts_loss > 0 else 15.0 
        
        lote_medio = trades_filtered['lote'].mean()
        ativo_ref = trades_filtered['ativo'].iloc[-1]
        
        df_sorted = trades_filtered.sort_values('created_at')
        equity = df_sorted['resultado'].cumsum()
        max_dd = (equity - equity.cummax()).min()
    else:
        net_profit = 0.0; gross_profit = 0.0; gross_loss = 0.0; pf = 0.0
        total_trades = 0; win_rate = 0.0; avg_win = 0.0; avg_loss = 0.0
        payoff = 0.0; expectancy = 0.0; avg_pts_gain = 0.0; pts_loss_medio_real = 15.0
        lote_medio = 0.0; ativo_ref = "MNQ"; max_dd = 0.0
        wins = pd.DataFrame(); losses = pd.DataFrame()

    # --- RISK ENGINE ---
    custo_stop_padrao = pts_loss_medio_real * (lote_medio if lote_medio > 0 else 1) * MULTIPLIERS.get(ativo_ref, 2)
    if custo_stop_padrao == 0: custo_stop_padrao = 15 * 1 * 2
    
    risco_impacto_grupo = custo_stop_padrao * (contas_ativas if contas_ativas > 0 else 1)
    
    try:
        vidas_u = RiskEngine.calculate_lives(total_buffer, custo_stop_padrao, contas_ativas)
    except:
        vidas_u = total_buffer / risco_impacto_grupo if risco_impacto_grupo > 0 else 0.0
    
    prob_ruina = RiskEngine.calculate_ruin(win_rate, avg_win, avg_loss, total_buffer)
    loss_rate_dec = (len(losses)/total_trades) if total_trades > 0 else 0
    edge_calc = ((win_rate/100) * payoff) - loss_rate_dec
    lote_min, lote_max, kelly_pct = PositionSizing.calculate_limits(win_rate, payoff, total_buffer, custo_stop_padrao)

    # ==============================================================================
    # RENDERIZAÇÃO
    # ==============================================================================

    st.markdown("### 🏁 Desempenho Geral")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card("Resultado Líquido", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f} / -${gross_loss:,.0f}", "#00FF88" if net_profit>=0 else "#FF4B4B")
    with c2: card("Fator de Lucro (PF)", f"{pf:.2f}", "Ideal > 1.5", "#FF4B4B" if pf < 1.5 else "#00FF88")
    with c3: card("Win Rate", f"{win_rate:.1f}%", f"{len(wins)}W / {len(losses)}L", "white")
    with c4: card("Expectativa Mat.", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy>0 else "#FF4B4B")

    st.markdown("### 💲 Médias Financeiras")
    m1, m2, m3, m4 = st.columns(4)
    with m1: card("Média Gain ($)", f"${avg_win:,.2f}", "", "#00FF88")
    with m2: card("Média Loss ($)", f"-${avg_loss:,.2f}", "", "#FF4B4B")
    with m3: card("Risco : Retorno", f"1 : {payoff:.2f}", "Payoff Real", "white")
    with m4: card("Drawdown Máximo", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B")
    
    st.markdown("### 🎯 Performance Técnica")
    t1, t2, t3, t4 = st.columns(4)
    with t1: card("Pts Médios (Gain)", f"{avg_pts_gain:.2f} pts", "", "#00FF88")
    with t2: card("Stop Médio (Real)", f"{pts_loss_medio_real:.2f} pts", "Base do Risco", "#FF4B4B")
    with t3: card("Lote Médio", f"{lote_medio:.1f}", "Contratos", "white")
    with t4: card("Total Trades", f"{total_trades}", "Executados", "white")

    st.markdown("---")

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
        card("Vidas Reais (U)", f"{vidas_u:.1f}", f"Risco Histórico: ${risco_impacto_grupo:,.0f}", cor_v)
    with k4:
        cor_r = "#00FF88" if prob_ruina < 1 else ("#FF4B4B" if prob_ruina > 5 else "#FFFF00")
        card("Prob. Ruína (Real)", f"{prob_ruina:.2f}%", "Risco Moderado", cor_r, border_color=cor_r)

    st.markdown("### 🧠 Inteligência de Lote (Faixa de Operação)")
    l1, l2, l3, l4 = st.columns(4)
    with l1:
        card("Buffer Disponível", f"${total_buffer:,.0f}", "Capital de Risco", "#00FF88" if total_buffer > 0 else "#FF4B4B")
    with l2:
        card("Half-Kelly (Math)", f"{kelly_pct*100:.1f}%", "Teto Teórico", "#888")
    with l3:
        alloc_dolar = total_buffer * kelly_pct
        card("Risco Financeiro", f"${alloc_dolar:,.0f}", "Alocação Global", "#00FF88")
    with l4:
        card("Sugestão de Lote", f"{lote_min} a {lote_max} ctrs", "ZONA DE ACELERAÇÃO", "#00FF88", border_color="#00FF88")

    # --- 6. GRÁFICOS (CORRIGIDOS) ---
    st.markdown("---")
    st.markdown("### 📈 Evolução Financeira")
    
    g1, g2 = st.columns([2.5, 1])
    
    with g1:
        if not trades_filtered.empty:
            trades_plot = trades_filtered.sort_values('created_at').copy()
            saldo_inicial_base = contas_alvo['saldo_inicial'].sum() if not contas_alvo.empty else 0.0
            trades_plot['saldo_acumulado'] = trades_plot['resultado'].cumsum() + saldo_inicial_base
            
            view_type = st.radio("Visualizar Curva por:", ["Sequência de Trades", "Data (Tempo)"], horizontal=True, label_visibility="collapsed")
            
            # Define Eixos
            if view_type == "Sequência de Trades":
                trades_plot['seq'] = range(1, len(trades_plot) + 1)
                x_axis = trades_plot['seq']
                x_title = "Quantidade de Trades"
            else:
                x_axis = trades_plot['created_at']
                x_title = "Data / Hora"

            # === GRÁFICO DE ÁREA COM ZOOM INTELIGENTE (IGUAL ABA CONTAS) ===
            fig = go.Figure()

            # 1. Área de Saldo
            fig.add_trace(go.Scatter(
                x=x_axis, y=trades_plot['saldo_acumulado'],
                mode='lines', name='Patrimônio',
                line=dict(color='#00FF88', width=2),
                fill='tozeroy', fillcolor='rgba(0, 255, 136, 0.1)'
            ))

            # 2. Linha Inicial
            fig.add_hline(y=saldo_inicial_base, line_dash="dash", line_color="gray", annotation_text="Inicial")
            
            # Lógica de Zoom
            y_vals = trades_plot['saldo_acumulado']
            min_y = min(y_vals.min(), saldo_inicial_base)
            max_y = max(y_vals.max(), saldo_inicial_base)
            
            diff = max_y - min_y
            padding = max(500.0, diff * 0.15) # Mínimo de $500 de margem

            fig.update_layout(
                title=f"Curva de Patrimônio",
                template="plotly_dark",
                xaxis_title=x_title,
                yaxis_title="Patrimônio ($)",
                yaxis=dict(range=[min_y - padding, max_y + padding]), # <--- ZOOM APLICADO
                height=400,
                margin=dict(l=10, r=10, t=40, b=10)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para exibir gráfico.")
            
    with g2:
        if not trades_filtered.empty:
            st.write("") 
            st.write("") 
            
            # === PIZZA ESTILIZADA (BORDAS PRETAS) ===
            ctx_perf = trades_filtered.groupby('contexto')['resultado'].sum().reset_index()
            colors = ['#00FF88' if x >= 0 else '#FF4B4B' for x in ctx_perf['resultado']]
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=ctx_perf['contexto'], 
                values=abs(ctx_perf['resultado']),
                hole=.5,
                textinfo='label+percent',
                marker=dict(
                    colors=colors,
                    line=dict(color='#161616', width=3) # <--- BORDAS PRETAS GROSSAS (CORTE)
                )
            )])
            
            fig_pie.update_layout(
                title="Resultado por Contexto",
                template="plotly_dark",
                showlegend=False,
                annotations=[dict(text='Contexto', x=0.5, y=0.5, font_size=14, showarrow=False)]
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)

    # --- GRÁFICOS TEMPORAIS ---
    st.markdown("### 📅 Performance Temporal")
    
    if not trades_filtered.empty:
        t1, t2 = st.columns(2)
        
        with t1:
            daily_perf = trades_filtered.groupby('data')['resultado'].sum().reset_index()
            fig_daily = px.bar(daily_perf, x='data', y='resultado', title="Resultado Diário (Timeline)", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
            fig_daily.update_layout(showlegend=False, xaxis_title="Data", yaxis_title="Resultado ($)")
            st.plotly_chart(fig_daily, use_container_width=True)
            
        with t2:
            trades_filtered['dia_semana'] = pd.to_datetime(trades_filtered['data']).dt.day_name()
            dias_pt = {'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua', 'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sab', 'Sunday': 'Dom'}
            trades_filtered['dia_pt'] = trades_filtered['dia_semana'].map(dias_pt)
            week_order = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
            week_perf = trades_filtered.groupby('dia_pt')['resultado'].sum().reindex(week_order).reset_index()
            
            fig_week = px.bar(week_perf, x='dia_pt', y='resultado', title="Dia da Semana (Estatístico)", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
            fig_week.update_layout(showlegend=False, xaxis_title="Dia", yaxis_title="Resultado ($)")
            st.plotly_chart(fig_week, use_container_width=True)
