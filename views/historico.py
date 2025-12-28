import streamlit as st
import pandas as pd
from supabase import create_client
import time
import json

# --- 1. CONEXÃO ---
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
@st.dialog("Detalhes da Operação", width="large")
def show_trade_details(row, user, role):
    # Cabeçalho
    if row.get('prints'):
        st.markdown("### 📸 Evidência (Full Screen)")
        st.image(row['prints'], use_container_width=True)
    
    st.markdown("---")
    
    # Dados Gerais
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**📅 Data:** {row['data']}")
    c1.markdown(f"**📈 Ativo:** {row['ativo']}")
    c1.markdown(f"**📂 Grupo:** {row['grupo_vinculo']}")
    
    c2.markdown(f"**🔄 Direção:** {row['direcao']}")
    c2.markdown(f"**🧠 Contexto:** {row['contexto']}")
    c2.markdown(f"**🧘 Estado:** {row.get('comportamento', '-')}")
    
    c3.markdown(f"**⚖️ Lote Total:** {row['lote']}")
    
    st.markdown("---")
    
    # ÁREA TÉCNICA
    st.subheader("📊 Raio-X Técnico")
    t1, t2 = st.columns(2)
    
    with t1:
        stop_real = row.get('stop_pts', 0.0)
        risco_usd = row.get('risco_fin', 0.0)
        
        # Fallback para trades antigos
        if stop_real == 0 and risco_usd > 0:
            mult = MULTIPLIERS.get(row['ativo'], 0)
            if mult > 0 and row['lote'] > 0:
                stop_real = risco_usd / (row['lote'] * mult)
                label_stop = "Stop (Estimado)"
            else:
                label_stop = "Stop (N/A)"
        else:
            label_stop = "Stop Técnico (Real)"

        st.markdown(f"""
        <div class="tech-box">
            <div class="tech-label">⛔ {label_stop}</div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <div><span style="color:#FF4B4B; font-size:24px; font-weight:bold;">-{stop_real:.2f} pts</span></div>
                <div style="text-align:right;">
                    <span style="color:#FF4B4B; font-weight:bold;">-${risco_usd:,.2f}</span><br>
                    <span style="font-size:10px; color:#666;">Risco Financeiro</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with t2:
        raw_partials = row.get('parciais', None)
        html_partials = ""
        
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
                    cor_p = "#00FF88" if pts > 0 else "#FF4B4B"
                    html_partials += f"""
                    <div class="partial-row">
                        <span>Saída {idx+1}</span>
                        <span><b>{qtd} ctrs</b> @ <span style="color:{cor_p}">{pts:.2f} pts</span></span>
                    </div>"""
            else: html_partials = "<div style='color:#666; font-size:12px; padding:10px;'>Sem dados detalhados.</div>"
        else:
             pts_medio = row['pts_medio']
             html_partials = f"<div style='padding:10px; text-align:center;'><div style='font-size:12px; color:#888;'>Preço Médio</div><div style='font-size:18px; color:white; font-weight:bold;'>{pts_medio:.2f} pts</div></div>"

        st.markdown(f"""
        <div class="tech-box">
            <div class="tech-label">🎯 Execução (Parciais)</div>
            {html_partials}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    res_c = "#00FF88" if row['resultado'] >= 0 else "#FF4B4B"
    st.markdown(f"<h1 style='color:{res_c}; text-align:center; font-size:50px; margin:0;'>${row['resultado']:,.2f}</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🗑️ DELETAR REGISTRO PERMANENTEMENTE", type="primary", use_container_width=True):
        sb = get_supabase()
        sb.table("trades").delete().eq("id", row['id']).execute()
        st.toast("Registro deletado!", icon="🗑️")
        time.sleep(1)
        st.rerun()

# --- 3. TELA PRINCIPAL (GALERIA) ---
def show(user, role):
    # [IMPORTANTE] O CSS AGORA ESTÁ DENTRO DO SHOW PARA GARANTIR O CARREGAMENTO
    st.markdown("""
        <style>
        /* 1. Card com Altura Fixa (BLINDAGEM) */
        .trade-card {
            background-color: #161616 !important; /* Força cor de fundo */
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 15px;
            border: 1px solid #333;
            transition: transform 0.2s, border-color 0.2s;
            height: 300px !important;  /* Altura FIXA para alinhar tudo */
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .trade-card:hover {
            transform: translateY(-3px);
            border-color: #B20000;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        
        /* 2. Container da Imagem Fixo */
        .card-img-container {
            width: 100%; 
            height: 160px !important; /* Altura fixa da área da foto */
            background-color: #111; /* Fundo escuro caso não tenha foto */
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
            object-fit: cover; /* Cobre a área sem distorcer (Zoom/Crop) */
            object-position: center; 
            display: block; 
        }
        
        /* 3. Textos Seguros */
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
        
        /* Box de Detalhes (Modal) */
        .tech-box {
            background-color: #111;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            height: 100%;
        }
        .tech-label { font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 5px; }
        .partial-row { 
            display: flex; justify-content: space-between; 
            border-bottom: 1px solid #222; padding: 4px 0; font-size: 12px; color: #ccc;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📜 Galeria de Trades")
    
    dfh = load_trades_db()
    if not dfh.empty: dfh = dfh[dfh['usuario'] == user]
    
    if not dfh.empty:
        with st.expander("🔍 Filtros", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            all_assets = sorted(list(dfh['ativo'].unique())) if 'ativo' in dfh.columns else ["NQ", "MNQ"]
            all_contexts = sorted(list(dfh['contexto'].unique())) if 'contexto' in dfh.columns else []
            all_groups = sorted(list(dfh['grupo_vinculo'].unique())) if 'grupo_vinculo' in dfh.columns else []
            
            fa = c1.multiselect("Ativo", all_assets)
            fr = c2.selectbox("Resultado", ["Todos", "Wins", "Losses"])
            fc = c3.multiselect("Contexto", all_contexts)
            fg = c4.multiselect("Grupo", all_groups)
            
            if fa: dfh = dfh[dfh['ativo'].isin(fa)]
            if fc: dfh = dfh[dfh['contexto'].isin(fc)]
            if fg: dfh = dfh[dfh['grupo_vinculo'].isin(fg)]
            if fr == "Wins": dfh = dfh[dfh['resultado'] > 0]
            if fr == "Losses": dfh = dfh[dfh['resultado'] < 0]
            
            dfh = dfh.sort_values('created_at', ascending=False)

        st.markdown(f"**Exibindo {len(dfh)} operações**")
        st.markdown("---")

        cols = st.columns(4)
        for i, (index, row) in enumerate(dfh.iterrows()):
            with cols[i % 4]:
                res_class = "card-res-win" if row['resultado'] >= 0 else "card-res-loss"
                res_fmt = f"${row['resultado']:,.2f}"
                
                if row.get('prints'):
                    img_html = f'<img src="{row["prints"]}" class="card-img">' 
                else:
                    img_html = '<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; color:#555; font-size:12px;">Sem Foto</div>'
                
                st.markdown(f"""
                    <div class="trade-card">
                        <div class="card-img-container">{img_html}</div>
                        <div class="card-content">
                            <div class="card-title">{row['ativo']} - {row['direcao']}</div>
                            <div class="card-sub">{row['data']} • {row['grupo_vinculo']}</div>
                        </div>
                        <div class="{res_class}">{res_fmt}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button("👁️ Detalhes", key=f"btn_{row['id']}", use_container_width=True):
                    show_trade_details(row, user, role)
    else:
        st.info("Nenhuma operação registrada ainda.")
