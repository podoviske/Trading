import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px # Para gráficos mais profissionais

# Configuração da Página
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide", page_icon="📊")

CSV_FILE = 'trades_v2.csv'

def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df
    return pd.DataFrame(columns=[
        'Data', 'Ativo', 'Contexto', 'Direcao', 'Entrada', 'Saida', 
        'Contratos_Total', 'Parcial_1_Pontos', 'Parcial_1_Contratos',
        'Risco_Financeiro', 'Risco_Pontos', 'Resultado', 'Notas'
    ])

df = load_data()

st.title("📊 Master Trading Analytics")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🚀 Registrar Operação", "📈 Dashboard de Performance", "📋 Livro de Ordens"])

with tab1:
    st.subheader("Novo Registro Detalhado")
    with st.form("trade_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        
        with c1:
            data = st.date_input("Data", datetime.now())
            ativo = st.text_input("Ativo").upper()
            contexto = st.selectbox("Contexto da Operação", ["Contexto A", "Contexto B", "Contexto C"])
            direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)

        with c2:
            entrada = st.number_input("Preço Entrada", min_value=0.0)
            saida = st.number_input("Preço Saída Final", min_value=0.0)
            contratos = st.number_input("Total de Contratos", min_value=1)
            p_parcial = st.number_input("1ª Parcial (Pontos)", min_value=0.0)
            q_parcial = st.number_input("Contratos na 1ª Parcial", min_value=0)

        with c3:
            risco_fin = st.number_input("Risco Financeiro (R$)", min_value=0.0)
            risco_pts = st.number_input("Risco em Pontos", min_value=0.0)
            notas = st.text_area("Notas / Psicológico")

        submit = st.form_submit_button("💾 Salvar no Banco de Dados")

        if submit:
            # Cálculo de resultado simplificado (ajuste conforme a regra do seu ativo)
            res = (saida - entrada) * contratos if direcao == "Compra" else (entrada - saida) * contratos
            
            novo_row = pd.DataFrame([{
                'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao,
                'Entrada': entrada, 'Saida': saida, 'Contratos_Total': contratos,
                'Parcial_1_Pontos': p_parcial, 'Parcial_1_Contratos': q_parcial,
                'Risco_Financeiro': risco_fin, 'Risco_Pontos': risco_pts, 'Resultado': res, 'Notas': notas
            }])
            
            df = pd.concat([df, novo_row], ignore_index=True)
            df.to_csv(CSV_FILE, index=False)
            st.success(f"Trade registrado! Lucro/Prejuízo: R$ {res:.2f}")
            st.rerun()

with tab2:
    if not df.empty:
        # --- INDICADORES (KPIs) ---
        total_ganho = df['Resultado'].sum()
        win_rate = (len(df[df['Resultado'] > 0]) / len(df)) * 100
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("P&L Total Acumulado", f"R$ {total_ganho:.2f}", delta=f"{total_ganho:.2f}")
        kpi2.metric("Taxa de Acerto", f"{win_rate:.1f}%")
        kpi3.metric("Total de Trades", len(df))

        st.markdown("---")
        
        # --- ANÁLISE DE RISCO POR CONTEXTO ---
        st.subheader("🎯 Inteligência por Contexto")
        col_risk1, col_risk2 = st.columns(2)
        
        # Agrupamento para média de risco
        stats_contexto = df.groupby('Contexto').agg({
            'Risco_Financeiro': 'mean',
            'Risco_Pontos': 'mean',
            'Resultado': 'sum'
        }).reset_index()

        with col_risk1:
            st.write("**Risco Médio Financeiro por Tipo**")
            fig_risco = px.bar(stats_contexto, x='Contexto', y='Risco_Financeiro', color='Contexto', template="plotly_dark")
            st.plotly_chart(fig_risco, use_container_width=True)

        with col_risk2:
            st.write("**Risco Médio em Pontos por Tipo**")
            fig_pts = px.line(stats_contexto, x='Contexto', y='Risco_Pontos', markers=True, template="plotly_dark")
            st.plotly_chart(fig_pts, use_container_width=True)

        # --- CURVA DE PATRIMÔNIO ---
        st.subheader("📈 Evolução da Conta")
        df['Acumulado'] = df['Resultado'].cumsum()
        fig_evolucao = px.area(df, x=df.index, y='Acumulado', title="Curva de Capital", template="plotly_dark")
        st.plotly_chart(fig_evolucao, use_container_width=True)
    else:
        st.info("Aguardando dados para gerar o Dashboard...")

with tab3:
    st.subheader("Histórico Completo")
    st.dataframe(df, use_container_width=True)
    if st.button("Limpar Histórico"):
        if os.path.exists(CSV_FILE): os.remove(CSV_FILE); st.rerun()
