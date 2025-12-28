import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from supabase import create_client
import math

# Importando seus motores matemáticos calibrados
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
            if 'fase_entrada' not in df.columns: df['fase_entrada'] = 'Fase 2'
            df['saldo_inicial'] = df['saldo_inicial'].astype(float)
            df['pico_previo'] = df['pico_previo'].astype(float)
        return df
    except: return pd.DataFrame()

# --- 2. COMPONENTE VISUAL ---
def card(label, value, sub_text, color="white", border_color="#333333"):
    st.markdown(f"""
        <div style="background-color: #161616; padding: 15px; border-radius: 8px; border: 1px solid {border_color}; text-align: center; margin-bottom: 10px; height: 100px; display: flex; flex-direction: column; justify-content: center;">
            <div style="color: #888; font-size: 10px; text-transform: uppercase; margin-bottom: 4px; display: flex; justify-content: center; align-items: center; gap: 5px;">
                {label} <span style="font-size:9px; border: 1px solid #444; border-radius: 50%; width: 10px; height: 10px; display: inline-flex; justify-content: center; align-items: center;">?</span>
            </div>
            <h2 style="color: {color}; margin: 0; font-size: 20px; font-weight: 600;">{value}</h2>
            <p style="color: #666; font-size: 10px; margin-top: 4px;">{sub_text}</p>
        </div>
    """, unsafe_allow_html=True)

# --- 3. DASHBOARD LOGIC ---
def show(user, role):
    df_trades_all = load_trades_db()
    df_contas_all = load_contas_config(user)
    if not df_trades_all.empty:
        df_trades_all = df_trades_all[df_trades_all['usuario'] == user]

    st.markdown("### 🔭 Visão do Operacional")
    grupos_disponiveis = ["Todos"] + (sorted(list(df_contas_all['grupo_nome'].unique())) if not df_contas_all.empty else [])
    
    c_sel1, c_sel2, c_date1, c_date2 = st.columns([1.5, 1.5, 1, 1])
    with c_sel1: grupo_sel = st.selectbox("📂 Grupo", grupos_disponiveis)
    
    contas_do_grupo = df_contas_all if grupo_sel == "Todos" else df_contas_all[df_contas_all['grupo_nome'] == grupo_sel]
    lista_contas_view = ["📊 VISÃO GERAL (Agregado)"] + (sorted(list(contas_do_grupo['conta_identificador'].unique())) if not contas_do_grupo.empty else [])
    
    with c_sel2: view_mode = st.selectbox("🔎 Detalhe", lista_contas_view)
    with c_date1: d_inicio = st.date_input("De", datetime.now().date() - timedelta(days=30))
    with c_date2: d_fim = st.date_input("Até", datetime.now().date())

    st.markdown("---")

    # Filtros de Dados
    trades_filtered = pd.DataFrame()
    if not df_trades_all.empty:
        trades_filtered = df_trades_all.copy()
        if grupo_sel != "Todos": trades_filtered = trades_filtered[trades_filtered['grupo_vinculo'] == grupo_sel]
        trades_filtered = trades_filtered[(trades_filtered['data'] >= d_inicio) & (trades_filtered['data'] <= d_fim)]
    
    contas_alvo = contas_do_grupo if "VISÃO GERAL" in view_mode else (contas_do_grupo[contas_do_grupo['conta_identificador'] == view_mode] if not contas_do_grupo.empty else pd.DataFrame())

    # --- ENGINE DE SAÚDE E METAS ---
    total_buffer, contas_ativas, fase_display, meta_calc, saldo_total_atual = 0.0, 0, "---", 160000.0, 0.0
    if not contas_alvo.empty:
        lucro_total = trades_filtered['resultado'].sum() if not trades_filtered.empty else 0.0
        n_c = len(contas_alvo) if len(contas_alvo) > 0 else 1
        for _, conta in contas_alvo.iterrows():
            if conta['status_conta'] == 'Ativa':
                # CALIBRAGEM 1 e 2: HWM do Banco + Fase PA
                saude = ApexEngine.calculate_health(float(conta['saldo_inicial']) + (lucro_total/n_c), float(conta['pico_previo']), fase_informada=conta.get('fase_entrada', 'Fase 2'))
                total_buffer += saude['buffer']
                saldo_total_atual += saude['saldo']
                contas_ativas += 1
                fase_display, meta_calc = saude['fase'], saude['meta_proxima']

    # --- CÁLCULOS KPI ---
    if not trades_filtered.empty:
        results_list = trades_filtered['resultado'].tolist()
        wins, losses = trades_filtered[trades_filtered['resultado'] > 0], trades_filtered[trades_filtered['resultado'] < 0]
        net_profit = trades_filtered['resultado'].sum()
        gross_p, gross_l = wins['resultado'].sum(), abs(losses['resultado'].sum())
        pf = gross_p / gross_l if gross_l > 0 else 99.99
        win_rate = (len(wins) / len(trades_filtered) * 100)
        avg_win, avg_loss = wins['resultado'].mean(), abs(losses['resultado'].mean())
        payoff = avg_win / avg_loss if avg_loss > 0 else 0.0
        expectancy = ((win_rate/100) * avg_win) - ((1 - (win_rate/100)) * avg_loss)
        pts_loss_medio = abs(losses['pts_medio'].mean()) if not losses.empty else 15.0
        lote_medio, ativo_ref = trades_filtered['lote'].mean(), trades_filtered['ativo'].iloc[-1]
        equity = trades_filtered.sort_values('created_at')['resultado'].cumsum()
        max_dd = (equity - equity.cummax()).min()
    else:
        results_list, net_profit, pf, win_rate, expectancy, avg_win, avg_loss, payoff, pts_loss_medio, lote_medio, max_dd, gross_p, gross_l, ativo_ref = [], 0, 0, 0, 0, 0, 0, 0, 15, 0, 0, 0, 0, "MNQ"

    # --- RISK ENGINE (CALIBRAGEM 3: SCAN ATÔMICO) ---
    custo_stop = pts_loss_medio * (lote_medio if lote_medio > 0 else 1) * MULTIPLIERS.get(ativo_ref, 2)
    risco_grupo = custo_stop * (contas_ativas if contas_ativas > 0 else 1)
    vidas_u = total_buffer / risco_grupo if risco_grupo > 0 else 0.0
    prob_ruina = RiskEngine.calculate_ruin(win_rate, avg_win, avg_loss, total_buffer, trades_results=results_list)
    # CALIBRAGEM 4: Z-SCORE
    edge_calc = ((win_rate/100) * payoff) - (1 - (win_rate/100))
    l_min, l_max, k_pct = PositionSizing.calculate_limits(win_rate, payoff, total_buffer, custo_stop)

    # --- CARDS VISUAIS ---
    st.markdown("### 🏁 Desempenho Geral")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card("Resultado Líquido", f"${net_profit:,.2f}", f"Bruto: ${gross_p:,.0f} / -${gross_l:,.0f}", "#00FF88" if net_profit>=0 else "#FF4B4B")
    with c2: card("Fator de Lucro (PF)", f"{pf:.2f}", f"Meta Atual: {fase_display}", "#FF4B4B" if pf < 1.5 else "#00FF88")
    with c3: card("Win Rate", f"{win_rate:.1f}%", f"{len(trades_filtered)} Trades Executados", "white")
    with c4: card("Expectativa Mat.", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy>0 else "#FF4B4B")

    st.markdown("### 🛡️ Análise de Sobrevivência")
    k1, k2, k3, k4 = st.columns(4)
    with k1: card("Z-Score (Edge)", f"{edge_calc:.4f}", "Vantagem Estatística", "#00FF88" if edge_calc > 0 else "#FF4B4B")
    with k2: card("Buffer Real (Trailing)", f"${total_buffer:,.0f}", "Trailing Apex Calibrado", "#00FF88")
    with k3: card("Vidas Reais (U)", f"{vidas_u:.1f}", f"Risco p/ Trade: ${risco_grupo:,.0f}", "#00FF88" if vidas_u > 15 else "#FF4B4B")
    with k4: card("Prob. Ruína (Real)", f"{prob_ruina:.4f}%", "Scan Atômico Ativo", "#00FF88" if prob_ruina < 1 else "#FF4B4B")

    # --- BARRA DE PROGRESSO E METAS (REINTEGRADO) ---
    st.markdown("---")
    st.markdown("### 🎯 Progresso da Jornada")
    pg1, pg2 = st.columns([2, 1])
    with pg1:
        base_v, meta_v = 150000.0 * contas_ativas, meta_calc * contas_ativas
        progresso = min(1.0, max(0.0, (saldo_total_atual - base_v) / (meta_v - base_v))) if (meta_v - base_v) > 0 else 0
        st.progress(progresso)
        st.write(f"Progresso rumo a **{fase_display}**: {progresso*100:.1f}% (Objetivo: ${meta_v:,.0f})")
    with pg2:
        falta = meta_v - saldo_total_atual
        if avg_win > 0 and falta > 0:
            st.info(f"Faltam aprox. **{math.ceil(falta/avg_win)} trades** de gain médio.")
        else: st.success("Meta Atingida ou em fase de Saques!")

    # --- GRÁFICOS DE PERFORMANCE ---
    st.markdown("### 📈 Evolução e Contextos")
    g1, g2 = st.columns([2.5, 1])
    with g1:
        if not trades_filtered.empty:
            df_plot = trades_filtered.sort_values('created_at').copy()
            df_plot['saldo_acc'] = df_plot['resultado'].cumsum()
            fig = px.line(df_plot, x='created_at', y='saldo_acc', title="Curva de Patrimônio Líquido")
            fig.update_traces(line_color='#00FF88', fill='tozeroy')
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)
    with g2:
        if not trades_filtered.empty:
            ctx = trades_filtered.groupby('contexto')['resultado'].count().reset_index()
            fig_pie = px.pie(ctx, values='resultado', names='contexto', hole=.4, title="Distribuição")
            fig_pie.update_layout(template="plotly_dark", height=400, showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### 📅 Performance por Período")
    t1, t2 = st.columns(2)
    with t1:
        daily = trades_filtered.groupby('data')['resultado'].sum().reset_index()
        st.plotly_chart(px.bar(daily, x='data', y='resultado', title="Diário", template="plotly_dark", color_discrete_sequence=['#00FF88']), use_container_width=True)
    with t2:
        trades_filtered['dia'] = pd.to_datetime(trades_filtered['data']).dt.day_name()
        week = trades_filtered.groupby('dia')['resultado'].sum().reset_index()
        st.plotly_chart(px.bar(week, x='dia', y='resultado', title="Dia da Semana", template="plotly_dark", color_discrete_sequence=['#2962FF']), use_container_width=True)
