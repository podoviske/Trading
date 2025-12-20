import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
import json
import time  # Importado para o timer

# Configuração da Página
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
    .stApp { background-color: #0F0F0F; }
    @keyframes blinking {
        0% { background-color: #440000; }
        50% { background-color: #B20000; }
        100% { background-color: #440000; }
    }
    .piscante-erro {
        padding: 15px; border-radius: 5px; color: white; font-weight: bold;
        text-align: center; animation: blinking 2.4s infinite; border: 1px solid #FF0000;
        margin-top: 10px;
    }
    .logo-container { padding: 20px 15px; display: flex; flex-direction: column; }
    .logo-main { color: #B20000; font-size: 26px; font-weight: 900; line-height: 1; }
    .logo-sub { color: white; font-size: 22px; font-weight: 700; margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- PERSISTÊNCIA ---
CSV_FILE = 'evotrade_data.csv'
ATM_FILE = 'atm_configs.json'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

def load_atm():
    if os.path.exists(ATM_FILE):
        try:
            with open(ATM_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"Personalizado": {"lote": 0, "stop": 0.0, "parciais": []}}

def save_atm(configs):
    with open(ATM_FILE, 'w') as f: json.dump(configs, f)

def load_data():
    cols = ['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin']
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            for col in cols:
                if col not in df.columns: df[col] = 0
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

atm_db = load_atm()
df = load_data()

# --- ESTADO ---
if 'n_extras' not in st.session_state: st.session_state.n_extras = 0
if 'confirmar_limpeza' not in st.session_state: st.session_state.confirmar_limpeza = False

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="logo-container"><div class="logo-main">EVO</div><div class="logo-sub">TRADE</div></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
        icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], styles={
            "nav-link-selected": {"background-color": "#B20000", "color": "white"}
        })

# --- PÁGINAS (DASHBOARD, REGISTRAR E CONFIGURAR SEGUEM A LÓGICA ANTERIOR) ---
# ... (Código intermediário omitido para focar na mudança do Histórico) ...

if selected == "Registrar Trade":
    # (Mantém toda a lógica de registro de trade com ATM que validamos)
    st.title("Registro de Trade")
    # ... (mesmo código do turno anterior) ...
    # (Copie a parte do Registrar Trade do código anterior se for substituir tudo)
    pass

elif selected == "Dashboard":
    # (Mantém o dashboard anterior)
    pass

elif selected == "Configurar ATM":
    # (Mantém o configurador anterior)
    pass

# --- PÁGINA: HISTÓRICO COM TIMER ---
elif selected == "Histórico":
    st.title("📜 Histórico de Trades")
    if not df.empty:
        col_export, col_limpar = st.columns([4, 1])
        
        csv_data = df.to_csv(index=False).encode('utf-8')
        col_export.download_button("📥 Exportar Backup (CSV)", data=csv_data, file_name="backup_trades.csv")
        
        if not st.session_state.confirmar_limpeza:
            if col_limpar.button("🗑️ Limpar Histórico", type="secondary", use_container_width=True):
                st.session_state.confirmar_limpeza = True
                st.rerun()
        else:
            with col_limpar:
                st.warning("Aguarde o Timer...")
                placeholder_timer = st.empty()
                
                # Loop do Timer de 10 segundos
                for i in range(10, 0, -1):
                    placeholder_timer.button(f"Confirmar em {i}s...", disabled=True, key=f"btn_time_{i}", use_container_width=True)
                    time.sleep(1)
                
                placeholder_timer.empty() # Limpa o botão desabilitado
                
                c_sim, c_nao = st.columns(2)
                if c_sim.button("✅ APAGAR", type="primary", key="confirma_real"):
                    if os.path.exists(CSV_FILE): os.remove(CSV_FILE)
                    st.session_state.confirmar_limpeza = False
                    st.success("Histórico apagado!")
                    st.rerun()
                
                if c_nao.button("❌ Cancelar", key="cancela_real"):
                    st.session_state.confirmar_limpeza = False
                    st.rerun()

        st.markdown("---")
        st.dataframe(df.sort_values('Data', ascending=False), use_container_width=True)
    else:
        st.info("Nenhum trade registrado.")
