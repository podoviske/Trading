import streamlit as st
import json
import time
from modules import database

def show(user, role):
    st.title("⚙️ Configurar ATM")
    
    # Listar
    atms = database.load_atms()
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Existentes")
        for nome, dados in atms.items():
            if st.button(f"🗑️ {nome}", key=f"del_{nome}"):
                database.supabase.table("atm_configs").delete().eq("nome", nome).execute()
                st.rerun()
    
    with c2:
        st.subheader("Nova Estratégia")
        with st.form("new_atm"):
            n = st.text_input("Nome (Ex: Scalp NQ)")
            l = st.number_input("Lote", min_value=1, value=1)
            s = st.number_input("Stop (Pts)", min_value=0.0)
            if st.form_submit_button("Salvar"):
                database.supabase.table("atm_configs").insert({
                    "nome": n, "lote": l, "stop": s, "parciais": []
                }).execute()
                st.success("Salvo!")
                time.sleep(1); st.rerun()
