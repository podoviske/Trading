import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- ESTILO CSS PARA LAYOUT DE CARDS BRANCOS ---
st.markdown("""
    <style>
    /* Fundo da aplicação e Sidebar */
    [data-testid="stSidebar"] { background-color: #1e2130 !important; color: white; }
    .stApp { background-color: #f0f2f6; }
    
    /* Logo na Sidebar */
    .sidebar-logo { color: #ff4b4b; font-size: 24px; font-weight: 900; padding: 20px; text-align: center; border-bottom: 1px solid #2d324a; margin-bottom: 20px; }

    /* Estilização dos Cards de Métricas (Brancos com Sombra) */
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #e6e9ef;
        text-align: center;
        margin-bottom: 10px;
    }
    
    .metric-label { color: #6c757d; font-size: 14px; font-weight: 600; text-transform: uppercase; margin-bottom: 5px; }
    .metric-value { color: #1e2130; font-size: 26px; font-weight: 800; }

    /* Card do Gráfico */
    .chart-card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #e6e9ef;
        margin-top: 20px;
    }

    /* Ajuste de Títulos */
    .dashboard-title { color: #1e2130; font-weight: 800; margin-bottom: 20px; }
    
    /* Customização de rádio e seletores para o novo tema */
    div[data-testid="stSegmentedControl"] button { background-color: #ffffff !important; color: #1e2130 !important; border: 1px solid #e6e9ef !important; }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] { background-color: #ff4b4b !important; color: white !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO CARREGAR DADOS ---
def load_dashboard_data():
    CSV_FILE = 'evotrade_data.csv'
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            df['Data'] = pd.to_datetime(df['Data'])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- LÓGICA DA ABA DASHBOARD ---
def render_analytics_dashboard():
    df = load_dashboard_data()
    
    st.markdown('<h1 class="dashboard-title">EvoTrade Analytics</h1>', unsafe_allow_html=True)

    if not df.empty:
        # --- FILTROS DE TOPO ---
        c_filter1, c_filter2 = st.columns([2, 1])
        with c_filter1:
            filtro_view = st.segmented_control(
                "Visualizar:", 
                options=["Capital", "Contexto A", "Contexto B", "Contexto C"], 
                default="Capital"
            )
        
        with c_filter2:
            tipo_grafico = st.radio("Evolução por:", ["Tempo (Data)", "Trade a Trade"], horizontal=True)

        # Aplicar Filtro de Contexto
        df_f = df.copy()
        if filtro_view != "Capital":
            df_f = df[df['Contexto'] == filtro_view]

        st.markdown("<br>", unsafe_allow_html=True)

        # --- CARDS DE MÉTRICAS (LINHA SUPERIOR) ---
        m1, m2, m3, m4 = st.columns(4)
        
        total_pnl = df_f['Resultado'].sum()
        total_trades = len(df_f)
        win_rate = (len(df_f[df_f['Resultado'] > 0]) / total_trades * 100) if total_trades > 0 else 0
        risco_medio = df_f['Risco_Fin'].mean() if not df_f.empty else 0

        metrics = [
            ("P&L Total", f"${total_pnl:,.2f}"),
            ("Trades", f"{total_trades}"),
            ("Win Rate", f"{win_rate:.1f}%"),
            ("Risco Médio", f"${risco_medio:,.2f}")
        ]

        cols = [m1, m2, m3, m4]
        for col, (label, value) in zip(cols, metrics):
            col.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
            """, unsafe_allow_html=True)

        # --- ÁREA DO GRÁFICO (CHART CARD) ---
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        
        df_g = df_f.sort_values('Data').reset_index(drop=True)
        df_g['Acumulado'] = df_g['Resultado'].cumsum()
        
        x_axis = 'Data' if tipo_grafico == "Tempo (Data)" else df_g.index + 1
        
        fig = px.area(
            df_g, 
            x=x_axis, 
            y='Acumulado', 
            title=f"Equity Curve - {filtro_view}",
            color_discrete_sequence=['#ff4b4b']
        )
        
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font_color='#1e2130',
            xaxis=dict(showgrid=True, gridcolor='#f0f2f6'),
            yaxis=dict(showgrid=True, gridcolor='#f0f2f6'),
            margin=dict(l=10, r=10, t=40, b=10)
        )
        
        fig.update_traces(
            line_width=3,
            fillcolor='rgba(255, 75, 75, 0.1)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("Nenhum dado de trade encontrado para gerar o Analytics.")

# Execução (Simulação de menu lateral para teste isolado)
if __name__ == "__main__":
    with st.sidebar:
        st.markdown('<div class="sidebar-logo">EVOTRADE</div>', unsafe_allow_html=True)
        # Espaço para o menu option_menu se necessário
    render_analytics_dashboard()
