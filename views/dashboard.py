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

# --- TOOLTIPS: Explicações claras para cada métrica ---
TOOLTIPS = {
    "resultado_liquido": "Soma de todos os seus ganhos menos todas as perdas no período selecionado. É o dinheiro real que você ganhou ou perdeu.",
    "fator_lucro": "Quanto você ganha para cada $1 que perde. Ex: PF 1.70 = você ganha $1.70 para cada $1 perdido. Ideal: acima de 1.5",
    "win_rate": "Porcentagem de trades que terminaram em lucro. Ex: 71% = de cada 100 trades, 71 foram gains.",
    "expectativa": "Quanto você espera ganhar EM MÉDIA por trade. É o valor que, estatisticamente, cada trade deve render.",
    "media_gain": "Valor médio dos seus trades positivos. Quanto você ganha, em média, quando acerta.",
    "media_loss": "Valor médio dos seus trades negativos. Quanto você perde, em média, quando erra.",
    "payoff": "Razão entre ganho médio e perda média. Ex: 1:0.69 significa que seu gain médio é 0.69x seu loss médio.",
    "drawdown": "Maior queda do seu saldo desde um pico até um vale. Mostra o pior momento da sua curva.",
    "pts_gain": "Média de pontos capturados nos trades positivos. Mostra sua eficiência técnica nos gains.",
    "stop_medio": "Média de pontos perdidos nos trades negativos. É a base para calcular seu risco real.",
    "lote_medio": "Quantidade média de contratos operados por trade.",
    "total_trades": "Quantidade total de operações realizadas no período filtrado.",
    "z_score_serial": "Mede se seus resultados são aleatórios ou têm padrão. Positivo = tendência a alternar W/L. Negativo = tendência a sequências.",
    "z_score_edge": "Mede sua vantagem estatística. Positivo = você tem edge. Negativo = o mercado tem vantagem sobre você.",
    "vidas": "Quantos stops você aguenta antes de zerar o buffer. Ex: 10.1 vidas = você pode tomar 10 stops seguidos.",
    "prob_ruina": "Probabilidade matemática de você quebrar a conta. Baseado no seu histórico. Ideal: abaixo de 1%.",
    "buffer": "Dinheiro disponível entre seu saldo atual e o stop da conta. É seu 'oxigênio' para operar.",
    "half_kelly": "Percentual do buffer que você deveria arriscar por trade, segundo o critério de Kelly (versão conservadora).",
    "risco_financeiro": "Valor em dólares que você deveria arriscar por trade, baseado no Half-Kelly.",
    "sugestao_lote": "Faixa de contratos recomendada para operar, baseada no seu buffer e risco calculado."
}

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

def load_metas_config(user):
    """Carrega configuracao de metas por grupo"""
    try:
        sb = get_supabase()
        res = sb.table("metas_config").select("*").eq("usuario", user).execute()
        return {m['grupo_nome']: m for m in res.data} if res.data else {}
    except:
        return {}

def get_meta_grupo(user, grupo_nome, metas_dict):
    """Retorna meta do grupo ou default 500"""
    if grupo_nome in metas_dict:
        return float(metas_dict[grupo_nome].get('meta_semanal', 500))
    return 500.0

def get_semana_atual():
    """Retorna inicio e fim da semana de trading (domingo a sexta)"""
    hoje = datetime.now().date()
    
    # weekday(): seg=0, ter=1, qua=2, qui=3, sex=4, sab=5, dom=6
    dia_semana = hoje.weekday()
    
    if dia_semana == 5:  # Sabado - mostra semana que acabou
        inicio_semana = hoje - timedelta(days=6)  # Domingo anterior
        fim_semana = hoje - timedelta(days=1)     # Sexta anterior
    elif dia_semana == 6:  # Domingo - nova semana comeca hoje
        inicio_semana = hoje
        fim_semana = hoje + timedelta(days=5)     # Sexta
    else:  # Segunda a Sexta
        dias_desde_domingo = dia_semana + 1
        inicio_semana = hoje - timedelta(days=dias_desde_domingo)
        fim_semana = inicio_semana + timedelta(days=5)  # Sexta
    
    return inicio_semana, fim_semana

def calcular_resultado_semana(df_trades, grupo_nome, inicio_semana, fim_semana):
    """Calcula resultado da semana para um grupo"""
    if df_trades.empty:
        return 0.0
    
    df_grupo = df_trades[df_trades['grupo_vinculo'] == grupo_nome]
    if df_grupo.empty:
        return 0.0
    
    df_semana = df_grupo[(df_grupo['data'] >= inicio_semana) & (df_grupo['data'] <= fim_semana)]
    return df_semana['resultado'].sum()

def salvar_meta_grupo(user, grupo_nome, meta_valor, bloquear):
    """Salva configuracao de meta para um grupo"""
    sb = get_supabase()
    dados = {
        "usuario": user,
        "grupo_nome": grupo_nome,
        "meta_semanal": meta_valor,
        "bloquear_ao_bater": bloquear
    }
    sb.table("metas_config").upsert(dados).execute()

def verificar_meta_batida(user, grupo_nome):
    """Verifica se a meta semanal do grupo foi batida - usado pelo trade.py"""
    try:
        df_trades = load_trades_db()
        if not df_trades.empty:
            df_trades = df_trades[df_trades['usuario'] == user]
        
        metas = load_metas_config(user)
        meta = get_meta_grupo(user, grupo_nome, metas)
        
        inicio, fim = get_semana_atual()
        resultado = calcular_resultado_semana(df_trades, grupo_nome, inicio, fim)
        
        bloquear = metas.get(grupo_nome, {}).get('bloquear_ao_bater', False)
        
        return {
            "batida": resultado >= meta,
            "resultado": resultado,
            "meta": meta,
            "bloquear": bloquear,
            "faltam": max(0, meta - resultado)
        }
    except:
        return {"batida": False, "resultado": 0, "meta": 500, "bloquear": False, "faltam": 500}

def render_metas_semanais(user, df_trades, grupos_lista):
    """Renderiza a secao de metas semanais"""
    
    inicio_semana, fim_semana = get_semana_atual()
    metas_dict = load_metas_config(user)
    
    # CSS para os cards de meta
    st.markdown("""
        <style>
        .meta-container {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .meta-card {
            background-color: #111;
            border: 1px solid #333;
            border-radius: 10px;
            padding: 15px;
            flex: 1;
            min-width: 200px;
            position: relative;
        }
        .meta-card.batida {
            border-color: #00FF88;
            background: linear-gradient(135deg, #0a1a0a 0%, #111 100%);
        }
        .meta-card.batida::after {
            content: "META BATIDA";
            position: absolute;
            top: 10px;
            right: 10px;
            background: #00FF88;
            color: #000;
            font-size: 9px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .meta-grupo {
            font-size: 12px;
            color: #888;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .meta-valores {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .meta-barra-bg {
            background-color: #222;
            border-radius: 4px;
            height: 8px;
            overflow: hidden;
        }
        .meta-barra-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        .meta-status {
            font-size: 11px;
            margin-top: 8px;
        }
        .meta-pare {
            background-color: #B20000;
            color: white;
            font-size: 11px;
            font-weight: 700;
            padding: 5px 10px;
            border-radius: 4px;
            margin-top: 10px;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header da secao
    col_header, col_config = st.columns([3, 1])
    with col_header:
        st.markdown(f"### 🎯 Metas Semanais ({inicio_semana.strftime('%d/%m')} - {fim_semana.strftime('%d/%m')})")
    with col_config:
        if st.button("⚙️ Configurar Metas", use_container_width=True):
            st.session_state["show_config_metas"] = True
    
    # Modal de configuracao
    if st.session_state.get("show_config_metas", False):
        with st.expander("Configurar Metas por Grupo", expanded=True):
            for grupo in grupos_lista:
                if grupo == "Todos":
                    continue
                col_g, col_m, col_b = st.columns([2, 1.5, 1])
                meta_atual = get_meta_grupo(user, grupo, metas_dict)
                bloquear_atual = metas_dict.get(grupo, {}).get('bloquear_ao_bater', False)
                
                with col_g:
                    st.markdown(f"**{grupo}**")
                with col_m:
                    nova_meta = st.number_input(f"Meta {grupo}", value=meta_atual, min_value=100.0, step=100.0, label_visibility="collapsed", key=f"meta_{grupo}")
                with col_b:
                    bloquear = st.checkbox("Bloquear", value=bloquear_atual, key=f"bloq_{grupo}", help="Bloquear trades quando bater")
                
                if nova_meta != meta_atual or bloquear != bloquear_atual:
                    salvar_meta_grupo(user, grupo, nova_meta, bloquear)
            
            if st.button("Fechar"):
                st.session_state["show_config_metas"] = False
                st.rerun()
    
    # Cards de cada grupo
    grupos_validos = [g for g in grupos_lista if g != "Todos"]
    
    if not grupos_validos:
        st.info("Nenhum grupo configurado ainda.")
        return
    
    # Calcula dados de cada grupo
    dados_grupos = []
    for grupo in grupos_validos:
        resultado = calcular_resultado_semana(df_trades, grupo, inicio_semana, fim_semana)
        meta = get_meta_grupo(user, grupo, metas_dict)
        batida = resultado >= meta
        progresso = min(100, (resultado / meta * 100)) if meta > 0 else 0
        faltam = max(0, meta - resultado)
        
        dados_grupos.append({
            "grupo": grupo,
            "resultado": resultado,
            "meta": meta,
            "batida": batida,
            "progresso": progresso,
            "faltam": faltam
        })
    
    # Renderiza cards
    cols = st.columns(len(dados_grupos))
    
    for i, dados in enumerate(dados_grupos):
        with cols[i]:
            classe_batida = "batida" if dados['batida'] else ""
            cor_valor = "#00FF88" if dados['resultado'] >= 0 else "#FF4B4B"
            cor_barra = "#00FF88" if dados['batida'] else ("#FFD700" if dados['progresso'] >= 50 else "#666")
            
            # Status text
            if dados['batida']:
                status_html = '<div class="meta-pare">PARE DE OPERAR ESTE GRUPO</div>'
            else:
                status_html = f'<div class="meta-status" style="color: #888;">Faltam <b style="color: #FFD700;">${dados["faltam"]:,.0f}</b></div>'
            
            html_card = f'<div class="meta-card {classe_batida}"><div class="meta-grupo">{dados["grupo"]}</div><div class="meta-valores"><span style="color: {cor_valor};">${dados["resultado"]:,.0f}</span><span style="color: #444;"> / </span><span style="color: #888;">${dados["meta"]:,.0f}</span></div><div class="meta-barra-bg"><div class="meta-barra-fill" style="width: {dados["progresso"]:.0f}%; background-color: {cor_barra};"></div></div>{status_html}</div>'
            
            st.markdown(html_card, unsafe_allow_html=True)
    
    st.markdown("---")

def card_simples(label, value, sub_text, tooltip_text, color="white", border_color="#333333"):
    """Card com tooltip apenas no icone de informacao"""
    import hashlib
    uid = hashlib.md5(label.encode()).hexdigest()[:6]
    
    html = f'''
        <style>
            .card-{uid} {{
                background-color: #161616; 
                padding: 15px; 
                border-radius: 8px; 
                border: 1px solid {border_color}; 
                text-align: center; 
                margin-bottom: 10px;
                height: 100px; 
                display: flex; 
                flex-direction: column; 
                justify-content: center;
                position: relative;
            }}
            .card-{uid} .info-wrapper {{
                display: inline-block;
                position: relative;
            }}
            .card-{uid} .info-icon {{
                color: #555;
                cursor: help;
                font-size: 11px;
                margin-left: 4px;
                padding: 2px 5px;
                border-radius: 50%;
                background: #222;
            }}
            .card-{uid} .info-icon:hover {{
                color: #fff;
                background: #B20000;
            }}
            .card-{uid} .tooltip-text {{
                visibility: hidden;
                opacity: 0;
                position: absolute;
                bottom: 120%;
                left: 50%;
                transform: translateX(-50%);
                background: #000;
                color: #fff;
                padding: 10px 12px;
                border-radius: 6px;
                font-size: 11px;
                width: 200px;
                text-align: center;
                z-index: 9999;
                border: 1px solid #B20000;
                line-height: 1.4;
                transition: opacity 0.2s;
            }}
            .card-{uid} .tooltip-text::after {{
                content: "";
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: #B20000 transparent transparent transparent;
            }}
            .card-{uid} .info-wrapper:hover .tooltip-text {{
                visibility: visible;
                opacity: 1;
            }}
        </style>
        <div class="card-{uid}">
            <div style="color: #888; font-size: 10px; text-transform: uppercase; margin-bottom: 4px;">
                {label}
                <span class="info-wrapper">
                    <span class="info-icon">?</span>
                    <span class="tooltip-text">{tooltip_text}</span>
                </span>
            </div>
            <h2 style="color: {color}; margin: 0; font-size: 20px; font-weight: 600;">{value}</h2>
            <p style="color: #666; font-size: 10px; margin-top: 4px;">{sub_text}</p>
        </div>
    '''
    st.markdown(html, unsafe_allow_html=True)

def show(user, role):
    df_trades_all = load_trades_db()
    df_contas_all = load_contas_config(user)
    
    if not df_trades_all.empty:
        df_trades_all = df_trades_all[df_trades_all['usuario'] == user]

    # --- SECAO DE METAS SEMANAIS ---
    grupos_disponiveis = ["Todos"]
    if not df_contas_all.empty:
        grupos_disponiveis += sorted(list(df_contas_all['grupo_nome'].unique()))
    
    render_metas_semanais(user, df_trades_all, grupos_disponiveis)
    
    # --- VISAO DO OPERACIONAL ---
    st.markdown("### 🔭 Visão do Operacional")
    
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
        lucro_total = 0.0
        if not df_trades.empty:
            if 'conta_id' in df_trades.columns:
                trades_individuais = df_trades[df_trades['conta_id'] == conta_id]
                lucro_total += trades_individuais['resultado'].sum()
                trades_replicados = df_trades[
                    (df_trades['grupo_vinculo'] == grupo_nome) & 
                    (df_trades['conta_id'].isna())
                ]
                lucro_total += trades_replicados['resultado'].sum()
            else:
                trades_grupo = df_trades[df_trades['grupo_vinculo'] == grupo_nome]
                lucro_total = trades_grupo['resultado'].sum()
        return lucro_total

    total_buffer = 0.0; contas_ativas = 0; hwm_updated_flag = False
    if not contas_alvo.empty:
        for _, conta in contas_alvo.iterrows():
            if conta['status_conta'] == 'Ativa':
                lucro_conta = calcular_lucro_conta(conta['id'], conta['grupo_nome'], trades_full_risk)
                saldo_atual_est = float(conta['saldo_inicial']) + lucro_conta
                hwm_dinamico = max(float(conta['pico_previo']), saldo_atual_est)
                if hwm_dinamico > float(conta['pico_previo']):
                    update_hwm(conta['id'], hwm_dinamico); hwm_updated_flag = True
                saude = ApexEngine.calculate_health(saldo_atual_est, hwm_dinamico, conta.get('fase_entrada', 'Fase 1'))
                total_buffer += saude['buffer']; contas_ativas += 1
    
    if hwm_updated_flag: st.toast("🚀 Novo Topo Histórico Salvo!", icon="💾")

    results_list_filtered = trades_filtered_view['resultado'].tolist() if not trades_filtered_view.empty else []

    # Inicialização segura
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
    pts_loss_medio_real = 15.0
    lote_medio = 0.0
    max_dd = 0.0
    wins = pd.DataFrame()
    losses = pd.DataFrame()
    ativo_ref = "MNQ"

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
    prob_ruina = RiskEngine.calculate_ruin(win_rate, avg_win, avg_loss, total_buffer, trades_results=results_list_filtered)
    
    loss_rate_dec = (len(losses)/total_trades) if total_trades > 0 else 0
    edge_calc = ((win_rate/100) * payoff) - loss_rate_dec
    lote_min, lote_max, kelly_pct = PositionSizing.calculate_limits(win_rate, payoff, total_buffer, custo_stop_padrao)

    # ============================================================
    # RENDERIZAÇÃO COM TOOLTIPS
    # ============================================================
    
    st.markdown("### 🏁 Desempenho Geral")
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        card_simples("Resultado Líquido", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f} / -${gross_loss:,.0f}", 
                     TOOLTIPS["resultado_liquido"], "#00FF88" if net_profit>=0 else "#FF4B4B")
    with c2: 
        card_simples("Fator de Lucro (PF)", f"{pf:.2f}", "Ideal > 1.5", 
                     TOOLTIPS["fator_lucro"], "#FF4B4B" if pf < 1.5 else "#00FF88")
    with c3: 
        card_simples("Win Rate", f"{win_rate:.1f}%", f"{len(wins)}W / {len(losses)}L", 
                     TOOLTIPS["win_rate"], "white")
    with c4: 
        card_simples("Expectativa Mat.", f"${expectancy:.2f}", "Por Trade", 
                     TOOLTIPS["expectativa"], "#00FF88" if expectancy>0 else "#FF4B4B")

    st.markdown("### 💲 Médias Financeiras")
    m1, m2, m3, m4 = st.columns(4)
    with m1: 
        card_simples("Média Gain ($)", f"${avg_win:,.2f}", "", 
                     TOOLTIPS["media_gain"], "#00FF88")
    with m2: 
        card_simples("Média Loss ($)", f"-${avg_loss:,.2f}", "", 
                     TOOLTIPS["media_loss"], "#FF4B4B")
    with m3: 
        card_simples("Risco : Retorno", f"1 : {payoff:.2f}", "Payoff Real", 
                     TOOLTIPS["payoff"], "white")
    with m4: 
        card_simples("Drawdown Máximo", f"${max_dd:,.2f}", "Pior Queda", 
                     TOOLTIPS["drawdown"], "#FF4B4B")
    
    st.markdown("### 🎯 Performance Técnica")
    t1, t2, t3, t4 = st.columns(4)
    with t1: 
        card_simples("Pts Médios (Gain)", f"{avg_pts_gain:.2f} pts", "", 
                     TOOLTIPS["pts_gain"], "#00FF88")
    with t2: 
        card_simples("Stop Médio (Real)", f"{pts_loss_medio_real:.2f} pts", "Base do Risco", 
                     TOOLTIPS["stop_medio"], "#FF4B4B")
    with t3: 
        card_simples("Lote Médio", f"{lote_medio:.1f}", "Contratos", 
                     TOOLTIPS["lote_medio"], "white")
    with t4: 
        card_simples("Total Trades", f"{total_trades}", "Executados", 
                     TOOLTIPS["total_trades"], "white")

    st.markdown("---")

    st.markdown(f"### 🛡️ Análise de Sobrevivência ({view_mode})")
    k1, k2, k3, k4 = st.columns(4)
    
    num_trades_risco = len(results_list_filtered)
    z_serial = RiskEngine.calculate_z_score_serial(results_list_filtered)
    
    if num_trades_risco < 15:
        cor_zs = "#888888"; val_zs = "---"; sub_zs = "Mín. 15 trades"
    elif num_trades_risco < 30:
        cor_zs = "#FFFF00"; val_zs = f"{z_serial:.2f}"; sub_zs = f"Calibrando ({num_trades_risco}/30)"
    else:
        cor_zs = "#00FF88" if z_serial > 0 else "#FF4B4B"
        val_zs = f"{z_serial:.2f}"; sub_zs = "Consistência OK"

    with k1: 
        card_simples("Z-Score (Sequência)", val_zs, sub_zs, 
                     TOOLTIPS["z_score_serial"], cor_zs, border_color=cor_zs)

    if num_trades_risco < 15:
        cor_ze = "#888888"; val_ze = "---"; sub_ze = "Mín. 15 trades"
    else:
        cor_ze = "#00FF88" if edge_calc > 0 else "#FF4B4B"
        val_ze = f"{edge_calc:.4f}"; sub_ze = "Vantagem" if edge_calc > 0 else "Sem Edge"

    with k2: 
        card_simples("Z-Score (Edge)", val_ze, sub_ze, 
                     TOOLTIPS["z_score_edge"], cor_ze, border_color=cor_ze)
    
    cor_v = "#FF4B4B" if vidas_u < 10 else ("#FFFF00" if vidas_u < 20 else "#00FF88")
    with k3: 
        card_simples("Vidas Reais (U)", f"{vidas_u:.1f}", f"Risco: ${custo_stop_padrao:,.0f}", 
                     TOOLTIPS["vidas"], cor_v)
    
    cor_r = "#00FF88" if prob_ruina < 1 else ("#FF4B4B" if prob_ruina > 5 else "#FFFF00")
    with k4: 
        card_simples("Prob. Ruína", f"{prob_ruina:.4f}%", "Risco de Quebra", 
                     TOOLTIPS["prob_ruina"], cor_r, border_color=cor_r)

    st.markdown("### 🧠 Inteligência de Lote (Faixa de Operação)")
    l1, l2, l3, l4 = st.columns(4)
    
    with l1:
        if total_buffer > 2500: cor_buf_lote = "#00FF88"
        elif total_buffer > 1000: cor_buf_lote = "#FFFF00"
        else: cor_buf_lote = "#FF4B4B"
        card_simples("Buffer Disponível", f"${total_buffer:,.0f}", "Base p/ Lote", 
                     TOOLTIPS["buffer"], cor_buf_lote, border_color=cor_buf_lote)

    with l2: 
        card_simples("Half-Kelly", f"{kelly_pct*100:.1f}%", "Aproveitamento", 
                     TOOLTIPS["half_kelly"], "#888")
    with l3: 
        card_simples("Risco Financeiro", f"${total_buffer * kelly_pct:,.0f}", "Alocação Sugerida", 
                     TOOLTIPS["risco_financeiro"], "#00FF88")
    with l4: 
        card_simples("Sugestão de Lote", f"{lote_min} a {lote_max} ctrs", "ZONA SEGURA", 
                     TOOLTIPS["sugestao_lote"], "#00FF88", border_color="#00FF88")

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
