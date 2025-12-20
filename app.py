# --- REGISTRAR TRADE (CORREÇÃO DE SINCRONIZAÇÃO ATM) ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    
    # Inicializa variáveis de controle se não existirem
    if 'n_extras' not in st.session_state: st.session_state.n_extras = 0
    if 'last_atm' not in st.session_state: st.session_state.last_atm = None

    c_topo1, c_topo2 = st.columns([3, 1])
    with c_topo1:
        # Seleção de ATM
        atm_sel = st.selectbox("🎯 ATM", list(atm_db.keys()))
        config = atm_db[atm_sel]
        
        # GATILHO DE CORREÇÃO: Se a ATM mudou, reseta os extras e limpa valores residuais
        if st.session_state.last_atm != atm_sel:
            st.session_state.n_extras = 0
            st.session_state.last_atm = atm_sel
            st.rerun() # Força a atualização dos campos com os novos valores da ATM
            
    with c_topo2:
        st.write(""); cb1, cb2 = st.columns(2)
        cb1.button("➕", on_click=lambda: st.session_state.update({"n_extras": st.session_state.n_extras + 1}))
        cb2.button("🧹", on_click=lambda: st.rerun())
    
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
    with c2:
        # Lote e Stop preenchidos via config da ATM (com IDs dinâmicos baseados na ATM para evitar conflito)
        lote_t = st.number_input("Contratos", min_value=0, value=int(config["lote"]), key=f"lote_{atm_sel}")
        stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]), key=f"stop_{atm_sel}")
        
        if lote_t > 0 and stop_p > 0:
            st.metric("Risco Total", f"${(stop_p * MULTIPLIERS[ativo] * lote_t):,.2f}")
        up_files = st.file_uploader("📸 Prints", accept_multiple_files=True)
    with c3:
        st.write("**Saídas**")
        saidas = []; alocado = 0
        
        # Renderiza saídas fixas da ATM
        for i, p_c in enumerate(config["parciais"]):
            s1, s2 = st.columns(2)
            # Chaves únicas por ATM garantem que o valor mude quando você troca de ATM
            p = s1.number_input(f"Pts P{i+1}", value=float(p_c[0]), key=f"p_{atm_sel}_{i}")
            q = s2.number_input(f"Qtd P{i+1}", value=int(p_c[1]), key=f"q_{atm_sel}_{i}")
            saidas.append((p, q)); alocado += q
            
        # Renderiza saídas extras (manuais)
        for i in range(st.session_state.n_extras):
            s1, s2 = st.columns(2)
            p = s1.number_input(f"Pts Ex {i+1}", key=f"pe_{i}")
            q = s2.number_input(f"Qtd Ex {i+1}", key=f"qe_{i}")
            saidas.append((p, q)); alocado += q
            
        # Alertas de discrepância de contratos
        if lote_t > 0 and lote_t != alocado: 
            st.markdown(f'<div class="piscante-erro">FALTAM {lote_t-alocado} CONTRATOS</div>', unsafe_allow_html=True)
        elif lote_t == alocado and lote_t > 0:
            st.success("✅ Posição Completa")

    # Botões de Registro (mantidos sem alteração conforme solicitado)
    r1, r2 = st.columns(2)
    # ... (restante do código de r1 e r2 permanece igual)
