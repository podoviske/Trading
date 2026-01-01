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
    # BLOCO 1: REGISTRO RÁPIDO (sempre visível)
    # ============================================================
    st.markdown("#### 🎯 Registro Rápido")
    
    # Linha 1: Vinculação + Ativo + Direção
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1.5])
    
    with c1:
        # Monta lista unificada: grupos e contas
        opcoes_vinculo = []
        mapa_vinculo = {}  # Para recuperar dados depois
        
        if not df_grupos.empty:
            for _, g in df_grupos.iterrows():
                label = f"🔄 {g['nome']}"
                opcoes_vinculo.append(label)
                # Conta quantas contas ativas no grupo
                if not df_contas.empty:
                    n_ativas = len(df_contas[(df_contas['grupo_nome'] == g['nome']) & (df_contas['status_conta'] == 'Ativa')])
                else:
                    n_ativas = 0
                mapa_vinculo[label] = {"tipo": "grupo", "nome": g['nome'], "conta_id": None, "n_contas": n_ativas}
        
        if not df_contas.empty:
            for _, conta in df_contas.iterrows():
                label = f"☝️ {conta['conta_identificador']} ({conta['grupo_nome']})"
                opcoes_vinculo.append(label)
                mapa_vinculo[label] = {"tipo": "individual", "nome": conta['grupo_nome'], "conta_id": conta['id'], "conta_nome": conta['conta_identificador']}
        
        if not opcoes_vinculo:
            st.warning("⚠️ Crie um grupo/conta primeiro.")
            st.stop()
        
        vinculo_sel = st.selectbox("Vincular a", opcoes_vinculo, label_visibility="collapsed")
        vinculo_info = mapa_vinculo[vinculo_sel]
    
    with c2:
        atv = st.selectbox("Ativo", ["MNQ", "NQ", "ES", "MES"], label_visibility="collapsed")
    
    with c3:
        dr = st.radio("Direção", ["Compra", "Venda"], horizontal=True, label_visibility="collapsed")
    
    with c4:
        dt = st.date_input("Data", datetime.now().date(), label_visibility="collapsed")
    
    # Linha 2: Lote + Pontos (entrada rápida)
    c5, c6, c7 = st.columns([1, 1, 2])
    
    with c5:
        lt = st.number_input("Lote", min_value=1, value=1)
    
    with c6:
        pts_rapido = st.number_input("Pontos", value=0.0, step=0.25, help="Resultado em pontos (+ gain, - loss)")
    
    with c7:
        # Resultado calculado em tempo real
        resultado_rapido = pts_rapido * MULTIPLIERS.get(atv, 2) * lt
        cor_res = "#00FF88" if resultado_rapido >= 0 else "#FF4B4B"
        st.markdown(f"""
            <div style="background:#111; border:1px solid {cor_res}; border-radius:8px; padding:12px; text-align:center; margin-top:5px;">
                <span style="color:#888; font-size:11px;">RESULTADO</span><br>
                <span style="color:{cor_res}; font-size:24px; font-weight:bold;">${resultado_rapido:,.2f}</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # ============================================================
    # BLOCO 2: DETALHES (expandir se quiser)
    # ============================================================
    with st.expander("📝 Detalhes (opcional)", expanded=False):
        d1, d2, d3, d4 = st.columns(4)
        
        with d1:
            atm_sel = st.selectbox("ATM / Estratégia", ["Manual"] + list(atm_db.keys()))
        
        with d2:
            ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        
        with d3:
            psi = st.selectbox("Psicológico", ["Focado/Bem", "Ansioso", "Vingativo", "Cansado", "Neutro"])
        
        with d4:
            stp = st.number_input("Stop (Pts)", min_value=0.0, value=15.0, step=0.25)
        
        # Upload
        up = st.file_uploader("📸 Evidências", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        
        # Risco calculado
        if stp > 0:
            risco_calc = stp * MULTIPLIERS.get(atv, 2) * lt
            st.caption(f"📉 Risco estimado: **${risco_calc:,.2f}**")

    # Carrega config do ATM se selecionado
    if 'atm_sel' in dir() and atm_sel != "Manual":
        config = atm_db.get(atm_sel, {})
        parciais_pre = []
        if config:
            try: 
                parciais_pre = json.loads(config["parciais"]) if isinstance(config.get("parciais"), str) else config.get("parciais", [])
            except: 
                parciais_pre = []
    else:
        atm_sel = "Manual"
        parciais_pre = []
        stp = 15.0
        ctx = "Contexto A"
        psi = "Focado/Bem"
        up = None

    # ============================================================
    # BLOCO 3: PARCIAIS (expandir se múltiplas saídas)
    # ============================================================
    with st.expander("🎯 Parciais (múltiplas saídas)", expanded=False):
        st.caption("Use se você saiu em mais de um preço. Senão, ignore - o sistema usa o 'Pontos' do registro rápido.")
        
        # Gestão de parciais
        if "num_parciais" not in st.session_state:
            st.session_state.num_parciais = 1

        # Botões Add/Reset
        cb1, cb2, cb3 = st.columns([1, 1, 3])
        if cb1.button("➕ Add"): 
            st.session_state.num_parciais += 1
            st.rerun()
        if cb2.button("🧹 Reset"): 
            st.session_state.num_parciais = 1
            st.rerun()

        saidas_parciais = []
        alocacao_parciais = 0
        
        for i in range(st.session_state.num_parciais):
            cp1, cp2, cp3 = st.columns([1.2, 0.8, 1])
            
            p_pts = cp1.number_input(f"Pts Saída {i+1}", value=0.0, key=f"parc_pts_{i}", step=0.25)
            p_qtd = cp2.number_input(f"Qtd {i+1}", value=1 if i == 0 else 0, key=f"parc_qtd_{i}", min_value=0)
            
            p_valor = p_pts * MULTIPLIERS.get(atv, 2) * p_qtd
            cor_p = "#00FF88" if p_valor >= 0 else "#FF4B4B"
            cp3.markdown(f"<div style='padding-top:28px; color:{cor_p}; font-weight:bold;'>${p_valor:,.2f}</div>", unsafe_allow_html=True)
            
            saidas_parciais.append({"pts": p_pts, "qtd": p_qtd})
            alocacao_parciais += p_qtd
        
        # Validação
        if alocacao_parciais > 0 and alocacao_parciais != lt:
            st.warning(f"⚠️ Soma das parciais ({alocacao_parciais}) ≠ Lote ({lt})")
        
        usar_parciais = alocacao_parciais > 0 and alocacao_parciais == lt and any(s['pts'] != 0 for s in saidas_parciais)

    st.markdown("---")
    
    # ============================================================
    # BLOCO 4: RESUMO + BOTÕES (sempre no final)
    # ============================================================
    
    # Decide qual resultado usar
    if 'usar_parciais' in dir() and usar_parciais:
        resultado_final = sum([s["pts"] * MULTIPLIERS.get(atv, 2) * s["qtd"] for s in saidas_parciais])
        pts_final = sum([s["pts"] * s["qtd"] for s in saidas_parciais]) / lt if lt > 0 else 0
        saidas_final = saidas_parciais
        modo_resultado = "parciais"
    else:
        resultado_final = resultado_rapido
        pts_final = pts_rapido
        saidas_final = [{"pts": pts_rapido, "qtd": lt}]
        modo_resultado = "rapido"
    
    cor_final = "#00FF88" if resultado_final >= 0 else "#FF4B4B"
    
    # Info de vinculação
    if vinculo_info["tipo"] == "grupo":
        st.info(f"🔄 **Trade Replicado** → Grupo **{vinculo_info['nome']}** ({vinculo_info['n_contas']} contas ativas)")
    else:
        st.info(f"☝️ **Trade Individual** → Conta **{vinculo_info['conta_nome']}**")
    
    # Card de resultado final
    st.markdown(f"""
        <div style="background:linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border:2px solid {cor_final}; border-radius:12px; padding:20px; text-align:center; margin:10px 0;">
            <div style="color:#888; font-size:12px; text-transform:uppercase; letter-spacing:1px;">Resultado Final</div>
            <div style="color:{cor_final}; font-size:36px; font-weight:800; margin:5px 0;">${resultado_final:,.2f}</div>
            <div style="color:#666; font-size:11px;">{pts_final:+.2f} pts • {lt} contrato(s) • {atv}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Botões de ação
    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    
    btn_gain = False
    btn_stop = False
    
    with b1:
        if st.button("🟢 REGISTRAR GAIN", use_container_width=True):
            btn_gain = True
    
    with b2:
        if st.button("🔴 REGISTRAR STOP", use_container_width=True):
            btn_stop = True

    # ============================================================
    # LÓGICA DE SALVAMENTO
    # ============================================================
    if btn_gain or btn_stop:
        sb = get_supabase()
        
        # Se clicou STOP, sobrescreve com valor negativo
        if btn_stop:
            stp_val = stp if 'stp' in dir() else 15.0
            saidas_final = [{"pts": -stp_val, "qtd": lt}]
            resultado_final = -stp_val * MULTIPLIERS.get(atv, 2) * lt
            pts_final = -stp_val
        
        with st.spinner("Gravando..."):
            try:
                img_url = ""
                if 'up' in dir() and up:
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
                    "contexto": ctx if 'ctx' in dir() else "Contexto A",
                    "comportamento": psi if 'psi' in dir() else "Focado/Bem",
                    "lote": lt,
                    "resultado": resultado_final,
                    "pts_medio": pts_final,
                    "grupo_vinculo": vinculo_info["nome"],
                    "prints": img_url,
                    "risco_fin": (stp if 'stp' in dir() else 15.0) * MULTIPLIERS.get(atv, 2) * lt,
                    "stop_pts": stp if 'stp' in dir() else 15.0,
                    "parciais": saidas_final,
                    "conta_id": vinculo_info.get("conta_id")
                }
                
                sb.table("trades").insert(trade_data).execute()
                
                st.balloons()
                tipo_msg = "Stop registrado" if btn_stop else "Gain registrado"
                st.toast(f"{tipo_msg}! ${resultado_final:,.2f}", icon="✅")
                time.sleep(1.5)
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro: {e}")
