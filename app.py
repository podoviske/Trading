import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração e Estilo
st.set_page_config(page_title="Master Trading Journal", layout="wide", page_icon="📈")

CSV_FILE = 'trades_database.csv'

def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=['Data', 'Ativo', 'Direcao', 'Entrada', 'Saida', 'Qtd', 'Resultado', 'Notas'])

df = load_data()

st.title("🚀 Meu Diário de Trade Profissional")

tab1, tab2, tab3 = st.tabs(["📝 Registrar", "📊 Performance", "📋 Histórico"])

with tab1:
    with st.form("main_form"):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data", datetime.now())
            ativo = st.text_input("Ativo").upper()
            direcao = st.selectbox("Operação", ["Compra", "Venda"])
        with col2:
            entrada = st.number_input("Preço Entrada", min_value=0.0)
            saida = st.number_input("Preço Saída", min_value=0.0)
            qtd = st.number_input("Quantidade", min_value=1)
        
        # Campo para anotações
        notas = st.text_area("O que aconteceu nesse trade?")
        
        submit = st.form_submit_button("Salvar Trade")
        
        if submit:
            res = (saida - entrada) * qtd if direcao == "Compra" else (entrada - saida) * qtd
            novo = pd.DataFrame([[data, ativo, direcao, entrada, saida, qtd, res, notas]], 
                                columns=df.columns)
            df = pd.concat([df, novo], ignore_index=True)
            df.to_csv(CSV_FILE, index=False)
            st.success("Registrado com sucesso!")
            st.rerun()

with tab2:
    if not df.empty:
        st.metric("Lucro Acumulado", f"R$ {df['Resultado'].sum():.2f}")
        st.line_chart(df['Resultado'].cumsum())
    else:
        st.info("Sem dados para exibir.")

with tab3:
    st.dataframe(df, use_container_width=True)
