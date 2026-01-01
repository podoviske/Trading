import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import uuid
import time
import json

# --- 1. CONFIGURAÇÕES E CONEXÃO ---
MULTIPLIERS = {"NQ": 20, "MNQ": 2, "ES": 50, "MES": 5}

def get_supabase():
    try:
        if "supabase" in st.session_state: return st.session_state["supabase"]
        else:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
    except: return None

def load_atms():
    sb = get_supabase()
    res = sb.table("atm_configs").select("*").execute()
    return {item['nome']: item for item in res.data}

def load_grupos(user):
    sb = get_supabase()
    res = sb.table("grupos_config").select("*").eq("usuario", user).execute()
    return pd.DataFrame(res.data)

def load_contas(user):
    """Carrega todas as contas do usuário para seleção individual"""
    sb = get_supabase()
    res = sb.table("contas_config").select("*").eq("usuario", user).execute()
    return pd.DataFrame(res.data)

# --- 2. TELA DE REGISTRO ---
def show(user, role):
    st.title("⚡ Registro de Operações")
    
    # Carrega dados
    atm_db = load_atms()
    df_grupos = load_grupos(user)
    df_contas = load_contas(user)
    
    # --- ÁREA 1: CONFIGURAÇÃO INICIAL ---
    with st.container():
        c1, c2 = st.columns([2, 1])
        with c1:
            atm_sel = st.selectbox("🎯 Estratégia / ATM", ["Manual"] + list(atm_db.keys()))
        
        with c2:
            st.caption("")  # Espaçamento

    st.markdown("---")
    
    # --- ÁREA 2: VINCULAÇÃO (GRUPO OU CONTA) ---
    st.subheader("📂 Vincular Operação")
    
    tipo_vinculo = st.radio(
        "Este trade foi:",
        ["🔄 Replicado (todas as contas do grupo)", "☝️ Individual (apenas uma conta)"],
        horizontal=True,
        help="Replicado = afeta todas as contas do grupo igualmente. Individual = afeta só uma conta específica."
    )
    
    grupo_sel = None
    conta_sel_id = None
    conta_sel_nome = None
    
    if "Replicado" in tipo_vinculo:
        # Trade replicado - seleciona GRUPO
        if not df_grupos.empty:
            lista_grupos = sorted(df_grupos['nome'].unique())
            grupo_sel = st.selectbox("📂 Selecione o Grupo", lista_grupos)
        else:
            st.warning("⚠️ Crie um grupo primeiro na aba Contas.")
            st.stop()
    else:
        # Trade individual - seleciona CONTA
        if not df_contas.empty:
            # Cria lista de contas com formato "PA-001 (Grupo A)"
            df_contas['display'] = df_contas['conta_identificador'] + " (" + df_contas['grupo_nome'] + ")"
            lista_contas = df_contas.sort_values('display')['display'].tolist()
            
            conta_display = st.selectbox("💳 Selecione a Conta", lista_contas)
            
            # Recupera o ID e grupo da conta selecionada
            conta_row = df_contas[df_contas['display'] == conta_display].iloc[0]
            conta_sel_id = conta_row['id']
            conta_sel_nome = conta_row['conta_identificador']
            grupo_sel = conta_row['grupo_nome']  # Mantém o grupo para filtros
        else:
            st.warning("⚠️ Cadastre uma conta primeiro na aba Contas.")
            st.stop()

    st.markdown("---")

    # Lógica de ATM
    if atm_sel != "Manual":
        config = atm_db[atm_sel]
        lt_default = int(config["lote"])
        stp_default = float(config["stop"])
        try: parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
        except: parciais_pre = []
    else:
        lt_default = 1; stp_default = 0.0; parciais_pre = []

    # --- LAYOUT DE DUAS COLUNAS VERTICAIS ---
    col_left, col_right = st.columns([1, 1.2]) 

    # ==========================
    # COLUNA DA ESQUERDA (INPUTS)
    # ==========================
    with col_left:
        st.subheader("📝 Detalhes da Execução")
        
        # Linha 1
        c_dt, c_dr = st.columns([1.5, 1])
        dt = c_dt.date_input("Data", datetime.now().date())
        dr = c_dr.radio("Direção", ["Compra", "Venda"], horizontal=True, label_visibility="collapsed")
        
        # Linha 2
        c_atv, c_ctx = st.columns(2)
        atv = c_atv.selectbox("Ativo", ["MNQ", "NQ", "ES", "MES"])
        ctx = c_ctx.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        
        # Linha 3
        psi = st.selectbox("Psicológico", ["Focado/Bem", "Ansioso", "Vingativo", "Cansado", "Neutro"])
        
        st.markdown("---")
        
        # Valores de Risco
        l1, l2 = st.columns(2)
        lt = l1.number_input("Lote Total", min_value=1, value=lt_default)
        stp = l2.number_input("Stop (Pts)", min_value=0.0, value=stp_default, step=0.25)
        
        if stp > 0:
            risco_calc = stp * MULTIPLIERS.get(atv, 2) * lt
            st.info(f"📉 Risco Estimado: **${risco_calc:,.2f}**")
            
        st.markdown("---")
        
        # Upload
        st.subheader("📸 Evidências")
        up = st.file_uploader("Upload de Prints", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    # ==========================
    # COLUNA DA DIREITA (FINANCEIRO)
    # ==========================
    with col_right:
        st.subheader("💰 Resultado & Parciais")
        
        # Gestão de ATM na sessão
        if "num_parciais" not in st.session_state or atm_sel != st.session_state.get("last_atm"):
            st.session_state.num_parciais = len(parciais_pre) if parciais_pre else 1
            st.session_state.last_atm = atm_sel

        # Botões
        cb1, cb2 = st.columns([1, 3])
        if cb1.button("➕ Add"): st.session_state.num_parciais += 1; st.rerun()
        if cb2.button("🧹 Reset"): st.session_state.num_parciais = 1; st.rerun()

        saidas = []
        alocacao_atual = 0
        
        # Loop de Parciais
        for i in range(st.session_state.num_parciais):
            val_pts = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
            val_qtd = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
            
            with st.container():
                cp1, cp2, cp3 = st.columns([1.5, 1.2, 1.5])
                pts = cp1.number_input(f"Pts Saída {i+1}", value=val_pts, key=f"pts_{i}_{atm_sel}", step=0.25)
                qtd = cp2.number_input(f"Qtd {i+1}", value=val_qtd, key=f"qtd_{i}_{atm_sel}", min_value=0)
                
                fin_parcial = pts * MULTIPLIERS.get(atv, 2) * qtd
                cor_fin = "#00FF88" if fin_parcial > 0 else ("#FF4B4B" if fin_parcial < 0 else "gray")
                cp3.markdown(f"<div style='padding-top:30px; text-align:right; font-weight:bold; color:{cor_fin}'>${fin_parcial:,.2f}</div>", unsafe_allow_html=True)
            
            st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)
            saidas.append({"pts": pts, "qtd": qtd})
            alocacao_atual += qtd

        # Validação Final
        diff = lt - alocacao_atual
        if diff != 0:
            st.warning(f"⚠️ Alocação Inválida: {alocacao_atual}/{lt} contratos.")
            bloquear_gain = True
        else:
            total_trade = sum([s["pts"] * MULTIPLIERS.get(atv, 2) * s["qtd"] for s in saidas])
            cor_tot = "#00FF88" if total_trade >= 0 else "#FF4B4B"
            st.markdown(f"""
                <div style="background:#161616; border:1px solid {cor_tot}; padding:15px; border-radius:10px; text-align:center; margin-top:20px;">
                    <div style="color:#888; font-size:12px;">RESULTADO FINAL</div>
                    <div style="font-size:28px; font-weight:bold; color:{cor_tot};">${total_trade:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
            bloquear_gain = False

    st.markdown("---")
    
    # --- RESUMO DA VINCULAÇÃO ---
    if "Replicado" in tipo_vinculo:
        # Conta quantas contas ativas no grupo
        contas_grupo = df_contas[df_contas['grupo_nome'] == grupo_sel] if not df_contas.empty else pd.DataFrame()
        num_contas = len(contas_grupo[contas_grupo['status_conta'] == 'Ativa']) if not contas_grupo.empty else 0
        st.info(f"🔄 **Trade Replicado** → Grupo **{grupo_sel}** ({num_contas} contas ativas)")
    else:
        st.info(f"☝️ **Trade Individual** → Conta **{conta_sel_nome}** (Grupo {grupo_sel})")

    # --- BOTÕES DE AÇÃO ---
    b1, b2 = st.columns(2)
    btn_gain = False
    
    if b1.button("🟢 REGISTRAR GAIN", use_container_width=True, type="primary", disabled=bloquear_gain):
        btn_gain = True
        
    if b2.button("🔴 REGISTRAR STOP", use_container_width=True):
        saidas = [{"pts": -stp, "qtd": lt}]
        btn_gain = True

    # --- LÓGICA DE SALVAMENTO ---
    if btn_gain:
        sb = get_supabase()
        with st.spinner("Gravando..."):
            try:
                res_financeiro = sum([s["pts"] * MULTIPLIERS.get(atv, 2) * s["qtd"] for s in saidas])
                pts_total_pond = sum([s["pts"] * s["qtd"] for s in saidas]) / lt if lt > 0 else 0
                
                img_url = ""
                if up:
                    arquivo = up[0] 
                    file_name = f"{uuid.uuid4()}.png"
                    sb.storage.from_("prints").upload(file_name, arquivo.getvalue())
                    img_url = sb.storage.from_("prints").get_public_url(file_name)
                
                # Monta o payload
                trade_data = {
                    "id": str(uuid.uuid4()),
                    "usuario": user,
                    "data": str(dt),
                    "ativo": atv,
                    "direcao": dr,
                    "contexto": ctx,
                    "comportamento": psi,
                    "lote": lt,
                    "resultado": res_financeiro,
                    "pts_medio": pts_total_pond,
                    "grupo_vinculo": grupo_sel,
                    "prints": img_url,
                    "risco_fin": (stp * MULTIPLIERS.get(atv, 2) * lt),
                    "stop_pts": stp,
                    "parciais": saidas,
                    "conta_id": conta_sel_id  # None se replicado, UUID se individual
                }
                
                sb.table("trades").insert(trade_data).execute()
                
                st.balloons()
                if conta_sel_id:
                    st.toast(f"Trade individual salvo! ${res_financeiro:,.2f}", icon="☝️")
                else:
                    st.toast(f"Trade replicado salvo! ${res_financeiro:,.2f}", icon="🔄")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")
