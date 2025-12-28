import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Inicializa conexão (Singleton)
@st.cache_resource
def get_db():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de conexão DB: {e}")
        return None

supabase = get_db()

def load_trades(user):
    try:
        res = supabase.table("trades").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['resultado'] = pd.to_numeric(df['resultado'], errors='coerce').fillna(0.0)
            df['lote'] = pd.to_numeric(df['lote'], errors='coerce').fillna(0)
            if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
            if 'comportamento' not in df.columns: df['comportamento'] = 'Normal'
            # Filtra pelo usuário aqui para segurança
            return df[df['usuario'] == user].copy()
        return pd.DataFrame()
    except: return pd.DataFrame()

def load_contas(user):
    try:
        res = supabase.table("contas_config").select("*").eq("usuario", user).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['saldo_inicial'] = pd.to_numeric(df['saldo_inicial'], errors='coerce').fillna(0.0)
            df['pico_previo'] = pd.to_numeric(df['pico_previo'], errors='coerce').fillna(0.0)
        return df
    except: return pd.DataFrame()

def load_grupos(user):
    try:
        res = supabase.table("grupos_config").select("*").eq("usuario", user).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def load_atms():
    try:
        res = supabase.table("atm_configs").select("*").execute()
        return {item['nome']: item for item in res.data}
    except: return {}
