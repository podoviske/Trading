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

# --- 2. CSS GLOBAL (Tema Dark Profundo) ---
st.markdown("""
    <style>
    /* Fundo e Textos */
    .stApp { background-color: #050505; }
    h1, h2, h3 { color: white; font-family: 'Segoe UI', sans-serif; }
    p, label, span { color: #b0b0b0; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0F0F0F !important; border-right: 1px solid #1E1E1E; }
    
    /* Inputs */
    .stTextInput>div>div>input { color: white; background-color: #111; border: 1px solid #333; }
    .stNumberInput>div>div>input { color: white; background-color: #111; border: 1px solid #333; }
    .stSelectbox>div>div>div { color: white; background-color: #111; border: 1px solid #333; }
    
    /* Botões */
    .stButton>button { border-radius: 6px; font-weight: 600; }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #000; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #555; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SISTEMA DE LOGIN (Mantido da v201) ---
if "password_correct" not in st.session_state: st.session_state["password_correct"] = False

def check_password():
    # Se já logou, pula
    if st.session_state["password_correct"]: return True

    # Interface de Login
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #B20000; margin-bottom:0;'>EVO</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: white; margin-top:-15px;'>TRADE EMPIRE</h3>", unsafe_allow_html=True)
        st.write("---")
        
        user = st.text_input("Usuário", key="login_user")
        pwd = st.text_input("Senha", type="password", key="login_pwd")
        
        if st.button("ACESSAR TERMINAL", use_container_width=True, type="primary"):
            try:
                url = st.secrets["SUPABASE_URL"]
                key = st.secrets["SUPABASE_KEY"]
                supabase = create_client(url, key)
                
                res = supabase.table("users").select("*").eq("username", user).eq("password", pwd).execute()
                
                if res.data:
                    st.session_state["password_correct"] = True
                    st.session_state["logged_user"] = user
                    st.session_state["user_role"] = res.data[0].get('role', 'user')
                    st.session_state["supabase"] = supabase # Salva cliente na sessão
                    st.rerun()
                else:
                    st.error("Acesso Negado.")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")
                
    return False

# --- 4. APLICAÇÃO PRINCIPAL ---
if check_password():
    user = st.session_state["logged_user"]
    role = st.session_state.get("user_role", "user")

    # --- MENU LATERAL ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        st.write(f"👤 **{user}**")
        
        # Definição do Menu
        options = ["Dashboard", "Registrar Trade", "Histórico", "Plano de Trading"]
        icons = ["grid", "lightning-charge", "clock-history", "file-text"]
        
        # Apenas Admins/Master veem gestão
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
