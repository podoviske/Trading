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
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="EvoTrade", layout="wide", page_icon="📈")

# --- CONEXÃO GOOGLE DRIVE (SISTEMA DE PERSISTÊNCIA) ---
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_NAME = "EvoTrade_Data"

def get_drive_service():
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Erro na conexão com Drive: {e}")
        return None

DRIVE = get_drive_service()

def get_folder_id():
    query = f"name = '{FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = DRIVE.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']
    else:
        file_metadata = {'name': FOLDER_NAME, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = DRIVE.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

FOLDER_ID = get_folder_id()

def save_to_drive(file_name, content, mime_type='application/octet-stream'):
    query = f"name = '{file_name}' and '{FOLDER_ID}' in parents and trashed = false"
    results = DRIVE.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    fh = io.BytesIO(content)
    media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)
    if items:
        DRIVE.files().update(fileId=items[0]['id'], media_body=media).execute()
    else:
        file_metadata = {'name': file_name, 'parents': [FOLDER_ID]}
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
            st.markdown('<h1 style="color:#B20000; text-align:center;">EVO TRADE</h1>', unsafe_allow_html=True)
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            st.button("Acessar Terminal", on_click=password_entered, use_container_width=True)
        return False
    return True

if check_password():
    CSV_FILE = 'evotrade_data.csv'
    ATM_FILE = 'atm_configs.json'
    MULTIPLIERS = {"NQ": 20, "MNQ": 2}

    csv_bytes = load_from_drive(CSV_FILE)
    if csv_bytes:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        df['Data'] = pd.to_datetime(df['Data']).dt.date
    else:
        df = pd.DataFrame(columns=['Data', 'Ativo', 'Contexto', 'Direcao', 'Lote', 'ATM', 'Resultado', 'Pts_Medio', 'Risco_Fin', 'ID', 'Prints', 'Notas'])

    atm_bytes = load_from_drive(ATM_FILE)
    atm_db = json.loads(atm_bytes.decode()) if atm_bytes else {"Personalizado": {"lote": 1, "stop": 0.0, "parciais": []}}

    # --- CSS PREMIUM ---
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #111111 !important; }
        .stApp { background-color: #0F0F0F; }
        .metric-container { background-color: #161616; border: 1px solid #262626; padding: 20px; border-radius: 10px; text-align: center; }
        .metric-label { color: #888; font-size: 12px; text-transform: uppercase; }
        .metric-value { color: white; font-size: 22px; font-weight: bold; }
        .trade-card { background-color: #161616; border: 1px solid #333; border-radius: 12px; height: 360px; overflow: hidden; display: flex; flex-direction: column; }
        .img-container { width: 100%; height: 180px; background-color: #000; display: flex; align-items: center; justify-content: center; }
        .card-footer { padding: 15px; text-align: center; }
        .piscante-erro { padding: 10px; background-color: #B20000; color: white; font-weight: bold; text-align: center; border-radius: 5px; animation: blinker 1.5s linear infinite; }
        @keyframes blinker { 50% { opacity: 0; } }
        </style>
    """, unsafe_allow_html=True)

    def card_metric(label, value, color="white"):
        st.markdown(f'<div class="metric-container"><div class="metric-label">{label}</div><div class="metric-value" style="color: {color};">{value}</div></div>', unsafe_allow_html=True)

    @st.dialog("Detalhes do Trade", width="large")
    def expand_modal(trade_id):
        row = df[df['ID'] == trade_id].iloc[0]
        c1, c2 = st.columns([1.5, 1])
        with c1:
            p_list = [p.strip() for p in str(row['Prints']).split("|") if p.strip()]
            if p_list:
                tabs = st.tabs([f"Print {i+1}" for i in range(len(p_list))])
                for i, tab in enumerate(tabs):
                    with tab:
                        img_data = load_from_drive(p_list[i])
                        if img_data: st.image(img_data, use_container_width=True)
            notas = st.text_area("Notas:", value=str(row['Notas']) if pd.notna(row['Notas']) else "", height=150)
            if st.button("💾 Salvar Notas"):
                df.loc[df['ID'] == trade_id, 'Notas'] = notas
                save_to_drive(CSV_FILE, df.to_csv(index=False).encode())
                st.success("Salvo!"); st.rerun()
        with c2:
            st.write(f"📅 **Data:** {row['Data']} | **Ativo:** {row['Ativo']}")
            st.markdown(f"💰 **P&L:** ${row['Resultado']:,.2f}")
            if st.button("🗑️ Deletar Trade"):
                new_df = df[df['ID'] != trade_id]
                save_to_drive(CSV_FILE, new_df.to_csv(index=False).encode())
                st.rerun()

    with st.sidebar:
        selected = option_menu("EVO TRADE", ["Dashboard", "Registrar Trade", "Configurar ATM", "Histórico"], icons=["grid-1x2", "currency-dollar", "gear", "clock-history"])

    if selected == "Dashboard":
        st.title("📊 Analytics")
        if not df.empty:
            f_v = st.segmented_control("Visão:", ["Capital", "Contexto A", "Contexto B", "Contexto C"], default="Capital")
            df_f = df.copy() if f_v == "Capital" else df[df['Contexto'] == f_v].copy()
            if not df_f.empty:
                total = len(df_f); wins = df_f[df_f['Resultado'] > 0]; losses = df_f[df_f['Resultado'] < 0]
                total_pl = df_f['Resultado'].sum(); wr = (len(wins)/total*100)
                aw = wins['Resultado'].mean() if not wins.empty else 0
                al = abs(losses['Resultado'].mean()) if not losses.empty else 0
                rr = (aw/al) if al > 0 else 0
                avg_pts_gain = wins['Pts_Medio'].mean() if not wins.empty else 0
                avg_pts_loss = abs(losses['Pts_Medio'].mean()) if not losses.empty else 0
                avg_lote = df_f['Lote'].mean()

                r1, r2, r3 = st.columns(3)
                with r1: card_metric("P&L TOTAL", f"${total_pl:,.2f}", "#00FF88" if total_pl > 0 else "#FF4B4B")
                with r1: card_metric("RISCO:RETORNO", f"1:{rr:.2f}")
                with r1: card_metric("PTS MÉD GAIN", f"{avg_pts_gain:.2f}")
                
                with r2: card_metric("WIN RATE", f"{wr:.1f}%", "#B20000")
                with r2: card_metric("LOTE MÉDIO", f"{avg_lote:.1f}")
                with r2: card_metric("PTS MÉD LOSS", f"{avg_pts_loss:.2f}")
                
                with r3: card_metric("TRADES TOTAL", total)
                with r3: card_metric("GAIN MÉDIO ($)", f"${aw:,.2f}", "#00FF88")
                with r3: card_metric("LOSS MÉDIO ($)", f"$-{al:,.2f}", "#FF4B4B")

                df_g = df_f.sort_values('Data').reset_index(drop=True); df_g['Acumulado'] = df_g['Resultado'].cumsum()
                st.plotly_chart(px.area(df_g, x=df_g.index+1, y='Acumulado', template="plotly_dark").update_traces(line_color='#B20000'), use_container_width=True)

    elif selected == "Registrar Trade":
        st.title("Registro")
        if 'n_extras' not in st.session_state: st.session_state.n_extras = 0
        atm_sel = st.selectbox("🎯 ATM", list(atm_db.keys()))
        config = atm_db[atm_sel]
        
        col1, col2, col3 = st.columns([1, 1, 2.5])
        with col1:
            data = st.date_input("Data", datetime.now().date()); ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
            contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"]); direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
        with col2:
            lote_t = st.number_input("Contratos", min_value=1, value=int(config["lote"])); stop_p = st.number_input("Stop (Pts)", min_value=0.0, value=float(config["stop"]))
            up_files = st.file_uploader("📸 Prints", accept_multiple_files=True)
        with col3:
            st.write("**Saídas**"); saidas = []; alocado = 0
            for i, p_c in enumerate(config["parciais"]):
                c_p1, c_p2 = st.columns(2); p = c_p1.number_input(f"Pts P{i+1}", value=float(p_c[0]), key=f"p_{i}"); q = c_p2.number_input(f"Qtd P{i+1}", value=int(p_c[1]), key=f"q_{i}"); saidas.append((p, q)); alocado += q
            if lote_t != alocado: st.markdown(f'<div class="piscante-erro">FALTAM {lote_t-alocado}</div>', unsafe_allow_html=True)
        
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            if st.button("💾 REGISTRAR GAIN", use_container_width=True):
                if lote_t == alocado:
                    res = sum([s[0]*MULTIPLIERS[ativo]*s[1] for s in saidas]); pts_m = sum([s[0]*s[1] for s in saidas]) / lote_t
                    n_id = str(uuid.uuid4()); paths = []
                    for i, f in enumerate(up_files):
                        p_name = f"{n_id}_{i}.png"; save_to_drive(p_name, f.getvalue(), 'image/png'); paths.append(p_name)
                    new_r = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': pts_m, 'ID': n_id, 'Prints': "|".join(paths), 'Notas': ""}])
                    df = pd.concat([df, new_r], ignore_index=True); save_to_drive(CSV_FILE, df.to_csv(index=False).encode()); st.success("🎯 Gain Salvo!"); time.sleep(1); st.rerun()
        with c_r2:
            if st.button("🚨 REGISTRAR STOP", type="secondary", use_container_width=True):
                res = -(stop_p * MULTIPLIERS[ativo] * lote_t); n_id = str(uuid.uuid4()); paths = []
                for i, f in enumerate(up_files):
                    p_name = f"{n_id}_{i}.png"; save_to_drive(p_name, f.getvalue(), 'image/png'); paths.append(p_name)
                new_r = pd.DataFrame([{'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao, 'Lote': lote_t, 'ATM': atm_sel, 'Resultado': res, 'Pts_Medio': -stop_p, 'ID': n_id, 'Prints': "|".join(paths), 'Notas': ""}])
                df = pd.concat([df, new_r], ignore_index=True); save_to_drive(CSV_FILE, df.to_csv(index=False).encode()); st.error("🚨 Stop Salvo!"); time.sleep(1); st.rerun()

    elif selected == "Histórico":
        st.title("📜 Histórico")
        if not df.empty:
            df_disp = df.iloc[::-1]
            for i in range(0, len(df_disp), 5):
                cols = st.columns(5)
                for j in range(5):
                    if i + j < len(df_disp):
                        row = df_disp.iloc[i + j]; p_list = str(row['Prints']).split("|") if row['Prints'] else []
                        with cols[j]:
                            img_b64 = ""; img_bytes = load_from_drive(p_list[0]) if p_list else None
                            if img_bytes: img_b64 = base64.b64encode(img_bytes).decode()
                            img_tag = f'<img src="data:image/png;base64,{img_b64}">' if img_b64 else 'Sem Foto'
                            st.markdown(f'<div class="trade-card"><div class="img-container">{img_tag}</div><div class="card-footer"><b>{row["Contexto"]}</b><br><span style="color:{"#00FF88" if row["Resultado"] > 0 else "#FF4B4B"}">${row["Resultado"]:,.2f}</span>', unsafe_allow_html=True)
                            if st.button("Ver", key=f"v_{row['ID']}"): expand_modal(row['ID'])
                            st.markdown('</div></div>', unsafe_allow_html=True)

    elif selected == "Configurar ATM":
        st.title("⚙️ Editor ATM")
        with st.expander("Nova ATM"):
            nome = st.text_input("Nome"); l_t = st.number_input("Lote Total", 1); s_t = st.number_input("Stop (Pts)", 0.0); n_alv = st.number_input("Alvos", 1, 5); novas = []
            for i in range(n_alv):
                c1, c2 = st.columns(2); novas.append([c1.number_input(f"Pts {i+1}", key=f"ap_{i}"), c2.number_input(f"Qtd {i+1}", key=f"aq_{i}", min_value=1)])
            if st.button("Salvar ATM"):
                atm_db[nome] = {"lote": l_t, "stop": s_t, "parciais": novas}
                save_to_drive(ATM_FILE, json.dumps(atm_db).encode()); st.rerun()
