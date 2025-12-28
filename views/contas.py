import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from supabase import create_client
import time
import math

# Importando a inteligência isolada
from modules.logic import ApexEngine

# --- 1. CONEXÃO E FUNÇÕES DE DADOS ---
def get_supabase():
    try:
        if "supabase" in st.session_state: return st.session_state["supabase"]
        else:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
    except: return None

def load_grupos(user):
    sb = get_supabase()
    res = sb.table("grupos_config").select("*").eq("usuario", user).execute()
    return pd.DataFrame(res.data)

def load_contas(user):
    sb = get_supabase()
    res = sb.table("contas_config").select("*").eq("usuario", user).execute()
    return pd.DataFrame(res.data)

def load_trades(user):
    sb = get_supabase()
    res = sb.table("trades").select("*").eq("usuario", user).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['created_at'] = pd.to_datetime(df['created_at'])
    return df

# --- 2. COMPONENTE VISUAL (CARD) ---
def card(label, value, sub_text, color="white", border_color="#333333"):
    st.markdown(
        f"""
        <div style="
            background-color: #161616; 
            padding: 15px; 
            border-radius: 8px; 
            border: 1px solid {border_color}; 
            text-align: center; 
            margin-bottom: 10px;
            height: 100px; 
            display: flex; flex-direction: column; justify-content: center;
        ">
            <div style="color: #888; font-size: 10px; text-transform: uppercase; margin-bottom: 4px; display: flex; justify-content: center; align-items: center; gap: 5px;">
                {label}
            </div>
            <h2 style="color: {color}; margin: 0; font-size: 20px; font-weight: 600;">{value}</h2>
            <p style="color: #666; font-size: 10px; margin-top: 4px;">{sub_text}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- 3. TELA PRINCIPAL ---
def show(user, role):
    st.title("💼 Gestão de Portfólio")
    
    if role not in ['master', 'admin']:
        st.error("🔒 Acesso restrito a gestores.")
        return

    sb = get_supabase()
    
    t1, t2, t3, t4 = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📋 Visão Geral", "🚀 Monitor Performance"])

    # --- ABA 1: CRIAR GRUPO ---
    with t1:
        st.subheader("Nova Estrutura")
        with st.form("form_grupo", clear_on_submit=True):
            novo_grupo = st.text_input("Nome do Grupo (Ex: Apex 20 Contas)")
            if st.form_submit_button("Criar Grupo"):
                if novo_grupo:
                    sb.table("grupos_config").insert({"usuario": user, "nome": novo_grupo}).execute()
                    st.toast("Grupo criado!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Digite um nome.")
        
        st.divider()
        st.caption("Grupos Existentes")
        df_g = load_grupos(user)
        if not df_g.empty:
            for _, row in df_g.iterrows():
                c1, c2 = st.columns([4, 1])
                c1.info(f"📂 {row['nome']}")
                if c2.button("🗑️", key=f"del_g_{row['id']}"):
                    sb.table("grupos_config").delete().eq("id", row['id']).execute()
                    st.rerun()

    # --- ABA 2: CADASTRAR CONTA ---
    with t2:
        st.subheader("Vincular Nova Conta")
        df_g = load_grupos(user)
        
        if not df_g.empty:
            grupos_opcoes = sorted(df_g['nome'].unique())
            
            with st.form("form_conta", clear_on_submit=True):
                c_a, c_b = st.columns(2)
                g_sel = c_a.selectbox("Vincular ao Grupo", grupos_opcoes)
                c_id = c_b.text_input("Identificador (Ex: PA-001)")
                
                s_ini = c_a.number_input("Saldo Inicial ($)", value=150000.0, step=100.0)
                p_pre = c_b.number_input("Pico Prévio / HWM ($)", value=150000.0, step=100.0)
                
                fase_ini = st.selectbox("Fase Inicial", ["Fase 1", "Fase 2", "Fase 3", "Fase 4"])
                
                if st.form_submit_button("💾 Salvar Conta"):
                    if c_id:
                        sb.table("contas_config").insert({
                            "usuario": user,
                            "grupo_nome": g_sel,
                            "conta_identificador": c_id,
                            "saldo_inicial": s_ini,
                            "pico_previo": p_pre,
                            "fase_entrada": fase_ini,
                            "status_conta": "Ativa"
                        }).execute()
                        st.success(f"Conta {c_id} criada com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Preencha o identificador.")
        else:
            st.warning("⚠️ Crie um GRUPO na primeira aba antes de cadastrar contas.")

    # --- ABA 3: VISÃO GERAL (Gerenciamento) ---
    with t3:
        st.subheader("📋 Gestão e Mobilidade")
        
        df_c = load_contas(user)
        df_g = load_grupos(user)
        df_t = load_trades(user)
        
        lista_grupos = sorted(df_g['nome'].unique()) if not df_g.empty else []
        
        if not df_c.empty:
            grupos_unicos = sorted(df_c['grupo_nome'].unique())
            
            for grp in grupos_unicos:
                with st.expander(f"📂 {grp}", expanded=True):
                    contas_deste_grupo = df_c[df_c['grupo_nome'] == grp]
                    trades_grp = df_t[df_t['grupo_vinculo'] == grp] if not df_t.empty else pd.DataFrame()
                    lucro_total_grp = trades_grp['resultado'].sum() if not trades_grp.empty else 0.0
                    qtd_contas = len(contas_deste_grupo)
                    lucro_por_conta = lucro_total_grp / qtd_contas if qtd_contas > 0 else 0
                    
                    for _, conta in contas_deste_grupo.iterrows():
                        status_icon = "🟢" if conta['status_conta'] == "Ativa" else "🔴"
                        cor_border = "#00FF88" if conta['status_conta'] == "Ativa" else "#FF4B4B"
                        saldo_estimado = float(conta['saldo_inicial']) + lucro_por_conta
                        delta = saldo_estimado - float(conta['saldo_inicial'])
                        cor_delta = "#00FF88" if delta >= 0 else "#FF4B4B"
                        
                        col_info, col_edit, col_del = st.columns([3, 0.5, 0.5])
                        
                        col_info.markdown(f"""
                            <div style='background-color: #222; padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 3px solid {cor_border}'>
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <span style="font-size:16px;">💳 <b>{conta['conta_identificador']}</b></span>
                                    <span style="font-size:12px; background:#111; padding:2px 6px; border-radius:4px;">{status_icon} {conta['status_conta']}</span>
                                </div>
                                <div style="font-size: 13px; color:#aaa; margin-top:4px;">
                                    Saldo Est: <span style="color:white; font-weight:bold;">${saldo_estimado:,.2f}</span> 
                                    (<span style="color:{cor_delta}">${delta:+,.2f}</span>)
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        with col_edit.popover("⚙️"):
                            st.markdown(f"**Editar {conta['conta_identificador']}**")
                            idx_grp = lista_grupos.index(conta['grupo_nome']) if conta['grupo_nome'] in lista_grupos else 0
                            novo_grp = st.selectbox("Mover Grupo", lista_grupos, index=idx_grp, key=f"g_{conta['id']}")
                            status_ops = ["Ativa", "Pausada", "Quebrada"]
                            idx_st = status_ops.index(conta['status_conta']) if conta['status_conta'] in status_ops else 0
                            novo_st = st.selectbox("Status", status_ops, index=idx_st, key=f"s_{conta['id']}")
                            novo_saldo = st.number_input("Corrigir Inicial", value=float(conta['saldo_inicial']), key=f"si_{conta['id']}")
                            
                            if st.button("Salvar Alterações", key=f"btn_{conta['id']}"):
                                sb.table("contas_config").update({
                                    "grupo_nome": novo_grp,
                                    "status_conta": novo_st,
                                    "saldo_inicial": novo_saldo
                                }).eq("id", conta['id']).execute()
                                st.rerun()
                        
                        if col_del.button("🗑️", key=f"del_{conta['id']}"):
                            sb.table("contas_config").delete().eq("id", conta['id']).execute()
                            st.rerun()
        else:
            st.info("Nenhuma conta cadastrada.")

    # --- ABA 4: MONITOR DE PERFORMANCE (Engine Integrada + Gráfico Apex) ---
    with t4:
        st.subheader("🚀 Monitor de Grupo (Apex Engine)")
        
        df_c = load_contas(user)
        df_t = load_trades(user)
        
        if not df_c.empty:
            grps = sorted(df_c['grupo_nome'].unique())
            
            # --- SELETORES HIERÁRQUICOS ---
            c_sel_grp, c_sel_acc = st.columns(2)
            
            sel_g = c_sel_grp.selectbox("1. Selecionar Grupo", grps)
            
            # Filtra contas e trades do grupo
            contas_g = df_c[df_c['grupo_nome'] == sel_g]
            trades_g = df_t[df_t['grupo_vinculo'] == sel_g] if not df_t.empty else pd.DataFrame()
            
            if not contas_g.empty:
                # Opções: Média ou Conta Específica
                opcoes_acc = ["Média do Grupo"] + sorted(list(contas_g['conta_identificador'].unique()))
                sel_acc = c_sel_acc.selectbox("2. Visualizar Detalhe", opcoes_acc)
                
                # --- LÓGICA DE DADOS (INDIVIDUAL vs GRUPO) ---
                if sel_acc == "Média do Grupo":
                    # Usa a primeira conta apenas como referência de Saldo Inicial Base (150k)
                    # Mas o saldo real é a média
                    conta_base_ref = contas_g.iloc[0]
                    saldo_inicial_calc = float(conta_base_ref['saldo_inicial']) # Assume 150k padrão
                    hwm_calc = float(conta_base_ref.get('pico_previo', saldo_inicial_calc)) # HWM aproximado
                    
                    lucro_total = trades_g['resultado'].sum() if not trades_g.empty else 0.0
                    lucro_aplicado = lucro_total / len(contas_g) # Rateio
                    
                    titulo_vis = f"Média ({len(contas_g)} contas)"
                else:
                    # Pega dados REAIS da conta selecionada
                    conta_alvo = contas_g[contas_g['conta_identificador'] == sel_acc].iloc[0]
                    saldo_inicial_calc = float(conta_alvo['saldo_inicial'])
                    hwm_calc = float(conta_alvo.get('pico_previo', saldo_inicial_calc))
                    
                    # Assume Copy Trading: A conta recebe a média do resultado do grupo
                    # Se você tiver trades com 'conta_id' no futuro, mude aqui para filtrar trades_g
                    lucro_total = trades_g['resultado'].sum() if not trades_g.empty else 0.0
                    lucro_aplicado = lucro_total / len(contas_g)
                    
                    titulo_vis = f"Conta {sel_acc}"

                saldo_atual_calc = saldo_inicial_calc + lucro_aplicado
                
                # --- CHAMA O MOTOR APEX ---
                saude = ApexEngine.calculate_health(saldo_atual_calc, hwm_calc)
                
                # --- CARDS DO TOPO ---
                st.caption(f"Visualizando: **{titulo_vis}**")
                k1, k2, k3, k4 = st.columns(4)
                with k1: card("Saldo Atual", f"${saude['saldo']:,.2f}", f"Lucro: ${saude['saldo'] - saldo_inicial_calc:+,.2f}", "#00FF88")
                with k2: card("HWM (Topo)", f"${saude['hwm']:,.2f}", saude['status_trailing'], "white")
                with k3:
                    cor_buf = "#00FF88" if saude['buffer'] > 2000 else "#FF4B4B"
                    card("Buffer (Oxigênio)", f"${saude['buffer']:,.2f}", f"Stop: ${saude['stop_atual']:,.0f}", cor_buf)
                with k4: card("Status / Fase", saude['fase'], f"Falta: ${saude['falta_para_trava']:,.0f}", "#00FF88")
                
                # --- GRÁFICO (LINHAS DINÂMICAS) ---
                c_graph, c_prog = st.columns([2.5, 1])
                
                with c_graph:
                    st.markdown("##### 🌊 Curva de Patrimônio vs Trailing Stop")
                    if not trades_g.empty:
                        trades_g['data_hora'] = pd.to_datetime(trades_g['created_at'])
                        trades_plot = trades_g.sort_values('data_hora').copy()
                        trades_plot['seq'] = range(1, len(trades_plot) + 1)
                        
                        # Reconstrói a curva baseada no Saldo Inicial da conta selecionada
                        trades_plot['saldo_curve'] = saldo_inicial_calc + (trades_plot['resultado'].cumsum() / len(contas_g))
                        trades_plot['hwm_hist'] = trades_plot['saldo_curve'].cummax()
                        
                        def get_stop_historico(row):
                            if row['hwm_hist'] >= 155100.0: return 150100.0
                            else: return row['hwm_hist'] - 5000.0

                        trades_plot['trailing_hist'] = trades_plot.apply(get_stop_historico, axis=1)
                        
                        fig = px.line(trades_plot, x='seq', y='saldo_curve', template="plotly_dark")
                        fig.update_traces(line_color='#2E93fA', name="Saldo", line=dict(width=3))
                        fig.add_scatter(x=trades_plot['seq'], y=trades_plot['trailing_hist'], mode='lines', line=dict(color='#FF4B4B', width=2), name='Trailing Stop')
                        
                        # --- LINHAS DE REFERÊNCIA (CINZA E VERDE DINÂMICA) ---
                        # Linha de Trava do Stop (Cinza - Neutro)
                        fig.add_hline(y=150100, line_dash="dot", line_color="#666666", annotation_text="Lock Level (Stop Travado)")
                        
                        # Linha de Meta (Verde - Dinâmica pela Fase)
                        # Se estiver na Fase 2 (<155k), meta é 155.100. Se passar, meta vira 161k.
                        meta_alvo_grafico = 155100.0 if saude['saldo'] < 155100 else 161000.0
                        label_meta = "Meta: Trava" if saude['saldo'] < 155100 else "Meta: Fase 3"
                        
                        fig.add_hline(y=meta_alvo_grafico, line_dash="dash", line_color="#00FF88", annotation_text=label_meta)
                        
                        # Zoom Inteligente
                        min_y = min(trades_plot['trailing_hist'].min(), trades_plot['saldo_curve'].min()) - 500
                        max_y = max(trades_plot['saldo_curve'].max(), meta_alvo_grafico) + 500
                        
                        fig.update_layout(
                            yaxis_range=[min_y, max_y], 
                            xaxis_title="Sequência de Trades",
                            yaxis_title="Capital ($)",
                            margin=dict(l=0, r=0, t=10, b=0),
                            height=350,
                            legend=dict(orientation="h", y=1.1)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else: st.info("Registre trades para ver a curva.")

                # --- PROGRESSO E META (CÁLCULO OTIMISTA) ---
                with c_prog:
                    st.markdown("##### 🎯 Progresso da Fase")
                    
                    # Define meta total baseada na fase atual para a barra de progresso
                    if saude['saldo'] < 155100:
                        meta_total_fase = 5100.0 # De 150k a 155.1k
                        lucro_na_fase = max(0.0, saude['saldo'] - 150000)
                    else:
                        meta_total_fase = 6000.0 # De 155k a 161k (aprox)
                        lucro_na_fase = max(0.0, saude['saldo'] - 155100)

                    progresso = max(0.0, min(1.0, lucro_na_fase / meta_total_fase))
                    st.progress(progresso)
                    st.caption(f"{progresso*100:.1f}% Concluído")
                    
                    falta_dinheiro = saude['falta_para_trava'] if saude['saldo'] < 155100 else (161000 - saude['saldo'])
                    label_falta = "Falta p/ Trava" if saude['saldo'] < 155100 else "Falta p/ Saque"
                    
                    if not trades_g.empty:
                        gains = trades_g[trades_g['resultado'] > 0]
                        if not gains.empty:
                            media_gain = gains['resultado'].mean()
                            label_base = f"Média Gain: ${media_gain:,.2f}"
                        else:
                            media_gain = 0
                            label_base = "Sem Gains ainda"
                    else:
                        media_gain = 0
                        label_base = "Sem dados"

                    st.markdown("---")
                    
                    if falta_dinheiro > 0 and media_gain > 0:
                        trades_restantes = math.ceil(falta_dinheiro / media_gain)
                        st.markdown(f"""
                            <div style="background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 10px; text-align: center;">
                                <div style="color: #888; font-size: 12px; margin-bottom: 5px;">ESTIMATIVA OTIMISTA (Só Gains)</div>
                                <div style="font-size: 24px; font-weight: bold; color: #2E93fA;">~{trades_restantes} Trades</div>
                                <div style="color: #666; font-size: 11px; margin-top: 5px;">{label_falta}: ${falta_dinheiro:,.0f}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    elif falta_dinheiro <= 0 and saude['saldo'] >= 155100:
                        st.success("🎉 STOP TRAVADO! Rumo aos 161k.")
                    else:
                        st.warning("Aguardando dados...")

            else: st.warning("Grupo vazio ou sem contas.")
        else: st.info("Cadastre contas para monitorar.")
