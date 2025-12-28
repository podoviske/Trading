import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client
import time
import math

# Importando a inteligência isolada
from modules.logic import ApexEngine

# --- 1. CONEXÃO E FUNÇÕES DE DADOS ---
def get_supabase():
    try:
        if "supabase" in st.session_state: return st.session_state["supabase"]
        else:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
    except: return None

def load_grupos(user):
    sb = get_supabase()
    res = sb.table("grupos_config").select("*").eq("usuario", user).execute()
    return pd.DataFrame(res.data)

def load_contas(user):
    sb = get_supabase()
    res = sb.table("contas_config").select("*").eq("usuario", user).execute()
    return pd.DataFrame(res.data)

def load_trades(user):
    sb = get_supabase()
    res = sb.table("trades").select("*").eq("usuario", user).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['created_at'] = pd.to_datetime(df['created_at'])
    return df

# --- 2. COMPONENTE VISUAL (CARD) ---
def card(label, value, sub_text, color="white", border_color="#333333"):
    st.markdown(
        f"""
        <div style="
            background-color: #161616; 
            padding: 15px; 
            border-radius: 8px; 
            border: 1px solid {border_color}; 
            text-align: center; 
            margin-bottom: 10px;
            height: 100px; 
            display: flex; flex-direction: column; justify-content: center;
        ">
            <div style="color: #888; font-size: 10px; text-transform: uppercase; margin-bottom: 4px; display: flex; justify-content: center; align-items: center; gap: 5px;">
                {label}
            </div>
            <h2 style="color: {color}; margin: 0; font-size: 20px; font-weight: 600;">{value}</h2>
            <p style="color: #666; font-size: 10px; margin-top: 4px;">{sub_text}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- 3. TELA PRINCIPAL ---
def show(user, role):
    st.title("💼 Gestão de Portfólio")
    
    # Validação de Permissão (Mantida da v201)
    if role not in ['master', 'admin']:
        st.error("🔒 Acesso restrito a gestores.")
        return

    sb = get_supabase()
    
    # Abas Iguais à v201
    t1, t2, t3, t4 = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📋 Visão Geral", "🚀 Monitor Performance"])

    # --- ABA 1: CRIAR GRUPO ---
    with t1:
        st.subheader("Nova Estrutura")
        with st.form("form_grupo", clear_on_submit=True):
            novo_grupo = st.text_input("Nome do Grupo (Ex: Apex 20 Contas)")
            if st.form_submit_button("Criar Grupo"):
                if novo_grupo:
                    sb.table("grupos_config").insert({"usuario": user, "nome": novo_grupo}).execute()
                    st.toast("Grupo criado!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Digite um nome.")
        
        st.divider()
        st.caption("Grupos Existentes")
        df_g = load_grupos(user)
        if not df_g.empty:
            for _, row in df_g.iterrows():
                c1, c2 = st.columns([4, 1])
                c1.info(f"📂 {row['nome']}")
                if c2.button("🗑️", key=f"del_g_{row['id']}"):
                    sb.table("grupos_config").delete().eq("id", row['id']).execute()
                    st.rerun()

    # --- ABA 2: CADASTRAR CONTA ---
    with t2:
        st.subheader("Vincular Nova Conta")
        df_g = load_grupos(user)
        
        if not df_g.empty:
            grupos_opcoes = sorted(df_g['nome'].unique())
            
            with st.form("form_conta", clear_on_submit=True):
                c_a, c_b = st.columns(2)
                g_sel = c_a.selectbox("Vincular ao Grupo", grupos_opcoes)
                c_id = c_b.text_input("Identificador (Ex: PA-001)")
                
                s_ini = c_a.number_input("Saldo Inicial ($)", value=150000.0, step=100.0)
                p_pre = c_b.number_input("Pico Prévio / HWM ($)", value=150000.0, step=100.0)
                
                fase_ini = st.selectbox("Fase Inicial", ["Fase 1", "Fase 2", "Fase 3", "Fase 4"])
                
                if st.form_submit_button("💾 Salvar Conta"):
                    if c_id:
                        sb.table("contas_config").insert({
                            "usuario": user,
                            "grupo_nome": g_sel,
                            "conta_identificador": c_id,
                            "saldo_inicial": s_ini,
                            "pico_previo": p_pre,
                            "fase_entrada": fase_ini,
                            "status_conta": "Ativa"
                        }).execute()
                        st.success(f"Conta {c_id} criada com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Preencha o identificador.")
        else:
            st.warning("⚠️ Crie um GRUPO na primeira aba antes de cadastrar contas.")

    # --- ABA 3: VISÃO GERAL (Gerenciamento) ---
    with t3:
        st.subheader("📋 Gestão e Mobilidade")
        
        df_c = load_contas(user)
        df_g = load_grupos(user)
        df_t = load_trades(user)
        
        lista_grupos = sorted(df_g['nome'].unique()) if not df_g.empty else []
        
        if not df_c.empty:
            grupos_unicos = sorted(df_c['grupo_nome'].unique())
            
            for grp in grupos_unicos:
                with st.expander(f"📂 {grp}", expanded=True):
                    # Filtra contas deste grupo
                    contas_deste_grupo = df_c[df_c['grupo_nome'] == grp]
                    
                    # Calcula lucro estimado do grupo (simplificado para exibição rápida)
                    trades_grp = df_t[df_t['grupo_vinculo'] == grp] if not df_t.empty else pd.DataFrame()
                    lucro_total_grp = trades_grp['resultado'].sum() if not trades_grp.empty else 0.0
                    
                    # Assume distribuição igualitária (Copy)
                    qtd_contas = len(contas_deste_grupo)
                    lucro_por_conta = lucro_total_grp / qtd_contas if qtd_contas > 0 else 0
                    
                    for _, conta in contas_deste_grupo.iterrows():
                        # Lógica Visual
                        status_icon = "🟢" if conta['status_conta'] == "Ativa" else "🔴"
                        cor_border = "#00FF88" if conta['status_conta'] == "Ativa" else "#FF4B4B"
                        
                        saldo_estimado = float(conta['saldo_inicial']) + lucro_por_conta
                        delta = saldo_estimado - float(conta['saldo_inicial'])
                        cor_delta = "#00FF88" if delta >= 0 else "#FF4B4B"
                        
                        # Layout da Linha da Conta
                        col_info, col_edit, col_del = st.columns([3, 0.5, 0.5])
                        
                        col_info.markdown(f"""
                            <div style='background-color: #222; padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 3px solid {cor_border}'>
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <span style="font-size:16px;">💳 <b>{conta['conta_identificador']}</b></span>
                                    <span style="font-size:12px; background:#111; padding:2px 6px; border-radius:4px;">{status_icon} {conta['status_conta']}</span>
                                </div>
                                <div style="font-size: 13px; color:#aaa; margin-top:4px;">
                                    Saldo Est: <span style="color:white; font-weight:bold;">${saldo_estimado:,.2f}</span> 
                                    (<span style="color:{cor_delta}">${delta:+,.2f}</span>)
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Botão Editar (Popover)
                        with col_edit.popover("⚙️"):
                            st.markdown(f"**Editar {conta['conta_identificador']}**")
                            
                            # Opções de Edição
                            idx_grp = lista_grupos.index(conta['grupo_nome']) if conta['grupo_nome'] in lista_grupos else 0
                            novo_grp = st.selectbox("Mover Grupo", lista_grupos, index=idx_grp, key=f"g_{conta['id']}")
                            
                            status_ops = ["Ativa", "Pausada", "Quebrada"]
                            idx_st = status_ops.index(conta['status_conta']) if conta['status_conta'] in status_ops else 0
                            novo_st = st.selectbox("Status", status_ops, index=idx_st, key=f"s_{conta['id']}")
                            
                            novo_saldo = st.number_input("Corrigir Inicial", value=float(conta['saldo_inicial']), key=f"si_{conta['id']}")
                            
                            if st.button("Salvar Alterações", key=f"btn_{conta['id']}"):
                                sb.table("contas_config").update({
                                    "grupo_nome": novo_grp,
                                    "status_conta": novo_st,
                                    "saldo_inicial": novo_saldo
                                }).eq("id", conta['id']).execute()
                                st.rerun()
                        
                        # Botão Excluir
                        if col_del.button("🗑️", key=f"del_{conta['id']}"):
                            sb.table("contas_config").delete().eq("id", conta['id']).execute()
                            st.rerun()
        else:
            st.info("Nenhuma conta cadastrada.")

    # --- ABA 4: MONITOR DE PERFORMANCE (Engine Integrada) ---
    with t4:
        st.subheader("🚀 Monitor de Grupo (Apex Engine)")
        
        df_c = load_contas(user)
        df_t = load_trades(user)
        
        if not df_c.empty:
            grps = sorted(df_c['grupo_nome'].unique())
            
            c_sel, c_view = st.columns([1, 2])
            sel_g = c_sel.selectbox("Monitorar Grupo", grps)
            
            # Filtra dados para o motor
            contas_g = df_c[df_c['grupo_nome'] == sel_g]
            trades_g = df_t[df_t['grupo_vinculo'] == sel_g] if not df_t.empty else pd.DataFrame()
            
            if not contas_g.empty:
                # Pega a primeira conta como referência de Saldo Inicial (Já que todas são 150k)
                conta_ref = contas_g.iloc[0]
                
                # Calcula Lucro Total do Grupo no DB
                lucro_total = trades_g['resultado'].sum() if not trades_g.empty else 0.0
                # Lucro por conta (Rateio)
                lucro_por_conta = lucro_total / len(contas_g)
                
                saldo_atual_ref = float(conta_ref['saldo_inicial']) + lucro_por_conta
                hwm_ref = float(conta_ref.get('pico_previo', conta_ref['saldo_inicial']))
                
                # --- CHAMA O MOTOR DE LÓGICA (ApexEngine) ---
                # Isso substitui aquele bloco gigante de IFs da v201
                saude = ApexEngine.calculate_health(saldo_atual_ref, hwm_ref)
                
                # Exibe Cards v300
                k1, k2, k3, k4 = st.columns(4)
                with k1:
                    card("Saldo Unitário", f"${saude['saldo']:,.2f}", f"Lucro: ${saude['saldo'] - 150000:+,.2f}", "#00FF88")
                with k2:
                    card("HWM (Topo)", f"${saude['hwm']:,.2f}", saude['status_trailing'], "white")
                with k3:
                    cor_buf = "#00FF88" if saude['buffer'] > 2000 else "#FF4B4B"
                    card("Buffer Unitário", f"${saude['buffer']:,.2f}", f"Stop: ${saude['stop_atual']:,.0f}", cor_buf)
                with k4:
                    card("Status / Fase", saude['fase'], f"Falta: ${saude['falta_para_trava']:,.0f}", "#00FF88")
                
                # Barra de Progresso da Fase
                st.write("")
                meta_total = 5100.0 # Meta para travar o stop (aprox 155.100)
                progresso = max(0.0, min(1.0, (saude['saldo'] - 150000) / meta_total))
                st.progress(progresso)
                st.caption(f"Progresso para Trava do Stop ({progresso*100:.1f}%)")

            else:
                st.warning("Grupo vazio.")
        else:
            st.info("Cadastre contas para monitorar.")
