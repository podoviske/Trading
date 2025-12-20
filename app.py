import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
import json
import time
from PIL import Image

# --- CONFIGURAÇÃO DE PÁGINA E DIRETÓRIOS ---
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

IMG_DIR = "trade_prints"
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

# --- ESTILO CSS: O "PRÉDIO COM JANELAS" ---
st.markdown("""
    <style>
    /* Estética Geral */
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    
    /* Grid da Galeria */
    .trade-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 20px;
        padding: 10px 0;
    }

    /* O Card (Apartamento) */
    .trade-card {
        background-color: #1E1E1E;
        border-radius: 12px;
        border: 1px solid #333;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        transition: transform 0.2s, border-color 0.2s;
    }
    .trade-card:hover {
        transform: translateY(-5px);
        border-color: #B20000;
    }

    /* A Janela (Corte da Imagem) */
    .trade-window {
        width: 100%;
        height: 160px; /* Altura fixa da janela */
        background-color: #111;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        border-bottom: 1px solid #333;
    }
    .trade-window img {
        width: 100%;
        height: 100%;
        object-fit: cover; /* O segredo do alinhamento: corta sem distorcer */
    }

    /* Conteúdo do Card */
    .trade-content {
        padding: 15px;
        text-align: left;
    }
    .trade-title { font-weight: bold; font-size: 16px; margin-bottom: 5px; color: white; }
    .trade-meta { font-size: 13px; color: #888; margin-bottom: 10px; }
    
    /* Botões */
    .stButton > button { width: 100%; border-radius: 6px; font-weight: 600; }
    
    /* Pop-up (Dialog) Style */
    div[data-testid="stDialog"] div[role="dialog"] {
        background-color: #0F0F0F !important;
        border: 1px solid #333;
        max-width: 1100px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def load_atm():
    if os.path.exists(ATM_FILE):
        try:
            with open(ATM_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"Personalizado": {"lote": 0, "stop": 0.0, "parciais": []}}

def save_atm(configs):
    with open(ATM_FILE, 'w') as f: json.dump(configs, f)

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID', 'Prints']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'ID' not in df.columns: df['ID'] = [f"ID_{int(time.time())}_{i}" for i in range(len(df))]
            if 'Prints' not in df.columns: df['Prints'] = ""
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

atm_db = load_atm()
df = load_data()

# --- MODAL DE EXPANSÃO (O POP-UP) ---
@st.dialog("Detalhes da Operação", width="large")
def show_trade_details(trade_id):
    row = df[df['ID'] == trade_id].iloc[0]
    col_img, col_info = st.columns([1.8, 1])
    
    with col_img:
        p_list = str(row['Prints']).split("|") if row['Prints'] and pd.notna(row['Prints']) else []
        if p_list and os.path.exists(p_list[0]):
            st.image(p_list[0], use_container_width=True)
            st.caption("🔍 Role para ver detalhes ou use o botão de tela cheia nativo da imagem.")
        else:
            st.info("Nenhum print anexado a esta operação.")
            
    with col_info:
        st.subheader(f"Trade #{df[df['ID'] == trade_id].index[0] + 1}")
        st.markdown(f"📅 **Data:** {row['Data']}")
        st.markdown(f"🎯 **Ativo:** {row['Ativo']} | {row['Direcao']}")
        color = "#00FF88" if row['Resultado'] > 0 else "#FF4B4B"
        st.markdown(f"💰 **Resultado:** <span style='color:{color}; font-size:22px; font-weight:bold'>${row['Resultado']:,.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"📑 **Contexto:** `{row['Contexto']}`")
        st.markdown(f"⚙️ **Estratégia:** {row['ATM']}")
        st.markdown(f"📊 **Lote:** {row['Lote']} contratos")
        
        st.divider()
        if st.button("🗑️ Excluir esta operação", type="secondary"):
            st.session_state.to_delete = trade_id
            st.rerun()

# --- MENU LATERAL ---
with st.sidebar:
    st.markdown('<div style="padding:20px 10px"><span style="color:#B20000; font-size:28px; font-weight:900">EVO</span><span style="color:white; font-size:24px; font-weight:700">TRADE</span></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], default_index=0)

# --- DASHBOARD ---
if selected == "Dashboard":
    st.title("📊 Performance Analytics")
    if not df.empty:
        filtro_view = st.segmented_control("Visualizar:", options=["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
        df_f = df[df['Contexto'] == filtro_view] if filtro_view != "Capital" else df.copy()
        
        tipo_grafico = st.radio("Evolução por:", ["Tempo (Data)", "Trade a Trade"], horizontal=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("P&L Total", f"${df_f['Resultado'].sum():,.2f}")
        m2.metric("Trades", len(df_f))
        m3.metric("Win Rate", f"{(len(df_f[df_f['Resultado']>0])/len(df_f)*100):.1f}%" if len(df_f)>0 else "0%")
        
        df_g = df_f.sort_values('Data').reset_index()
        df_g['Acumulado'] = df_g['Resultado'].cumsum()
        x_axis = 'Data' if tipo_grafico == "Tempo (Data)" else df_g.index + 1
        
        fig = px.area(df_g, x=x_axis, y='Acumulado', template="plotly_dark")
        fig.update_traces(line_color='#B20000', line_shape='spline', fillcolor='rgba(178, 0, 0, 0.2)')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

# --- REGISTRAR TRADE ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    atm_sel = st.selectbox("Estratégia ATM", options=list(atm_db.keys()))
    config = atm_db[atm_sel]
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
    with c2:
        lote_t = st.number_input("Lote", min_value=0, value=int(config["lote"]))
        stop_p = st.number_input("Stop Pts", min_value=0.0, value=float(config["stop"]))
        up_files = st.file_uploader("📸 Prints (Ctrl+V aqui)", accept_multiple_files=True)
    with c3:
        st.write("**Parciais**")
        saidas = []; alocado = 0
        for i, p_c in enumerate(config["parciais"]):
            sc1, sc2 = st.columns(2)
            pts = sc1.number_input(f"Pts P{i+1}", value=float(p_c[0]), key=f"pts_{i}")
            qtd = sc2.number_input(f"Qtd P{i+1}", value=int(p_c[1]), key=f"qtd_{i}")
            saidas.append((pts, qtd)); alocado += qtd
        if lote_t > 0 and lote_t == alocado: st.success("✅ Tudo pronto")
    
    if st.button("💾 Salvar Operação"):
        t_id = f"ID_{int(time.time())}"
        paths = []
        for i, f in enumerate(up_files):
            p = os.path.join(IMG_DIR, f"{t_id}_{i}.png"); paths.append(p)
            with open(p, "wb") as bf: bf.write(f.getbuffer())
        res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas])
        n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'ID': t_id, 'Prints': "|".join(paths)}])
        df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
        st.success("🎯 Trade registrado!")

# --- HISTÓRICO (GALERIA PROFISSIONAL) ---
elif selected == "Histórico":
    st.title("📜 Galeria de Operações")
    
    if 'to_delete' in st.session_state:
        df = df[df['ID'] != st.session_state.to_delete]
        df.to_csv(CSV_FILE, index=False)
        del st.session_state.to_delete
        st.rerun()

    if not df.empty:
        df_disp = df.copy()
        df_disp['Num'] = range(1, len(df_disp) + 1)
        df_disp = df_disp.iloc[::-1]
        
        # Grid System
        cols = st.columns(4) # 4 janelas por linha
        for i, (_, row) in enumerate(df_disp.iterrows()):
            with cols[i % 4]:
                # HTML Estrutural para alinhamento via CSS
                st.markdown(f'''
                <div class="trade-card">
                    <div class="trade-window">
                        <img src="data:image/png;base64,{""}" style="display:none;"> ''', unsafe_allow_html=True)
                
                # Imagem Real do Streamlit dentro da janela
                p_list = str(row['Prints']).split("|") if row['Prints'] and pd.notna(row['Prints']) else []
                if p_list and os.path.exists(p_list[0]):
                    st.image(p_list[0], use_container_width=True)
                else:
                    st.markdown('<div style="color:#444; font-size:12px;">📁 Sem Print</div>', unsafe_allow_html=True)
                
                # Fechamento da janela e abertura da info
                st.markdown(f'''
                    </div>
                    <div class="trade-content">
                        <div class="trade-title">Trade #{row['Num']}</div>
                        <div class="trade-meta">{row['Contexto']} • {row['Ativo']}</div>
                        <div style="color:{"#00FF88" if row['Resultado'] > 0 else "#FF4B4B"}; font-weight:bold; margin-bottom:10px;">
                            ${row['Resultado']:,.2f}
                        </div>
                ''', unsafe_allow_html=True)
                
                if st.button("Ver Trade", key=f"btn_{row['ID']}", type="primary"):
                    show_trade_details(row['ID'])
                
                st.markdown('</div></div>', unsafe_allow_html=True)
    else: st.info("Vazio.")

elif selected == "Configurar ATM":
    st.title("⚙️ Editor ATM")
    # ... (Lógica de configuração ATM mantida)
