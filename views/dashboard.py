import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from supabase import create_client

# IMPORTANTE: Importando seus novos motores matemáticos
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
            if 'conta_id' not in df.columns: df['conta_id'] = 'Geral' # Caso não tenha coluna, assume geral
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
    
    # Carrega dados crus
    df_trades_all = load_trades_db()
    df_contas_all = load_contas_config(user)
    
    # Filtra trades do usuário
    if not df_trades_all.empty:
        df_trades_all = df_trades_all[df_trades_all['usuario'] == user]

    # --- TOP BAR: SELEÇÃO DE ESCOPO (O "Pulo do Gato") ---
    # Aqui resolvemos a questão de ver o Grupo ou a Conta Individual
    
    st.markdown("### 🔭 Visão do Operacional")
    
    # 1. Seleciona o Grupo
    grupos_disponiveis = ["Todos"]
    if not df_contas_all.empty:
        grupos_disponiveis = sorted(list(df_contas_all['grupo_nome'].unique()))
    
    c_sel1, c_sel2, c_date1, c_date2 = st.columns([1.5, 1.5, 1, 1])
    
    with c_sel1:
        grupo_sel = st.selectbox("📂 Selecionar Grupo", grupos_disponiveis)
    
    # 2. Seleciona a Conta (Depende do Grupo)
    contas_do_grupo = []
    if not df_contas_all.empty:
        if grupo_sel != "Todos":
            contas_do_grupo = df_contas_all[df_contas_all['grupo_nome'] == grupo_sel]
        else:
            contas_do_grupo = df_contas_all
            
    lista_contas_view = ["📊 VISÃO GERAL (Agregado)"] + sorted(list(contas_do_grupo['conta_identificador'].unique()))
    
    with c_sel2:
        view_mode = st.selectbox("🔎 Detalhe", lista_contas_view)

    # 3. Filtros de Data
    with c_date1:
        d_inicio = st.date_input("De", datetime.now().date() - timedelta(days=30))
    with c_date2:
        d_fim = st.date_input("Até", datetime.now().date())

    st.markdown("---")

    # --- PROCESSAMENTO DOS DADOS (AGREGAÇÃO) ---
    
    # 1. Filtra Trades pelo Grupo e Data
    trades_filtered = df_trades_all.copy()
    if grupo_sel != "Todos":
        trades_filtered = trades_filtered[trades_filtered['grupo_vinculo'] == grupo_sel]
        
    trades_filtered = trades_filtered[
        (trades_filtered['data'] >= d_inicio) & 
        (trades_filtered['data'] <= d_fim)
    ]
    
    # 2. Determina quais contas analisar
    if "VISÃO GERAL" in view_mode:
        # Modo Grupo: Analisa TODAS as contas do grupo selecionado
        contas_alvo = contas_do_grupo
        # Trades já estão filtrados pelo grupo acima
    else:
        # Modo Individual: Analisa só a conta específica
        contas_alvo = contas_do_grupo[contas_do_grupo['conta_identificador'] == view_mode]
        # Filtra trades só dessa conta (supondo que exista coluna conta_id ou identificador no trade)
        # Se não tiver coluna conta_id no trade, o filtro por grupo é o melhor que temos por enquanto.
        # Ajuste conforme seu DB real.
        pass 

    # --- CÁLCULO FINANCEIRO E APEX (LOOP INTELIGENTE) ---
    
    total_buffer = 0.0
    soma_saldos = 0.0
    total_risco_base = 0.0
    contas_ativas = 0
    
    # Itera sobre cada conta para calcular o buffer individualmente (Regra: 150k cada)
    # Depois soma tudo para dar a visão do grupo
    if not contas_alvo.empty:
        for _, conta in contas_alvo.iterrows():
            if conta['status_conta'] == 'Ativa':
                # Pega trades "deste grupo/conta" para calcular o saldo atual dela
                # Nota: Na v300 idealmente cada trade tem 'conta_id'. 
                # Se não tiver, usamos o proporcional ou assumimos simetria.
                # Aqui usaremos a lógica simplificada: Saldo Atual = Saldo Inicial + Lucro do Grupo (se for visão grupo)
                # Para ser EXATO, precisaria filtrar trades por conta_id.
                
                # Simulação para o Motor (Assumindo simetria se não tiver ID):
                # Se estamos vendo o grupo todo, o "Saldo Atual" desta conta é estimado
                # Se seu DB de trades não separa por conta individual, o Buffer será uma estimativa baseada no total.
                
                # Abordagem Robusta:
                # O Motor Apex precisa de (Saldo Atual, HWM).
                # Vamos calcular o Saldo Atual real somando o lucro.
                saldo_ini = float(conta['saldo_inicial'])
                hwm_prev = float(conta['pico_previo'])
                
                # Se for visão individual, filtra trades dessa conta (se possível)
                # Se for visão geral, o lucro é rateado ou somado? 
                # Assumindo CopyTrading: O lucro total do grupo dividido pelo num contas = lucro desta conta.
                
                lucro_total_periodo = trades_filtered['resultado'].sum()
                num_contas_grupo = len(contas_do_grupo) if len(contas_do_grupo) > 0 else 1
                lucro_desta_conta = lucro_total_periodo / num_contas_grupo # Estimativa de Copy
                
                saldo_atual_est = saldo_ini + lucro_desta_conta
                
                # CHAMA O MOTOR APEX (Importado do logic.py)
                saude = ApexEngine.calculate_health(saldo_atual_est, hwm_prev)
                
                total_buffer += saude['buffer']
                soma_saldos += saude['saldo']
                contas_ativas += 1
                
                # Soma HWM apenas para referência
                # hwm_grupo += saude['hwm']

    # Se não tiver contas, zera tudo
    if contas_ativas == 0:
        total_buffer = 0
        soma_saldos = 0

    # --- CÁLCULOS ESTATÍSTICOS (KPIs) ---
    wins = trades_filtered[trades_filtered['resultado'] > 0]
    losses = trades_filtered[trades_filtered['resultado'] < 0]
    
    net_profit = trades_filtered['resultado'].sum()
    gross_profit = wins['resultado'].sum()
    gross_loss = abs(losses['resultado'].sum())
    
    pf = gross_profit / gross_loss if gross_loss > 0 else 99.99
    win_rate = (len(wins) / len(trades_filtered) * 100) if not trades_filtered.empty else 0.0
    
    avg_win = wins['resultado'].mean() if not wins.empty else 0
    avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0
    payoff = avg_win / avg_loss if avg_loss > 0 else 0
    
    # Expectativa Matemática ($)
    expectancy = ( (win_rate/100) * avg_win ) - ( (1 - (win_rate/100)) * avg_loss )

    # Risco Comportamental (Baseado nos Stops tomados)
    pts_loss_medio = abs(losses['pts_medio'].mean()) if not losses.empty else 15.0
    ativo_ref = trades_filtered['ativo'].iloc[-1] if not trades_filtered.empty else "MNQ"
    custo_stop_padrao = pts_loss_medio * MULTIPLIERS.get(ativo_ref, 2) 
    
    # O Risco "Unitário" para o grupo é o custo do stop x número de contas ativas (pois o copy replica)
    # Se stopou em uma, stopou em todas.
    risco_impacto_grupo = custo_stop_padrao * contas_ativas
    if risco_impacto_grupo == 0: risco_impacto_grupo = 1.0 # Evita div zero

    # --- CHAMADA AOS MOTORES DE RISCO E KELLY ---
    
    # 1. Vidas Reais (Quantos stops o GRUPO aguenta antes de ALGUMA conta quebrar)
    # Como somamos os buffers, e o risco é replicado, a divisão se mantém proporcional.
    vidas_u = total_buffer / risco_impacto_grupo if risco_impacto_grupo > 0 else 0
    
    # 2. Probabilidade de Ruína (RiskEngine)
    prob_ruina = RiskEngine.calculate_ruin(win_rate, avg_win, avg_loss, total_buffer)
    
    # 3. Sugestão de Lote (PositionSizing)
    # Aqui ele sugere o lote TOTAL para o grupo.
    # Ex: Se buffer é 50k, ele sugere lote para proteger 50k.
    # Como você opera via Copy, esse lote será distribuído.
    lote_min, lote_max, kelly_pct = PositionSizing.calculate_limits(win_rate, payoff, total_buffer, custo_stop_padrao * contas_ativas)

    # --- RENDERIZAÇÃO VISUAL ---

    # Linha 1: Financeiro
    st.markdown("### 🏁 Desempenho Financeiro")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Resultado Líquido", f"${net_profit:,.2f}", f"Soma do Período", "#00FF88" if net_profit>=0 else "#FF4B4B")
    with c2:
        card("Fator de Lucro (PF)", f"{pf:.2f}", "Ideal > 1.5", "#FF4B4B" if pf < 1.5 else "#00FF88")
    with c3:
        card("Win Rate", f"{win_rate:.1f}%", f"{len(wins)}W / {len(losses)}L", "white")
    with c4:
        card("Expectativa", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy>0 else "#FF4B4B")

    # Linha 2: Sobrevivência (Dados dos Motores)
    st.markdown(f"### 🛡️ Saúde & Risco ({view_mode})")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        card("Buffer Total (Oxigênio)", f"${total_buffer:,.0f}", f"{contas_ativas} Contas Ativas", "#00FF88" if total_buffer > 2000 else "#FF4B4B")
    with k2:
        # Cor dinâmica para Vidas
        cor_v = "#FF4B4B" if vidas_u < 10 else ("#FFFF00" if vidas_u < 20 else "#00FF88")
        card("Vidas (Tentativas)", f"{vidas_u:.1f}", f"Risco Impacto: ${risco_impacto_grupo:,.0f}", cor_v)
    with k3:
        # Cor dinâmica para Ruína
        cor_r = "#00FF88" if prob_ruina < 1 else ("#FF4B4B" if prob_ruina > 5 else "#FFFF00")
        card("Prob. Ruína", f"{prob_ruina:.2f}%", "Chance de Quebrar", cor_r, border_color=cor_r)
    with k4:
        card("Sugestão Lote (Grupo)", f"{lote_min} a {lote_max}", f"Kelly: {kelly_pct*100:.1f}%", "#00FF88", border_color="#00FF88")

    # --- GRÁFICOS ---
    st.markdown("### 📈 Evolução de Capital")
    
    g1, g2 = st.columns([3, 1])
    
    with g1:
        if not trades_filtered.empty:
            trades_plot = trades_filtered.sort_values('created_at').copy()
            
            # Ajuste do Eixo Y (Saldo Base)
            # Se for Geral: Soma dos Saldos Iniciais de todas as contas do grupo
            # Se for Individual: Saldo Inicial da conta
            saldo_inicial_base = contas_alvo['saldo_inicial'].sum() if not contas_alvo.empty else 0
            
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
            df_pie = trades_filtered.groupby('resultado').count() # Simplificado
            fig_pie = go.Figure(data=[go.Pie(labels=['Gain', 'Loss'], values=[len(wins), len(losses)], hole=.6)])
            fig_pie.update_layout(template="plotly_dark", title="Proporção W/L", showlegend=False)
            fig_pie.update_traces(marker=dict(colors=['#00FF88', '#FF4B4B']))
            st.plotly_chart(fig_pie, use_container_width=True)
