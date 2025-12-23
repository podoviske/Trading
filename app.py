import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
import json
import uuid
import time
from supabase import create_client, Client

# --- 1. CONEXÃO SUPABASE ---
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro crítico: Chaves do Supabase não encontradas nos Secrets.")

# --- 2. CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="EvoTrade Terminal", layout="wide", page_icon="📈")

# --- 3. SISTEMA DE LOGIN ---
def check_password():
    def password_entered():
        u = st.session_state.get("username_input")
        p = st.session_state.get("password_input")
        try:
            res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data:
                st.session_state["password_correct"] = True
                st.session_state["logged_user"] = u
            else:
                st.session_state["password_correct"] = False
        except Exception as e:
            st.error(f"Erro de conexão (Verifique as Keys): {e}")

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown("""
            <style>
            .login-container {
                max-width: 400px; margin: 50px auto; padding: 30px;
                background-color: #161616; border-radius: 15px;
                border: 1px solid #B20000; text-align: center;
            }
            .logo-main { color: #B20000; font-size: 50px; font-weight: 900; }
            .logo-sub { color: white; font-size: 35px; font-weight: 700; margin-top: -15px; }
            </style>
        """, unsafe_allow_html=True)
        
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.markdown('<div class="login-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div>', unsafe_allow_html=True)
            st.write("---")
            st.text_input("Usuário", key="username_input")
            st.text_input("Senha", type="password", key="password_input")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
            if st.session_state.get("password_correct") == False:
                st.error("😕 Credenciais incorretas.")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if check_password():
    # --- 4. CONSTANTES E ESTILOS ---
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}

    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #0F0F0F !important; border-right: 1px solid #1E1E1E; }
        .stApp { background-color: #0F0F0F; }
        .metric-container { 
            background-color: #161616; border: 1px solid #262626; padding: 15px; 
            border-radius: 10px; text-align: center; margin-bottom: 12px;
        }
        .metric-label { color: #888; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .metric-value { color: white; font-size: 22px; font-weight: bold; margin-top: 5px; }
        .piscante-erro { 
            padding: 15px; border-radius: 5px; color: white; font-weight: bold; 
            text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000; 
        }
        @keyframes blinking { 0% { background-color: #440000; } 50% { background-color: #B20000; } 100% { background-color: #440000; } }
        </style>
    """, unsafe_allow_html=True)

    # --- 5. FUNÇÕES DE DADOS ---
    def load_trades_db():
        try:
            res = supabase.table("trades").select("*").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.date
                df['created_at'] = pd.to_datetime(df['created_at'])
            return df
        except:
            return pd.DataFrame()

    def load_atms_db():
        try:
            res = supabase.table("atm_configs").select("*").execute()
            return {item['nome']: item for item in res.data}
        except:
            return {}

    def card_metric(label, value, color="white"):
        st.markdown(f'<div class="metric-container"><div class="metric-label">{label}</div><div class="metric-value" style="color: {color};">{value}</div></div>', unsafe_allow_html=True)

    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        if st.session_state["logged_user"] == "admin": menu.append("Gerenciar Usuários")
        selected = option_menu(None, menu, icons=["grid", "currency-dollar", "gear", "clock", "people"], styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    atm_db = load_atms_db()

    # --- 7. ABA: DASHBOARD ---
    if selected == "Dashboard":
        st.title("📊 Analytics Pessoal")
        df = load_trades_db()
        if not df.empty:
            df_u = df[df['usuario'] == st.session_state["logged_user"]]
            if not df_u.empty:
                t_pl = df_u['resultado'].sum()
                c1, c2, c3, c4 = st.columns(4)
                with c1: card_metric("P&L TOTAL", f"${t_pl:,.2f}", "#00FF88" if t_pl >= 0 else "#FF4B4B")
                with c2: card_metric("TRADES", str(len(df_u)))
                with c3:
                    wr = (len(df_u[df_u['resultado'] > 0]) / len(df_u)) * 100
                    card_metric("WIN RATE", f"{wr:.1f}%", "#B20000")
                with c4: card_metric("USER", st.session_state["logged_user"])
                
                df_u = df_u.sort_values('created_at')
                df_u['Acumulado'] = df_u['resultado'].cumsum()
                fig = px.area(df_u, x=range(len(df_u)), y='Acumulado', title="Curva de Patrimônio", template="plotly_dark")
                fig.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Sem operações registradas.")
        else: st.warning("Banco de dados vazio.")

    # --- 8. REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_sel = st.selectbox("🎯 Escolher ATM", ["Manual"] + list(atm_db.keys()))
        config = atm_db.get(atm_sel, {"lote": 1, "stop": 0.0, "parciais": "[]"})
        
        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date())
            atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        with f2:
            lt = st.number_input("Contratos", min_value=1, value=int(config["lote"]))
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]))
            up = st.file_uploader("📸 Print", type=['png', 'jpg', 'jpeg'])
        with f3:
            st.write("**Saídas (Alocação)**")
            parciais_list = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
            saidas = []
            aloc = 0
            for i in range(len(parciais_list) if parciais_list else 1):
                c_pts, c_qtd = st.columns(2)
                p_val = parciais_list[i] if i < len(parciais_list) else {"pts": 0.0, "qtd": lt}
                pts = c_pts.number_input(f"Pts P{i+1}", value=float(p_val["pts"]), key=f"pts_{i}")
                qtd = c_qtd.number_input(f"Qtd Contratos {i+1}", value=int(p_val["qtd"]), key=f"qtd_{i}")
                saidas.append({"pts": pts, "qtd": qtd})
                aloc += qtd
            
            if lt != aloc:
                st.markdown(f'<div class="piscante-erro">FALTAM {lt-aloc} CONTRATOS</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Posição Sincronizada")

        if st.button("💾 REGISTRAR TRADE", use_container_width=True) and lt == aloc:
            with st.spinner("Salvando..."):
                res_fin = sum([s["pts"] * MULTIPLIERS[atv] * s["qtd"] for s in saidas])
                pt_med = sum([s["pts"] * s["qtd"] for s in saidas]) / lt
                trade_id = str(uuid.uuid4())
                img_url = ""
                if up:
                    file_path = f"{trade_id}.png"
                    supabase.storage.from_("prints").upload(file_path, up.getvalue())
                    img_url = supabase.storage.from_("prints").get_public_url(file_path)

                supabase.table("trades").insert({
                    "id": trade_id, "data": str(dt), "ativo": atv, "contexto": ctx,
                    "direcao": dr, "lote": lt, "resultado": res_fin, "pts_medio": pt_med,
                    "prints": img_url, "usuario": st.session_state["logged_user"],
                    "risco_fin": (stp * MULTIPLIERS[atv] * lt)
                }).execute()
                st.success("🎯 Trade Registrado!"); time.sleep(1); st.rerun()

    # --- 9. CONFIGURAR ATM ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Editor de ATM")
        with st.expander("✨ Novo Template", expanded=True):
            nome_atm = st.text_input("Nome da Estratégia")
            c_l, c_s = st.columns(2)
            lote_atm = c_l.number_input("Lote Total", min_value=1)
            stop_atm = c_s.number_input("Stop Padrão (Pts)", min_value=0.0)
            
            st.write("Parciais")
            p1_pts = st.number_input("Pts Alvo 1", min_value=0.0)
            p1_qtd = st.number_input("Qtd Alvo 1", min_value=1)
            if st.button("💾 Salvar ATM"):
                parciais_json = [{"pts": p1_pts, "qtd": p1_qtd}]
                supabase.table("atm_configs").insert({"nome": nome_atm, "lote": lote_atm, "stop": stop_atm, "parciais": parciais_json}).execute()
                st.success("ATM Salva!"); st.rerun()

    # --- 10. HISTÓRICO ---
    elif selected == "Histórico":
        st.title("📜 Histórico")
        df = load_trades_db()
        if not df.empty:
            df_h = df[df['usuario'] == st.session_state["logged_user"]].sort_values('created_at', ascending=False)
            for _, row in df_h.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([1.5, 2, 1])
                    if row.get('prints'): c1.image(row['prints'], use_container_width=True)
                    else: c1.info("Sem Print")
                    c2.write(f"**{row['data']} - {row['ativo']} ({row['contexto']})**")
                    c2.write(f"Lote: {row['lote']} | Pts Médio: {row['pts_medio']:.1f} | {row['direcao']}")
                    res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
                    col3.markdown(f"<h2 style='color:{res_c}'>${row['resultado']:,.2f}</h2>", unsafe_allow_html=True)
                    if c3.button("Deletar", key=row['id']):
                        supabase.table("trades").delete().eq("id", row['id']).execute(); st.rerun()
                    st.divider()

    # --- 11. GERENCIAR USUÁRIOS ---
    elif selected == "Gerenciar Usuários":
        st.title("👥 Usuários")
        res = supabase.table("users").select("*").execute()
        users_df = pd.DataFrame(res.data)
        with st.expander("Novo Usuário"):
            nu = st.text_input("Username")
            np = st.text_input("Password", type="password")
            if st.button("Criar"):
                supabase.table("users").insert({"username": nu, "password": np}).execute()
                st.success("Criado!"); st.rerun()
        if not users_df.empty:
            st.table(users_df[['username', 'created_at']])
