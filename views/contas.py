import streamlit as st
import time
from modules import database, logic

def show(user, role):
    st.title("💼 Gestão de Portfólio")
    
    t1, t2, t3 = st.tabs(["Monitor Apex", "Cadastrar Conta", "Criar Grupo"])
    
    # --- MONITOR ---
    with t1:
        st.subheader("🚀 Monitor de Saúde")
        df_c = database.load_contas(user)
        df_t = database.load_trades(user)
        
        if not df_c.empty:
            grps = sorted(df_c['grupo_nome'].unique())
            sel_g = st.selectbox("Selecionar Grupo", grps)
            
            contas = df_c[df_c['grupo_nome'] == sel_g]
            trades = df_t[df_t['grupo_vinculo'] == sel_g]
            
            if not contas.empty:
                # Pega a primeira conta como referência de regra (Assumindo 150k padrao)
                ref = contas.iloc[0] 
                saude = logic.calcular_saude_apex(ref['saldo_inicial'], ref['pico_previo'], trades)
                
                k1, k2, k3 = st.columns(3)
                k1.metric("Saldo Atual", f"${saude['saldo_atual']:,.2f}")
                k2.metric("Trailing Stop", f"${saude['stop_atual']:,.2f}", saude['status_stop'])
                k3.metric("BUFFER (VIDA)", f"${saude['buffer']:,.2f}", delta_color="normal")
                
                st.progress(min(1.0, max(0.0, saude['buffer'] / saude['dd_max'])))
                st.caption(f"Fase Atual: {saude['fase']} | Meta: ${saude['meta']:,.0f}")
            else: st.warning("Grupo sem contas.")
        else: st.info("Cadastre contas primeiro.")

    # --- CADASTRAR CONTA ---
    with t2:
        grupos = database.load_grupos(user)
        if not grupos.empty:
            with st.form("add_conta"):
                g = st.selectbox("Grupo", grupos['nome'].unique())
                ident = st.text_input("Nome da Conta (Ex: PA-01)")
                saldo = st.number_input("Saldo Inicial", value=150000.0)
                pico = st.number_input("Pico Histórico (Se houver)", value=150000.0)
                if st.form_submit_button("Salvar"):
                    database.supabase.table("contas_config").insert({
                        "usuario": user, "grupo_nome": g, "conta_identificador": ident,
                        "saldo_inicial": saldo, "pico_previo": pico, "status_conta": "Ativa"
                    }).execute()
                    st.success("Conta Criada!")
                    time.sleep(1); st.rerun()
        else: st.warning("Crie um grupo na aba ao lado.")

    # --- CRIAR GRUPO ---
    with t3:
        with st.form("add_grp"):
            nome = st.text_input("Nome do Grupo")
            if st.form_submit_button("Criar"):
                database.supabase.table("grupos_config").insert({"usuario": user, "nome": nome}).execute()
                st.success("Grupo Criado!")
                time.sleep(1); st.rerun()
