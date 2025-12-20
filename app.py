import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Trading Dashboard Pro", layout="wide", page_icon="📈")

CSV_FILE = 'trades_nq_mnq_v3.csv'
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

# --- ESTADO DAS PARCIAIS ---
if 'n_parciais' not in st.session_state:
    st.session_state.n_parciais = 1

def adicionar_parcial():
    if st.session_state.n_parciais < 6:
        st.session_state.n_parciais += 1

def limpar_parciais():
    st.session_state.n_parciais = 1

# --- MENU LATERAL (SIDEBAR) ---
st.sidebar.title("💎 ProTrader Menu")
menu = st.sidebar.radio(
    "Gerenciamento",
    ["🚀 Registrar Trade", "📈 Dashboard Avançado", "📋 Histórico"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.info("Configurado para: **NQ / MNQ**")

# --- LÓGICA DAS PÁGINAS ---

if menu == "🚀 Registrar Trade":
    # Cabeçalho da página com botões no topo direito
    col_tit, col_btns = st.columns([2, 1])
    with col_tit:
        st.title("Registrar Operação")
    with col_btns:
        st.write("") # Espaçamento
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
            st.metric("Risco Calculado", f"${risco_financeiro:.2f}")

        with c3:
            st.write("**Saídas / Parciais**")
            parciais_inputs = []
            contratos_alocados = 0
            
            for i in range(st.session_state.n_parciais):
                cp1, cp2 = st.columns([1, 1])
                with cp1:
                    pts = st.number_input(f"Pts Parcial {i+1}", min_value=0.0, step=0.25, key=f"pts_{i}")
                with cp2:
                    qtd = st.number_input(f"Contratos P{i+1}", min_value=0, step=1, key=f"qtd_{i}")
                parciais_inputs.append((pts, qtd))
                contratos_alocados += qtd
            
            # Validação dinâmica de contratos
            restante = lote_total - contratos_alocados
            if restante > 0:
                st.warning(f"⚠️ Restam {restante} contratos para fechar.")
            elif restante < 0:
                st.error(f"❌ Erro: Alocou {abs(restante)} contratos a mais!")

        notas = st.text_area("Notas do Trade")
        submit = st.form_submit_button("💾 Salvar Trade")

        if submit:
            if contratos_alocados != lote_total:
                st.error(f"Erro: A soma das parciais ({contratos_alocados}) deve ser igual ao total ({lote_total}).")
            elif entrada == 0:
                st.error("Insira o preço de entrada.")
            else:
                lucro_total = sum([p[0] * MULTIPLIERS[ativo] * p[1] for p in parciais_inputs])
                pts_medios = sum([p[0] * p[1] for p in parciais_inputs]) / lote_total
                
                # Faixas de Lote
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
                st.success("✅ Trade salvo!")
                st.rerun()

elif menu == "📈 Dashboard Avançado":
    st.title("Analytics de Performance")
    if not df.empty:
        # Filtros no topo do dashboard
        st.write("### 🔍 Filtros")
        f1, f2, f3 = st.columns(3)
        with f1:
            f_faixa = st.multiselect("Faixa de Contratos", df['Faixa_Lote'].unique(), default=df['Faixa_Lote'].unique())
        with f2:
            f_contexto = st.multiselect("Contexto", df['Contexto'].unique(), default=df['Contexto'].unique())
        with f3:
            f_ativo = st.multiselect("Ativo", df['Ativo'].unique(), default=df['Ativo'].unique())
        
        dff = df[(df['Faixa_Lote'].isin(f_faixa)) & (df['Contexto'].isin(f_contexto)) & (df['Ativo'].isin(f_ativo))]

        # KPIs principais
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("P&L Total", f"${dff['Resultado'].sum():.2f}")
        k2.metric("Taxa de Acerto", f"{(len(dff[dff['Resultado'] > 0]) / len(dff) * 100):.1f}%")
        k3.metric("Média de Pontos", f"{dff['Pts_Medio'].mean():.2f}")
        k4.metric("Risk Reward Médio", f"1:{dff['RR'].mean():.2f}")

        st.markdown("---")
        
        # Gráficos de barra e dispersão
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            fig_res = px.bar(dff, x='Contexto', y='Resultado', color='Faixa_Lote', 
                             title="Lucro Acumulado por Contexto", template="plotly_dark", barmode='group')
            st.plotly_chart(fig_res, use_container_width=True)
        with c_g2:
            fig_risk = px.box(dff, x='Faixa_Lote', y='Risco_Fin', color='Contexto',
                              title="Distribuição de Risco Financeiro por Faixa", template="plotly_dark")
            st.plotly_chart(fig_risk, use_container_width=True)

        st.write("### 📉 Curva de Capital")
        dff = dff.sort_values('Data')
        dff['Acumulado'] = dff['Resultado'].cumsum()
        fig_evol = px.line(dff, x='Data', y='Acumulado', markers=True, template="plotly_dark")
        st.plotly_chart(fig_evol, use_container_width=True)
    else:
        st.info("Aguardando dados para gerar o Dashboard.")

elif menu == "📋 Histórico":
    st.title("Histórico de Operações")
    if not df.empty:
        st.dataframe(df.sort_values('Data', ascending=False), use_container_width=True)
        if st.button("🗑️ Limpar Banco de Dados"):
            if os.path.exists(CSV_FILE):
                os.remove(CSV_FILE)
                st.rerun()
    else:
        st.write("Nenhum trade registrado.")
