import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* Reset Geral e Fundo */
        .stApp { background-color: #0F0F0F; color: #E0E0E0; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #222; }
        
        /* Metric Card (Dashboard) */
        div[data-testid="column"] > div > div > div > .metric-container {
            height: 100%; /* Força altura igual nas colunas */
        }

        .metric-container { 
            background-color: #161616; 
            border: 1px solid #262626; 
            padding: 15px; 
            border-radius: 12px; 
            text-align: center; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.2); 
            min-height: 120px;
            display: flex; 
            flex-direction: column; 
            justify-content: center;
            align-items: center;
            margin-bottom: 10px; /* Margem reduzida */
            width: 100%; /* Garante que preencha a coluna */
        }
        
        .metric-label { 
            color: #888; 
            font-size: 11px; 
            text-transform: uppercase; 
            letter-spacing: 1px; 
            font-weight: 700; 
            margin-bottom: 5px;
        }
        
        .metric-value { 
            color: white; 
            font-size: 22px; 
            font-weight: 800; 
            margin: 0;
        }
        
        .metric-sub { 
            font-size: 11px; 
            margin-top: 4px; 
            color: #666; 
        }
        
        /* Trade Card (Histórico) */
        .trade-card { 
            background-color: #161616; 
            border-radius: 12px; 
            padding: 15px; 
            border: 1px solid #262626; 
            margin-bottom: 15px; 
            transition: transform 0.2s;
        }
        .trade-card:hover {
            transform: translateY(-3px);
            border-color: #B20000;
        }
        .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; } 
        .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }
        
        /* Ajuste para telas menores */
        @media (max-width: 768px) {
            .metric-value { font-size: 18px; }
        }
        </style>
    """, unsafe_allow_html=True)

def card_metric(label, value, sub_value="", color="white"):
    # Renderiza HTML puro para controle total do layout
    st.markdown(f"""
        <div class="metric-container" style="border-top: 3px solid {color};">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {color};">{value}</div>
            <div class="metric-sub">{sub_value}</div>
        </div>
    """, unsafe_allow_html=True)
