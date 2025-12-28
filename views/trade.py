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

# --- 2. TELA DE REGISTRO ---
def show(user, role):
    st.title("⚡ Registro de Operações")
    
    # Carrega dados auxiliares
    atm_db = load_atms()
    df_grupos = load_grupos(user)
    
    # --- ÁREA 1: CONFIGURAÇÃO INICIAL (ATM & GRUPO) ---
    with st.container():
        c1, c2 = st.columns([2, 1])
        
        with c1:
            atm_sel = st.selectbox("🎯 Estratégia / ATM", ["Manual"] + list(atm_db.keys()))
        
        with c2:
            # Seleção de Grupo (Obrigatório para o Dashboard novo funcionar bem)
            grupo_sel = "Geral"
            if not df_grupos.empty:
                lista_grupos = sorted(df_grupos['nome'].unique())
                grupo_sel = st.selectbox("📂 Vincular ao Grupo", lista_grupos)
            else:
                st.caption("Crie grupos na aba Contas.")

    st.markdown("---")

    # Lógica de Preenchimento Automático via ATM
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

    # --- ÁREA 2: DADOS DO TRADE (FORMULÁRIO) ---
    c_form, c_upload = st.columns([2, 1])
    
    with c_form:
        st.subheader("📝 Detalhes da Execução")
        
        f1, f2, f3 = st.columns(3)
        with f1:
            dt = st.date_input("Data", datetime.now().date())
            dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        with f2:
            atv = st.selectbox("Ativo", ["MNQ", "NQ", "ES", "MES"])
            ctx = st.selectbox("Contexto", ["Tendência", "Lateral", "Rompimento", "Contra-Tendência", "News"])
        with f3:
            psi = st.selectbox("Psicológico", ["Focado/Bem", "Ansioso", "Vingativo", "Cansado", "Neutro"])
            
        st.markdown("") # Espaço
        
        # Linha de Valores
        l1, l2 = st.columns(2)
        with l1:
            lt = st.number_input("Lote Total (Contratos)", min_value=1, value=lt_default)
        with l2:
            stp = st.number_input("Stop Loss (Pontos)", min_value=0.0, value=stp_default, step=0.25)
            
        # Feedback de Risco
        if stp > 0:
            risco_calc = stp * MULTIPLIERS.get(atv, 2) * lt
            st.info(f"📉 Risco Estimado: **${risco_calc:,.2f}**")

    # --- ÁREA 3: UPLOAD & VISUAL ---
    with c_upload:
        st.subheader("📸 Evidências")
        up = st.file_uploader("Upload de Prints", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        if up:
            st.success(f"{len(up)} arquivos selecionados.")

    st.markdown("---")

    # --- ÁREA 4: GESTÃO DE SAÍDAS (ATM) ---
    st.subheader("💰 Resultado & Parciais")
    
    # Inicializa ATM na sessão se mudou
    if "num_parciais" not in st.session_state or atm_sel != st.session_state.get("last_atm"):
        st.session_state.num_parciais = len(parciais_pre) if parciais_pre else 1
        st.session_state.last_atm = atm_sel

    # Botões de controle de parciais
    cb1, cb2, cb3 = st.columns([1, 1, 4])
    if cb1.button("➕ Add"): st.session_state.num_parciais += 1; st.rerun()
    if cb2.button("🧹 Reset"): st.session_state.num_parciais = 1; st.rerun()

    saidas = []
    alocacao_atual = 0
    
    # Loop para gerar inputs de parciais
    for i in range(st.session_state.num_parciais):
        # Tenta pegar valores padrão do ATM se existirem
        val_pts = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
        val_qtd = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
        
        c_p1, c_p2, c_p3 = st.columns([2, 2, 3])
        with c_p1:
            pts = st.number_input(f"Pontos (Saída {i+1})", value=val_pts, key=f"p_pts_{i}_{atm_sel}", step=0.25)
        with c_p2:
            qtd = st.number_input(f"Contratos (Saída {i+1})", value=val_qtd, key=f"p_qtd_{i}_{atm_sel}", min_value=0)
        with c_p3:
            if pts != 0:
                fin_parcial = pts * MULTIPLIERS.get(atv, 2) * qtd
                cor_fin = "green" if fin_parcial > 0 else "red"
                st.markdown(f"<div style='margin-top: 30px; font-weight:bold; color:{cor_fin}'>= ${fin_parcial:,.2f}</div>", unsafe_allow_html=True)
                
        saidas.append({"pts": pts, "qtd": qtd})
        alocacao_atual += qtd

    # Validação de Alocação
    diff = lt - alocacao_atual
    if diff != 0:
        st.warning(f"⚠️ Atenção: Lote Total ({lt}) difere da soma das saídas ({alocacao_atual}). Ajuste os contratos.")
        bloquear_gain = True
    else:
        st.success("✅ Alocação perfeita. Pronto para registrar.")
        bloquear_gain = False

    st.markdown("---")

    # --- BOTÕES DE AÇÃO ---
    b1, b2 = st.columns(2)
    
    btn_gain = False
    
    # Botão Gain (Verde)
    if b1.button("🟢 REGISTRAR RESULTADO (GAIN/MISTO)", use_container_width=True, type="primary", disabled=bloquear_gain):
        btn_gain = True
        
    # Botão Stop Full (Vermelho) - Atalho rápido
    if b2.button("🔴 REGISTRAR STOP FULL (RÁPIDO)", use_container_width=True):
        # Sobrescreve as saídas para ser 1 saída única de Stop Cheio
        saidas = [{"pts": -stp, "qtd": lt}]
        btn_gain = True # Ativa a flag de salvar

    # --- LÓGICA DE SALVAMENTO ---
    if btn_gain:
        sb = get_supabase()
        with st.spinner("Gravando no Banco de Dados..."):
            try:
                # 1. Cálculo Financeiro Final
                res_financeiro = sum([s["pts"] * MULTIPLIERS.get(atv, 2) * s["qtd"] for s in saidas])
                pts_total_pond = sum([s["pts"] * s["qtd"] for s in saidas]) / lt if lt > 0 else 0
                
                # 2. Upload de Imagem (Se houver)
                img_url = ""
                if up:
                    # Pega o primeiro arquivo para ser a capa
                    arquivo = up[0] 
                    # Nome único para não sobrescrever
                    file_name = f"{uuid.uuid4()}.png"
                    sb.storage.from_("prints").upload(file_name, arquivo.getvalue())
                    img_url = sb.storage.from_("prints").get_public_url(file_name)
                
                # 3. Insert no Banco
                payload = {
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
                    "grupo_vinculo": grupo_sel, # FUNDAMENTAL para o Dashboard
                    "prints": img_url,
                    "risco_fin": (stp * MULTIPLIERS.get(atv, 2) * lt) # Salva o risco planejado
                }
                
                sb.table("trades").insert(payload).execute()
                
                st.balloons()
                st.toast(f"Trade registrado! Resultado: ${res_financeiro:,.2f}", icon="🦅")
                time.sleep(1.5)
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
