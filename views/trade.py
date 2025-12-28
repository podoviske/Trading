import streamlit as st
import uuid
import json
from datetime import datetime
from modules import database

def show(user, role):
    st.title("Registro de Operação")
    
    # Carregamento de Dados Auxiliares
    atms = database.load_atms()
    grupos = database.load_grupos(user)
    
    c1, c2 = st.columns([3, 1.5])
    atm_sel = c1.selectbox("ATM", ["Manual"] + list(atms.keys()))
    
    grp_sel = "Geral"
    if not grupos.empty:
        grp_sel = c2.selectbox("Grupo", sorted(grupos['nome'].unique()))
    
    # Configuração ATM
    lote = 1; stop = 0.0
    if atm_sel != "Manual":
        lote = int(atms[atm_sel]['lote'])
        stop = float(atms[atm_sel]['stop'])

    f1, f2 = st.columns(2)
    with f1:
        dt = st.date_input("Data", datetime.now())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ", "ES", "MES"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        res_pts = st.number_input("Resultado (Pontos)", step=0.25)
    
    with f2:
        qtd = st.number_input("Lote", value=lote, min_value=1)
        stop_loss = st.number_input("Stop (Pts)", value=stop)
        prints = st.file_uploader("Prints", accept_multiple_files=True)
        ctx = st.selectbox("Contexto", ["Tendência", "Lateral", "Rompimento", "Contra"])
        psi = st.selectbox("Mental", ["Focado", "Ansioso", "Fomo", "Vingativo"])

    # Multiplicadores
    multi = {"NQ": 20, "MNQ": 2, "ES": 50, "MES": 5}
    res_fin = res_pts * multi.get(ativo, 2) * qtd
    
    if st.button("💾 REGISTRAR TRADE", type="primary", use_container_width=True):
        try:
            # Upload
            url_img = ""
            trade_id = str(uuid.uuid4())
            if prints:
                f = prints[0] # Pega o primeiro
                path = f"{trade_id}.png"
                database.supabase.storage.from_("prints").upload(path, f.getvalue())
                url_img = database.supabase.storage.from_("prints").get_public_url(path)
            
            # Save
            payload = {
                "id": trade_id, "usuario": user, "data": str(dt),
                "ativo": ativo, "direcao": direcao, "lote": qtd,
                "resultado": res_fin, "pts_medio": res_pts, # Simplificado
                "grupo_vinculo": grp_sel, "contexto": ctx, "comportamento": psi,
                "prints": url_img, "risco_fin": stop_loss * multi.get(ativo, 2) * qtd
            }
            database.supabase.table("trades").insert(payload).execute()
            st.success(f"Salvo! Resultado: ${res_fin:.2f}")
        except Exception as e:
            st.error(f"Erro: {e}")
