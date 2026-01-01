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
    
    # ============================================================
    # LINHA 1: ATM + VINCULAÇÃO (lado a lado)
    # ============================================================
    col_atm, col_vinculo = st.columns([1, 1.5])
    
    with col_atm:
        atm_sel = st.selectbox("🎯 Estratégia / ATM", ["Manual"] + list(atm_db.keys()))
    
    with col_vinculo:
        tipo_vinculo = st.radio(
            "📂 Vincular a:",
            ["Replicado (grupo)", "Individual (conta)"],
            horizontal=True,
            label_visibility="visible"
        )
    
    # Seleção de Grupo ou Conta
    grupo_sel = None
    conta_sel_id = None
    conta_sel_nome = None
    num_contas_grupo = 0
    
    if "Replicado" in tipo_vinculo:
        if not df_grupos.empty:
            lista_grupos = sorted(df_grupos['nome'].unique())
            grupo_sel = st.selectbox("Selecione o Grupo", lista_grupos, label_visibility="collapsed")
            # Conta quantas contas ativas
            if not df_contas.empty:
                contas_grp = df_contas[(df_contas['grupo_nome'] == grupo_sel) & (df_contas['status_conta'] == 'Ativa')]
                num_contas_grupo = len(contas_grp)
        else:
            st.warning("⚠️ Crie um grupo primeiro na aba Contas.")
            st.stop()
    else:
        if not df_contas.empty:
            df_contas['display'] = df_contas['conta_identificador'] + " (" + df_contas['grupo_nome'] + ")"
            lista_contas = df_contas.sort_values('display')['display'].tolist()
            conta_display = st.selectbox("Selecione a Conta", lista_contas, label_visibility="collapsed")
            conta_row = df_contas[df_contas['display'] == conta_display].iloc[0]
            conta_sel_id = conta_row['id']
            conta_sel_nome = conta_row['conta_identificador']
            grupo_sel = conta_row['grupo_nome']
        else:
            st.warning("⚠️ Cadastre uma conta primeiro na aba Contas.")
            st.stop()

    st.markdown("---")

    # Carrega config do ATM
    if atm_sel != "Manual":
        config = atm_db[atm_sel]
        lt_default = int(config["lote"])
        stp_default = float(config["stop"])
        try: parciais_pre = json.loads(config["parciais"]) if isinstance(config["parciais"], str) else config["parciais"]
        except: parciais_pre = []
    else:
        lt_default = 1; stp_default = 0.0; parciais_pre = []

    # ============================================================
    # LINHA 2: DETALHES + RESULTADO (lado a lado)
    # ============================================================
    col_esq, col_dir = st.columns([1, 1.2])
    
    # --- COLUNA ESQUERDA: DETALHES ---
    with col_esq:
        st.markdown("##### 📝 Detalhes da Execução")
        
        # Data + Direção
        c1, c2 = st.columns([1.5, 1])
        dt = c1.date_input("Data", datetime.now().date())
        dr = c2.radio("Direção", ["Compra", "Venda"], horizontal=True)
        
        # Ativo + Contexto
        c3, c4 = st.columns(2)
        atv = c3.selectbox("Ativo", ["MNQ", "NQ", "ES", "MES"])
        ctx = c4.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        
        # Psicológico
        psi = st.selectbox("Psicológico", ["Focado/Bem", "Ansioso", "Vingativo", "Cansado", "Neutro"])
        
        # Lote + Stop
        c5, c6 = st.columns(2)
        lt = c5.number_input("Lote Total", min_value=1, value=lt_default)
        stp = c6.number_input("Stop (Pts)", min_value=0.0, value=stp_default, step=0.25)
        
        # Risco calculado
        if stp > 0:
            risco_calc = stp * MULTIPLIERS.get(atv, 2) * lt
            st.error(f"📉 Risco: **${risco_calc:,.2f}**")

    # --- COLUNA DIREITA: RESULTADO ---
    with col_dir:
        st.markdown("##### 💰 Resultado & Parciais")
        
        # Gestão de parciais
        if "num_parciais" not in st.session_state or atm_sel != st.session_state.get("last_atm"):
            st.session_state.num_parciais = len(parciais_pre) if parciais_pre else 1
            st.session_state.last_atm = atm_sel

        # Botões Add/Reset
        cb1, cb2, cb3 = st.columns([1, 1, 2])
        if cb1.button("➕ Add"): st.session_state.num_parciais += 1; st.rerun()
        if cb2.button("🧹 Reset"): st.session_state.num_parciais = 1; st.rerun()

        saidas = []
        alocacao_atual = 0
        
        # Loop de Parciais
        for i in range(st.session_state.num_parciais):
            val_pts = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
            val_qtd = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
            
            cp1, cp2, cp3 = st.columns([1.2, 0.8, 1])
            pts = cp1.number_input(f"Pts {i+1}", value=val_pts, key=f"pts_{i}_{atm_sel}", step=0.25, label_visibility="collapsed" if i > 0 else "visible")
            qtd = cp2.number_input(f"Qtd {i+1}", value=val_qtd, key=f"qtd_{i}_{atm_sel}", min_value=0, label_visibility="collapsed" if i > 0 else "visible")
            
            fin_parcial = pts * MULTIPLIERS.get(atv, 2) * qtd
            cor_fin = "#00FF88" if fin_parcial > 0 else ("#FF4B4B" if fin_parcial < 0 else "#666")
            cp3.markdown(f"<div style='padding-top:28px; text-align:right; font-weight:bold; color:{cor_fin}'>${fin_parcial:,.2f}</div>", unsafe_allow_html=True)
            
            saidas.append({"pts": pts, "qtd": qtd})
            alocacao_atual += qtd

        # Validação + Resultado Final
        diff = lt - alocacao_atual
        if diff != 0:
            st.warning(f"⚠️ Alocação: {alocacao_atual}/{lt} contratos")
            bloquear_gain = True
            total_trade = 0
        else:
            total_trade = sum([s["pts"] * MULTIPLIERS.get(atv, 2) * s["qtd"] for s in saidas])
            cor_tot = "#00FF88" if total_trade >= 0 else "#FF4B4B"
            st.markdown(f"""
                <div style="background:#111; border:2px solid {cor_tot}; padding:15px; border-radius:8px; text-align:center; margin-top:10px;">
                    <div style="color:#888; font-size:11px;">RESULTADO FINAL</div>
                    <div style="font-size:26px; font-weight:bold; color:{cor_tot};">${total_trade:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
            bloquear_gain = False
        
        # Upload de evidências (compacto)
        st.markdown("<br>", unsafe_allow_html=True)
        up = st.file_uploader("📸 Evidências", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, label_visibility="collapsed")

    st.markdown("---")
    
    # ============================================================
    # RODAPÉ: RESUMO + BOTÕES
    # ============================================================
    
    # Resumo da vinculação
    if "Replicado" in tipo_vinculo:
        st.info(f"🔄 **Trade Replicado** → Grupo **{grupo_sel}** ({num_contas_grupo} contas ativas)")
    else:
        st.info(f"☝️ **Trade Individual** → Conta **{conta_sel_nome}**")

    # Botões de ação
    b1, b2 = st.columns(2)
    btn_gain = False
    
    if b1.button("🟢 REGISTRAR GAIN", use_container_width=True, type="primary", disabled=bloquear_gain):
        btn_gain = True
        
    if b2.button("🔴 REGISTRAR STOP", use_container_width=True):
        saidas = [{"pts": -stp, "qtd": lt}]
        btn_gain = True

    # ============================================================
    # LÓGICA DE SALVAMENTO
    # ============================================================
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
                    "conta_id": conta_sel_id
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
