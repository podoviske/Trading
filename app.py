import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Trading Dashboard NQ/MNQ", layout="wide", page_icon="📈")

CSV_FILE = 'trades_nq_mnq_v2.csv'
MULTIPLIERS = {"NQ": 20, "MNQ": 2}

def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df
    return pd.DataFrame()

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

df = load_data()

# --- LÓGICA DE PARCIAIS ---
if 'n_parciais' not in st.session_state:
    st.session_state.n_parciais = 1

def adicionar_parcial():
    if st.session_state.n_parciais < 6:
        st.session_state.n_parciais += 1

def limpar_parciais():
    st.session_state.n_parciais = 1

st.title("📊 Master Analytics - NQ & MNQ")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🚀 Registrar Trade", "📈 Dashboard Avançado", "📋 Histórico"])

with tab1:
    # Cabeçalho com botões alinhados à direita
    col_tit, col_btns = st.columns([2, 1])
    with col_tit:
        st.subheader("Novo Registro Detalhado")
    with col_btns:
        c_add, c_res = st.columns(2)
        with c_add:
            st.button("➕ Add Parcial", on_click=adicionar_parcial, use_container_width=True)
        with c_res:
            st.button("🧹 Resetar", on_click=limpar_parciais, use_container_width=True)

    with st.form("trade_form"):
        c1, c2, c3 = st.columns([1, 1, 2])
        
        with c1:
            data = st.date_input("Data", datetime.now())
            ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
            contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
            direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            entrada = st.number_input("Preço de Entrada", min_value=0.0, step=0.25, format="%.2f")

        with c2:
            lote_total = st.number_input("Contratos Totais", min_value=1, step=1, value=1)
            stop_pts = st.number_input("Risco em Pontos (Stop)", min_value=0.0, step=0.25, format="%.2f")
            risco_financeiro = stop_pts * MULTIPLIERS[ativo] * lote_total
            st.info(f"Risco Calculado: ${risco_financeiro:.2f}")

        with c3:
            st.write("**Saídas / Parciais**")
            parciais_inputs = []
            contratos_alocados = 0
            
            for i in range(st.session_state.n_parciais):
                cp1, cp2 = st.columns([1, 1])
                with cp1:
                    pts = st.number_input(f"Pts Parcial {i+1}", min_value=0.0, step=0.25, key=f"pts_{i}")
                with cp2:
                    # O valor padrão é 0 para não estourar a conta antes do usuário digitar
                    qtd = st.number_input(f"Contratos P{i+1}", min_value=0, step=1, key=f"qtd_{i}")
                parciais_inputs.append((pts, qtd))
                contratos_alocados += qtd
            
            # --- CORREÇÃO DO ERRO DE VALIDAÇÃO ---
            restante = lote_total - contratos_alocados
            if restante > 0:
                st.warning(f"⚠️ Restam {restante} contratos para fechar a posição.")
            elif restante < 0:
                st.error(f"❌ Erro: Você alocou {abs(restante)} contratos a mais do que a entrada!")

        notas = st.text_area("Notas do Trade (Psicológico, Por que entrou?)")
        submit = st.form_submit_button("💾 Salvar Trade")

        if submit:
            if contratos_alocados != lote_total:
                st.error(f"Impossível salvar: A soma das parciais ({contratos_alocados}) deve ser igual ao total ({lote_total}).")
            elif entrada == 0:
                st.error("Por favor, insira o preço de entrada.")
            else:
                # Cálculo financeiro baseado na regra NQ/MNQ
                lucro_total = sum([p[0] * MULTIPLIERS[ativo] * p[1] for p in parciais_inputs])
                pts_medios = sum([p[0] * p[1] for p in parciais_inputs]) / lote_total
                
                # Classificação automática por faixa de lote
                if lote_total <= 10: faixa = "Até 10"
                elif lote_total <= 20: faixa = "11 a 20"
                else: faixa = "Acima de 20"

                novo_trade = pd.DataFrame([{
                    'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao,
                    'Lote': lote_total, 'Faixa_Lote': faixa, 'Stop_Pts': stop_pts,
                    'Risco_Fin': risco_financeiro, 'Resultado': lucro_total,
                    'Pts_Medio': pts_medios, 'RR': lucro_total / risco_financeiro if risco_financeiro > 0 else 0,
                    'Notas': notas
                }])
                
                df = pd.concat([df, novo_trade], ignore_index=True)
                save_data(df)
                st.success("✅ Trade registrado com sucesso!")
                st.rerun()

with tab2:
    if not df.empty:
        st.subheader("🔍 Filtros de Performance")
        f1, f2 = st.columns(2)
        with f1:
            f_faixa = st.multiselect("Faixa de Contratos", df['Faixa_Lote'].unique(), default=df['Faixa_Lote'].unique())
        with f2:
            f_contexto = st.multiselect("Contexto", df['Contexto'].unique(), default=df['Contexto'].unique())
        
        dff = df[(df['Faixa_Lote'].isin(f_faixa)) & (df['Contexto'].isin(f_contexto))]

        # KPIs Estilo Dashboard Profissional
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("P&L Total", f"${dff['Resultado'].sum():.2f}")
        k2.metric("Win Rate", f"{(len(dff[dff['Resultado'] > 0]) / len(dff) * 100):.1f}%")
        k3.metric("Média Pontos", f"{dff['Pts_Medio'].mean():.2f}")
        k4.metric("R:R Médio", f"1:{dff['RR'].mean():.2f}")

        # Gráficos
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            fig_res = px.bar(dff, x='Contexto', y='Resultado', color='Faixa_Lote', title="Resultado por Contexto e Lote", template="plotly_dark")
            st.plotly_chart(fig_res, use_container_width=True)
        with c_g2:
            fig_risk = px.scatter(dff, x='Stop_Pts', y='Resultado', size='Lote', color='Contexto', title="Risco vs Retorno", template="plotly_dark")
            st.plotly_chart(fig_risk, use_container_width=True)
    else:
        st.info("Registre trades para ver a análise.")

with tab3:
    st.dataframe(df, use_container_width=True)
