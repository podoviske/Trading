import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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

# --- CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    /* Card da Galeria */
    .trade-card {
        background-color: #161616;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 15px;
        border: 1px solid #333;
        transition: transform 0.2s, border-color 0.2s;
    }
    .trade-card:hover {
        transform: translateY(-3px);
        border-color: #B20000;
    }
    .card-img-container {
        width: 100%;
        height: 140px;
        background-color: #222;
        border-radius: 5px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 10px;
    }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 14px; font-weight: 700; color: white; margin-bottom: 2px; }
    .card-sub { font-size: 11px; color: #888; margin-bottom: 8px; }
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; }
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }

    /* Geral */
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
    .risco-alert {
        color: #FF4B4B; font-weight: bold; font-size: 16px; margin-top: 5px;
        background-color: rgba(255, 75, 75, 0.1); padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #FF4B4B;
    }
    @keyframes blinking { 0% { background-color: #440000; } 50% { background-color: #B20000; } 100% { background-color: #440000; } }
    </style>
""", unsafe_allow_html=True)

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
            st.error(f"Erro de conexão: {e}")

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
    # --- 4. CONSTANTES ---
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}

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
        if st.button("Sair / Logout"): 
            st.session_state.clear()
            st.rerun()

    # --- 7. DASHBOARD ---
    if selected == "Dashboard":
        st.title("📊 Analytics Pessoal")
        df = load_trades_db()
        if not df.empty:
            df_u = df[df['usuario'] == st.session_state["logged_user"]]
            if not df_u.empty:
                filtro_periodo = st.selectbox("📅 Período", ["Geral", "Hoje", "Esta Semana", "Este Mês"])
                
                if filtro_periodo == "Hoje":
                    df_u = df_u[df_u['data'] == datetime.now().date()]
                elif filtro_periodo == "Esta Semana":
                    inicio_semana = datetime.now().date() - timedelta(days=datetime.now().weekday())
                    df_u = df_u[df_u['data'] >= inicio_semana]
                elif filtro_periodo == "Este Mês":
                    inicio_mes = datetime.now().date().replace(day=1)
                    df_u = df_u[df_u['data'] >= inicio_mes]

                if df_u.empty:
                    st.info(f"Sem trades registrados em: {filtro_periodo}")
                else:
                    t_pl = df_u['resultado'].sum()
                    wins = len(df_u[df_u['resultado'] > 0])
                    total = len(df_u)
                    wr = (wins / total) * 100 if total > 0 else 0
                    
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: card_metric("P&L LIQUIDO", f"${t_pl:,.2f}", "#00FF88" if t_pl >= 0 else "#FF4B4B")
                    with c2: card_metric("TRADES", str(total))
                    with c3: card_metric("WIN RATE", f"{wr:.1f}%", "#B20000")
                    with c4: card_metric("FATOR DE LUCRO", f"{(df_u[df_u['resultado']>0]['resultado'].sum() / abs(df_u[df_u['resultado']<0]['resultado'].sum()) if len(df_u[df_u['resultado']<0]) > 0 else 0):.2f}")

                    g1, g2 = st.columns([2, 1])
                    with g1:
                        df_u = df_u.sort_values('created_at')
                        df_u['Acumulado'] = df_u['resultado'].cumsum()
                        fig = px.area(df_u, x='data', y='Acumulado', title="Curva de Patrimônio", template="plotly_dark")
                        fig.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                        st.plotly_chart(fig, use_container_width=True)
                    with g2:
                        fig_pie = px.pie(df_u, names='ativo', title="Distribuição por Ativo", template="plotly_dark", hole=0.4)
                        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_pie, use_container_width=True)
            else: st.info("Sem operações registradas para este usuário.")
        else: st.warning("Banco de dados vazio.")

    # --- 8. REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Registro de Operação")
        atm_db = load_atms_db()
        atm_sel = st.selectbox("🎯 Escolher Template ATM", ["Manual"] + list(atm_db.keys()))
        
        if atm_sel != "Manual":
            config = atm_db[atm_sel]
            lt_default = int(config["lote"])
            stp_default = float(config["stop"])
            try:
                parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
            except:
                parciais_pre = []
        else:
            lt_default = 1
            stp_default = 0.0
            parciais_pre = []

        f1, f2, f3 = st.columns([1, 1, 2.5])
        with f1:
            dt = st.date_input("Data", datetime.now().date())
            atv = st.selectbox("Ativo", ["MNQ", "NQ"])
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
        with f2:
            lt = st.number_input("Contratos Total", min_value=1, value=lt_default)
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=stp_default, step=0.25)
            if stp > 0:
                risco_calc = stp * MULTIPLIERS[atv] * lt
                st.markdown(f'<div class="risco-alert">📉 Risco Estimado: ${risco_calc:,.2f}</div>', unsafe_allow_html=True)
            up = st.file_uploader("📸 Anexar Print", type=['png', 'jpg', 'jpeg'])

        with f3:
            st.write("**Saídas (Alocação)**")
            if "num_parciais" not in st.session_state or atm_sel != st.session_state.get("last_atm"):
                st.session_state.num_parciais = len(parciais_pre) if parciais_pre else 1
                st.session_state.last_atm = atm_sel

            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("➕ Add Parcial"): st.session_state.num_parciais += 1
            if col_btn2.button("🧹 Limpar"): st.session_state.num_parciais = 1; st.rerun()

            saidas = []
            aloc = 0
            for i in range(st.session_state.num_parciais):
                c_pts, c_qtd = st.columns(2)
                val_pts = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
                val_qtd = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
                pts = c_pts.number_input(f"Pts Alvo {i+1}", value=val_pts, key=f"p_pts_{i}_{atm_sel}", step=0.25)
                qtd = c_qtd.number_input(f"Contratos {i+1}", value=val_qtd, key=f"p_qtd_{i}_{atm_sel}", min_value=0)
                saidas.append({"pts": pts, "qtd": qtd})
                aloc += qtd
            
            if lt != aloc:
                diff = lt - aloc
                st.markdown(f'<div class="piscante-erro">{"FALTAM" if diff > 0 else "SOBRAM"} {abs(diff)} CONTRATOS</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Posição Sincronizada")

        st.divider()
        col_gain, col_loss = st.columns(2)
        btn_registrar = False
        if col_gain.button("🟢 REGISTRAR GAIN", use_container_width=True, disabled=(lt != aloc)): btn_registrar = True
        if col_loss.button("🔴 REGISTRAR STOP FULL", use_container_width=True): saidas = [{"pts": -stp, "qtd": lt}]; btn_registrar = True

        if btn_registrar:
            with st.spinner("Salvando..."):
                try:
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
                    st.balloons() 
                    st.success(f"✅ SUCESSO! Resultado: ${res_fin:,.2f}")
                    time.sleep(2); st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    # --- 9. CONFIGURAR ATM ---
    elif selected == "Configurar ATM":
        st.title("⚙️ Gerenciar ATMs")

        if "atm_form_data" not in st.session_state:
            st.session_state.atm_form_data = {
                "id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]
            }

        def reset_atm_form():
            st.session_state.atm_form_data = {
                "id": None, "nome": "", "lote": 1, "stop": 0.0, "parciais": [{"pts": 0.0, "qtd": 1}]
            }

        res = supabase.table("atm_configs").select("*").order("nome").execute()
        existing_atms = res.data

        c_form, c_list = st.columns([1.5, 1])

        with c_list:
            st.subheader("📋 Estratégias Salvas")
            if st.button("✨ Criar Nova (Limpar)", use_container_width=True):
                reset_atm_form(); st.rerun()
            if existing_atms:
                for item in existing_atms:
                    with st.expander(f"📍 {item['nome']}", expanded=False):
                        st.write(f"**Lote:** {item['lote']} | **Stop:** {item['stop']}")
                        c_edit, c_del = st.columns(2)
                        if c_edit.button("✏️ Editar", key=f"edit_{item['id']}"):
                            p_data = item['parciais'] if isinstance(item['parciais'], list) else json.loads(item['parciais'])
                            st.session_state.atm_form_data = {
                                "id": item['id'], "nome": item['nome'], "lote": item['lote'],
                                "stop": item['stop'], "parciais": p_data
                            }
                            st.rerun()
                        if c_del.button("🗑️ Excluir", key=f"del_{item['id']}"):
                            supabase.table("atm_configs").delete().eq("id", item['id']).execute()
                            if st.session_state.atm_form_data["id"] == item['id']: reset_atm_form()
                            st.rerun()
            else: st.info("Nenhuma estratégia salva.")

        with c_form:
            form_data = st.session_state.atm_form_data
            titulo = f"✏️ Editando: {form_data['nome']}" if form_data["id"] else "✨ Nova Estratégia"
            st.subheader(titulo)
            
            new_nome = st.text_input("Nome da Estratégia", value=form_data["nome"])
            c_l, c_s = st.columns(2)
            new_lote = c_l.number_input("Lote Total", min_value=1, value=int(form_data["lote"]))
            new_stop = c_s.number_input("Stop Padrão (Pts)", min_value=0.0, value=float(form_data["stop"]), step=0.25)
            
            st.markdown("---")
            st.write("🎯 Configuração de Alvos")
            c_add, c_rem = st.columns([1, 4])
            if c_add.button("➕ Adicionar Alvo"): form_data["parciais"].append({"pts": 0.0, "qtd": 1})
            if c_rem.button("➖ Remover Último") and len(form_data["parciais"]) > 1: form_data["parciais"].pop()
            
            updated_partials = []
            total_aloc = 0
            for i, p in enumerate(form_data["parciais"]):
                c1, c2 = st.columns(2)
                p_pts = c1.number_input(f"Alvo {i+1} (Pts)", value=float(p["pts"]), key=f"edm_pts_{i}", step=0.25)
                p_qtd = c2.number_input(f"Qtd {i+1}", value=int(p["qtd"]), min_value=1, key=f"edm_qtd_{i}")
                updated_partials.append({"pts": p_pts, "qtd": p_qtd})
                total_aloc += p_qtd
            
            if total_aloc != new_lote: st.warning(f"⚠️ Atenção: Soma das parciais ({total_aloc}) difere do Lote Total ({new_lote}).")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("💾 SALVAR ESTRATÉGIA", use_container_width=True):
                payload = {"nome": new_nome, "lote": new_lote, "stop": new_stop, "parciais": updated_partials}
                if form_data["id"]:
                    supabase.table("atm_configs").update(payload).eq("id", form_data["id"]).execute()
                    st.toast("Atualizado!", icon="✅")
                else:
                    supabase.table("atm_configs").insert(payload).execute()
                    st.toast("Criado!", icon="✨")
                time.sleep(1); reset_atm_form(); st.rerun()

    # --- 10. HISTÓRICO (GALERIA 4 CARDS + MODAL GRANDE) ---
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        
        col_f1, col_f2 = st.columns(2)
        filtro_ativo = col_f1.multiselect("Filtrar por Ativo", ["NQ", "MNQ"])
        filtro_res = col_f2.selectbox("Filtrar Resultado", ["Todos", "Wins", "Losses"])
        
        df = load_trades_db()
        if not df.empty:
            df_h = df[df['usuario'] == st.session_state["logged_user"]]
            if filtro_ativo: df_h = df_h[df_h['ativo'].isin(filtro_ativo)]
            if filtro_res == "Wins": df_h = df_h[df_h['resultado'] > 0]
            if filtro_res == "Losses": df_h = df_h[df_h['resultado'] < 0]
            
            df_h = df_h.sort_values('created_at', ascending=False)
            
            # Modal de Detalhes (Grande)
            @st.dialog("Detalhes da Operação", width="large")
            def show_trade_details(row):
                # Imagem Grande no Topo
                if row.get('prints'): st.image(row['prints'], use_container_width=True)
                else: st.info("Sem Print disponível.")
                
                st.markdown("---")
                
                # Dados
                c1, c2, c3 = st.columns(3)
                c1.write(f"📅 **Data:** {row['data']}")
                c1.write(f"📈 **Ativo:** {row['ativo']}")
                
                c2.write(f"⚖️ **Lote:** {row['lote']}")
                c2.write(f"🎯 **Médio:** {row['pts_medio']:.2f} pts")
                
                c3.write(f"🔄 **Direção:** {row['direcao']}")
                c3.write(f"🧠 **Contexto:** {row['contexto']}")
                
                res_c = "green" if row['resultado'] >= 0 else "red"
                st.markdown(f"<h1 style='color:{res_c}; text-align:center; font-size:40px;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
                
                if st.button("🗑️ DELETAR REGISTRO", type="primary", use_container_width=True):
                    supabase.table("trades").delete().eq("id", row['id']).execute()
                    st.rerun()

            # Grid Layout (4 Colunas)
            cols = st.columns(4)
            for i, (index, row) in enumerate(df_h.iterrows()):
                with cols[i % 4]: # Distribui entre as 4 colunas
                    res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                    res_fmt = f"${row['resultado']:,.2f}"
                    
                    img_html = f'<img src="{row["prints"]}" class="card-img">' if row.get('prints') else '<div style="width:100%; height:100%; background:#333; display:flex; align-items:center; justify-content:center; color:#555;">Sem Foto</div>'
                    
                    st.markdown(f"""
                        <div class="trade-card">
                            <div class="card-img-container">{img_html}</div>
                            <div class="card-title">{row['ativo']} - {row['direcao']}</div>
                            <div class="card-sub">{row['data']} • {row['contexto']}</div>
                            <div class="{res_class}">{res_fmt}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("👁️ Ver", key=f"btn_{row['id']}", use_container_width=True):
                        show_trade_details(row)

    # --- 11. GERENCIAR USUÁRIOS ---
    elif selected == "Gerenciar Usuários":
        st.title("👥 Usuários do Terminal")
        res = supabase.table("users").select("*").execute()
        users_df = pd.DataFrame(res.data)
        
        with st.expander("Novo Usuário"):
            nu = st.text_input("Username")
            np = st.text_input("Password", type="password")
            if st.button("Criar Acesso"):
                supabase.table("users").insert({"username": nu, "password": np}).execute()
                st.success("Usuário Criado!"); st.rerun()
        
        if not users_df.empty:
            cols_show = ['username']
            if 'created_at' in users_df.columns: cols_show.append('created_at')
            st.table(users_df[cols_show])
