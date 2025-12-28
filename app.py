import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client

# Importação das Views (Telas)
import views.dashboard as dashboard
import views.trade as trade
import views.contas as contas
import views.atm as atm
import views.historico as historico
import views.plano as plano
import views.admin as admin

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="EvoTrade Empire v300",
    layout="wide",
    page_icon="🦅",
    initial_sidebar_state="expanded"
)

# --- 2. CSS ORIGINAL (RESTAURADO DA v201) ---
st.markdown("""
    <style>
    /* Fundo Geral (Cinza Chumbo da v201) */
    .stApp { background-color: #0F0F0F; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0F0F0F !important; border-right: 1px solid #1E1E1E; }
    
    /* Estilo do Login Antigo */
    .login-container {
        max-width: 400px;
        margin: 50px auto; 
        padding: 30px;
        background-color: #161616; 
        border-radius: 15px;
        border: 1px solid #B20000; 
        text-align: center;
    }
    .logo-main { color: #B20000; font-size: 50px; font-weight: 900; line-height: 1; }
    .logo-sub { color: white; font-size: 35px; font-weight: 700; margin-top: -10px; margin-bottom: 20px; }
    
    /* Inputs e Botões */
    .stTextInput>div>div>input { color: white; background-color: #111; border: 1px solid #333; }
    .stButton>button { border-radius: 6px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SISTEMA DE LOGIN (DESIGN ANTIGO) ---
if "password_correct" not in st.session_state: st.session_state["password_correct"] = False

def check_password():
    if st.session_state["password_correct"]: return True

    # Layout de Colunas para Centralizar (Estilo v201)
    _, col_login, _ = st.columns([1, 2, 1])
    
    with col_login:
        # Abre o Container Estilizado
        st.markdown('<div class="login-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div>', unsafe_allow_html=True)
        
        user = st.text_input("Usuário", key="login_user")
        pwd = st.text_input("Senha", type="password", key="login_pwd")
        
        if st.button("ACESSAR TERMINAL", use_container_width=True):
            try:
                url = st.secrets["SUPABASE_URL"]
                key = st.secrets["SUPABASE_KEY"]
                supabase = create_client(url, key)
                
                res = supabase.table("users").select("*").eq("username", user).eq("password", pwd).execute()
                
                if res.data:
                    st.session_state["password_correct"] = True
                    st.session_state["logged_user"] = user
                    st.session_state["user_role"] = res.data[0].get('role', 'user')
                    st.session_state["supabase"] = supabase
                    st.rerun()
                else:
                    st.error("Credenciais Incorretas")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")
        
        # Fecha o Container
        st.markdown('</div>', unsafe_allow_html=True)
                
    return False

# --- 4. APLICAÇÃO PRINCIPAL ---
if check_password():
    user = st.session_state["logged_user"]
    role = st.session_state.get("user_role", "user")

    # --- MENU LATERAL ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        st.write(f"👤 **{user}**")
        
        options = ["Dashboard", "Registrar Trade", "Histórico", "Plano de Trading"]
        icons = ["grid", "lightning-charge", "clock-history", "file-text"]
        
        if role in ['master', 'admin']:
            options.insert(2, "Contas")
            icons.insert(2, "wallet2")
            options.insert(3, "Configurar ATM")
            icons.insert(3, "gear")
            
        if role == 'admin':
            options.append("Admin")
            icons.append("person-badge")

        selected = option_menu(
            menu_title=None,
            options=options,
            icons=icons,
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#888", "font-size": "14px"}, 
                "nav-link": {"font-size": "14px", "text-align": "left", "margin":"5px", "--hover-color": "#222"},
                "nav-link-selected": {"background-color": "#B20000", "color": "white", "font-weight": "bold"},
            }
        )
        
        st.write("---")
        if st.button("Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- ROTEAMENTO DE PÁGINAS ---
    if selected == "Dashboard":
        dashboard.show(user, role)
        
    elif selected == "Registrar Trade":
        trade.show(user, role)
        
    elif selected == "Contas":
        contas.show(user, role)
        
    elif selected == "Configurar ATM":
        atm.show(user, role)
        
    elif selected == "Histórico":
        historico.show(user, role)
        
    elif selected == "Plano de Trading":
        plano.show()
        
    elif selected == "Admin":
        admin.show(user, role)
