import streamlit as st

def show():
    st.title("📜 Empire Builder: Plano de Trading")
    
    st.markdown("""
        <style>
        .rule-card {
            background-color: #161616;
            border-left: 4px solid #B20000;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .rule-title { font-weight: bold; color: white; font-size: 16px; margin-bottom: 5px; }
        .rule-desc { color: #aaa; font-size: 14px; }
        
        .goal-card {
            background-color: #0f2e1d;
            border: 1px solid #00FF88;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        }
        .goal-val { font-size: 30px; font-weight: 900; color: #00FF88; }
        </style>
    """, unsafe_allow_html=True)

    # --- OBJETIVO MACRO ---
    c_goal, c_info = st.columns([1, 2])
    
    with c_goal:
        st.markdown("""
            <div class="goal-card">
                <div style="color:#ddd; font-size:12px; text-transform:uppercase;">Meta Final por Conta</div>
                <div class="goal-val">$161,000</div>
                <div style="color:#888; font-size:11px; margin-top:5px;">SAQUE LIBERADO: $20K TOTAL</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c_info:
        st.info("""
        **🎯 Estratégia de Crescimento:**
        * Manter meta de **$500/semana** por conta consistentemente.
        * Não alavancar antes de atingir o **Colchão de Segurança (Fase 2)**.
        * O objetivo não é ficar rico num dia, é construir o Império de 20 Contas.
        """)

    st.markdown("---")

    # --- REGRAS OPERACIONAIS ---
    st.subheader("🛡️ Regras de Ouro")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div class="rule-card">
                <div class="rule-title">1. Ativos & Foco</div>
                <div class="rule-desc">
                    • <b>MNQ (Micro):</b> Ativo Principal para construção de capital.<br>
                    • <b>NQ (Mini):</b> APENAS com Edge confirmado e Gordura acumulada.
                </div>
            </div>
            
            <div class="rule-card">
                <div class="rule-title">2. Horário de Elite</div>
                <div class="rule-desc">
                    Defina sua janela de foco (ex: 10:30 - 12:00).<br>
                    Não operar em horários de baixa liquidez ou notícias de alto impacto (Tier 1).
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
            <div class="rule-card">
                <div class="rule-title">3. Gestão de Lote (Vidas)</div>
                <div class="rule-desc">
                    Siga RIGOROSAMENTE a sugestão do Dashboard.<br>
                    Alvo ideal: <b>20 Vidas</b> (Stops) de gordura.<br>
                    Se o Dashboard marcar "Risco Crítico", volte para 1 contrato.
                </div>
            </div>
            
            <div class="rule-card">
                <div class="rule-title">4. Stop Diário (Loss Limit)</div>
                <div class="rule-desc">
                    Defina um limite financeiro de perda por dia por grupo.<br>
                    Atingiu o limite? <b>Feche a plataforma.</b> Amanhã tem mais.
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # --- ÁREA DE ANOTAÇÕES ---
    st.subheader("📝 Notas Pessoais / Diário Mental")
    st.text_area("O que você precisa lembrar hoje?", height=200, placeholder="Ex: Estou ansioso hoje, operar metade da mão. Não perseguir preço...")
