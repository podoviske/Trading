import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from supabase import create_client
import time

# Importa o Cérebro para cálculos de Fase
from modules.logic import ApexEngine

# --- 1. CONEXÃO E FUNÇÕES DE CARGA ---
def get_supabase():
    try:
        if "supabase" in st.session_state: return st.session_state["supabase"]
        else:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key)
    except: return None

def load_grupos(user):
    try:
        sb = get_supabase()
        res = sb.table("grupos_config").select("*").eq("usuario", user).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def load_contas(user):
    try:
        sb = get_supabase()
        res = sb.table("contas_config").select("*").eq("usuario", user).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            # Garante tipos numéricos e valores padrão
            if 'pico_previo' not in df.columns: df['pico_previo'] = df['saldo_inicial']
            if 'fase_entrada' not in df.columns: df['fase_entrada'] = 'Fase 1'
            if 'status_conta' not in df.columns: df['status_conta'] = 'Ativa'
            df['saldo_inicial'] = df['saldo_inicial'].astype(float)
            df['pico_previo'] = df['pico_previo'].astype(float)
        return df
    except: return pd.DataFrame()

def load_trades(user):
    try:
        sb = get_supabase()
        res = sb.table("trades").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df = df[df['usuario'] == user]
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['created_at'] = pd.to_datetime(df['created_at'])
            if 'grupo_vinculo' not in df.columns: df['grupo_vinculo'] = 'Geral'
            df['resultado'] = pd.to_numeric(df['resultado'], errors='coerce').fillna(0.0)
        return df
    except: return pd.DataFrame()

# --- 2. COMPONENTE VISUAL (CARD PEQUENO) ---
# Ajustado CSS para não vazar texto
def card_monitor(label, value, sub_text, color="white", border_color="#333"):
    st.markdown(
        f"""
        <div style="
            background-color: #161616; 
            padding: 10px; 
            border-radius: 8px; 
            border: 1px solid {border_color}; 
            text-align: center; 
            margin-bottom: 10px;
            height: 90px; /* Altura fixa controlada */
            display: flex; flex-direction: column; justify-content: center; overflow: hidden;
        ">
            <div style="color: #888; font-size: 10px; text-transform: uppercase; margin-bottom: 2px;">
                {label}
            </div>
            <h3 style="color: {color}; margin: 0; font-size: 18px; font-weight: 700; white-space: nowrap;">{value}</h3>
            <div style="color: #666; font-size: 10px; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {sub_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- 3. TELA PRINCIPAL ---
def show(user, role):
    st.title("💼 Gestão de Portfólio")
    
    if role not in ['master', 'admin']:
        st.error("Acesso restrito a administradores.")
        return

    sb = get_supabase()
    
    # Abas
    t1, t2, t3, t4 = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📋 Visão Geral", "🚀 Monitor de Performance"])
    
    # --- ABA 1: GRUPOS ---
    with t1:
        st.subheader("Nova Estrutura de Contas")
        with st.form("form_grupo"):
            novo_grupo = st.text_input("Nome do Grupo (Ex: Apex 5 Contas - A)")
            if st.form_submit_button("Criar Grupo"):
                if novo_grupo:
                    sb.table("grupos_config").insert({"usuario": user, "nome": novo_grupo}).execute()
                    st.toast("Grupo criado!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else: st.warning("Digite um nome.")
        
        st.divider()
        st.write("Grupos Existentes:")
        df_g = load_grupos(user)
        if not df_g.empty:
            for idx, row in df_g.iterrows():
                c1, c2 = st.columns([4, 1])
                c1.info(f"📂 {row['nome']}")
                if c2.button("Excluir", key=f"del_g_{row['id']}"):
                    sb.table("grupos_config").delete().eq("id", row['id']).execute()
                    st.rerun()
        else:
            st.info("Nenhum grupo criado.")

    # --- ABA 2: CADASTRAR CONTA ---
    with t2:
        st.subheader("Vincular Conta")
        df_g = load_grupos(user)
        
        if not df_g.empty:
            with st.form("form_conta"):
                col_a, col_b = st.columns(2)
                g_sel = col_a.selectbox("Grupo", sorted(df_g['nome'].unique()))
                c_id = col_b.text_input("Identificador (Ex: PA-001)")
                
                s_ini = col_a.number_input("Saldo ATUAL na Corretora ($)", value=150000.0, step=100.0)
                p_pre = col_b.number_input("Pico Máximo (HWM)", value=150000.0, step=100.0)
                fase_ini = col_a.selectbox("Fase Inicial (Referência)", ["Fase 1", "Fase 2", "Fase 3", "Fase 4"])
                
                if st.form_submit_button("Cadastrar Conta"):
                    if c_id:
                        try:
                            sb.table("contas_config").insert({
                                "usuario": user, "grupo_nome": g_sel, "conta_identificador": c_id,
                                "saldo_inicial": s_ini, "pico_previo": p_pre,
                                "fase_entrada": fase_ini, "status_conta": "Ativa"
                            }).execute()
                            st.toast("Conta cadastrada!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
        else:
            st.warning("Crie um grupo primeiro na aba anterior.")

    # --- ABA 3: VISÃO GERAL (COM EDIÇÃO DE FASE) ---
    with t3:
        st.subheader("📋 Gestão e Edição")
        df_c = load_contas(user)
        df_g_list = load_grupos(user)
        df_t = load_trades(user)
        
        lista_grupos_existentes = sorted(df_g_list['nome'].unique()) if not df_g_list.empty else []

        if not df_c.empty:
            grupos_unicos = sorted(df_c['grupo_nome'].unique())
            for grp in grupos_unicos:
                with st.expander(f"📂 {grp}", expanded=True):
                    # Calcula lucro do grupo (Copy Trading: trades do grupo impactam todas as contas dele)
                    trades_grp = df_t[df_t['grupo_vinculo'] == grp] if not df_t.empty else pd.DataFrame()
                    lucro_grupo = trades_grp['resultado'].sum() if not trades_grp.empty else 0.0
                    
                    contas_g = df_c[df_c['grupo_nome'] == grp]
                    
                    for _, row in contas_g.iterrows():
                        st_icon = "🟢" if row['status_conta'] == "Ativa" else "🔴"
                        saldo_atual = float(row['saldo_inicial']) + lucro_grupo
                        delta = saldo_atual - float(row['saldo_inicial'])
                        cor_delta = "#00FF88" if delta >= 0 else "#FF4B4B"
                        
                        # Layout da Linha da Conta
                        c_info, c_edit, c_del = st.columns([3, 0.5, 0.5])
                        
                        c_info.markdown(f"""
                            <div style='background-color: #222; padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 3px solid {"#00FF88" if row['status_conta']=="Ativa" else "#FF4B4B"}'>
                                <div style="display:flex; justify-content:space-between;">
                                    <span>💳 <b>{row['conta_identificador']}</b> <small>({row['fase_entrada']})</small></span>
                                    <span>{st_icon} {row['status_conta']}</span>
                                </div>
                                <div style='font-size: 1.1em; margin-top: 5px;'>💰 Saldo: <b>${saldo_atual:,.2f}</b> (<span style='color:{cor_delta}'>${delta:+,.2f}</span>)</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # -- POPOVER DE EDIÇÃO --
                        with c_edit.popover("⚙️"):
                            st.write(f"Editar **{row['conta_identificador']}**")
                            
                            # 1. Grupo
                            idx_grp = lista_grupos_existentes.index(row['grupo_nome']) if row['grupo_nome'] in lista_grupos_existentes else 0
                            novo_grp = st.selectbox("Grupo", lista_grupos_existentes, index=idx_grp, key=f"mv_g_{row['id']}")
                            
                            # 2. Status
                            status_ops = ["Ativa", "Pausada", "Quebrada"]
                            idx_st = status_ops.index(row['status_conta']) if row['status_conta'] in status_ops else 0
                            novo_status = st.selectbox("Status", status_ops, index=idx_st, key=f"mv_s_{row['id']}")
                            
                            # 3. Fase (NOVO)
                            fase_ops = ["Fase 1", "Fase 2", "Fase 3", "Fase 4"]
                            idx_fase = fase_ops.index(row.get('fase_entrada', 'Fase 1')) if row.get('fase_entrada', 'Fase 1') in fase_ops else 0
                            nova_fase = st.selectbox("Fase", fase_ops, index=idx_fase, key=f"mv_f_{row['id']}")

                            # 4. Saldo
                            novo_saldo_ini = st.number_input("Saldo Inicial", value=float(row['saldo_inicial']), key=f"mv_si_{row['id']}")
                            
                            if st.button("💾 Salvar", key=f"btn_sv_{row['id']}"):
                                sb.table("contas_config").update({
                                    "grupo_nome": novo_grp, 
                                    "status_conta": novo_status, 
                                    "saldo_inicial": novo_saldo_ini,
                                    "fase_entrada": nova_fase
                                }).eq("id", row['id']).execute()
                                st.toast("Atualizado!")
                                time.sleep(1)
                                st.rerun()

                        # Botão Deletar
                        if c_del.button("🗑️", key=f"del_acc_{row['id']}"):
                            sb.table("contas_config").delete().eq("id", row['id']).execute()
                            st.rerun()
        else:
            st.info("Nenhuma conta configurada.")

    # --- ABA 4: MONITOR DE PERFORMANCE (CORRIGIDO) ---
    with t4:
        st.subheader("🚀 Monitor de Grupo (Apex Engine)")
        df_c = load_contas(user)
        df_t = load_trades(user)

        if not df_c.empty:
            grps = sorted(df_c['grupo_nome'].unique())
            
            # Seletores
            col_sel, col_detalhe = st.columns([1.5, 1.5])
            sel_g = col_sel.selectbox("Selecionar Grupo", grps)
            
            # Filtra contas do grupo
            contas_g = df_c[df_c['grupo_nome'] == sel_g]
            
            # Dropdown de Detalhe (Escolher Conta Específica)
            lista_contas_detalhe = sorted(contas_g['conta_identificador'].unique())
            sel_conta_id = col_detalhe.selectbox("Visualizar Detalhe", lista_contas_detalhe)
            
            st.markdown("---")
            
            # Filtra trades do grupo
            trades_g = df_t[df_t['grupo_vinculo'] == sel_g] if not df_t.empty else pd.DataFrame()
            
            # [CORREÇÃO CRÍTICA] Seleciona a conta ESPECÍFICA escolhida no dropdown
            conta_alvo = contas_g[contas_g['conta_identificador'] == sel_conta_id]
            
            if not conta_alvo.empty:
                conta_ref = conta_alvo.iloc[0] # Agora pega a conta certa!
                
                # --- CÁLCULO APEX ENGINE ---
                # Estima saldo atual = Saldo Inicial da Conta + Lucro do Grupo
                lucro_acumulado = trades_g['resultado'].sum() if not trades_g.empty else 0.0
                saldo_atual_est = float(conta_ref['saldo_inicial']) + lucro_acumulado
                hwm_prev = float(conta_ref.get('pico_previo', conta_ref['saldo_inicial']))
                
                saude = ApexEngine.calculate_health(saldo_atual_est, hwm_prev)
                
                # --- EXIBIÇÃO ---
                # Cards Superiores
                k1, k2, k3, k4 = st.columns(4)
                
                with k1:
                    card_monitor("SALDO ATUAL", f"${saude['saldo']:,.2f}", f"Lucro: ${lucro_acumulado:+,.2f}", "#00FF88" if lucro_acumulado >=0 else "#FF4B4B")
                with k2:
                    card_monitor("HWM (TOPO)", f"${saude['hwm']:,.2f}", f"{saude['status_trailing']}", "#FFFF00")
                with k3:
                    cor_buf = "#00FF88" if saude['buffer'] > 2000 else "#FF4B4B"
                    card_monitor("BUFFER (OXIGÊNIO)", f"${saude['buffer']:,.2f}", f"Stop: ${saude['stop_atual']:,.0f}", cor_buf)
                with k4:
                    falta = saude.get('falta_para_trava', 0)
                    lbl_fase = saude['fase']
                    sub_fase = f"Falta: ${falta:,.0f}" if falta > 0 else "Stop Travado 🔒"
                    card_monitor("STATUS / FASE", lbl_fase, sub_fase, "#00FF88", "#00FF88")

                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- ÁREA DE GRÁFICO E PROGRESSO ---
                cg, cp = st.columns([2.5, 1])

                with cg:
                    st.markdown(f"**🌊 Curva de Patrimônio: {sel_conta_id}**")
                    if not trades_g.empty:
                        # Prepara dados para o gráfico
                        df_plot = trades_g.sort_values('created_at').copy()
                        df_plot['saldo_acc'] = df_plot['resultado'].cumsum() + float(conta_ref['saldo_inicial'])
                        df_plot['seq'] = range(1, len(df_plot)+1)
                        
                        # Recalcula Trailing para histórico (Aprox)
                        # Nota: O ideal seria salvar o stop histórico, mas aqui simulamos
                        def calc_trail_hist(saldo):
                            # Simulação simples da regra
                            lock = 155100.0
                            if saldo >= lock: return 150100.0
                            return max(150000.0 - 5000, saldo - 5000)
                        
                        # Plota
                        fig = px.line(df_plot, x='seq', y='saldo_acc', template="plotly_dark")
                        fig.update_traces(line_color='#00FF88', fill='tozeroy', fillcolor='rgba(0, 255, 136, 0.1)')
                        
                        # Linhas de referência
                        fig.add_hline(y=float(conta_ref['saldo_inicial']), line_dash="dash", line_color="gray", annotation_text="Inicial")
                        if saude['stop_atual'] > 0:
                            fig.add_hline(y=saude['stop_atual'], line_color="#FF4B4B", annotation_text="Stop Atual")
                            
                        fig.update_layout(xaxis_title="Trades", yaxis_title="Saldo ($)", height=350)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Registre trades para ver a curva.")

                with cp:
                    st.markdown("**🎯 Progresso da Fase**")
                    
                    # Definição de Meta Visual baseada na Fase
                    meta_visual = 155100.0 # Meta da Fase 2 (Trava)
                    if saude['saldo'] >= 155100.0: meta_visual = 161000.0 # Meta da Fase 3
                    
                    progresso = 0.0
                    total_range = meta_visual - 150000.0
                    ganho = saude['saldo'] - 150000.0
                    
                    if total_range > 0:
                        progresso = min(1.0, max(0.0, ganho / total_range))
                    
                    st.progress(progresso)
                    st.caption(f"Meta Próxima: ${meta_visual:,.0f}")
                    
                    if progresso >= 1.0:
                        st.success("META ATINGIDA! 🚀")
                    else:
                        falta_meta = meta_visual - saude['saldo']
                        st.write(f"Faltam: **${falta_meta:,.2f}**")

            else:
                st.warning("Conta não encontrada.")
        else:
            st.info("Crie um Grupo e Contas primeiro.")
