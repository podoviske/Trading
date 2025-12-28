import streamlit as st
import pandas as pd
import plotly.express as px
import math
from datetime import datetime
from modules import database, logic, ui

def show(user, role):
    st.title(f"📊 Central de Controle ({user})")
    
    # Carregar dados via Módulo
    df_raw = database.load_trades(user)
    df_contas = database.load_contas(user)
    
    # Inicializa variáveis
    win_rate_dec = 0.0; loss_rate_dec = 0.0; payoff = 0.0; total_trades = 0
    r_min = 0.0; r_max = 0.0
    
    if not df_raw.empty:
        # Filtros
        with st.expander("🔍 Filtros Avançados", expanded=True):
            if role in ['master', 'admin']:
                c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1.8])
                grps = ["Todos"] + sorted(list(df_raw['grupo_vinculo'].unique()))
                sel_grupo = c3.selectbox("Grupo", grps)
            else:
                c1, c2, c4 = st.columns([1, 1, 2]); sel_grupo = "Todos"
            
            d_ini = c1.date_input("Início", df_raw['data'].min())
            d_fim = c2.date_input("Fim", df_raw['data'].max())
            ctxs = list(df_raw['contexto'].unique())
            sel_ctx = c4.multiselect("Contexto", ctxs, default=ctxs)
            
        # Aplica Filtros
        mask = (df_raw['data'] >= d_ini) & (df_raw['data'] <= d_fim) & (df_raw['contexto'].isin(sel_ctx))
        if sel_grupo != "Todos": mask = mask & (df_raw['grupo_vinculo'] == sel_grupo)
        df = df_raw[mask].copy()
        
        if not df.empty:
            # --- MOTOR APEX (Iteração) ---
            buffer_total = 0.0; saldo_agora = 0.0; n_contas = 0
            
            if not df_contas.empty:
                alvo = df_contas if sel_grupo == "Todos" else df_contas[df_contas['grupo_nome'] == sel_grupo]
                for _, row in alvo.iterrows():
                    if row.get('status_conta') == 'Ativa':
                        trades_conta = df_raw[df_raw['grupo_vinculo'] == row['grupo_nome']]
                        # Chama Módulo Lógico
                        saude = logic.calcular_saude_apex(row['saldo_inicial'], row['pico_previo'], trades_conta)
                        buffer_total += saude['buffer']
                        saldo_agora += saude['saldo_atual']
                        n_contas += 1
            
            # --- CÁLCULOS ESTATÍSTICOS ---
            wins = df[df['resultado'] > 0]; losses = df[df['resultado'] < 0]
            total_trades = len(df)
            net = df['resultado'].sum()
            
            if total_trades > 0:
                win_rate_dec = len(wins) / total_trades
                avg_win = wins['resultado'].mean() if not wins.empty else 0
                avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0
                payoff = avg_win / avg_loss if avg_loss > 0 else 0
                expectancy = (win_rate_dec * avg_win) - ((1-win_rate_dec) * avg_loss)
            else: avg_win=0; avg_loss=0; expectancy=0
            
            # --- CARDS VISUAIS (Módulo UI) ---
            st.markdown("##### 🏁 Desempenho Geral")
            c1, c2, c3, c4 = st.columns(4)
            ui.card_metric("RESULTADO", f"${net:,.2f}", color="#00FF88" if net>=0 else "#FF4B4B")
            ui.card_metric("FATOR DE LUCRO", f"{abs(wins['resultado'].sum()/losses['resultado'].sum()):.2f}" if not losses.empty else "∞", color="#B20000")
            ui.card_metric("WIN RATE", f"{win_rate_dec*100:.1f}%")
            ui.card_metric("EXPECTATIVA", f"${expectancy:.2f}", color="#00FF88" if expectancy>0 else "#FF4B4B")
            
            # --- RISCO E SOBREVIVÊNCIA ---
            st.markdown("---")
            st.subheader("🛡️ Sobrevivência & Risco")
            k1, k2, k3, k4 = st.columns(4)
            
            # Chama Módulo Lógico para Ruína
            prob_ruina, status_ruina = logic.calcular_risco_ruina(win_rate_dec, avg_win, avg_loss, buffer_total, expectancy)
            
            # Lote Sugerido (Simplificado)
            risco_base = 300.0 * (n_contas if n_contas > 0 else 1) # $300 por conta
            vidas = buffer_total / risco_base if risco_base > 0 else 0
            
            ui.card_metric("BUFFER REAL", f"${buffer_total:,.0f}", f"{n_contas} Contas", "#00FF88")
            ui.card_metric("VIDAS (U)", f"{vidas:.1f}", f"Risco ${risco_base:.0f}", "#FF4B4B" if vidas<6 else "#00FF88")
            
            # Card Customizado para Ruína
            with k4:
                cor_r = "#FF4B4B" if prob_ruina > 5 else "#00FF88"
                st.markdown(f"""<div style="background:#161616; border:2px solid {cor_r}; border-radius:12px; padding:10px; text-align:center;">
                <div style="color:#888; font-size:11px;">RUÍNA</div>
                <div style="color:{cor_r}; font-size:24px; font-weight:900;">{prob_ruina:.1f}%</div>
                <div style="color:#AAA; font-size:10px;">{status_ruina}</div></div>""", unsafe_allow_html=True)

            if prob_ruina > 10 and total_trades > 5:
                st.markdown('<div class="piscante-erro">💀 RISCO CRÍTICO DE RUÍNA 💀</div>', unsafe_allow_html=True)

            # --- GRÁFICOS ---
            st.markdown("---")
            df['equity'] = df['resultado'].cumsum()
            fig = px.area(df, x='data', y='equity', title="Curva de Patrimônio", template="plotly_dark")
            fig.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
            st.plotly_chart(fig, use_container_width=True)
            
        else: st.warning("Sem dados no período.")
    else: st.info("Nenhum trade registrado.")
