import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from supabase import create_client

# Importando seus motores matemáticos
from modules.logic import ApexEngine, RiskEngine, PositionSizing
from modules.database import update_hwm 

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

def show(user, role):
    df_trades_all = load_trades_db()
    df_contas_all = load_contas_config(user)
    
    if not df_trades_all.empty:
        df_trades_all = df_trades_all[df_trades_all['usuario'] == user]

    st.markdown("### 🔭 Visão do Operacional")
    grupos_disponiveis = ["Todos"]
    if not df_contas_all.empty:
        grupos_disponiveis += sorted(list(df_contas_all['grupo_nome'].unique()))
    
    c_sel1, c_sel2, c_date1, c_date2 = st.columns([1.5, 1.5, 1, 1])
    with c_sel1: grupo_sel = st.selectbox("📂 Grupo", grupos_disponiveis)
    
    contas_do_grupo = pd.DataFrame()
    if not df_contas_all.empty:
        contas_do_grupo = df_contas_all[df_contas_all['grupo_nome'] == grupo_sel] if grupo_sel != "Todos" else df_contas_all
            
    lista_contas_view = ["📊 VISÃO GERAL (Agregado)"] + sorted(list(contas_do_grupo['conta_identificador'].unique())) if not contas_do_grupo.empty else ["📊 VISÃO GERAL (Agregado)"]
    with c_sel2: view_mode = st.selectbox("🔎 Detalhe", lista_contas_view)
    with c_date1: d_inicio = st.date_input("De", datetime.now().date() - timedelta(days=30))
    with c_date2: d_fim = st.date_input("Até", datetime.now().date())

    st.markdown("---")

    trades_filtered_view = pd.DataFrame()
    trades_full_risk = pd.DataFrame()

    if not df_trades_all.empty:
        base_df = df_trades_all[df_trades_all['grupo_vinculo'] == grupo_sel] if grupo_sel != "Todos" else df_trades_all.copy()
        trades_full_risk = base_df.copy()
        if 'data' in base_df.columns:
            trades_filtered_view = base_df[(base_df['data'] >= d_inicio) & (base_df['data'] <= d_fim)]
    
    contas_alvo = contas_do_grupo if "VISÃO GERAL" in view_mode else contas_do_grupo[contas_do_grupo['conta_identificador'] == view_mode]

    # Função para calcular lucro real por conta
    def calcular_lucro_conta(conta_id, grupo_nome, df_trades):
        """
        Calcula o lucro real de uma conta específica.
        - Trades INDIVIDUAIS (conta_id = esta conta) → soma 100%
        - Trades REPLICADOS (conta_id = NULL, grupo = este grupo) → soma 100% (cada conta recebe o trade completo)
        """
        lucro_total = 0.0
        
        if not df_trades.empty:
            # Trades individuais desta conta
            if 'conta_id' in df_trades.columns:
                trades_individuais = df_trades[df_trades['conta_id'] == conta_id]
                lucro_total += trades_individuais['resultado'].sum()
                
                # Trades replicados do grupo (conta_id é NULL)
                trades_replicados = df_trades[
                    (df_trades['grupo_vinculo'] == grupo_nome) & 
                    (df_trades['conta_id'].isna())
                ]
                lucro_total += trades_replicados['resultado'].sum()
            else:
                # Fallback: se não tem conta_id, usa lógica antiga (divide por grupo)
                trades_grupo = df_trades[df_trades['grupo_vinculo'] == grupo_nome]
                lucro_total = trades_grupo['resultado'].sum()
        
        return lucro_total

    total_buffer = 0.0; contas_ativas = 0; hwm_updated_flag = False
    if not contas_alvo.empty:
        for _, conta in contas_alvo.iterrows():
            if conta['status_conta'] == 'Ativa':
                # Calcula lucro REAL desta conta (individual + replicado)
                lucro_conta = calcular_lucro_conta(conta['id'], conta['grupo_nome'], trades_full_risk)
                
                saldo_atual_est = float(conta['saldo_inicial']) + lucro_conta
                hwm_dinamico = max(float(conta['pico_previo']), saldo_atual_est)
                if hwm_dinamico > float(conta['pico_previo']):
                    update_hwm(conta['id'], hwm_dinamico); hwm_updated_flag = True
                saude = ApexEngine.calculate_health(saldo_atual_est, hwm_dinamico, conta.get('fase_entrada', 'Fase 1'))
                total_buffer += saude['buffer']; contas_ativas += 1
    
    if hwm_updated_flag: st.toast("🚀 Novo Topo Histórico Salvo!", icon="💾")

    # --- CORREÇÃO ITEM 5: USAR TRADES FILTRADOS PARA CÁLCULO DE RUÍNA ---
    # Antes: results_list_full = trades_full_risk['resultado'].tolist()
    # Agora: Usa o período selecionado pelo usuário
    results_list_filtered = trades_filtered_view['resultado'].tolist() if not trades_filtered_view.empty else []

    # --- INICIALIZAÇÃO SEGURA DAS VARIÁVEIS ---
    # Isso garante que elas existam mesmo se o banco estiver vazio
    net_profit = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    pf = 0.0
    win_rate = 0.0
    total_trades = 0
    avg_win = 0.0
    avg_loss = 0.0
    payoff = 0.0
    expectancy = 0.0
    avg_pts_gain = 0.0
    pts_loss_medio_real = 15.0 # Padrão seguro
    lote_medio = 0.0
    max_dd = 0.0
    wins = pd.DataFrame()
    losses = pd.DataFrame()
    ativo_ref = "MNQ" # Padrão seguro

    if not trades_filtered_view.empty:
        wins = trades_filtered_view[trades_filtered_view['resultado'] > 0]
        losses = trades_filtered_view[trades_filtered_view['resultado'] < 0]
        net_profit = trades_filtered_view['resultado'].sum()
        gross_profit = wins['resultado'].sum()
        gross_loss = abs(losses['resultado'].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else 99.99
        total_trades = len(trades_filtered_view)
        win_rate = (len(wins) / total_trades * 100)
        avg_win = wins['resultado'].mean() if not wins.empty else 0.0
        avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0.0
        payoff = avg_win / avg_loss if avg_loss > 0 else 0.0
        expectancy = ((win_rate/100) * avg_win) - ((1 - (win_rate/100)) * avg_loss)
        avg_pts_gain = wins['pts_medio'].mean() if not wins.empty else 0.0 
        avg_pts_loss = abs(losses['pts_medio'].mean()) if not losses.empty else 0.0
        
        if avg_pts_loss > 0:
            pts_loss_medio_real = avg_pts_loss
            
        lote_medio = trades_filtered_view['lote'].mean()
        if 'ativo' in trades_filtered_view.columns:
            ativo_ref = trades_filtered_view['ativo'].iloc[-1]
            
        equity = trades_filtered_view.sort_values('created_at')['resultado'].cumsum()
        max_dd = (equity - equity.cummax()).min()

    custo_stop_padrao = pts_loss_medio_real * (lote_medio if lote_medio > 0 else 1) * MULTIPLIERS.get(ativo_ref, 2)
    vidas_u = RiskEngine.calculate_lives(total_buffer, custo_stop_padrao, contas_ativas)
    
    # --- CORREÇÃO ITEM 5: Ruína agora usa trades FILTRADOS ---
    prob_ruina = RiskEngine.calculate_ruin(win_rate, avg_win, avg_loss, total_buffer, trades_results=results_list_filtered)
    
    loss_rate_dec = (len(losses)/total_trades) if total_trades > 0 else 0
    edge_calc = ((win_rate/100) * payoff) - loss_rate_dec
    lote_min, lote_max, kelly_pct = PositionSizing.calculate_limits(win_rate, payoff, total_buffer, custo_stop_padrao)

    # --- RENDERIZAÇÃO ---
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
    
    # --- CORREÇÃO ITEM 5: Z-Score também usa trades filtrados ---
    num_trades_risco = len(results_list_filtered)
    z_serial = RiskEngine.calculate_z_score_serial(results_list_filtered)
    
    if num_trades_risco < 15:
        cor_zs = "#888888"; val_zs = "---"; sub_zs = "Amostra Insuficiente"
    elif num_trades_risco < 30:
        cor_zs = "#FFFF00"; val_zs = f"{z_serial:.2f}"; sub_zs = f"Calibrando ({num_trades_risco}/30)"
    else:
        cor_zs = "#00FF88" if z_serial > 0 else "#FF4B4B"
        val_zs = f"{z_serial:.2f}"; sub_zs = "Consistência (Runs)"

    with k1: card("Z-Score (Sequência)", val_zs, sub_zs, cor_zs, border_color=cor_zs)

    # 2. LOGICA Z-SCORE EDGE
    if num_trades_risco < 15:
        cor_ze = "#888888"; val_ze = "---"; sub_ze = "Amostra Insuficiente"
    else:
        cor_ze = "#00FF88" if edge_calc > 0 else "#FF4B4B"
        val_ze = f"{edge_calc:.4f}"; sub_ze = "Expectativa (GPS)"

    with k2: card("Z-Score (Edge)", val_ze, sub_ze, cor_ze, border_color=cor_ze)
    
    # 3. VIDAS REAIS
    cor_v = "#FF4B4B" if vidas_u < 10 else ("#FFFF00" if vidas_u < 20 else "#00FF88")
    with k3: card("Vidas Reais (U)", f"{vidas_u:.1f}", f"Risco: ${custo_stop_padrao:,.0f}", cor_v)
    
    # 4. PROBABILIDADE DE RUINA
    cor_r = "#00FF88" if prob_ruina < 1 else ("#FF4B4B" if prob_ruina > 5 else "#FFFF00")
    with k4: card("Prob. Ruína", f"{prob_ruina:.4f}%", "Risco de Quebra", cor_r, border_color=cor_r)

    st.markdown("### 🧠 Inteligência de Lote (Faixa de Operação)")
    l1, l2, l3, l4 = st.columns(4)
    with l1:
        # Buffer Color Logic
        if total_buffer > 2500: cor_buf_lote = "#00FF88"
        elif total_buffer > 1000: cor_buf_lote = "#FFFF00"
        else: cor_buf_lote = "#FF4B4B"
        card("Buffer Disponível", f"${total_buffer:,.0f}", "Base p/ Lote (Apex)", cor_buf_lote, border_color=cor_buf_lote)

    with l2: card("Half-Kelly", f"{kelly_pct*100:.1f}%", "Aproveitamento", "#888")
    with l3: card("Risco Financeiro", f"${total_buffer * kelly_pct:,.0f}", "Alocação Sugerida", "#00FF88")
    with l4: card("Sugestão de Lote", f"{lote_min} a {lote_max} ctrs", "ZONA DE OPERAÇÃO", "#00FF88", border_color="#00FF88")

    # --- GRÁFICOS ---
    st.markdown("---")
    st.markdown("### 📈 Evolução Financeira")
    
    g1, g2 = st.columns([2.5, 1])
    
    with g1:
        if not trades_filtered_view.empty:
            trades_plot = trades_filtered_view.sort_values('created_at').copy()
            saldo_inicial_base = contas_alvo['saldo_inicial'].sum() if not contas_alvo.empty else 0.0
            trades_plot['saldo_acumulado'] = trades_plot['resultado'].cumsum() + saldo_inicial_base
            
            view_type = st.radio("Visualizar Curva por:", ["Sequência de Trades", "Data (Tempo)"], horizontal=True, label_visibility="collapsed")
            
            if view_type == "Sequência de Trades":
                trades_plot['seq'] = range(1, len(trades_plot) + 1)
                x_axis = trades_plot['seq']; x_title = "Quantidade de Trades"
            else:
                x_axis = trades_plot['created_at']; x_title = "Data / Hora"

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_axis, y=trades_plot['saldo_acumulado'],
                mode='lines', name='Patrimônio',
                line=dict(color='#00FF88', width=2),
                fill='tozeroy', fillcolor='rgba(0, 255, 136, 0.1)'
            ))
            fig.add_hline(y=saldo_inicial_base, line_dash="dash", line_color="gray", annotation_text="Inicial")
            
            y_vals = trades_plot['saldo_acumulado']
            min_y = min(y_vals.min(), saldo_inicial_base); max_y = max(y_vals.max(), saldo_inicial_base)
            diff = max_y - min_y; padding = max(500.0, diff * 0.15)

            fig.update_layout(
                title=f"Curva de Patrimônio",
                template="plotly_dark",
                xaxis_title=x_title,
                yaxis_title="Patrimônio ($)",
                yaxis=dict(range=[min_y - padding, max_y + padding]),
                height=400,
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para exibir gráfico.")
            
    with g2:
        if not trades_filtered_view.empty:
            st.write(""); st.write("") 
            if 'contexto' in trades_filtered_view.columns:
                 ctx_perf = trades_filtered_view.groupby('contexto')['resultado'].sum().reset_index()
                 colors = ['#00FF88' if x >= 0 else '#FF4B4B' for x in ctx_perf['resultado']]
                 fig_pie = go.Figure(data=[go.Pie(
                    labels=ctx_perf['contexto'], 
                    values=abs(ctx_perf['resultado']),
                    hole=.5, textinfo='label+percent',
                    marker=dict(colors=colors, line=dict(color='#161616', width=3))
                 )])
                 fig_pie.update_layout(title="Resultado por Contexto", template="plotly_dark", showlegend=False)
                 st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### 📅 Performance Temporal")
    if not trades_filtered_view.empty:
        t1, t2 = st.columns(2)
        with t1:
            daily_perf = trades_filtered_view.groupby('data')['resultado'].sum().reset_index()
            fig_daily = px.bar(daily_perf, x='data', y='resultado', title="Resultado Diário (Timeline)", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
            fig_daily.update_layout(showlegend=False, xaxis_title="Data", yaxis_title="Resultado ($)")
            st.plotly_chart(fig_daily, use_container_width=True)
        with t2:
            trades_filtered_view['dia_semana'] = pd.to_datetime(trades_filtered_view['data']).dt.day_name()
            dias_pt = {'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua', 'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sab', 'Sunday': 'Dom'}
            trades_filtered_view['dia_pt'] = trades_filtered_view['dia_semana'].map(dias_pt)
            week_order = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
            week_perf = trades_filtered_view.groupby('dia_pt')['resultado'].sum().reindex(week_order).reset_index()
            fig_week = px.bar(week_perf, x='dia_pt', y='resultado', title="Dia da Semana (Estatístico)", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
            fig_week.update_layout(showlegend=False, xaxis_title="Dia", yaxis_title="Resultado ($)")
            st.plotly_chart(fig_week, use_container_width=True)
