import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* =====================================================================
           RESET GERAL E FUNDO
           ===================================================================== */
        .stApp { background-color: #0F0F0F; color: #E0E0E0; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #222; }
        
        /* =====================================================================
           CORREÇÃO DE LAYOUT (GRID vs LISTA)
           ===================================================================== */
        
        /* Força que os containers dentro das colunas tenham altura igual */
        div[data-testid="column"] {
            display: flex;
            flex-direction: column;
        }
        
        div[data-testid="column"] > div > div > div > .metric-container {
            height: 100%;
        }

        /* =====================================================================
           METRIC CARD (Dashboard)
           ===================================================================== */
        .metric-container { 
            background-color: #161616; 
            border: 1px solid #262626; 
            padding: 15px; 
            border-radius: 12px; 
            text-align: center; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.2); 
            min-height: 130px;      /* Altura mínima para padronizar */
            display: flex; 
            flex-direction: column; 
            justify-content: center;
            align-items: center;
            margin-bottom: 0px;     /* Remove margem excessiva que quebrava o grid */
            width: 100%;            /* Garante uso total da largura da coluna */
        }
        
        .metric-label { 
            color: #888; 
            font-size: 11px; 
            text-transform: uppercase; 
            letter-spacing: 1px; 
            font-weight: 700; 
            margin-bottom: 8px;
        }
        
        .metric-value { 
            color: white; 
            font-size: 24px; 
            font-weight: 800; 
            margin: 0;
            line-height: 1.2;
        }
        
        .metric-sub { 
            font-size: 11px; 
            margin-top: 6px; 
            color: #666; 
        }
        
        /* =====================================================================
           TRADE CARD (Histórico)
           ===================================================================== */
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
        
        /* Ajuste responsivo para telas menores */
        @media (max-width: 768px) {
            .metric-value { font-size: 18px; }
            .metric-container { min-height: 110px; }
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
