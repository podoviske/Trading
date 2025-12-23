import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
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
    /* Cards do Histórico */
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
        width: 100%; height: 140px; background-color: #222;
        border-radius: 5px; overflow: hidden; display: flex;
        align-items: center; justify-content: center; margin-bottom: 10px;
    }
    .card-img { width: 100%; height: 100%; object-fit: cover; }
    .card-title { font-size: 14px; font-weight: 700; color: white; margin-bottom: 2px; }
    .card-sub { font-size: 11px; color: #888; margin-bottom: 8px; }
    .card-res-win { font-size: 16px; font-weight: 800; color: #00FF88; }
    .card-res-loss { font-size: 16px; font-weight: 800; color: #FF4B4B; }

    /* Métricas do Dashboard */
    .metric-container { 
        background-color: #161616; border: 1px solid #262626; padding: 15px; 
        border-radius: 10px; text-align: center; margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-label { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
    .metric-value { color: white; font-size: 24px; font-weight: 800; margin-top: 5px; }
    .metric-sub { font-size: 12px; margin-top: 2px; }

    /* Geral */
    [data-testid="stSidebar"] { background-color: #0F0F0F !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    
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

    def card_metric(label, value, sub_value="", color="white"):
        sub_html = f'<div class="metric-sub" style="color: #666;">{sub_value}</div>' if sub_value else ""
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color: {color};">{value}</div>
                {sub_html}
            </div>
        """, unsafe_allow_html=True)

    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.markdown('<h1 style="color:#B20000; font-weight:900; margin-bottom:0;">EVO</h1><h2 style="color:white; margin-top:-15px;">TRADE</h2>', unsafe_allow_html=True)
        menu = ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"]
        if st.session_state["logged_user"] == "admin": menu.append("Gerenciar Usuários")
        selected = option_menu(None, menu, icons=["grid", "currency-dollar", "gear", "clock", "people"], styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair / Logout"): 
            st.session_state.clear()
            st.rerun()

    # --- 7. ABA: DASHBOARD PROFISSIONAL ---
    if selected == "Dashboard":
        st.title("📊 Central de Controle")
        df_raw = load_trades_db()
        
        if not df_raw.empty:
            df = df_raw[df_raw['usuario'] == st.session_state["logged_user"]]
            
            if not df.empty:
                # --- FILTROS ---
                with st.expander("🔍 Filtros Avançados", expanded=True):
                    col_d1, col_d2, col_ctx = st.columns([1, 1, 2])
                    
                    # Filtro de Data
                    min_date = df['data'].min()
                    max_date = df['data'].max()
                    
                    d_inicio = col_d1.date_input("Data Início", min_date)
                    d_fim = col_d2.date_input("Data Fim", max_date)
                    
                    # Filtro de Contexto
                    all_contexts = list(df['contexto'].unique())
                    filters_ctx = col_ctx.multiselect("Filtrar Contextos", all_contexts, default=all_contexts)

                # Aplica Filtros
                mask = (df['data'] >= d_inicio) & (df['data'] <= d_fim) & (df['contexto'].isin(filters_ctx))
                df_filtered = df[mask].copy()

                if df_filtered.empty:
                    st.warning("⚠️ Nenhum trade encontrado com os filtros selecionados.")
                else:
                    # --- CÁLCULO DE KPIs ---
                    total_trades = len(df_filtered)
                    net_profit = df_filtered['resultado'].sum()
                    
                    wins = df_filtered[df_filtered['resultado'] > 0]
                    losses = df_filtered[df_filtered['resultado'] < 0]
                    
                    gross_profit = wins['resultado'].sum()
                    gross_loss = abs(losses['resultado'].sum())
                    
                    # Profit Factor
                    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                    pf_str = f"{pf:.2f}" if gross_loss > 0 else "∞"
                    
                    # Win Rate
                    win_rate = (len(wins) / total_trades) * 100
                    
                    # Payoff (Risco:Retorno Real)
                    avg_win = wins['resultado'].mean() if not wins.empty else 0
                    avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0
                    payoff = avg_win / avg_loss if avg_loss > 0 else 0
                    
                    # Expectativa Matemática (Expectancy)
                    loss_rate = (len(losses) / total_trades)
                    expectancy = ( (win_rate/100) * avg_win ) - ( loss_rate * avg_loss )
                    
                    # Drawdown Máximo
                    df_filtered = df_filtered.sort_values('created_at')
                    df_filtered['equity'] = df_filtered['resultado'].cumsum()
                    df_filtered['peak'] = df_filtered['equity'].cummax()
                    df_filtered['drawdown'] = df_filtered['equity'] - df_filtered['peak']
                    max_dd = df_filtered['drawdown'].min()

                    # --- EXIBIÇÃO KPIs (LINHA 1) ---
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: card_metric("RESULTADO LÍQUIDO", f"${net_profit:,.2f}", f"Bruto: ${gross_profit:,.0f} / -${gross_loss:,.0f}", "#00FF88" if net_profit >= 0 else "#FF4B4B")
                    with c2: card_metric("FATOR DE LUCRO (PF)", pf_str, "Ideal > 1.5", "#B20000")
                    with c3: card_metric("WIN RATE", f"{win_rate:.1f}%", f"{len(wins)} Wins / {len(losses)} Loss", "white")
                    with c4: card_metric("PAYOFF (RR)", f"{payoff:.2f}", f"Avg Win: ${avg_win:.0f} / Loss: ${avg_loss:.0f}", "white")
                    
                    # --- EXIBIÇÃO KPIs (LINHA 2) ---
                    c5, c6, c7, c8 = st.columns(4)
                    with c5: card_metric("EXPECTATIVA MAT.", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy > 0 else "#FF4B4B")
                    with c6: card_metric("DRAWDOWN MÁXIMO", f"${max_dd:,.2f}", "Queda do Topo", "#FF4B4B")
                    with c7: card_metric("TOTAL TRADES", str(total_trades), "No Período", "white")
                    with c8: card_metric("MELHOR TRADE", f"${df_filtered['resultado'].max():,.2f}", "Maior Gain", "#00FF88")

                    st.markdown("---")

                    # --- GRÁFICOS ---
                    g1, g2 = st.columns([2, 1])
                    
                    with g1:
                        # Curva de Patrimônio
                        fig_eq = px.area(df_filtered, x='data', y='equity', title="📈 Curva de Patrimônio (Equity)", template="plotly_dark")
                        fig_eq.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                        fig_eq.add_hline(y=0, line_dash="dash", line_color="gray")
                        st.plotly_chart(fig_eq, use_container_width=True)
                        
                    with g2:
                        # Resultado por Contexto
                        ctx_perf = df_filtered.groupby('contexto')['resultado'].sum().reset_index()
                        fig_bar = px.bar(ctx_perf, x='contexto', y='resultado', title="📊 Resultado por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                        st.plotly_chart(fig_bar, use_container_width=True)

                    # Performance por Dia da Semana
                    st.markdown("### 📅 Performance por Dia da Semana")
                    df_filtered['dia_semana'] = pd.to_datetime(df_filtered['data']).dt.day_name()
                    # Tradução
                    dias_pt = {'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua', 'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sab', 'Sunday': 'Dom'}
                    df_filtered['dia_pt'] = df_filtered['dia_semana'].map(dias_pt)
                    
                    day_perf = df_filtered.groupby('dia_pt')['resultado'].sum().reindex(['Seg', 'Ter', 'Qua', 'Qui', 'Sex']).reset_index()
                    
                    fig_day = px.bar(day_perf, x='dia_pt', y='resultado', template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                    fig_day.update_layout(xaxis_title="Dia da Semana", yaxis_title="Resultado ($)")
                    st.plotly_chart(fig_day, use_container_width=True)

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

    # --- 10. HISTÓRICO ---
    elif selected == "Histórico":
        st.title("📜 Galeria de Trades")
        
        c_f1, c_f2, c_f3 = st.columns(3)
        filtro_ativo = c_f1.multiselect("Filtrar Ativo", ["NQ", "MNQ"])
        filtro_res = c_f2.selectbox("Filtrar Resultado", ["Todos", "Wins", "Losses"])
        filtro_ctx = c_f3.multiselect("Filtrar Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
        
        df = load_trades_db()
        if not df.empty:
            df_h = df[df['usuario'] == st.session_state["logged_user"]]
            if filtro_ativo: df_h = df_h[df_h['ativo'].isin(filtro_ativo)]
            if filtro_ctx: df_h = df_h[df_h['contexto'].isin(filtro_ctx)]
            if filtro_res == "Wins": df_h = df_h[df_h['resultado'] > 0]
            if filtro_res == "Losses": df_h = df_h[df_h['resultado'] < 0]
            
            df_h = df_h.sort_values('created_at', ascending=False)
            
            @st.dialog("Detalhes da Operação", width="large")
            def show_trade_details(row):
                if row.get('prints'): st.image(row['prints'], use_container_width=True)
                else: st.info("Sem Print disponível.")
                st.markdown("---")
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

            cols = st.columns(4)
            for i, (index, row) in enumerate(df_h.iterrows()):
                with cols[i % 4]:
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

    # --- 11. GERENCIAR USUÁRIOS (SEM ERRO DE DATA) ---
    elif selected == "Gerenciar Usuários":
        st.title("👥 Gestão de Usuários")

        if "user_form_data" not in st.session_state:
            st.session_state.user_form_data = {"id": None, "username": "", "password": ""}

        def reset_user_form():
            st.session_state.user_form_data = {"id": None, "username": "", "password": ""}

        res = supabase.table("users").select("*").execute()
        users_list = res.data

        c_form, c_list = st.columns([1, 1.5])

        with c_list:
            st.subheader("📋 Usuários Ativos")
            if st.button("✨ Criar Novo Usuário", use_container_width=True):
                reset_user_form(); st.rerun()
            
            if users_list:
                for u in users_list:
                    with st.container():
                        c1, c2, c3 = st.columns([2, 2, 1])
                        c1.write(f"👤 **{u['username']}**")
                        c2.caption("******") 
                        
                        col_edit, col_del = st.columns(2)
                        if col_edit.button("✏️", key=f"u_edit_{u['id']}"):
                            st.session_state.user_form_data = {"id": u['id'], "username": u['username'], "password": u['password']}
                            st.rerun()
                        if col_del.button("🗑️", key=f"u_del_{u['id']}"):
                            supabase.table("users").delete().eq("id", u['id']).execute()
                            if st.session_state.user_form_data["id"] == u['id']: reset_user_form()
                            st.rerun()
                        st.divider()
            else: st.info("Nenhum usuário encontrado.")

        with c_form:
            u_data = st.session_state.user_form_data
            titulo = f"✏️ Editando: {u_data['username']}" if u_data["id"] else "✨ Novo Usuário"
            st.subheader(titulo)
            
            form_user = st.text_input("Login (Username)", value=u_data["username"])
            form_pass = st.text_input("Senha (Password)", value=u_data["password"], type="default")
            
            if st.button("💾 SALVAR USUÁRIO", use_container_width=True):
                if u_data["id"]:
                    supabase.table("users").update({"username": form_user, "password": form_pass}).eq("id", u_data["id"]).execute()
                    st.toast("Usuário atualizado!", icon="✅")
                else:
                    supabase.table("users").insert({"username": form_user, "password": form_pass}).execute()
                    st.toast("Usuário criado!", icon="✨")
                
                time.sleep(1); reset_user_form(); st.rerun()
