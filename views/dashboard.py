import streamlit as st

# --- 1. FUNÇÃO DE ESTILO ---
def card(label, value, sub_text, color="white", border_color="#333333"):
    st.markdown(
        f"""
        <div style="
            background-color: #161616; 
            padding: 20px; 
            border-radius: 8px; 
            border: 1px solid {border_color}; 
            text-align: center; 
            margin-bottom: 10px;
            height: 140px; 
            display: flex; flex-direction: column; justify-content: center;
        ">
            <div style="color: #888; font-size: 11px; text-transform: uppercase; margin-bottom: 8px; display: flex; justify-content: center; align-items: center; gap: 5px;">
                {label} <span style="font-size:10px; border: 1px solid #444; border-radius: 50%; width: 12px; height: 12px; display: inline-flex; justify-content: center; align-items: center;">?</span>
            </div>
            <h2 style="color: {color}; margin: 0; font-size: 24px; font-weight: 600;">{value}</h2>
            <p style="color: #666; font-size: 11px; margin-top: 8px;">{sub_text}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- 2. O LAYOUT DO DASHBOARD ---
# AQUI ESTAVA O ERRO: Renomeado para 'show' e adicionado args user/role
def show(user, role): 
    
    st.markdown("### 🏁 Desempenho Geral")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Resultado Líquido", "$1,500.00", "Bruto: $3,750 / $2,250", color="#00FF00")
    with c2:
        card("Fator de Lucro (PF)", "1.67", "Ideal > 1.5", color="#FF4B4B")
    with c3:
        card("Win Rate", "50.0%", "5W / 5L", color="white")
    with c4:
        card("Expectativa Mat.", "$150.00", "Por Trade", color="#00FF00")

    st.markdown("### 💲 Médias Financeiras")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Média Gain ($)", "$750.00", "", color="#00FF00")
    with c2:
        card("Média Loss ($)", "-$450.00", "", color="#FF4B4B")
    with c3:
        card("Risco : Retorno", "1:1.67", "Payoff Real", color="white")
    with c4:
        card("Drawdown Máximo", "-$900.00", "Pior Queda", color="#FF4B4B")

    st.markdown("### 🎯 Performance Técnica")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Pts Médios (Gain)", "25.00 pts", "", color="#00FF00")
    with c2:
        card("Stop Médio (Loss)", "15.00 pts", "Base do Risco", color="#FF4B4B")
    with c3:
        card("Lote Médio", "15.0", "Contratos", color="white")
    with c4:
        card("Total Trades", "10", "Executados", color="white")

    st.markdown("### 🛡️ Análise de Sobrevivência (Brownian Motion)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Z-Score (Edge)", "0.3333", "Edge Positivo", color="#00FF00")
    with c2:
        card("Buffer Real (Hoje)", "$5,000", "1 Contas Ativas", color="#00FF00")
    with c3:
        card("Vidas Reais (U)", "11.1", "Risco Base: $450", color="#00FF00")
    with c4:
        card("Prob. Ruína (Real)", "1.55%", "Risco Moderado", color="#FFD700", border_color="#FFD700")

    st.markdown("### 🧠 Inteligência de Lote (Faixa de Operação)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Buffer Disponível", "$5,000", "Stop: $146,500", color="#00FF00")
    with c2:
        card("Half-Kelly (Math)", "10.0%", "Teto Teórico", color="#888")
    with c3:
        card("Risco Financeiro", "$240 - $330", "Por Trade", color="#00FF00")
    with c4:
        card("Sugestão de Lote", "8 a 11 ctrs", "ZONA DE ACELERAÇÃO", color="#00FF00", border_color="#00FF00")
