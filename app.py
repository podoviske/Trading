import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
import json
import time
from PIL import Image
import io

# --- CONFIGURAÇÃO DE PÁGINA E DIRETÓRIOS ---
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# Diretório para salvar os prints das operações
IMG_DIR = "trade_prints"
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

# --- ESTILO CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    @keyframes blinking {
        0% { background-color: #440000; } 50% { background-color: #B20000; } 100% { background-color: #440000; }
    }
    .piscante-erro {
        padding: 15px; border-radius: 5px; color: white; font-weight: bold;
        text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000; margin-top: 10px;
    }
    .logo-container { padding: 20px 15px; display: flex; flex-direction: column; }
    .logo-main { color: #B20000; font-size: 26px; font-weight: 900; line-height: 1; }
    .logo-sub { color: white; font-size: 22px; font-weight: 700; margin-top: -5px; }
    .stButton > button { width: 100%; }
    
    /* Estilização do Seletor Segmentado */
    div[data-testid="stSegmentedControl"] button {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background-color: #B20000 !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE PERSISTÊNCIA DE DADOS ---
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
            if 'ID' not in df.columns: 
                df['ID'] = [f"ID_{int(time.time())}_{i}" for i in range(len(df))]
            if 'Prints' not in df.columns: df['Prints'] = ""
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

atm_db = load_atm()
df = load_data()

# --- ESTADOS DE SESSÃO ---
if 'n_extras' not in st.session_state: st.session_state.n_extras = 0
if 'confirmar_limpeza' not in st.session_state: st.session_state.confirmar_limpeza = False

def on_atm_change():
    st.session_state.n_extras = 0

# --- MENU LATERAL ---
with st.sidebar:
    st.markdown('<div class="logo-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], 
        styles={"nav-link-selected": {"background-color": "#B20000", "color": "white"}},
        default_index=1)

# --- PÁGINA: DASHBOARD ---
if selected == "Dashboard":
    st.title("📊 EvoTrade Analytics")
    if not df.empty:
        filtro_view = st.segmented_control("Visualizar:", options=["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
        df_f = df[df['Contexto'] == filtro_view] if filtro_view != "Capital" else df.copy()
        
        # Cálculos de Performance
        wins = df_f[df_f['Resultado'] > 0]
        losses = df_f[df_f['Resultado'] < 0]
        wr = (len(wins)/len(df_f)*100) if len(df_f) > 0 else 0
        aw = wins['Resultado'].mean() if not wins.empty else 0
        al = abs(losses['Resultado'].mean()) if not losses.empty else 0
        rr = (aw/al) if al > 0 else 0
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("P&L Total", f"${df_f['Resultado'].sum():,.2f}")
        m2.metric("Win Rate", f"{wr:.1f}%")
        m3.metric("Risco:Retorno", f"1:{rr:.2f}")
        m4.metric("Ganho Médio", f"${aw:,.2f}")
        m5.metric("Perda Média", f"$-{al:,.2f}")
        
        st.markdown("---")
        tipo_grafico = st.radio("Evolução por:", ["Tempo (Data)", "Trade a Trade"], horizontal=True)
        
        df_g = df_f.sort_values('Data').reset_index()
        df_g['Acumulado'] = df_g['Resultado'].cumsum()
        x_axis = 'Data' if tipo_grafico == "Tempo (Data)" else df_g.index + 1
        
        fig = px.area(df_g, x=x_axis, y='Acumulado', title=f"Curva de Capital - {filtro_view}", template="plotly_dark")
        fig.update_traces(line_color='#B20000', line_shape='spline', fillcolor='rgba(178, 0, 0, 0.2)', mode='lines')
        fig.update_layout(hovermode="x unified", yaxis_title="Acumulado ($)", xaxis_title=str(tipo_grafico))
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Registre operações para visualizar o Dashboard.")

# --- PÁGINA: REGISTRAR TRADE ---
elif selected == "Registrar Trade":
    st.title("Registro de Trade")
    atm_sel = st.selectbox("🎯 Estratégia ATM", options=list(atm_db.keys()), key='atm_selecionado', on_change=on_atm_change)
    config = atm_db[atm_sel]
    key_prefix = atm_sel.replace(" ", "_")
    
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1:
        data = st.date_input("Data", datetime.now().date())
        ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
        contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
        direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
    with c2:
        lote_t = st.number_input("Lote Total", min_value=0, value=int(config["lote"]), key=f"lote_{key_prefix}")
        stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]), key=f"stop_{key_prefix}")
        st.metric("Risco Total", f"${(stop_p * MULTIPLIERS[ativo] * lote_t):,.2f}")
        
        st.write("📸 **Anexar Prints**")
        up_files = st.file_uploader("Upload de arquivos", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        pasted_img = st.image_input("Clique e Cole (Ctrl+V) o Print") # Recurso para colar imagem

    with c3:
        st.write("**Saídas Executadas**")
        saidas = []; alocado = 0
        for i, p_c in enumerate(config["parciais"]):
            s1, s2 = st.columns(2)
            pts = s1.number_input(f"Pts P{i+1}", key=f"p_{i}_{key_prefix}", value=float(p_c[0]))
            qtd = s2.number_input(f"Qtd P{i+1}", key=f"q_{i}_{key_prefix}", value=int(p_c[1]))
            saidas.append((pts, qtd)); alocado += qtd
        
        for i in range(st.session_state.n_extras):
            idx = len(config["parciais"]) + i
            s1, s2 = st.columns(2)
            pts = s1.number_input(f"Pts Extra {i+1}", key=f"pe_{idx}_{key_prefix}", value=0.0)
            qtd = s2.number_input(f"Qtd Extra {i+1}", key=f"qe_{idx}_{key_prefix}", value=0)
            saidas.append((pts, qtd)); alocado += qtd
            
        if lote_t > 0:
            res_c = lote_t - alocado
            if res_c != 0: st.markdown(f'<div class="piscante-erro">{"FALTAM" if res_c > 0 else "EXCESSO DE"} {abs(res_c)} CONTRATOS</div>', unsafe_allow_html=True)
            else: st.success("✅ Posição Completa")

    st.markdown("---")
    r1, r2 = st.columns(2)
    with r1:
        if st.button("💾 REGISTRAR GAIN"):
            if lote_t > 0 and alocado == lote_t:
                t_id = f"ID_{int(time.time())}"
                paths = []
                # Salva arquivos de upload
                for i, f in enumerate(up_files):
                    p = os.path.join(IMG_DIR, f"{t_id}_up_{i}.png"); paths.append(p)
                    with open(p, "wb") as bf: bf.write(f.getbuffer())
                # Salva imagem colada
                if pasted_img:
                    p_pst = os.path.join(IMG_DIR, f"{t_id}_pst.png"); paths.append(p_pst)
                    Image.open(pasted_img).save(p_pst)
                
                res = sum([s[0] * MULTIPLIERS[ativo] * s[1] for s in saidas])
                n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': (res/(lote_t*MULTIPLIERS[ativo])), 'Risco_Fin': (stop_p * MULTIPLIERS[ativo] * lote_t), 'ID': t_id, 'Prints': "|".join(paths)}])
                df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.success("🎯 Trade registrado!"); time.sleep(1); st.rerun()

    with r2:
        if st.button("🚨 REGISTRAR STOP FULL", type="secondary"):
            if lote_t > 0:
                t_id = f"ID_{int(time.time())}"
                res = -(stop_p * MULTIPLIERS[ativo] * lote_t)
                n_t = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': -stop_p, 'Risco_Fin': abs(res), 'ID': t_id, 'Prints': ""}])
                df = pd.concat([df, n_t], ignore_index=True); df.to_csv(CSV_FILE, index=False)
                st.error("🚨 Stop registrado!"); time.sleep(1); st.rerun()

# --- PÁGINA: HISTÓRICO (MODO GALERIA) ---
elif selected == "Histórico":
    st.title("📜 Galeria de Operações")
    if not df.empty:
        df_h = df.copy(); df_h['Num'] = range(1, len(df_h)+1)
        df_disp = df_h.iloc[::-1] # Mais recente primeiro
        
        cols = st.columns(4)
        for i, (idx, row) in enumerate(df_disp.iterrows()):
            with cols[i % 4]:
                p_list = str(row['Prints']).split("|") if row['Prints'] else []
                if p_list and os.path.exists(p_list[0]): st.image(p_list[0], use_container_width=True)
                else: st.image("https://via.placeholder.com/150/111111/FFFFFF?text=Sem+Print", use_container_width=True)
                st.caption(f"Trade #{row['Num']} | ${row['Resultado']:,.2f}")
                if st.button("👁️ Ver", key=f"v_{row['ID']}"): st.session_state.selected_id = row['ID']

        if 'selected_id' in st.session_state:
            st.markdown("---")
            sel = df[df['ID'] == st.session_state.selected_id].iloc[0]
            ci, cd = st.columns([2, 1])
            with ci:
                ps = str(sel['Prints']).split("|") if sel['Prints'] else []
                for p in ps: 
                    if os.path.exists(p): st.image(p)
            with cd:
                st.subheader(f"Detalhes Trade #{sel.name + 1}")
                st.write(f"**Ativo:** {sel['Ativo']} | **Direção:** {sel['Direcao']}")
                st.write(f"**Resultado:** ${sel['Resultado']:,.2f}")
                if st.button("Deletar"):
                    df = df[df['ID'] != sel['ID']]; df.to_csv(CSV_FILE, index=False)
                    del st.session_state.selected_id; st.rerun()
                if st.button("Fechar"): del st.session_state.selected_id; st.rerun()
    else: st.info("Histórico vazio.")

# --- PÁGINA: CONFIGURAR ATM ---
elif selected == "Configurar ATM":
    st.title("⚙️ Editor de Estratégias ATM")
    with st.expander("✨ Criar Novo Template", expanded=True):
        n = st.text_input("Nome da Estratégia")
        ca1, ca2 = st.columns(2)
        l = ca1.number_input("Lote Total", min_value=1)
        s = ca2.number_input("Stop (Pts)", 0.0)
        np = st.number_input("Número de Alvos", 1, 6)
        nps = []
        for i in range(np):
            cp1, cp2 = st.columns(2)
            pt = cp1.number_input(f"Alvo P{i+1} (Pts)", key=f"ap{i}")
            qt = cp2.number_input(f"Contratos P{i+1}", key=f"aq{i}")
            nps.append([pt, qt])
        if st.button("💾 Salvar Estratégia"):
            if n:
                atm_db[n] = {"lote": l, "stop": s, "parciais": nps}
                save_atm(atm_db); st.success("Salvo!"); st.rerun()
    st.markdown("---")
    for nome in list(atm_db.keys()):
        if nome != "Personalizado":
            col_n, col_b = st.columns([4, 1])
            col_n.write(f"**{nome}**")
            if col_b.button("Excluir", key=f"del_{nome}"):
                del atm_db[nome]; save_atm(atm_db); st.rerun()
