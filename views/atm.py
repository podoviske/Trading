import streamlit as st
import pandas as pd
from supabase import create_client
import json
import time

# --- 1. CONEXÃO ---
def get_supabase():
    try:
        if "supabase" in st.session_state: return st.session_state["supabase"]
        else:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
    except: return None

# --- 2. TELA DE CONFIGURAÇÃO ATM ---
def show(user, role):
    st.title("⚙️ Gerenciar Estratégias (ATM)")
    
    sb = get_supabase()
    
    # Inicializa o estado do formulário se não existir
    if "atm_form_data" not in st.session_state:
        st.session_state.atm_form_data = {
            "id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]
        }

    # Função para limpar o formulário
    def reset_atm_form():
        st.session_state.atm_form_data = {
            "id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]
        }

    # Carrega ATMs existentes
    try:
        res = sb.table("atm_configs").select("*").order("nome").execute()
        existing_atms = res.data
    except:
        existing_atms = []

    # Layout: Formulário (Esq) e Lista (Dir)
    c_form, c_list = st.columns([1.5, 1])

    # --- COLUNA DIREITA: LISTA DE ATMS SALVOS ---
    with c_list:
        st.subheader("📋 Estratégias Salvas")
        
        if st.button("✨ Criar Nova (Limpar)", use_container_width=True):
            reset_atm_form()
            st.rerun()
            
        if existing_atms:
            for item in existing_atms:
                # Card expansível para cada ATM
                with st.expander(f"📍 {item['nome']}", expanded=False):
                    st.write(f"**Lote Total:** {item['lote']} | **Stop Padrão:** {item['stop']} pts")
                    
                    # Botões de Ação
                    c_edit, c_del = st.columns(2)
                    
                    if c_edit.button("✏️ Editar", key=f"edit_{item['id']}"):
                        # Carrega dados para o form (trata JSON ou string)
                        p_data = item['parciais'] if isinstance(item['parciais'], list) else json.loads(item['parciais'])
                        st.session_state.atm_form_data = {
                            "id": item['id'], 
                            "nome": item['nome'], 
                            "lote": item['lote'], 
                            "stop": item['stop'], 
                            "parciais": p_data
                        }
                        st.rerun()
                        
                    if c_del.button("🗑️ Excluir", key=f"del_{item['id']}"):
                        sb.table("atm_configs").delete().eq("id", item['id']).execute()
                        if st.session_state.atm_form_data["id"] == item['id']:
                            reset_atm_form()
                        st.rerun()
        else:
            st.info("Nenhuma estratégia salva.")

    # --- COLUNA ESQUERDA: FORMULÁRIO DE EDIÇÃO ---
    with c_form:
        form_data = st.session_state.atm_form_data
        titulo = f"✏️ Editando: {form_data['nome']}" if form_data["id"] else "✨ Nova Estratégia"
        
        st.subheader(titulo)
        
        # Inputs Principais
        new_nome = st.text_input("Nome da Estratégia (Ex: Rompimento 30cts)", value=form_data["nome"])
        
        c_l, c_s = st.columns(2)
        new_lote = c_l.number_input("Lote Total", min_value=1, value=int(form_data["lote"]))
        new_stop = c_s.number_input("Stop Padrão (Pts)", min_value=0.0, value=float(form_data["stop"]), step=0.25)
        
        st.markdown("---")
        
        # Gestão de Parciais (Alvos)
        st.write("🎯 Configuração de Saídas (Parciais)")
        
        c_add, c_rem = st.columns([1, 4])
        if c_add.button("➕ Adicionar Alvo"):
            st.session_state.atm_form_data["parciais"].append({"pts": 0.0, "qtd": 1})
            st.rerun()
            
        if c_rem.button("➖ Remover Último"):
            if len(form_data["parciais"]) > 1:
                st.session_state.atm_form_data["parciais"].pop()
                st.rerun()
        
        # Inputs Dinâmicos das Parciais
        updated_partials = []
        total_aloc = 0
        
        for i, p in enumerate(form_data["parciais"]):
            c1, c2 = st.columns([1, 1])
            p_pts = c1.number_input(f"Alvo {i+1} (Pts)", value=float(p["pts"]), key=f"edm_pts_{i}", step=0.25)
            p_qtd = c2.number_input(f"Qtd {i+1}", value=int(p["qtd"]), min_value=1, key=f"edm_qtd_{i}")
            
            updated_partials.append({"pts": p_pts, "qtd": p_qtd})
            total_aloc += p_qtd
            
        # Validação Visual
        if total_aloc != new_lote:
            st.warning(f"⚠️ Atenção: Soma das parciais ({total_aloc}) difere do Lote Total ({new_lote}).")
            cor_botao = "secondary"
        else:
            st.success("✅ Distribuição correta.")
            cor_botao = "primary"
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Botão Salvar
        if st.button("💾 SALVAR ESTRATÉGIA", use_container_width=True, type=cor_botao):
            if not new_nome:
                st.error("Dê um nome para a estratégia.")
            else:
                payload = {
                    "nome": new_nome, 
                    "lote": new_lote, 
                    "stop": new_stop, 
                    "parciais": updated_partials
                }
                
                if form_data["id"]:
                    # Update
                    sb.table("atm_configs").update(payload).eq("id", form_data["id"]).execute()
                    st.toast("Estratégia Atualizada!", icon="✅")
                else:
                    # Insert
                    sb.table("atm_configs").insert(payload).execute()
                    st.toast("Estratégia Criada!", icon="✨")
                
                time.sleep(1)
                reset_atm_form()
                st.rerun()
