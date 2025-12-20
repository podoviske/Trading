import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu

# Configuração da Página
st.set_page_config(page_title="ProTrader Dashboard", layout="wide", page_icon="📈")

# --- ESTILO CSS PERSONALIZADO (SIDEBAR FIEL À IMAGEM) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #111418 !important;
        border-right: 1px solid #222;
    }
    .sidebar-category {
        color: #4F545C;
        font-size: 0.70rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-top: 25px;
        margin-left: 15px;
        margin-bottom: 5px;
        letter-spacing: 1px;
    }
    /* Ajuste para remover espaços em branco no topo da sidebar */
    .css-1d391kg { padding-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# Banco de dados e constantes
CSV_FILE = 'trades_nq_mnq_final.csv'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df
    return pd.DataFrame()

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

df = load_data()

# --- LÓGICA DE ESTADO (PARCIAIS) ---
if 'n_parciais' not in st.session_state:
    st.session_state.n_parciais = 1

def adicionar_parcial():
    if st.session_state.n_parciais < 6: st.session_state.n_parciais += 1
def limpar_parciais():
    st.session_state.n_parciais = 1

# --- SIDEBAR COM STREAMLIT OPTION MENU ---
with st.sidebar:
    st.markdown("<h2 style='color:#00FF88; margin-left:15px;'>M</h2>", unsafe_allow_html=True) # Logo M verde
    
    st.markdown('<p class="sidebar-category">Menu</p>', unsafe_allow_html=True)
    selected = option_menu(
        menu_title=None,
        options=["Registrar Trade", "Histórico"],
        icons=["graph-up-arrow", "plus-circle", "clock-history"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#8E9196", "font-size": "16px"}, 
            "nav-link": {"font-size": "14px", "text-align": "left", "margin":"0px", "--hover-color": "#1A1F24", "color": "#8E9196"},
            "nav-link-selected": {"background-color": "#1A2E28", "color": "#00FF88", "border-left": "4px solid #00FF88", "font-weight": "500"},
        }
    )
    
    st.markdown('<p class="sidebar-category">Gerenciamento</p>', unsafe_allow_html=True)
    option_menu(
        menu_title=None,
        options=["Usuário", "Configurações", "Transações"],
        icons=["person", "gear", "arrow-left-right"],
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#8E9196", "font-size": "16px"},
            "nav-link": {"font-size": "14px", "text-align": "left", "color": "#8E9196"},
            "nav-link-selected": {"background-color": "transparent", "color": "#8E9196"},
        }
    )

# --- CONTEÚDO DAS PÁGINAS ---

if selected == "Registrar Trade":
    col_t, col_b = st.columns([3, 1])
    with col_t: st.title("🚀 Novo Registro NQ/MNQ")
    with col_b:
        st.write("<br>", unsafe_allow_html=True)
        c_a, c_r = st.columns(2)
        with c_a: st.button("➕ Parcial", on_click=adicionar_parcial, use_container_width=True)
        with c_r: st.button("🧹 Reset", on_click=limpar_parciais, use_container_width=True)

    with st.form("trade_form"):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            data = st.date_input("Data", datetime.now())
            ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
            contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
            direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            entrada = st.number_input("Preço de Entrada", min_value=0.0, step=0.25, format="%.2f")
        with c2:
            lote_total = st.number_input("Lote Total", min_value=1, step=1)
            stop_pts = st.number_input("Stop (Pts)", min_value=0.0, step=0.25)
            risco_fin = stop_pts * MULTIPLIERS[ativo] * lote_total
            st.metric("Risco Financeiro", f"${risco_fin:.2f}")
        with c3:
            st.write("**Saídas**")
            p_inputs = []
            alocado = 0
            for i in range(st.session_state.n_parciais):
                ca, cb = st.columns(2)
                with ca: pts = st.number_input(f"Pts P{i+1}", min_value=0.0, step=0.25, key=f"pts_{i}")
                with cb: qtd = st.number_input(f"Qtd P{i+1}", min_value=0, step=1, key=f"qtd_{i}")
                p_inputs.append((pts, qtd)); alocado += qtd
            
            resta = lote_total - alocado
            if resta > 0: st.warning(f"Resta alocar {resta} contratos.")
            elif resta < 0: st.error(f"Excesso de {abs(resta)} contratos!")

        if st.form_submit_button("💾 Salvar Operação"):
            if alocado == lote_total:
                res = sum([p[0] * MULTIPLIERS[ativo] * p[1] for p in p_inputs])
                med = sum([p[0] * p[1] for p in p_inputs]) / lote_total
                faixa = "Até 10" if lote_total <= 10 else "11 a 20" if lote_total <= 20 else "Acima de 20"
                
                novo = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_total, 'Faixa_Lote': faixa, 'Risco_Fin': risco_fin, 'Resultado': res, 'Pts_Medio': med, 'RR': res/risco_fin if risco_fin>0 else 0}])
                df = pd.concat([df, novo], ignore_index=True)
                save_data(df)
                st.success("Operação Salva!")
                st.rerun()
            else:
                st.error("A soma das parciais deve bater com o Lote Total.")

elif selected == "Vendas Analytics":
    st.title("📊 Vendas Analytics (Performance)")
    if not df.empty:
        # Filtros
        with st.expander("🔍 Filtros de Análise"):
            f_lote = st.multiselect("Faixa de Lotes", df['Faixa_Lote'].unique(), default=df['Faixa_Lote'].unique())
            f_ctx = st.multiselect("Contexto", df['Contexto'].unique(), default=df['Contexto'].unique())
            dff = df[(df['Faixa_Lote'].isin(f_lote)) & (df['Contexto'].isin(f_ctx))]
        
        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Faturamento Total", f"${dff['Resultado'].sum():.2f}")
        k2.metric("Taxa de Acerto", f"{(len(dff[dff['Resultado']>0])/len(dff)*100):.1f}%")
        k3.metric("Risco Médio", f"${dff['Risco_Fin'].mean():.2f}")
        k4.metric("Pontos Médios", f"{dff['Pts_Medio'].mean():.2f}")

        # Gráfico de Faturamento Neon
        st.markdown("### Faturamento")
        df_ev = dff.sort_values('Data').copy()
        df_ev['Acumulado'] = df_ev['Resultado'].cumsum()
        fig = px.area(df_ev, x='Data', y='Acumulado', template="plotly_dark", color_discrete_sequence=['#00FF88'])
        fig.update_traces(line_shape='spline', fillcolor='rgba(0, 255, 136, 0.1)')
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de Barras por Contexto
        st.markdown("### Quantidade de Vendas por Contexto")
        fig_bar = px.bar(dff.groupby('Contexto')['Resultado'].sum().reset_index(), x='Contexto', y='Resultado', template="plotly_dark", color_discrete_sequence=['#00FF88'])
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Aguardando registros...")

elif selected == "Histórico":
    st.title("📋 Histórico")
    st.dataframe(df.sort_values('Data', ascending=False), use_container_width=True)
    if st.button("🗑️ Resetar Tudo"):
        if os.path.exists(CSV_FILE): os.remove(CSV_FILE); st.rerun()
