import streamlit as st
import pandas as pd
import plotly.express as px
import math
from datetime import datetime, timedelta
from supabase import create_client

# --- 1. CONFIGURAÇÕES E CONEXÃO (Herdado da v250) ---
MULTIPLIERS = {"NQ": 20, "MNQ": 2, "ES": 50, "MES": 5}

# Tenta pegar o cliente Supabase do session_state ou cria um novo
def get_supabase():
    try:
        if "supabase" in st.session_state:
            return st.session_state["supabase"]
        else:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
    except:
        return None

# Funções de Dados (Trazidas da v250 para garantir funcionamento local)
def load_trades_db():
    try:
        supabase = get_supabase()
        res = supabase.table("trades").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['created_at'] = pd.to_datetime(df['created_at'])
            if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
        return df
    except:
        return pd.DataFrame()

def load_contas_config(user):
    try:
        supabase = get_supabase()
        res = supabase.table("contas_config").select("*").eq("usuario", user).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            if 'pico_previo' not in df.columns: df['pico_previo'] = df['saldo_inicial']
            if 'status_conta' not in df.columns: df['status_conta'] = 'Ativa'
        return df
    except:
        return pd.DataFrame()

# --- 2. MOTOR DE RISCO (Engine Apex v250) ---
def calcular_saude_apex(saldo_inicial, pico_previo, trades_df):
    # Regras por Tamanho de Conta
    if saldo_inicial >= 250000:   # 300k
        dd_max = 7500.0; meta_trava = saldo_inicial + dd_max + 100.0
    elif saldo_inicial >= 100000: # 150k
        dd_max = 5000.0; meta_trava = 155100.0
    elif saldo_inicial >= 50000:  # 50k
        dd_max = 2500.0; meta_trava = 52600.0
    else:                         # 25k
        dd_max = 1500.0; meta_trava = 26600.0
        
    lucro_acc = trades_df['resultado'].sum() if not trades_df.empty else 0.0
    saldo_atual = saldo_inicial + lucro_acc
    
    # HWM Real
    if not trades_df.empty:
        trades_sorted = trades_df.sort_values('created_at')
        equity_curve = trades_sorted['resultado'].cumsum() + saldo_inicial
        pico_grafico = equity_curve.max()
        pico_real = max(saldo_inicial, pico_grafico)
    else:
        pico_real = saldo_inicial

    # Trailing Stop
    stop_travado = saldo_inicial + 100.0
    if pico_real >= meta_trava:
        stop_atual = stop_travado
    else:
        stop_atual = pico_real - dd_max
        
    buffer = max(0.0, saldo_atual - stop_atual)
    
    return {
        "saldo_atual": saldo_atual,
        "stop_atual": stop_atual,
        "buffer": buffer,
        "hwm": pico_real
    }

# --- 3. COMPONENTE VISUAL (Card v300) ---
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

# --- 4. RENDERIZAÇÃO DO DASHBOARD ---
def show(user, role):
    
    # Carrega dados Reais
    df_raw = load_trades_db()
    df_contas = load_contas_config(user)
    
    if df_raw.empty:
        st.info("Aguardando dados... Registre seu primeiro trade.")
        return

    # Filtra usuário
    df = df_raw[df_raw['usuario'] == user].copy()
    if df.empty:
        st.warning("Nenhum trade encontrado para este usuário.")
        return

    # --- ÁREA DE FILTROS ---
    with st.expander("🔍 Filtros Avançados", expanded=True):
        c_d1, c_d2, c_grp, c_ctx = st.columns([1, 1, 1, 2])
        
        # Datas
        min_date = df['data'].min()
        max_date = df['data'].max()
        d_inicio = c_d1.date_input("Início", min_date)
        d_fim = c_d2.date_input("Fim", max_date)
        
        # Grupos
        if 'grupo_vinculo' in df.columns:
            lista_grupos = ["Todos"] + sorted(list(df['grupo_vinculo'].unique()))
            sel_grupo = c_grp.selectbox("Grupo", lista_grupos)
        else:
            sel_grupo = "Todos"

        # Contexto
        all_ctx = list(df['contexto'].unique())
        sel_ctx = c_ctx.multiselect("Contexto", all_ctx, default=all_ctx)

    # Aplica Filtros
    mask = (df['data'] >= d_inicio) & (df['data'] <= d_fim) & (df['contexto'].isin(sel_ctx))
    if sel_grupo != "Todos":
        mask = mask & (df['grupo_vinculo'] == sel_grupo)
    
    df_filtered = df[mask].copy()

    if df_filtered.empty:
        st.warning("Sem dados para os filtros selecionados.")
        return

    # --- CÁLCULOS KPI (Lógica v250) ---
    wins = df_filtered[df_filtered['resultado'] > 0]
    losses = df_filtered[df_filtered['resultado'] < 0]
    
    net_profit = df_filtered['resultado'].sum()
    gross_profit = wins['resultado'].sum()
    gross_loss = abs(losses['resultado'].sum())
    
    pf = gross_profit / gross_loss if gross_loss > 0 else 99.99
    win_rate = (len(wins) / len(df_filtered) * 100) if len(df_filtered) > 0 else 0.0
    
    avg_win = wins['resultado'].mean() if not wins.empty else 0
    avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0
    payoff = avg_win / avg_loss if avg_loss > 0 else 0
    expectancy = ( (win_rate/100) * avg_win ) - ( (1 - (win_rate/100)) * avg_loss )
    
    max_dd = 0.0
    if not df_filtered.empty:
        df_filtered = df_filtered.sort_values('created_at')
        df_filtered['equity'] = df_filtered['resultado'].cumsum()
        max_dd = (df_filtered['equity'] - df_filtered['equity'].cummax()).min()

    # --- CÁLCULO DE RISCO/SAÚDE (Motor Apex) ---
    total_buffer_real = 0.0
    contas_analisadas = 0
    
    if not df_contas.empty:
        c_alvo = df_contas if sel_grupo == "Todos" else df_contas[df_contas['grupo_nome'] == sel_grupo]
        for _, row in c_alvo.iterrows():
            if row.get('status_conta', 'Ativa') == 'Ativa':
                # Trades específicos desta conta/grupo para o cálculo de HWM
                trades_deste_grupo = df[df['grupo_vinculo'] == row['grupo_nome']]
                status_conta = calcular_saude_apex(
                    float(row['saldo_inicial']), 
                    float(row.get('pico_previo', row['saldo_inicial'])), 
                    trades_deste_grupo
                )
                total_buffer_real += status_conta['buffer']
                contas_analisadas += 1

    # Risco Comportamental (Vidas)
    lote_medio = df_filtered['lote'].mean() if not df_filtered.empty else 0
    pts_loss_medio = abs(losses['pts_medio'].mean()) if not losses.empty else 15.0
    ativo_ref = df_filtered['ativo'].iloc[-1] if not df_filtered.empty else "MNQ"
    
    risco_por_trade = lote_medio * pts_loss_medio * MULTIPLIERS.get(ativo_ref, 2)
    if risco_por_trade == 0: risco_por_trade = 300.0 # Fallback
    
    # Multiplica pelo número de contas copiadas
    risco_grupo_total = risco_por_trade * (contas_analisadas if contas_analisadas > 0 else 1)
    vidas_u = total_buffer_real / risco_grupo_total if risco_grupo_total > 0 else 0

    # Probabilidade de Ruína Simplificada
    prob_ruina = 0.0
    if vidas_u < 5: prob_ruina = 80.0
    elif vidas_u < 10: prob_ruina = 20.0
    elif expectancy <= 0: prob_ruina = 100.0

    # Kelly (Inteligência de Lote)
    kelly_val = (win_rate/100) - ((1 - (win_rate/100)) / payoff) if payoff > 0 else 0
    kelly_half = max(0.0, kelly_val / 2)
    lote_sug_min = 0
    lote_sug_max = 0
    if kelly_half > 0 and total_buffer_real > 0:
         risco_teto = total_buffer_real * kelly_half
         base_unit = pts_loss_medio * MULTIPLIERS.get(ativo_ref, 2)
         if base_unit > 0:
             lote_sug_max = int(risco_teto / base_unit)
             lote_sug_min = int(lote_sug_max * 0.7)

    # --- RENDERIZAÇÃO DOS CARDS (Layout v300) ---
    st.markdown("---")
    
    st.markdown("### 🏁 Desempenho Geral")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Resultado Líquido", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f} / -${gross_loss:,.0f}", "#00FF88" if net_profit>=0 else "#FF4B4B")
    with c2:
        card("Fator de Lucro (PF)", f"{pf:.2f}", "Ideal > 1.5", "#FF4B4B" if pf < 1.5 else "#00FF88")
    with c3:
        card("Win Rate", f"{win_rate:.1f}%", f"{len(wins)}W / {len(losses)}L", "white")
    with c4:
        card("Expectativa Mat.", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy>0 else "#FF4B4B")

    st.markdown("### 🛡️ Análise de Sobrevivência")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        card("Buffer Real (Hoje)", f"${total_buffer_real:,.0f}", f"{contas_analisadas} Contas Ativas", "#00FF88")
    with k2:
        cor_v = "#FF4B4B" if vidas_u < 10 else "#00FF88"
        card("Vidas Reais (U)", f"{vidas_u:.1f}", f"Risco: ${risco_grupo_total:,.0f}", cor_v)
    with k3:
        card("Half-Kelly", f"{kelly_half*100:.1f}%", "Teto Teórico", "#888")
    with k4:
        card("Sugestão Lote", f"{lote_sug_min} a {lote_sug_max}", "Zona de Aceleração", "#00FF88", border_color="#00FF88")

    # --- RENDERIZAÇÃO DOS GRÁFICOS (Layout v250 Adaptado) ---
    st.markdown("### 📈 Evolução Financeira")
    
    g1, g2 = st.columns([2, 1])
    with g1:
        # Gráfico de Equity
        if sel_grupo == "Todos":
            saldo_inicial_plot = df_contas['saldo_inicial'].sum() if not df_contas.empty else 0
        else:
            saldo_inicial_plot = df_contas[df_contas['grupo_nome'] == sel_grupo]['saldo_inicial'].sum() if not df_contas.empty else 0
            
        # Fallback se não tiver contas cadastradas
        if saldo_inicial_plot == 0: saldo_inicial_plot = 0
            
        df_filtered = df_filtered.sort_values('created_at')
        df_filtered['equity_curve'] = df_filtered['resultado'].cumsum() + saldo_inicial_plot
        
        fig_eq = px.area(df_filtered, x='created_at', y='equity_curve', title="Curva de Patrimônio", template="plotly_dark")
        fig_eq.update_traces(line_color='#00FF88', fillcolor='rgba(0, 255, 136, 0.1)')
        fig_eq.add_hline(y=saldo_inicial_plot, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_eq, use_container_width=True)

    with g2:
        # Gráfico por Contexto
        ctx_perf = df_filtered.groupby('contexto')['resultado'].sum().reset_index()
        fig_bar = px.bar(ctx_perf, x='contexto', y='resultado', title="Resultado por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
        st.plotly_chart(fig_bar, use_container_width=True)
