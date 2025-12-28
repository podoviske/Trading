import streamlit as st
import pandas as pd
import plotly.express as px
import math
from datetime import datetime
from modules import database, logic, ui

def show(user, role):
    st.title(f"📊 Central de Controle ({user})")
    
    # Carregar dados
    df_raw = database.load_trades(user)
    df_contas = database.load_contas(user)
    
    # Inicializa variáveis
    win_rate_dec = 0.0; loss_rate_dec = 0.0; payoff = 0.0; total_trades = 0
    r_min_show = 0.0; r_max_show = 0.0; kelly_half = 0.0
    lote_medio_real = 0.0; pts_loss_medio_real = 0.0; avg_pts_gain = 0.0
    
    if not df_raw.empty:
        # --- FILTROS ---
        with st.expander("🔍 Filtros Avançados", expanded=True):
            if role in ['master', 'admin']:
                c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1.8])
                grps = ["Todos"] + sorted(list(df_raw['grupo_vinculo'].unique()))
                sel_grupo = c3.selectbox("Grupo", grps)
            else:
                c1, c2, c4 = st.columns([1, 1, 2]); sel_grupo = "Todos"
            
            d_min = df_raw['data'].min(); d_max = df_raw['data'].max()
            d_ini = c1.date_input("Início", d_min)
            d_fim = c2.date_input("Fim", d_max)
            ctxs = list(df_raw['contexto'].unique())
            sel_ctx = c4.multiselect("Contexto", ctxs, default=ctxs)
            
        # Aplica Filtros
        mask = (df_raw['data'] >= d_ini) & (df_raw['data'] <= d_fim) & (df_raw['contexto'].isin(sel_ctx))
        if sel_grupo != "Todos": mask = mask & (df_raw['grupo_vinculo'] == sel_grupo)
        df = df_raw[mask].copy()
        
        if not df.empty:
            # --- MOTOR APEX ---
            buffer_total = 0.0; soma_saldo_agora = 0.0; n_contas = 0
            
            if not df_contas.empty:
                alvo = df_contas if sel_grupo == "Todos" else df_contas[df_contas['grupo_nome'] == sel_grupo]
                for _, row in alvo.iterrows():
                    if row.get('status_conta') == 'Ativa':
                        trades_conta = df_raw[df_raw['grupo_vinculo'] == row['grupo_nome']]
                        saude = logic.calcular_saude_apex(row['saldo_inicial'], row['pico_previo'], trades_conta)
                        buffer_total += saude['buffer']
                        soma_saldo_agora += saude['saldo_atual']
                        n_contas += 1
            
            stop_atual_val = soma_saldo_agora - buffer_total if n_contas > 0 else 0.0

            # --- CÁLCULOS ESTATÍSTICOS ---
            wins = df[df['resultado'] > 0]; losses = df[df['resultado'] < 0]
            total_trades = len(df)
            net = df['resultado'].sum()
            
            gross_profit = wins['resultado'].sum(); gross_loss = abs(losses['resultado'].sum())
            pf_str = f"{gross_profit/gross_loss:.2f}" if gross_loss > 0 else "∞"
            
            if total_trades > 0:
                win_rate_dec = len(wins) / total_trades
                loss_rate_dec = len(losses) / total_trades
                avg_win = wins['resultado'].mean() if not wins.empty else 0
                avg_loss = abs(losses['resultado'].mean()) if not losses.empty else 0
                payoff = avg_win / avg_loss if avg_loss > 0 else 1.0
                expectancy = (win_rate_dec * avg_win) - (loss_rate_dec * avg_loss)
                
                lote_medio_real = df['lote'].mean()
                pts_loss_medio_real = abs(losses['pts_medio'].mean()) if not losses.empty else 15.0
                ativo_ref = df['ativo'].iloc[-1]
                avg_pts_gain = wins['pts_medio'].mean() if not wins.empty else 0
            else: 
                avg_win=0; avg_loss=0; expectancy=0; ativo_ref="MNQ"
            
            # ==========================================================
            # CORREÇÃO AQUI: USANDO 'WITH' PARA COLOCAR DENTRO DA COLUNA
            # ==========================================================
            
            # --- LINHA 1: GERAL ---
            st.markdown("##### 🏁 Desempenho Geral")
            c1, c2, c3, c4 = st.columns(4)
            with c1: ui.card_metric("RESULTADO", f"${net:,.2f}", color="#00FF88" if net>=0 else "#FF4B4B")
            with c2: ui.card_metric("FATOR DE LUCRO", pf_str, "Ideal > 1.5", "#B20000")
            with c3: ui.card_metric("WIN RATE", f"{win_rate_dec*100:.1f}%", f"{len(wins)}W / {len(losses)}L")
            with c4: ui.card_metric("EXPECTATIVA", f"${expectancy:.2f}", "Por Trade", "#00FF88" if expectancy>0 else "#FF4B4B")
            
            # --- LINHA 2: MÉDIAS ---
            st.markdown("##### 💲 Médias Financeiras")
            c5, c6, c7, c8 = st.columns(4)
            with c5: ui.card_metric("MÉDIA GAIN", f"${avg_win:,.2f}", "", "#00FF88")
            with c6: ui.card_metric("MÉDIA LOSS", f"-${avg_loss:,.2f}", "", "#FF4B4B")
            with c7: ui.card_metric("PAYOFF", f"1 : {payoff:.2f}", "Risco/Retorno")
            
            df_sorted = df.sort_values('created_at')
            df_sorted['equity'] = df_sorted['resultado'].cumsum()
            max_dd = (df_sorted['equity'] - df_sorted['equity'].cummax()).min()
            with c8: ui.card_metric("DRAWDOWN MAX", f"${max_dd:,.2f}", "Pior Queda", "#FF4B4B")

            # --- LINHA 3: TÉCNICA ---
            st.markdown("##### 🎯 Performance Técnica")
            c9, c10, c11, c12 = st.columns(4)
            with c9: ui.card_metric("PTS MÉDIOS (GAIN)", f"{avg_pts_gain:.2f} pts", "", "#00FF88")
            with c10: ui.card_metric("STOP MÉDIO", f"{pts_loss_medio_real:.2f} pts", "Base Risco", "#FF4B4B")
            with c11: ui.card_metric("LOTE MÉDIO", f"{lote_medio_real:.1f}", "Contratos")
            with c12: ui.card_metric("TOTAL TRADES", str(total_trades), "Executados")

            # --- LINHA 4: RISCO ---
            st.markdown("---")
            st.subheader("🛡️ Sobrevivência & Risco")
            
            prob_ruina, status_ruina = logic.calcular_risco_ruina(win_rate_dec, avg_win, avg_loss, buffer_total, expectancy)
            
            if payoff > 0 and expectancy > 0:
                kelly_full = win_rate_dec - ((1 - win_rate_dec) / payoff)
                kelly_half = max(0.0, kelly_full / 2)
            
            multipliers = {"NQ": 20, "MNQ": 2, "ES": 50, "MES": 5}
            risco_por_lote = pts_loss_medio_real * multipliers.get(ativo_ref, 2)
            fator_rep = n_contas if n_contas > 0 else 1
            risco_base = risco_por_lote * lote_medio_real * fator_rep
            if risco_base == 0: risco_base = 300.0 * fator_rep
            
            vidas = buffer_total / risco_base if risco_base > 0 else 0
            z_score = (win_rate_dec * payoff) - loss_rate_dec

            k1, k2, k3, k4 = st.columns(4)
            with k1: ui.card_metric("Z-SCORE", f"{z_score:.2f}", "Força do Edge", "#00FF88" if z_score > 0 else "#FF4B4B")
            with k2: ui.card_metric("BUFFER REAL", f"${buffer_total:,.0f}", f"{n_contas} Contas", "#00FF88")
            with k3: ui.card_metric("VIDAS (U)", f"{vidas:.1f}", f"Base ${risco_base:.0f}", "#FF4B4B" if vidas<6 else "#00FF88")
            
            with k4:
                cor_r = "#FF4B4B" if prob_ruina > 5 else "#00FF88"
                st.markdown(f"""<div style="background:#161616; border:2px solid {cor_r}; border-radius:12px; padding:10px; text-align:center; height:100%; display:flex; flex-direction:column; justify-content:center;">
                <div style="color:#888; font-size:10px;">RUÍNA</div>
                <div style="color:{cor_r}; font-size:22px; font-weight:900;">{prob_ruina:.1f}%</div>
                <div style="color:#AAA; font-size:10px;">{status_ruina}</div></div>""", unsafe_allow_html=True)

            if prob_ruina > 10 and total_trades > 5:
                st.markdown('<div class="piscante-erro">💀 RISCO CRÍTICO DE RUÍNA 💀</div>', unsafe_allow_html=True)

            # --- LINHA 5: KELLY ---
            st.markdown("---")
            st.subheader("🧠 Inteligência de Lote")
            
            lote_sug = 0; status_k = "Sem Dados"
            if kelly_half > 0 and buffer_total > 0 and risco_por_lote > 0:
                risco_teto = buffer_total * kelly_half
                risco_vidas = buffer_total / 20.0
                risco_final = min(risco_teto, risco_vidas)
                lote_sug = math.floor(risco_final / risco_por_lote)
                if lote_sug > 40: lote_sug = 40
                r_min_show = lote_sug * risco_por_lote
                status_k = "Zona de Aceleração" if lote_sug > 0 else "Sem Gordura"
                cor_k = "#00FF88" if lote_sug > 0 else "#FF4B4B"
            else:
                cor_k = "#888"

            ka, kb, kc, kd = st.columns(4)
            with ka: ui.card_metric("BUFFER DISP.", f"${buffer_total:,.0f}", f"Stop Global: ${stop_atual_val:,.0f}", "#00FF88")
            with kb: ui.card_metric("HALF-KELLY", f"{kelly_half*100:.1f}%", "Teto Matemático", "#888")
            with kc: ui.card_metric("RISCO FIN.", f"${r_min_show:,.0f}", "Sugerido", cor_k)
            with kd:
                st.markdown(f"""<div style="background:#161616; border:2px solid {cor_k}; border-radius:12px; padding:10px; text-align:center; height:100%; display:flex; flex-direction:column; justify-content:center;">
                <div style="color:#888; font-size:10px;">LOTE SUGERIDO</div>
                <div style="color:{cor_k}; font-size:22px; font-weight:900;">{lote_sug} ctrs</div>
                <div style="color:#AAA; font-size:10px;">{status_k}</div></div>""", unsafe_allow_html=True)

            # --- GRÁFICOS ---
            st.markdown("---")
            g1, g2 = st.columns([2, 1])
            
            with g1:
                saldo_plot = soma_saldo_agora - net if soma_saldo_agora > 0 else 0
                df_sorted['equity_real'] = df_sorted['resultado'].cumsum() + saldo_plot
                fig = px.area(df_sorted, x='data', y='equity_real', title="Curva de Patrimônio", template="plotly_dark")
                fig.update_traces(line_color='#B20000', fillcolor='rgba(178, 0, 0, 0.2)')
                st.plotly_chart(fig, use_container_width=True)
            
            with g2:
                ctx_perf = df.groupby('contexto')['resultado'].sum().reset_index()
                fig_bar = px.bar(ctx_perf, x='contexto', y='resultado', title="Por Contexto", template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
                st.plotly_chart(fig_bar, use_container_width=True)

            # --- GRÁFICO SEMANAL ---
            st.markdown("### 📅 Performance por Dia")
            df['data_dt'] = pd.to_datetime(df['data'])
            df['dia_num'] = df['data_dt'].dt.dayofweek
            mapa_dias = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sab', 6: 'Dom'}
            df['dia_nome'] = df['dia_num'].map(mapa_dias)
            
            df_day = df.groupby('dia_nome')['resultado'].sum()
            ordem = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex']
            df_final = df_day.reindex(ordem, fill_value=0.0).reset_index()
            
            fig_day = px.bar(df_final, x='dia_nome', y='resultado', template="plotly_dark", color='resultado', color_continuous_scale=["#FF4B4B", "#00FF88"])
            st.plotly_chart(fig_day, use_container_width=True)
            
        else: st.warning("Sem dados no período.")
    else: st.info("Nenhum trade registrado.")
