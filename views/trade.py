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
    
    # ============================================================
    # VERIFICAÇÃO ANTI-TILT
    # ============================================================
    antitilt_ativo = False
    
    try:
        from views.antitilt import usuario_pode_operar, get_checkin_hoje, registrar_stop, registrar_gain
        
        status = usuario_pode_operar(user)
        antitilt_ativo = True
        
        if not status['pode']:
            if status['motivo'] == 'checkin_pendente':
                st.warning("🌅 **Você precisa fazer o Check-in Pré-Mercado antes de operar.**")
                if st.button("Ir para Check-in", type="primary"):
                    st.session_state["navegar_para"] = "Anti-Tilt"
                    st.rerun()
                return  # Para a execução aqui
            
            elif status['motivo'] == 'score_baixo':
                st.error(f"🚫 **Score muito baixo ({status['score']}). Não é recomendado operar hoje.**")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Ir para Anti-Tilt"):
                        st.session_state["navegar_para"] = "Anti-Tilt"
                        st.rerun()
                with col2:
                    if st.button("⚠️ Operar mesmo assim"):
                        from views.antitilt import ignorar_recomendacao
                        ignorar_recomendacao(user)
                        st.rerun()
                return  # Para a execução aqui
            
            elif status['motivo'] == 'bloqueado':
                st.error(f"🔴 **Você está bloqueado até {status['ate'][:16]}**")
                st.info("Respira. Levanta. Bebe água. Amanhã tem mais.")
                return  # Para a execução aqui
        
    except Exception as e:
        antitilt_ativo = False
    
    # Carrega dados
    atm_db = load_atms()
    df_grupos = load_grupos(user)
    df_contas = load_contas(user)
    
    # ============================================================
    # LINHA 1: ATM (preenche automaticamente os campos)
    # ============================================================
    atm_sel = st.selectbox("🎯 Estratégia / ATM", ["Manual"] + list(atm_db.keys()))
    
    # Carrega config do ATM
    if atm_sel != "Manual" and atm_sel in atm_db:
        config = atm_db[atm_sel]
        lt_default = int(config.get("lote", 1))
        stp_default = float(config.get("stop", 15.0))
        try: 
            parciais_pre = json.loads(config["parciais"]) if isinstance(config.get("parciais"), str) else config.get("parciais", [])
        except: 
            parciais_pre = []
    else:
        lt_default = 1
        stp_default = 15.0
        parciais_pre = []

    st.markdown("---")
    
    # ============================================================
    # DUAS COLUNAS: CONFIGURAÇÃO | RESULTADO
    # ============================================================
    col_config, col_resultado = st.columns([1, 1.2])
    
    # --- COLUNA ESQUERDA: CONFIGURAÇÃO ---
    with col_config:
        st.markdown("##### 🎛️ Configuração")
        
        # Vinculação (Grupo ou Conta)
        opcoes_vinculo = []
        mapa_vinculo = {}
        
        if not df_grupos.empty:
            for _, g in df_grupos.iterrows():
                label = f"🔄 {g['nome']}"
                opcoes_vinculo.append(label)
                n_ativas = 0
                if not df_contas.empty:
                    n_ativas = len(df_contas[(df_contas['grupo_nome'] == g['nome']) & (df_contas['status_conta'] == 'Ativa')])
                mapa_vinculo[label] = {"tipo": "grupo", "nome": g['nome'], "conta_id": None, "n_contas": n_ativas}
        
        if not df_contas.empty:
            for _, conta in df_contas.iterrows():
                label = f"☝️ {conta['conta_identificador']}"
                opcoes_vinculo.append(label)
                mapa_vinculo[label] = {"tipo": "individual", "nome": conta['grupo_nome'], "conta_id": conta['id'], "conta_nome": conta['conta_identificador']}
        
        if not opcoes_vinculo:
            st.warning("⚠️ Crie um grupo/conta primeiro na aba Contas.")
            st.stop()
        
        vinculo_sel = st.selectbox("📂 Vincular a", opcoes_vinculo)
        vinculo_info = mapa_vinculo[vinculo_sel]
        
        # Ativo + Direção
        c1, c2 = st.columns(2)
        atv = c1.selectbox("Ativo", ["MNQ", "NQ", "ES", "MES"])
        dr = c2.radio("Direção", ["Compra", "Venda"], horizontal=True)
        
        # Data + Lote + Stop
        c3, c4, c5 = st.columns(3)
        dt = c3.date_input("Data", datetime.now().date())
        lt = c4.number_input("Lote", min_value=1, value=lt_default)
        stp = c5.number_input("Stop (pts)", min_value=0.0, value=stp_default, step=0.25)
        
        # Contexto + Psicológico
        c6, c7 = st.columns(2)
        ctx = c6.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        psi = c7.selectbox("Psicológico", ["Focado/Bem", "Ansioso", "Vingativo", "Cansado", "Neutro"])
        
        # Risco estimado
        risco_calc = stp * MULTIPLIERS.get(atv, 2) * lt
        st.caption(f"📉 Risco estimado: **${risco_calc:,.2f}**")

    # --- COLUNA DIREITA: RESULTADO + PARCIAIS ---
    with col_resultado:
        st.markdown("##### 💰 Resultado & Parciais")
        
        # Gestão de parciais na sessão
        if "num_parciais" not in st.session_state or atm_sel != st.session_state.get("last_atm"):
            st.session_state.num_parciais = len(parciais_pre) if parciais_pre else 1
            st.session_state.last_atm = atm_sel

        # Botões Add/Reset
        cb1, cb2, _ = st.columns([1, 1, 2])
        if cb1.button("➕ Add"): 
            st.session_state.num_parciais += 1
            st.rerun()
        if cb2.button("🧹 Reset"): 
            st.session_state.num_parciais = 1
            st.rerun()

        saidas = []
        alocacao_atual = 0
        
        # Loop de Parciais
        for i in range(st.session_state.num_parciais):
            # Valores default do ATM
            val_pts = float(parciais_pre[i]["pts"]) if i < len(parciais_pre) else 0.0
            val_qtd = int(parciais_pre[i]["qtd"]) if i < len(parciais_pre) else (lt if i == 0 else 0)
            
            cp1, cp2, cp3 = st.columns([1.2, 0.8, 1])
            pts = cp1.number_input(f"Pts {i+1}", value=val_pts, key=f"pts_{i}_{atm_sel}", step=0.25)
            qtd = cp2.number_input(f"Qtd {i+1}", value=val_qtd, key=f"qtd_{i}_{atm_sel}", min_value=0)
            
            fin_parcial = pts * MULTIPLIERS.get(atv, 2) * qtd
            cor_fin = "#00FF88" if fin_parcial > 0 else ("#FF4B4B" if fin_parcial < 0 else "#666")
            cp3.markdown(f"<div style='padding-top:25px; text-align:right; font-weight:bold; color:{cor_fin}'>${fin_parcial:,.2f}</div>", unsafe_allow_html=True)
            
            saidas.append({"pts": pts, "qtd": qtd})
            alocacao_atual += qtd

        # Validação de alocação
        if alocacao_atual != lt:
            st.warning(f"⚠️ Alocação: {alocacao_atual}/{lt} contratos")
            bloquear = True
        else:
            bloquear = False
        
        # Total
        total_trade = sum([s["pts"] * MULTIPLIERS.get(atv, 2) * s["qtd"] for s in saidas])
        pts_medio = sum([s["pts"] * s["qtd"] for s in saidas]) / lt if lt > 0 else 0
        cor_total = "#00FF88" if total_trade >= 0 else "#FF4B4B"
        
        st.markdown(f"""
            <div style="background:#111; border:2px solid {cor_total}; border-radius:8px; padding:15px; text-align:center; margin:10px 0;">
                <div style="color:#888; font-size:11px;">TOTAL</div>
                <div style="color:{cor_total}; font-size:28px; font-weight:bold;">${total_trade:,.2f}</div>
                <div style="color:#666; font-size:11px;">{pts_medio:+.2f} pts</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Upload de print
        st.markdown("##### 📸 Evidência")
        up = st.file_uploader("Arraste ou clique", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, label_visibility="collapsed")

    st.markdown("---")
    
    # ============================================================
    # RODAPÉ: RESUMO + BOTÕES
    # ============================================================
    
    # Info de vinculação
    if vinculo_info["tipo"] == "grupo":
        st.info(f"🔄 **Trade Replicado** → Grupo **{vinculo_info['nome']}** ({vinculo_info['n_contas']} contas ativas)")
    else:
        st.info(f"☝️ **Trade Individual** → Conta **{vinculo_info['conta_nome']}**")
    
    # Botões
    b1, b2 = st.columns(2)
    
    with b1:
        btn_gain = st.button("🟢 REGISTRAR GAIN", use_container_width=True, disabled=bloquear)
    
    with b2:
        btn_stop = st.button("🔴 REGISTRAR STOP", use_container_width=True)

    # ============================================================
    # LÓGICA DE SALVAMENTO
    # ============================================================
    if btn_gain or btn_stop:
        sb = get_supabase()
        
        # Se clicou STOP, sobrescreve
        if btn_stop:
            saidas = [{"pts": -stp, "qtd": lt}]
            total_trade = -stp * MULTIPLIERS.get(atv, 2) * lt
            pts_medio = -stp
        
        with st.spinner("Gravando..."):
            try:
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
                    "resultado": total_trade,
                    "pts_medio": pts_medio,
                    "grupo_vinculo": vinculo_info["nome"],
                    "prints": img_url,
                    "risco_fin": stp * MULTIPLIERS.get(atv, 2) * lt,
                    "stop_pts": stp,
                    "parciais": saidas,
                    "conta_id": vinculo_info.get("conta_id")
                }
                
                sb.table("trades").insert(trade_data).execute()
                
                # Integração Anti-Tilt
                if antitilt_ativo:
                    if btn_stop:
                        stop_info = registrar_stop(user)
                        if stop_info['alerta_vermelho']:
                            st.error("🔴 3 stops no dia! Você foi bloqueado por 1 hora.")
                        elif stop_info['alerta_amarelo']:
                            st.warning("⚠️ 2 stops consecutivos! Considere parar por hoje.")
                    else:
                        registrar_gain(user)
                
                st.balloons()
                tipo_msg = "Stop" if btn_stop else "Gain"
                st.toast(f"{tipo_msg} registrado! ${total_trade:,.2f}", icon="✅")
                time.sleep(1.5)
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro: {e}")
