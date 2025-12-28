import streamlit as st
import pandas as pd
from supabase import create_client
import time

def get_supabase():
    try:
        if "supabase" in st.session_state: return st.session_state["supabase"]
        else:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
    except: return None

def show(user, role):
    st.title("👥 Admin: Gerenciar Usuários")
    
    if role != 'admin':
        st.error("Acesso negado.")
        return

    sb = get_supabase()
    
    c_list, c_form = st.columns([1.5, 1])
    
    try:
        res = sb.table("users").select("*").order("id").execute()
        users = res.data
    except: users = []

    if "edit_user" not in st.session_state:
        st.session_state.edit_user = {"id": None, "username": "", "password": "", "role": "user"}

    with c_list:
        st.subheader("Usuários Cadastrados")
        if users:
            for u in users:
                with st.container():
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.write(f"👤 **{u['username']}**")
                    c2.caption(f"{u.get('role', 'user').upper()}")
                    if c3.button("✏️", key=f"ed_{u['id']}"):
                        st.session_state.edit_user = u
                        st.rerun()
                    st.divider()
        else:
            st.info("Nenhum usuário encontrado.")

    with c_form:
        st.subheader("Editar / Criar")
        form = st.session_state.edit_user
        
        with st.form("user_form"):
            nu = st.text_input("Username", value=form["username"])
            np = st.text_input("Password", value=form["password"], type="password")
            nr = st.selectbox("Role (Permissão)", ["user", "master", "admin"], index=["user", "master", "admin"].index(form.get("role", "user")))
            
            if st.form_submit_button("💾 Salvar Usuário"):
                payload = {"username": nu, "password": np, "role": nr}
                if form["id"]:
                    sb.table("users").update(payload).eq("id", form["id"]).execute()
                    st.toast("Usuário atualizado!")
                else:
                    sb.table("users").insert(payload).execute()
                    st.toast("Usuário criado!")
                st.session_state.edit_user = {"id": None, "username": "", "password": "", "role": "user"}
                time.sleep(1)
                st.rerun()
                
        if st.button("Limpar Formulário"):
            st.session_state.edit_user = {"id": None, "username": "", "password": "", "role": "user"}
            st.rerun()
