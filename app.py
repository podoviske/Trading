import streamlit as st
from streamlit_option_menu import option_menu
from modules import database, ui

# Importando as Telas (Views)
from views import dashboard, trade, contas, atm, historico, admin

# ==============================================================================
# 1. CONFIGURAÇÃO E CSS
# ==============================================================================
st.set_page_config(
    page_title="EvoTrade Empire v300", 
    layout="wide", 
    page_icon="🦅",
    initial_sidebar_state="expanded"
)

# Aplica o estilo global (Dark Mode)
ui.apply_custom_css()

# ==============================================================================
# 2. SISTEMA DE LOGIN (Gatekeeper)
# ==============================================================================
if "password_correct" not in st.session_state: st.session_state.password_correct = False

def check_login():
    """Gerencia a tela de login."""
    def password_entered():
        u = st.session_state.username_input
        p = st.session_state.password_input
        try:
            # Verifica no banco via módulo database
            res = database.supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data:
                st.session_state.password_correct = True
                st.session_state.logged_user = u
                st.session_state.user_role = res.data[0].get('role', 'user')
            else:
                st.error("Credenciais inválidas.")
        except Exception as e:
            st.error(f"Erro de conexão: {e}")

    if not st.session_state.password_correct:
        # Layout Login
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.markdown('<div style="text-align:center; margin-top:50px;"><h1 style="color:#B20000; font-size:60px;">EVO</h1><h3>TRADE v300</h3></div>', unsafe_allow_html=True)
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("ACESSAR", on_click=password_entered, type="primary", use_container_width=True)
        return False
    return True

# ==============================================================================
# 3. MAESTRO (Navegação)
# ==============================================================================
if check_login():
    USER = st.session_state.logged_user
    ROLE = st.session_state.user_role

    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; margin-bottom:0;">EVO</h1><h3 style="color:white; margin-top:-15px;">TRADE</h3>', unsafe_allow_html=True)
        st.markdown("---")
        
        # Define opções do menu baseado no cargo
        opts = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        icons = ["grid", "currency-dollar", "gear", "clock"]
        
        if ROLE in ['master', 'admin']:
            opts.insert(2, "Contas")
            icons.insert(2, "briefcase")
            
        if ROLE == 'admin':
            opts.append("Admin")
            icons.append("shield-lock")
            
        selected = option_menu(
            menu_title=None,
            options=opts,
            icons=icons,
            styles={
                "nav-link-selected": {"background-color": "#B20000"},
                "nav-link": {"font-size": "14px", "margin": "5px"}
            }
        )
        
        st.markdown("---")
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()

    # ROTEADOR DE TELAS
    # Cada "if" chama a função show() do arquivo correspondente na pasta views/
    if selected == "Dashboard":
        dashboard.show(USER, ROLE)
        
    elif selected == "Registrar Trade":
        trade.show(USER, ROLE)
        
    elif selected == "Contas":
        contas.show(USER, ROLE)
        
    elif selected == "Configurar ATM":
        atm.show(USER, ROLE)
        
    elif selected == "Histórico":
        historico.show(USER, ROLE)
        
    elif selected == "Admin":
        admin.show(USER, ROLE)
