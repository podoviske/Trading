import streamlit as st
import uuid
import json
from datetime import datetime
from modules import database

def show(user, role):
    st.title("Registro de Operação")
    
    # Carregamento
    atms = database.load_atms()
    grupos = database.load_grupos(user)
    
    c1, c2 = st.columns([3, 1.5])
    atm_sel = c1.selectbox("ATM", ["Manual"] + list(atms.keys()))
    
    grp_sel = "Geral"
    if not grupos.empty:
        # Se for Master/Admin, deixa escolher
        grp_sel = c2.selectbox("Grupo", sorted(grupos['nome'].unique()))
    
    # ATM Defaults
    lote = 1; stop = 0.0
    if atm_sel != "Manual":
        lote = int(atms[atm_sel]['lote'])
        stop = float(atms[atm_sel]['stop'])

    f1, f2 = st.columns([1, 2])
    with f1:
        dt = st.date_input("Data", datetime.now())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ", "ES", "MES"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        # Contextos restaurados do print
        ctx = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C", "Outro"])
        psi = st.selectbox("Mental", ["Focado/Bem", "Ansioso", "Vingativo", "Cansado", "Fomo"])
        
    with f2:
        qtd = st.number_input("Lote Total", value=lote, min_value=1)
        stop_pts = st.number_input("Stop (Pts)", value=stop)
        
        # Correção: Upload Múltiplo
        prints = st.file_uploader("Prints (1º será capa)", accept_multiple_files=True)
        
        # Parciais (Simplificado para input direto de pts medio por enquanto ou manter o calculo)
        st.write("---")
        pts_medio = st.number_input("Pontos Capturados (Média)", step=0.25)

    # Cálculo
    multi = {"NQ": 20, "MNQ": 2, "ES": 50, "MES": 5}
    res_fin = pts_medio * multi.get(ativo, 2) * qtd
    risco_fin = stop_pts * multi.get(ativo, 2) * qtd
    
    if stop_pts > 0:
        st.caption(f"Risco Estimado: ${risco_fin:.2f}")

    if st.button("💾 REGISTRAR TRADE", type="primary", use_container_width=True):
        try:
            # Upload (Pega o primeiro se houver lista)
            url_img = ""
            trade_id = str(uuid.uuid4())
            if prints:
                f = prints[0] if isinstance(prints, list) else prints
                path = f"{trade_id}.png"
                database.supabase.storage.from_("prints").upload(path, f.getvalue())
                url_img = database.supabase.storage.from_("prints").get_public_url(path)
            
            payload = {
                "id": trade_id, 
                "usuario": user, # Obrigatório
                "data": str(dt),
                "ativo": ativo, "direcao": direcao, "lote": qtd,
                "resultado": res_fin, "pts_medio": pts_medio,
                "grupo_vinculo": grp_sel, "contexto": ctx, "comportamento": psi,
                "prints": url_img, "risco_fin": risco_fin
            }
            database.supabase.table("trades").insert(payload).execute()
            st.balloons()
            st.success(f"Salvo! Resultado: ${res_fin:.2f}")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
