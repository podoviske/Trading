# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from supabase import create_client
import time
import json

# --- 1. CONEXAO ---
MULTIPLIERS = {"NQ": 20, "MNQ": 2, "ES": 50, "MES": 5}

def get_supabase():
    try:
        if "supabase" in st.session_state: return st.session_state["supabase"]
        else:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
    except: return None

def load_trades_db():
    try:
        sb = get_supabase()
        res = sb.table("trades").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['created_at'] = pd.to_datetime(df['created_at'])
            if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
            
            cols_num = ['resultado', 'lote', 'pts_medio', 'risco_fin', 'stop_pts']
            for c in cols_num:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
                    
        return df
    except: return pd.DataFrame()

# --- 2. POP-UP DE DETALHES ---
@st.dialog("Detalhes da Operacao", width="large")
def show_trade_details(row, user, role):
    # CSS dentro do dialog
    st.markdown("""
        <style>
        .detail-box {
            background-color: #111;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
        }
        .detail-label {
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }
        .detail-value {
            font-size: 18px;
            font-weight: 700;
        }
        .partial-card {
            background-color: #0d0d0d;
            border: 1px solid #222;
            border-radius: 6px;
            padding: 10px;
            margin-bottom: 8px;
        }
        .partial-label {
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
        }
        .obs-box {
            background-color: #0d0d0d;
            border: 1px solid #222;
            border-radius: 8px;
            padding: 15px;
            min-height: 200px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # PRINTS (suporte a multiplos)
    prints_data = row.get('prints', '')
    
    if prints_data:
        st.markdown("### Evidencias")
        
        # Tenta parsear como JSON (lista de URLs)
        try:
            if isinstance(prints_data, str) and prints_data.startswith('['):
                lista_prints = json.loads(prints_data)
            elif isinstance(prints_data, list):
                lista_prints = prints_data
            else:
                lista_prints = [prints_data]
        except:
            lista_prints = [prints_data]
        
        # Mostra todos os prints
        if len(lista_prints) == 1:
            st.image(lista_prints[0], use_container_width=True)
        else:
            cols_prints = st.columns(len(lista_prints))
            for idx, img_url in enumerate(lista_prints):
                with cols_prints[idx]:
                    st.image(img_url, use_container_width=True)
                    if st.button(f"Expandir {idx+1}", key=f"exp_print_{idx}"):
                        st.session_state["print_expandido"] = img_url
        
        # Modal para print expandido
        if st.session_state.get("print_expandido"):
            st.image(st.session_state["print_expandido"], use_container_width=True)
            if st.button("Fechar"):
                del st.session_state["print_expandido"]
                st.rerun()
    
    st.markdown("---")
    
    # Dados Gerais
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Data:** {row['data']}")
    c1.markdown(f"**Ativo:** {row['ativo']}")
    c1.markdown(f"**Grupo:** {row['grupo_vinculo']}")
    
    c2.markdown(f"**Direcao:** {row['direcao']}")
    c2.markdown(f"**Contexto:** {row['contexto']}")
    c2.markdown(f"**Estado:** {row.get('comportamento', '-')}")
    
    c3.markdown(f"**Lote Total:** {row['lote']}")
    
    st.markdown("---")
    
    # AREA TECNICA - NOVO LAYOUT
    st.subheader("Raio-X Tecnico")
    
    col_esq, col_dir = st.columns([1, 1.5])
    
    with col_esq:
        # Card do Risco
        stop_real = row.get('stop_pts', 0.0)
        risco_usd = row.get('risco_fin', 0.0)
        
        if stop_real == 0 and risco_usd > 0:
            mult = MULTIPLIERS.get(row['ativo'], 0)
            if mult > 0 and row['lote'] > 0:
                stop_real = risco_usd / (row['lote'] * mult)
        
        st.markdown(f"""
            <div class="detail-box">
                <div class="detail-label">Stop Tecnico</div>
                <div class="detail-value" style="color: #FF4B4B;">-{stop_real:.2f} pts</div>
                <div style="color: #FF4B4B; font-size: 14px;">-${risco_usd:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Cards das Parciais
        raw_partials = row.get('parciais', None)
        
        if raw_partials:
            if isinstance(raw_partials, str):
                try: lista_parciais = json.loads(raw_partials)
                except: lista_parciais = []
            elif isinstance(raw_partials, list):
                lista_parciais = raw_partials
            else: lista_parciais = []
            
            if lista_parciais:
                for idx, p in enumerate(lista_parciais):
                    pts = float(p.get('pts', 0))
                    qtd = int(p.get('qtd', 0))
                    mult = MULTIPLIERS.get(row['ativo'], 2)
                    valor = pts * qtd * mult
                    cor = "#00FF88" if pts > 0 else "#FF4B4B"
                    
                    st.markdown(f"""
                        <div class="partial-card">
                            <div class="partial-label">Saida {idx+1}</div>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: {cor}; font-size: 16px; font-weight: 600;">{pts:+.2f} pts</span>
                                <span style="color: #888; font-size: 12px;">{qtd} cts</span>
                            </div>
                            <div style="color: {cor}; font-size: 14px; font-weight: 500;">${valor:+,.2f}</div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                pts_medio = row.get('pts_medio', 0)
                st.markdown(f"""
                    <div class="partial-card">
                        <div class="partial-label">Preco Medio</div>
                        <div style="color: #fff; font-size: 18px; font-weight: 600;">{pts_medio:.2f} pts</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            pts_medio = row.get('pts_medio', 0)
            st.markdown(f"""
                <div class="partial-card">
                    <div class="partial-label">Preco Medio</div>
                    <div style="color: #fff; font-size: 18px; font-weight: 600;">{pts_medio:.2f} pts</div>
                </div>
            """, unsafe_allow_html=True)
    
    with col_dir:
        # Area de Observacoes
        st.markdown("""
            <div class="detail-label" style="margin-bottom: 10px;">Observacoes do Trade</div>
        """, unsafe_allow_html=True)
        
        obs_atual = row.get('observacoes', '')
        nova_obs = st.text_area(
            "Observacoes",
            value=obs_atual,
            height=200,
            placeholder="Anote aqui suas observacoes sobre este trade...",
            label_visibility="collapsed"
        )
        
        if nova_obs != obs_atual:
            if st.button("Salvar Observacoes", use_container_width=True):
                sb = get_supabase()
                sb.table("trades").update({"observacoes": nova_obs}).eq("id", row['id']).execute()
                st.toast("Observacoes salvas!")
                st.rerun()
    
    st.markdown("---")
    
    # Resultado Final
    res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
    st.markdown(f"""
        <h1 style='color:{res_c}; text-align:center; font-size:50px; margin:0;'>
            ${row['resultado']:,.2f}
        </h1>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("DELETAR REGISTRO PERMANENTEMENTE", type="primary", use_container_width=True):
        sb = get_supabase()
        sb.table("trades").delete().eq("id", row['id']).execute()
        st.toast("Registro deletado!")
        time.sleep(1)
        st.rerun()

# --- 3. TELA PRINCIPAL (GALERIA) ---
def show(user, role):
    # CSS
    st.markdown("""
        <style>
        .trade-card {
            background-color: #161616 !important;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 15px;
            border: 1px solid #333;
            transition: transform 0.2s, border-color 0.2s;
            height: 300px !important;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .trade-card:hover {
            transform: translateY(-3px);
            border-color: #B20000;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        
        .card-img-container {
            width: 100%; 
            height: 160px !important;
            background-color: #111;
            border-radius: 5px; 
            overflow: hidden; 
            display: flex;
            align-items: center; 
            justify-content: center; 
            margin-bottom: 10px; 
            position: relative;
            flex-shrink: 0; 
        }
        
        .card-img { 
            width: 100%; height: 100%; 
            object-fit: cover;
            object-position: center; 
            display: block; 
        }
        
        .card-title { 
            font-size: 14px; font-weight: 700; color: white; margin-bottom: 4px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .card-sub { 
            font-size: 11px; color: #888; margin-bottom: 8px; 
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .card-res-win { font-size: 18px; font-weight: 800; color: #00FF88; text-align: right; } 
        .card-res-loss { font-size: 18px; font-weight: 800; color: #FF4B4B; text-align: right; }
        
        .filtro-ativo {
            background-color: #1a0a0a;
            border: 1px solid #B20000;
            border-radius: 8px;
            padding: 10px 15px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("Galeria de Trades")
    
    dfh = load_trades_db()
    if not dfh.empty: dfh = dfh[dfh['usuario'] == user]
    
    # --- VERIFICA FILTRO VINDO DO PLANO ---
    filtro_contexto_externo = st.session_state.pop("filtro_contexto_historico", None)
    
    if filtro_contexto_externo:
        st.markdown(f"""
            <div class="filtro-ativo">
                <span>Filtro ativo: <b>{filtro_contexto_externo}</b></span>
            </div>
        """, unsafe_allow_html=True)
        
        col_clear, _ = st.columns([1, 4])
        with col_clear:
            if st.button("Limpar filtro"):
                st.rerun()
    
    if not dfh.empty:
        with st.expander("Filtros", expanded=not bool(filtro_contexto_externo)):
            c1, c2, c3, c4 = st.columns(4)
            all_assets = sorted(list(dfh['ativo'].unique())) if 'ativo' in dfh.columns else ["NQ", "MNQ"]
            all_contexts = sorted(list(dfh['contexto'].unique())) if 'contexto' in dfh.columns else []
            all_groups = sorted(list(dfh['grupo_vinculo'].unique())) if 'grupo_vinculo' in dfh.columns else []
            
            fa = c1.multiselect("Ativo", all_assets)
            fr = c2.selectbox("Resultado", ["Todos", "Wins", "Losses"])
            
            # Se veio filtro externo, pre-seleciona
            default_ctx = [filtro_contexto_externo] if filtro_contexto_externo and filtro_contexto_externo in all_contexts else []
            fc = c3.multiselect("Contexto", all_contexts, default=default_ctx)
            
            fg = c4.multiselect("Grupo", all_groups)
            
            if fa: dfh = dfh[dfh['ativo'].isin(fa)]
            if fc: dfh = dfh[dfh['contexto'].isin(fc)]
            if fg: dfh = dfh[dfh['grupo_vinculo'].isin(fg)]
            if fr == "Wins": dfh = dfh[dfh['resultado'] > 0]
            if fr == "Losses": dfh = dfh[dfh['resultado'] < 0]
            
            dfh = dfh.sort_values('created_at', ascending=False)

        st.markdown(f"**Exibindo {len(dfh)} operacoes**")
        st.markdown("---")

        cols = st.columns(4)
        for i, (index, row) in enumerate(dfh.iterrows()):
            with cols[i % 4]:
                res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                res_fmt = f"${row['resultado']:,.2f}"
                
                # Pega primeiro print (se for lista)
                prints_data = row.get('prints', '')
                if prints_data:
                    try:
                        if isinstance(prints_data, str) and prints_data.startswith('['):
                            lista_prints = json.loads(prints_data)
                            img_url = lista_prints[0] if lista_prints else ''
                        elif isinstance(prints_data, list):
                            img_url = prints_data[0] if prints_data else ''
                        else:
                            img_url = prints_data
                    except:
                        img_url = prints_data
                else:
                    img_url = ''
                
                if img_url:
                    img_html = f'<img src="{img_url}" class="card-img">' 
                else:
                    img_html = '<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; color:#555; font-size:12px;">Sem Foto</div>'
                
                st.markdown(f"""
                    <div class="trade-card">
                        <div class="card-img-container">{img_html}</div>
                        <div class="card-content">
                            <div class="card-title">{row['ativo']} - {row['direcao']}</div>
                            <div class="card-sub">{row['data']} - {row['grupo_vinculo']}</div>
                        </div>
                        <div class="{res_class}">{res_fmt}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button("Detalhes", key=f"btn_{row['id']}", use_container_width=True):
                    show_trade_details(row, user, role)
    else:
        st.info("Nenhuma operacao registrada ainda.")
