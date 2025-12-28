import streamlit as st
from modules import database

def show(user, role):
    st.title("👥 Admin")
    if role != "admin":
        st.error("Acesso negado.")
        return

    users = database.supabase.table("users").select("*").execute().data
    for u in users:
        c1, c2 = st.columns(2)
        c1.write(f"**{u['username']}** ({u['role']})")
        if c2.button("Editar", key=u['id']):
            st.session_state.edit_u = u

    if 'edit_u' in st.session_state:
        with st.form("edit"):
            u = st.session_state.edit_u
            r = st.selectbox("Role", ["user", "master", "admin"], index=["user","master","admin"].index(u['role']))
            if st.form_submit_button("Salvar"):
                database.supabase.table("users").update({"role": r}).eq("id", u['id']).execute()
                del st.session_state.edit_u
                st.rerun()
