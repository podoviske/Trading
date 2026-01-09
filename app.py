import streamlit as st
from supabase import create_client

# Importação das Views (Telas)
import views.dashboard as dashboard
import views.trade as trade
import views.contas as contas
import views.atm as atm
import views.historico as historico
import views.plano as plano
import views.admin as admin
import views.antitilt as antitilt

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Apex Shield",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# --- 2. CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    /* === RESET E BASE === */
    .stApp { 
        background-color: #0a0a0a; 
    }
    
    /* === BOTÃO EXPANDIR SIDEBAR (FORÇADO) === */
    [data-testid="collapsedControl"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: fixed !important;
        left: 0 !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        z-index: 999999 !important;
        background-color: #B20000 !important;
        color: white !important;
        border-radius: 0 10px 10px 0 !important;
        padding: 15px 8px !important;
        min-width: 30px !important;
        min-height: 60px !important;
        box-shadow: 2px 0 10px rgba(0,0,0,0.5) !important;
    }
    
    [data-testid="collapsedControl"] svg {
        width: 20px !important;
        height: 20px !important;
        stroke: white !important;
    }
    
    /* === SIDEBAR === */
    [data-testid="stSidebar"] { 
        background-color: #0d0d0d !important; 
        border-right: 1px solid #1a1a1a;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0;
    }
    
    /* === LOGO === */
    .sidebar-logo {
        padding: 25px 20px;
        border-bottom: 1px solid #1a1a1a;
        margin-bottom: 10px;
    }
    
    .sidebar-logo h1 {
        font-size: 26px;
        font-weight: 800;
        margin: 0;
        letter-spacing: -1px;
    }
    
    .sidebar-logo .red {
        color: #B20000;
    }
    
    .sidebar-logo .white {
        color: #fff;
        font-weight: 400;
    }
    
    /* === SEÇÕES DO MENU === */
    .menu-section {
        padding: 20px 20px 8px 20px;
        font-size: 10px;
        font-weight: 600;
        color: #444;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    /* === PERFIL DO USUÁRIO === */
    .user-profile {
        padding: 15px 20px;
        margin: 10px;
        background-color: #111;
        border-radius: 10px;
        border: 1px solid #1a1a1a;
    }
    
    .user-info {
        display: flex;
        align-items: center;
    }
    
    .user-avatar {
        width: 38px;
        height: 38px;
        border-radius: 10px;
        background: linear-gradient(135deg, #B20000, #800000);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-weight: 700;
        font-size: 14px;
        margin-right: 12px;
    }
    
    .user-name {
        color: #fff;
        font-size: 14px;
        font-weight: 600;
    }
    
    .user-role {
        color: #555;
        font-size: 11px;
        text-transform: capitalize;
    }
    
    /* === INPUTS E BOTÕES === */
    .stTextInput > div > div > input { 
        color: white !important; 
        background-color: #0a0a0a !important; 
        border: 1px solid #222 !important;
        border-radius: 10px !important;
        padding: 12px 15px !important;
    }
    
    .stTextInput > div > div > input:focus { 
        border-color: #B20000 !important;
        box-shadow: 0 0 0 1px #B20000 !important;
    }
    
    .stButton > button { 
        border-radius: 10px !important; 
        font-weight: 600 !important;
        padding: 12px 20px !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(178, 0, 0, 0.3);
    }
    
    /* === LOGIN === */
    .login-container {
        max-width: 380px;
        margin: 60px auto 20px auto; 
        padding: 40px;
        background-color: #0d0d0d; 
        border-radius: 16px;
        border: 1px solid #1a1a1a;
        text-align: center;
    }
    
    .login-logo {
        font-size: 38px;
        font-weight: 800;
        margin-bottom: 5px;
        letter-spacing: -1px;
    }
    
    .login-logo .red {
        color: #B20000;
    }
    
    .login-logo .white {
        color: #fff;
        font-weight: 400;
    }
    
    .login-subtitle {
        color: #444;
        font-size: 12px;
        margin-bottom: 30px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    
    /* === ESCONDER ELEMENTOS PADRÃO DO STREAMLIT === */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* === ESTILO DO MENU OPTION_MENU === */
    .nav-link {
        border-radius: 10px !important;
        margin: 3px 10px !important;
    }
    
    /* Remove fundo claro do option_menu */
    div[data-testid="stSidebar"] .st-emotion-cache-1gwvy71,
    div[data-testid="stSidebar"] .st-emotion-cache-ue6h4q,
    div[data-testid="stSidebar"] nav,
    div[data-testid="stSidebar"] ul {
        background-color: #0d0d0d !important;
    }
    
    /* Garante fundo escuro em todo container do menu */
    .st-emotion-cache-1gwvy71 {
        background-color: #0d0d0d !important;
    }
    
    /* === DIVIDER === */
    .sidebar-divider {
        height: 1px;
        background-color: #1a1a1a;
        margin: 15px 20px;
    }
    
    /* === BOTÃO SAIR === */
    .logout-btn button {
        background-color: transparent !important;
        border: 1px solid #222 !important;
        color: #666 !important;
    }
    
    .logout-btn button:hover {
        background-color: #1a1a1a !important;
        border-color: #333 !important;
        color: #fff !important;
        transform: none !important;
        box-shadow: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. SISTEMA DE LOGIN ---
if "password_correct" not in st.session_state: 
    st.session_state["password_correct"] = False

def check_password():
    if st.session_state["password_correct"]: 
        return True

    _, col_login, _ = st.columns([1, 1.2, 1])
    
    with col_login:
        st.markdown('''
            <div class="login-container">
                <div class="login-logo">
                    <span class="red">EVO</span><span class="white">TRADE</span>
                </div>
                <div class="login-subtitle">Terminal de Operações</div>
            </div>
        ''', unsafe_allow_html=True)
        
        user = st.text_input("Usuário", key="login_user", placeholder="Digite seu usuário", label_visibility="collapsed")
        pwd = st.text_input("Senha", type="password", key="login_pwd", placeholder="Digite sua senha", label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("ACESSAR", use_container_width=True, type="primary"):
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
                    st.error("Credenciais incorretas")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")
                
    return False

# --- 4. APLICAÇÃO PRINCIPAL ---
if check_password():
    user = st.session_state["logged_user"]
    role = st.session_state.get("user_role", "user")
    
    # Pega inicial do usuário para o avatar
    user_initial = user[0].upper() if user else "U"

    # --- SIDEBAR REDESENHADA ---
    with st.sidebar:
        
        # Logo
        st.markdown('''
            <div class="sidebar-logo">
                <h1><span class="red">EVO</span><span class="white">TRADE</span></h1>
            </div>
        ''', unsafe_allow_html=True)
        
        # Perfil do usuário
        role_display = "Administrador" if role == "admin" else ("Master" if role == "master" else "Trader")
        st.markdown(f'''
            <div class="user-profile">
                <div class="user-info">
                    <div class="user-avatar">{user_initial}</div>
                    <div>
                        <div class="user-name">{user}</div>
                        <div class="user-role">{role_display}</div>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Monta menu baseado no role
        from streamlit_option_menu import option_menu
        
        # Lista base de opções
        options = ["Dashboard", "Registrar Trade", "Histórico", "Anti-Tilt"]
        icons = ["grid-1x2-fill", "lightning-charge-fill", "clock-history", "shield-check"]
        
        # Adiciona opções de gestão para admin/master
        if role in ['master', 'admin']:
            options.extend(["Contas", "Configurar ATM", "Plano de Trading"])
            icons.extend(["wallet2", "gear-fill", "file-earmark-text"])
            
        # Adiciona Admin só para admin
        if role == 'admin':
            options.append("Admin")
            icons.append("person-badge")
        
        # Seção label
        st.markdown('<div class="menu-section">Menu</div>', unsafe_allow_html=True)
        
        # Verifica se tem navegação forçada pendente
        navegacao_forcada = False
        if "navegar_para" in st.session_state:
            # Limpa navegação forçada e seta a página
            st.session_state["pagina_ativa"] = st.session_state.pop("navegar_para")
            navegacao_forcada = True
        
        selected = option_menu(
            menu_title=None,
            options=options,
            icons=icons,
            default_index=0,
            key="main_menu",
            styles={
                "container": {"padding": "0", "background-color": "#0d0d0d"},
                "menu-container": {"background-color": "#0d0d0d"},
                "icon": {"color": "#666", "font-size": "14px"}, 
                "nav-link": {
                    "font-size": "14px", 
                    "text-align": "left", 
                    "margin": "3px 10px",
                    "padding": "12px 15px",
                    "border-radius": "10px",
                    "background-color": "#0d0d0d",
                    "color": "#888",
                    "--hover-color": "#1a1a1a"
                },
                "nav-link-selected": {
                    "background-color": "#B20000", 
                    "color": "white", 
                    "font-weight": "600"
                },
            }
        )
        
        # Se usuário clicou no menu (e não foi navegação forçada), atualiza página ativa
        if not navegacao_forcada and selected != st.session_state.get("pagina_ativa"):
            st.session_state["pagina_ativa"] = selected
        
        # Divider
        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        
        # Botão Sair
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ROTEAMENTO DE PÁGINAS ---
    # Usa página ativa (navegação forçada) ou seleção do menu
    pagina_atual = st.session_state.get("pagina_ativa", selected)
    
    if pagina_atual == "Dashboard":
        dashboard.show(user, role)
        
    elif pagina_atual == "Registrar Trade":
        trade.show(user, role)
        
    elif pagina_atual == "Contas":
        contas.show(user, role)
        
    elif pagina_atual == "Configurar ATM":
        atm.show(user, role)
        
    elif pagina_atual == "Histórico":
        historico.show(user, role)
    
    elif pagina_atual == "Anti-Tilt":
        antitilt.show(user, role)
        
    elif pagina_atual == "Plano de Trading":
        plano.show()
        
    elif pagina_atual == "Admin":
        admin.show(user, role)
