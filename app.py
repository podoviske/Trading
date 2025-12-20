import streamlit as st
import pandas as pd
import os
import json
import time
import uuid
import base64
import io
from datetime import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

# --- CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# --- CONEXÃO GOOGLE DRIVE ---
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_NAME = "EvoTrade_Data"

def get_drive_service():
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Erro na credencial: {e}")
        return None

DRIVE = get_drive_service()

def get_folder_id():
    query = f"name = '{FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = DRIVE.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    return items[0]['id'] if items else None

FOLDER_ID = get_folder_id()

def save_to_drive(file_name, content, mime_type='application/octet-stream'):
    query = f"name = '{file_name}' and '{FOLDER_ID}' in parents and trashed = false"
    results = DRIVE.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    
    fh = io.BytesIO(content)
    media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)
    file_metadata = {'name': file_name, 'parents': [FOLDER_ID]}
    
    if items:
        DRIVE.files().update(fileId=items[0]['id'], media_body=media).execute()
    else:
        DRIVE.files().create(body=file_metadata, media_body=media, fields='id').execute()

def load_from_drive(file_name):
    query = f"name = '{file_name}' and '{FOLDER_ID}' in parents and trashed = false"
    results = DRIVE.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    if not items: return None
    
    request = DRIVE.files().get_media(fileId=items[0]['id'])
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return fh.getvalue()

# --- SISTEMA DE LOGIN ---
def check_password():
    def password_entered():
        if st.session_state["username"] == "admin" and st.session_state["password"] == "1234":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else: st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            st.markdown("<h1 style='text-align:center; color:#B20000;'>EVO TRADE</h1>", unsafe_allow_html=True)
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("😕 Credenciais incorretas.")
        return False
    return True

if check_password():
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}
    
    # Carregar Banco de Dados do Drive
    csv_data = load_from_drive("evotrade_data.csv")
    if csv_data:
        df = pd.read_csv(io.BytesIO(csv_data))
        df['Data'] = pd.to_datetime(df['Data']).dt.date
    else:
        df = pd.DataFrame(columns=['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID', 'Prints', 'Notas'])

    # Carregar ATMs do Drive
    atm_data = load_from_drive("atm_configs.json")
    atm_db = json.loads(atm_data.decode('utf-8')) if atm_data else {"Personalizado": {"lote": 1, "stop": 0.0, "parciais": []}}

    # --- ESTILO CSS ---
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #1E1E1E; }
        .stApp { background-color: #0F0F0F; }
        .metric-container { background-color: #161616; border: 1px solid #262626; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 15px; }
        .metric-label { color: #888; font-size: 13px; text-transform: uppercase; }
        .metric-value { color: white; font-size: 24px; font-weight: bold; }
        .trade-card { background-color: #161616; border: 1px solid #333; border-radius: 12px; margin-bottom: 20px; height: 360px; display: flex; flex-direction: column; overflow: hidden; }
        .img-container { width: 100%; height: 180px; background-color: #000; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid #333; }
        .img-container img { width: 100%; height: 100%; object-fit: cover; }
        .card-footer { padding: 15px; text-align: center; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        </style>
    """, unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown('<h2 style="color:#B20000;">EVO TRADE</h2>', unsafe_allow_html=True)
        selected = option_menu(None, ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], 
            icons=["grid-1x2", "currency-dollar", "gear", "clock-history"], styles={"nav-link-selected": {"background-color": "#B20000"}})
        if st.button("Sair"):
            del st.session_state["password_correct"]
            st.rerun()

    # --- ABA: DASHBOARD ---
    if selected == "Dashboard":
        st.markdown("## 📊 Dashboard")
        if not df.empty:
            f_v = st.segmented_control("Ver:", ["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
            df_f = df.copy() if f_v == "Capital" else df[df['Contexto'] == f_v].copy()
            
            if not df_f.empty:
                total = len(df_f)
                total_pl = df_f['Resultado'].sum()
                wr = (len(df_f[df_f['Resultado'] > 0])/total*100)
                
                c1, c2, c3 = st.columns(3)
                with c1: st.markdown(f'<div class="metric-container"><div class="metric-label">P&L TOTAL</div><div class="metric-value">${total_pl:,.2f}</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="metric-container"><div class="metric-label">WIN RATE</div><div class="metric-value">{wr:.1f}%</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="metric-container"><div class="metric-label">TRADES</div><div class="metric-value">{total}</div></div>', unsafe_allow_html=True)
                
                df_g = df_f.sort_values('Data').reset_index(drop=True)
                df_g['Acumulado'] = df_g['Resultado'].cumsum()
                fig = px.area(df_g, x=df_g.index + 1, y='Acumulado', template="plotly_dark", markers=True)
                fig.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                st.plotly_chart(fig, use_container_width=True)

    # --- ABA: REGISTRAR TRADE ---
    elif selected == "Registrar Trade":
        st.title("Registrar Trade")
        atm_sel = st.selectbox("🎯 ATM", list(atm_db.keys()))
        config = atm_db[atm_sel]
        
        c1, c2 = st.columns(2)
        with c1:
            data = st.date_input("Data", datetime.now().date())
            ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
            contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
            direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        with c2:
            lote_t = st.number_input("Contratos", min_value=1, value=int(config["lote"]))
            pts = st.number_input("Média Pts", value=0.0)
            up_files = st.file_uploader("Prints", accept_multiple_files=True)

        if st.button("💾 REGISTRAR", use_container_width=True):
            n_id = str(uuid.uuid4())
            print_names = []
            for i, f in enumerate(up_files):
                name = f"{n_id}_{i}.png"
                save_to_drive(name, f.getvalue(), 'image/png')
                print_names.append(name)
            
            res = pts * lote_t * MULTIPLIERS[ativo]
            new_trade = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': pts, 'ID': n_id, 'Prints': "|".join(print_names)}])
            df = pd.concat([df, new_trade], ignore_index=True)
            save_to_drive("evotrade_data.csv", df.to_csv(index=False).encode('utf-8'))
            st.success("🎯 Trade Salvo no Drive!"); time.sleep(1); st.rerun()

    # --- ABA: HISTÓRICO ---
    elif selected == "Histórico":
        st.title("Histórico")
        if not df.empty:
            df_disp = df.iloc[::-1]
            for i in range(0, len(df_disp), 5):
                cols = st.columns(5)
                for j in range(5):
                    if i + j < len(df_disp):
                        row = df_disp.iloc[i + j]
                        with cols[j]:
                            p_list = str(row['Prints']).split("|") if row['Prints'] else []
                            img_data = load_from_drive(p_list[0]) if p_list else None
                            b64 = base64.b64encode(img_data).decode() if img_data else ""
                            img_html = f'<img src="data:image/png;base64,{b64}">' if b64 else "Sem Print"
                            st.markdown(f'<div class="trade-card"><div class="img-container">{img_html}</div><div class="card-footer"><div><b>Trade</b><br><small>{row["Contexto"]}</small></div><div style="color:{"#00FF88" if row["Resultado"] > 0 else "#FF4B4B"}; font-weight:bold;">${row["Resultado"]:,.2f}</div></div></div>', unsafe_allow_html=True)

    # --- ABA: CONFIGURAR ATM ---
    elif selected == "Configurar ATM":
        st.title("Configurar ATM")
        n = st.text_input("Nome da ATM")
        l = st.number_input("Lote Total", 1)
        if st.button("Salvar ATM"):
            atm_db[n] = {"lote": l}
            save_to_drive("atm_configs.json", json.dumps(atm_db).encode('utf-8'))
            st.success("ATM Salva!"); st.rerun()
