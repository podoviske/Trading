import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
import json
import time

# Configuração da Página
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    @keyframes blinking {
        0% { background-color: #440000; }
        50% { background-color: #B20000; }
        100% { background-color: #440000; }
    }
    .piscante-erro {
        padding: 15px; border-radius: 5px; color: white; font-weight: bold;
        text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000;
        margin-top: 10px;
    }
    .logo-container { padding: 20px 15px; display: flex; flex-direction: column; }
    .logo-main { color: #B20000; font-size: 26px; font-weight: 900; line-height: 1; }
    .logo-sub { color: white; font-size: 22px; font-weight: 700; margin-top: -5px; }
    
    .stButton > button { width: 100%; }
    .stButton > button[kind="secondary"] {
        color: #FF4B4B !important; border: 1px solid #FF4B4B !important; background: transparent !important;
    }
    /* Estilização para o segmented_control para parecer com a imagem */
    div[data-testid="stSegmentedControl"] button {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background-color: #B20000 !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- PERSISTÊNCIA ---
CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

def load_atm():
    if os.path.exists(ATM_FILE):
        try:
            with open(ATM_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"Personalizado": {"lote": 0, "stop": 0.0, "parciais": []}}

def save_atm(configs):
    with open(ATM_FILE, 'w') as f: json.dump(configs, f)

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'ID' not in df.columns:
                df['ID'] = [f"ID_{int(time.time())}_{i}" for i in range(len(df))]
            for col in cols:
                if col not in df.columns: df[col] = 0
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

atm_db = load_atm()
df = load_data()

# --- ESTADO ---
if 'n_extras' not in st.session_state: st.session_state.n_extras = 0
if 'confirmar_limpeza' not in st.session_state: st.session_state.confirmar_limpeza = False

def on_atm_change():
    st.session_state.n_extras = 0

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="logo-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], styles={
            "nav-link-selected": {"background-color": "#B20000", "color": "white"}
        })

# --- PÁGINA: DASHBOARD ---
if selected == "Dashboard":
    st.title("📊 EvoTrade Analytics")
    if not df.empty:
        # 1. SELETOR ESTILO SEGMENTADO (Filtrar Visão)
        filtro_view = st.segmented_control(
            "Visualizar:",
            options=["Capital", "Contexto A", "Contexto B", "Contexto C"],
            default="Capital"
        )

        df_filtrado = df.copy()
        if filtro_view != "Capital":
            df_filtrado = df[df['Contexto'] == filtro_view]

        # 2. MÉTRICAS BASEADAS NO FILTRO
        total_trades = len(df_filtrado)
        wins = df_filtrado[df_filtrado['Resultado'] > 0]
        losses = df_filtrado[df_filtrado['Resultado'] < 0]
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        avg_win = wins['Resultado'].mean() if not wins.empty else 0
        avg_loss = losses['Resultado'].mean() if not losses.empty else 0
        total_pnl = df_filtrado['Resultado'].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("P&L Total", f"${total_pnl:,.2f}")
        m2.metric("Taxa de Acerto", f"{win_rate:.1f}%")
        m3.metric("Ganho Médio", f"${avg_win:,.2f}")
        m4.metric("Perda Média", f"${avg_loss:,.2f}")
        
        st.markdown("---")

        # 3. SELETOR DE EVOLUÇÃO (Tempo vs Trade)
        col_tipo, _ = st.columns([1, 2])
        tipo_grafico = col_tipo.radio("Visualizar evolução por:", ["Tempo (Data)", "Trade a Trade"], horizontal=True)

        # Preparação do gráfico suave (Spline)
        df_grafico = df_filtrado.sort_values('Data').reset_index(drop=True)
        df_grafico['Acumulado'] = df_grafico['Resultado'].cumsum()
        
        if tipo_grafico == "Tempo (Data)":
            x_axis = 'Data'
        else:
            df_grafico['Trade_Num'] = df_grafico.index + 1
            x_axis = 'Trade_Num'

        fig = px.area(df_grafico, x=x_axis, y='Acumulado', title=f"Curva de Capital - {filtro_view}", template="plotly_dark")
        fig.update_traces(
            line_color='#B20000', 
            line_shape='spline', 
            fillcolor='rgba(178, 0, 0, 0.2)', 
            mode='lines'
        )
        fig.update_layout(
            hovermode="x unified", yaxis_title="Acumulado ($)", xaxis_title=x_axis,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#1E1E1E'),
            margin=dict(l=0, r=0, t=50, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info("Nenhum dado encontrado para análise.")

# --- PÁGINA: REGISTRAR TRADE ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    c_topo1, c_topo2 = st.columns([3, 1])
    with c_topo1:
        atm_sel_nome = st.selectbox("🎯 Estratégia ATM", options=list(atm_db.keys()), key='atm_selecionado', on_change=on_atm_change)
        config = atm_db[atm_sel_nome]
    with c_topo2:
        st.write("") 
        cb1, cb2 = st.columns(2)
        cb1.button("➕", on_click=lambda: st.session_state.update({"n_extras": st.session_state.n_extras + 1}))
        cb2.button("🧹", on_click=lambda: st.rerun())

    st.markdown("---")
    key_prefix = atm_sel_nome.replace(" ", "_")
    c1, c2, c3 = st.columns([1, 1, 2.5])
    
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)

    with c2:
        lote_t = st.number_input("Contratos", min_value=0, step=1, value=int(config["lote"]), key=f"lote_{key_prefix}")
        stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]), key=f"stop_{key_prefix}")
        risco = stop_p * MULTIPLIERS[ativo] * lote_t
        if lote_t > 0: st.metric("Risco Total", f"${risco:,.2f}")

    with c3:
        st.write("**Saídas Executadas**")
        saidas = []; alocado = 0
        for i, p_config in enumerate(config["parciais"]):
            s1, s2 = st.columns(2)
            p = s1.number_input(f"Pts P{i+1}", key=f"p_atm_{i}_{key_prefix}", value=float(p_config[0]))
            q = s2.number_input(f"Qtd P{i+1}", key=f"q_atm_{i}_{key_prefix}", value=int(p_config[1]), step=1)
            saidas.append((p, q)); alocado += q
            
        for i in range(st.session_state.n_extras):
            idx = len(config["parciais"]) + i
            s1, s2 = st.columns(2)
            p = s1.number_input(f"Pts Extra {i+1}", key=f"p_ext_{idx}_{key_prefix}", value=0.0)
            q = s2.number_input(f"Qtd Extra {i+1}", key=f"q_ext_{idx}_{key_prefix}", value=0, step=1)
            saidas.append((p, q)); alocado += q
        
        if lote_t > 0:
            resta = lote_t - alocado
            if resta != 0:
                msg = f"FALTAM {resta} CONTRATOS" if resta > 0 else f"EXCESSO DE {abs(resta)} CONTRATOS"
                st.markdown(f'<div class="piscante-erro">{msg}</div>', unsafe_allow_html=True)
            else: st.success("✅ Posição Completa")

    st.markdown("---")
    r1, r2 = st.columns(2)
    with r1:
        if st.button("💾 REGISTRAR GAIN", use_container_width=True):
            if lote_t > 0 and alocado == lote_t:
                res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas])
                pts_m = sum([s[0] * s[1] for s in saidas]) / lote_t
                n_id = f"ID_{int(time.time())}"
                n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel_nome, 'Resultado': res, 'Pts_Medio': pts_m, 'Risco_Fin': risco, 'ID': n_id}])
                df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.success("🎯 Trade registrado com sucesso!"); time.sleep(1); st.rerun()
    with r2:
        if st.button("🚨 REGISTRAR STOP FULL", type="secondary", use_container_width=True):
            if lote_t > 0 and stop_p > 0:
                pre = -(stop_p * MULTIPLIERS[ativo] * lote_t)
                n_id = f"ID_{int(time.time())}"
                n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel_nome, 'Resultado': pre, 'Pts_Medio': -stop_p, 'Risco_Fin': risco, 'ID': n_id}])
                df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.error("🚨 Stop registrado com sucesso!"); time.sleep(1); st.rerun()

# --- PÁGINA: CONFIGURAR ATM ---
elif selected == "Configurar ATM":
    st.title("⚙️ Editor de Estratégias ATM")
    with st.expander("✨ Criar Novo Template ATM", expanded=True):
        nome_novo = st.text_input("Nome da Estratégia")
        ca1, ca2 = st.columns(2)
        l_p = ca1.number_input("Lote Total", min_value=1, step=1)
        s_p = ca2.number_input("Stop (Pts)", min_value=0.0, step=0.25)
        n_p = st.number_input("Número de Alvos", 1, 6, 1)
        novas_p = []
        for i in range(n_p):
            cp1, cp2 = st.columns(2)
            pt = cp1.number_input(f"Alvo P{i+1} (Pts)", key=f"conf_pts_{i}", value=0.0)
            qt = cp2.number_input(f"Contratos P{i+1}", key=f"conf_qtd_{i}", min_value=1, step=1)
            novas_p.append([pt, qt])
        if st.button("💾 Salvar Estratégia"):
            if nome_novo:
                atm_db[nome_novo] = {"lote": l_p, "stop": s_p, "parciais": novas_p}
                save_atm(atm_db); st.success("Estratégia salva!"); st.rerun()
    st.markdown("---")
    for nome in list(atm_db.keys()):
        if nome != "Personalizado":
            col_n, col_b = st.columns([4, 1])
            col_n.write(f"**{nome}**")
            if col_b.button("Excluir Estratégia", key=f"del_{nome}"):
                del atm_db[nome]; save_atm(atm_db); st.rerun()

# --- PÁGINA: HISTÓRICO ---
elif selected == "Histórico":
    st.title("📜 Histórico de Trades")
    if not df.empty:
        col_export, col_limpar = st.columns([4, 1])
        csv_data = df.to_csv(index=False).encode('utf-8')
        col_export.download_button("📥 Backup Completo (CSV)", data=csv_data, file_name="backup_trades.csv")
        
        if not st.session_state.confirmar_limpeza:
            if col_limpar.button("🗑️ LIMPAR TUDO", type="secondary"):
                st.session_state.confirmar_limpeza = True
                st.rerun()
        else:
            with col_limpar:
                st.warning("Timer de Segurança...")
                ph = st.empty()
                for i in range(10, 0, -1):
                    ph.button(f"Confirmar em {i}s...", disabled=True, key=f"t_{i}")
                    time.sleep(1)
                ph.empty()
                c_sim, c_nao = st.columns(2)
                if c_sim.button("✅ SIM", type="primary"):
                    if os.path.exists(CSV_FILE): os.remove(CSV_FILE)
                    st.session_state.confirmar_limpeza = False
                    st.rerun()
                if c_nao.button("❌ NÃO"):
                    st.session_state.confirmar_limpeza = False
                    st.rerun()

        st.markdown("---")
        df_display = df.sort_values('Data', ascending=False)
        for index, row in df_display.iterrows():
            with st.expander(f"📅 {row['Data']} | {row['Ativo']} | {row['Direcao']} | Resultado: ${row['Resultado']:,.2f}"):
                c_info, c_del = st.columns([4, 1])
                with c_info:
                    st.write(f"**Lote:** {row['Lote']} | **ATM:** {row['ATM']} | **Contexto:** {row['Contexto']} | **Risco:** ${row['Risco_Fin']:,.2f}")
                with c_del:
                    if st.button("Deletar Trade", key=f"del_trade_{row['ID']}"):
                        df = df[df['ID'] != row['ID']]
                        df.to_csv(CSV_FILE, index=False)
                        st.warning("Operação removida!"); time.sleep(1); st.rerun()
    else:
        st.info("Histórico vazio.")
