import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Trading Dashboard NQ/MNQ", layout="wide", page_icon="📈")

CSV_FILE = 'trades_nq_mnq.csv'

# Multiplicadores NQ/MNQ
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

# --- LÓGICA DE PARCIAIS DINÂMICAS ---
if 'n_parciais' not in st.session_state:
    st.session_state.n_parciais = 1

def adicionar_parcial():
    if st.session_state.n_parciais < 5: # Limite de 5 parciais
        st.session_state.n_parciais += 1

def limpar_parciais():
    st.session_state.n_parciais = 1

st.title("📊 Master Analytics - NQ & MNQ")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🚀 Registrar Trade", "📈 Dashboard Avançado", "📋 Histórico"])

with tab1:
    with st.form("trade_form"):
        c1, c2, c3 = st.columns([1, 1, 2])
        
        with c1:
            data = st.date_input("Data", datetime.now())
            ativo = st.selectbox("Ativo", ["MNQ", "NQ"])
            contexto = st.selectbox("Contexto", ["Contexto A", "Contexto B", "Contexto C"])
            direcao = st.radio("Direção", ["Compra", "Venda"], horizontal=True)
            entrada = st.number_input("Preço de Entrada", min_value=0.0, format="%.2f")

        with c2:
            lote_total = st.number_input("Contratos Totais", min_value=1, step=1)
            stop_pts = st.number_input("Risco em Pontos (Stop)", min_value=0.0, format="%.2f")
            risco_financeiro = stop_pts * MULTIPLIERS[ativo] * lote_total
            st.info(f"Risco Calculado: ${risco_financeiro:.2f}")

        with c3:
            st.write("**Saídas / Parciais**")
            parciais_data = []
            contratos_alocados = 0
            
            for i in range(st.session_state.n_parciais):
                col_pts, col_qtd = st.columns(2)
                with col_pts:
                    pts = st.number_input(f"Pts Parcial {i+1}", min_value=0.0, key=f"pts_{i}", help="Pontos a favor da entrada")
                with col_qtd:
                    qtd = st.number_input(f"Contratos P{i+1}", min_value=1, key=f"qtd_{i}")
                parciais_data.append((pts, qtd))
                contratos_alocados += qtd
            
            restante = lote_total - contratos_alocados
            if restante > 0:
                st.warning(f"Restam {restante} contratos sem saída definida.")
            elif restante < 0:
                st.error(f"Erro: Você alocou {abs(restante)} contratos a mais do que a entrada!")

        notas = st.text_area("Notas do Trade")
        
        # Botões do formulário
        col_btn1, col_btn2 = st.columns(2)
        submit = st.form_submit_button("💾 Salvar Trade")
    
    st.button("➕ Adicionar Parcial", on_click=adicionar_parcial)
    st.button("🧹 Resetar Parciais", on_click=limpar_parciais)

    if submit:
        if contratos_alocados != lote_total:
            st.error("A soma dos contratos das parciais deve ser igual ao Lote Total!")
        else:
            # Cálculo do Resultado Final
            # Resultado = Soma de (Pontos de cada parcial * multiplicador * qtd da parcial)
            lucro_total = 0
            pontos_ponderados = 0
            for pts, qtd in parciais_data:
                lucro_total += (pts * MULTIPLIERS[ativo] * qtd)
                pontos_ponderados += (pts * qtd)
            
            media_pontos_saida = pontos_ponderados / lote_total
            
            # Definir faixa de contratos
            if lote_total <= 10: faixa = "Até 10"
            elif lote_total <= 20: faixa = "11 a 20"
            else: faixa = "Acima de 20"

            novo_trade = pd.DataFrame([{
                'Data': data, 'Ativo': ativo, 'Contexto': contexto, 'Direcao': direcao,
                'Lote': lote_total, 'Faixa_Lote': faixa, 'Stop_Pts': stop_pts,
                'Risco_Fin': risco_financeiro, 'Resultado': lucro_total,
                'Pts_Medio_Saida': media_pontos_saida, 'RR': lucro_total / risco_financeiro if risco_financeiro > 0 else 0,
                'Notas': notas
            }])
            
            df = pd.concat([df, novo_trade], ignore_index=True)
            save_data(df)
            st.success("Trade registrado com sucesso!")
            st.rerun()

with tab2:
    if not df.empty:
        # --- FILTROS ---
        st.subheader("🔍 Filtros de Análise")
        f_faixa = st.multiselect("Filtrar por Faixa de Contratos", df['Faixa_Lote'].unique(), default=df['Faixa_Lote'].unique())
        f_contexto = st.multiselect("Filtrar por Contexto", df['Contexto'].unique(), default=df['Contexto'].unique())
        
        dff = df[(df['Faixa_Lote'].isin(f_faixa)) & (df['Contexto'].isin(f_contexto))]

        # --- KPIs ---
        m1, m2, m3, m4 = st.columns(4)
        total_pnl = dff['Resultado'].sum()
        m1.metric("P&L Total", f"${total_pnl:.2f}")
        m2.metric("Risco Médio Fin.", f"${dff['Risco_Fin'].mean():.2f}")
        m3.metric("Média Pontos Saída", f"{dff['Pts_Medio_Saida'].mean():.2f} pts")
        m4.metric("Risco:Retorno Médio", f"1:{dff['RR'].mean():.2f}")

        st.markdown("---")

        # --- GRÁFICOS ---
        c_graf1, c_graf2 = st.columns(2)
        
        with c_graf1:
            st.write("**Performance por Faixa de Contratos**")
            fig_lote = px.bar(dff.groupby('Faixa_Lote')['Resultado'].sum().reset_index(), 
                              x='Faixa_Lote', y='Resultado', color='Faixa_Lote', template="plotly_dark")
            st.plotly_chart(fig_lote, use_container_width=True)

        with c_graf2:
            st.write("**Risco Médio por Contexto**")
            fig_ctx = px.box(dff, x='Contexto', y='Risco_Fin', color='Contexto', template="plotly_dark")
            st.plotly_chart(fig_ctx, use_container_width=True)

        st.write("**Curva de Capital (Patrimônio)**")
        dff['Acumulado'] = dff['Resultado'].cumsum()
        st.line_chart(dff['Acumulado'])
        
    else:
        st.info("Adicione trades para visualizar a análise.")

with tab3:
    st.dataframe(df, use_container_width=True)
    if st.button("Limpar Tudo"):
        if os.path.exists(CSV_FILE): os.remove(CSV_FILE); st.rerun()
