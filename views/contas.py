import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
import time
import math
import uuid

# Importa o Cérebro
from modules.logic import ApexEngine

# --- 1. CONEXÃO ---
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
            if 'conta_id' not in df.columns: df['conta_id'] = None
            df['resultado'] = pd.to_numeric(df['resultado'], errors='coerce').fillna(0.0)
        return df
    except: return pd.DataFrame()

def load_ajustes(user):
    """Carrega ajustes manuais (taxas, slippage, etc)"""
    try:
        sb = get_supabase()
        res = sb.table("ajustes_manuais").select("*").eq("usuario", user).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
            df['created_at'] = pd.to_datetime(df['created_at'])
        return df
    except: return pd.DataFrame()

def calcular_lucro_conta(conta_id, grupo_nome, df_trades, df_ajustes):
    """
    Calcula o lucro real de uma conta específica.
    
    Lógica:
    1. Trades INDIVIDUAIS (conta_id = esta conta) → soma 100%
    2. Trades REPLICADOS (conta_id = NULL, grupo = este grupo) → divide pelo número de contas do grupo
    3. Ajustes manuais desta conta → soma 100%
    """
    lucro_total = 0.0
    
    if not df_trades.empty:
        # Trades individuais desta conta
        trades_individuais = df_trades[df_trades['conta_id'] == conta_id]
        lucro_total += trades_individuais['resultado'].sum()
        
        # Trades replicados do grupo (conta_id é NULL)
        trades_replicados = df_trades[
            (df_trades['grupo_vinculo'] == grupo_nome) & 
            (df_trades['conta_id'].isna())
        ]
        if not trades_replicados.empty:
            lucro_total += trades_replicados['resultado'].sum()
    
    # Ajustes manuais desta conta
    if not df_ajustes.empty:
        ajustes_conta = df_ajustes[df_ajustes['conta_id'] == conta_id]
        lucro_total += ajustes_conta['valor'].sum()
    
    return lucro_total

# --- 2. COMPONENTE VISUAL ---
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
            height: 90px;
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
    
    t1, t2, t3, t4, t5 = st.tabs(["📂 Criar Grupo", "💳 Cadastrar Conta", "📋 Visão Geral", "📉 Ajustes Manuais", "🚀 Monitor de Performance"])
    
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
            st.warning("Crie um grupo primeiro.")

    # --- ABA 3: VISÃO GERAL ---
    with t3:
        st.subheader("📋 Gestão e Edição")
        df_c = load_contas(user)
        df_g_list = load_grupos(user)
        df_t = load_trades(user)
        df_aj = load_ajustes(user)
        
        lista_grupos_existentes = sorted(df_g_list['nome'].unique()) if not df_g_list.empty else []

        if not df_c.empty:
            grupos_unicos = sorted(df_c['grupo_nome'].unique())
            for grp in grupos_unicos:
                with st.expander(f"📂 {grp}", expanded=True):
                    contas_g = df_c[df_c['grupo_nome'] == grp]
                    
                    for _, row in contas_g.iterrows():
                        # Calcula lucro REAL desta conta (individual + replicado + ajustes)
                        lucro_conta = calcular_lucro_conta(row['id'], grp, df_t, df_aj)
                        
                        st_icon = "🟢" if row['status_conta'] == "Ativa" else "🔴"
                        saldo_atual = float(row['saldo_inicial']) + lucro_conta
                        delta = lucro_conta
                        cor_delta = "#00FF88" if delta >= 0 else "#FF4B4B"
                        
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
                        
                        with c_edit.popover("⚙️"):
                            st.write(f"Editar **{row['conta_identificador']}**")
                            idx_grp = lista_grupos_existentes.index(row['grupo_nome']) if row['grupo_nome'] in lista_grupos_existentes else 0
                            novo_grp = st.selectbox("Grupo", lista_grupos_existentes, index=idx_grp, key=f"mv_g_{row['id']}")
                            
                            status_ops = ["Ativa", "Pausada", "Quebrada"]
                            idx_st = status_ops.index(row['status_conta']) if row['status_conta'] in status_ops else 0
                            novo_status = st.selectbox("Status", status_ops, index=idx_st, key=f"mv_s_{row['id']}")
                            
                            fase_ops = ["Fase 1", "Fase 2", "Fase 3", "Fase 4"]
                            idx_fase = fase_ops.index(row.get('fase_entrada', 'Fase 1')) if row.get('fase_entrada', 'Fase 1') in fase_ops else 0
                            nova_fase = st.selectbox("Fase", fase_ops, index=idx_fase, key=f"mv_f_{row['id']}")

                            novo_saldo_ini = st.number_input("Saldo Inicial", value=float(row['saldo_inicial']), key=f"mv_si_{row['id']}")
                            novo_pico = st.number_input("Pico (HWM)", value=float(row['pico_previo']), key=f"mv_pico_{row['id']}")
                            
                            if st.button("💾 Salvar", key=f"btn_sv_{row['id']}"):
                                sb.table("contas_config").update({
                                    "grupo_nome": novo_grp, 
                                    "status_conta": novo_status, 
                                    "saldo_inicial": novo_saldo_ini,
                                    "pico_previo": novo_pico,
                                    "fase_entrada": nova_fase
                                }).eq("id", row['id']).execute()
                                st.toast("Atualizado!")
                                time.sleep(1)
                                st.rerun()

                        if c_del.button("🗑️", key=f"del_acc_{row['id']}"):
                            sb.table("contas_config").delete().eq("id", row['id']).execute()
                            st.rerun()
        else:
            st.info("Nenhuma conta configurada.")

    # --- ABA 4: AJUSTES MANUAIS (NOVA!) ---
    with t4:
        st.subheader("📉 Ajustes Manuais (Taxas, Slippage, Correções)")
        st.caption("Use para registrar taxas, slippage, correções de saldo ou qualquer ajuste que não seja um trade.")
        
        df_c = load_contas(user)
        df_aj = load_ajustes(user)
        
        if not df_c.empty:
            col_form, col_hist = st.columns([1, 1])
            
            with col_form:
                st.markdown("### ➕ Novo Ajuste")
                
                # Lista de contas para seleção
                df_c['display'] = df_c['conta_identificador'] + " (" + df_c['grupo_nome'] + ")"
                lista_contas = df_c.sort_values('display')['display'].tolist()
                
                with st.form("form_ajuste"):
                    conta_display = st.selectbox("💳 Conta", lista_contas)
                    
                    tipo_ajuste = st.selectbox("Tipo", [
                        "Taxa (Comissão)", 
                        "Slippage", 
                        "Correção de Saldo",
                        "Saque",
                        "Depósito",
                        "Outro"
                    ])
                    
                    valor_ajuste = st.number_input(
                        "Valor ($)", 
                        value=0.0, 
                        step=0.01,
                        help="Use valor NEGATIVO para taxas/slippage/saques. Positivo para depósitos/correções."
                    )
                    
                    descricao = st.text_input("Descrição (opcional)", placeholder="Ex: Slippage trade #42")
                    
                    if st.form_submit_button("💾 Registrar Ajuste", use_container_width=True):
                        if valor_ajuste != 0:
                            # Recupera o ID da conta
                            conta_row = df_c[df_c['display'] == conta_display].iloc[0]
                            
                            sb.table("ajustes_manuais").insert({
                                "id": str(uuid.uuid4()),
                                "usuario": user,
                                "conta_id": conta_row['id'],
                                "tipo": tipo_ajuste,
                                "valor": valor_ajuste,
                                "descricao": descricao
                            }).execute()
                            
                            st.toast(f"Ajuste registrado: ${valor_ajuste:+,.2f}", icon="✅")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("Valor não pode ser zero.")
            
            with col_hist:
                st.markdown("### 📜 Histórico de Ajustes")
                
                if not df_aj.empty:
                    # Junta com nome da conta
                    df_aj_display = df_aj.merge(
                        df_c[['id', 'conta_identificador']], 
                        left_on='conta_id', 
                        right_on='id', 
                        how='left',
                        suffixes=('', '_conta')
                    )
                    
                    df_aj_display = df_aj_display.sort_values('created_at', ascending=False)
                    
                    for _, aj in df_aj_display.head(20).iterrows():
                        cor_val = "#00FF88" if aj['valor'] >= 0 else "#FF4B4B"
                        st.markdown(f"""
                            <div style='background:#1a1a1a; padding:8px; border-radius:5px; margin-bottom:5px; border-left:3px solid {cor_val}'>
                                <div style='display:flex; justify-content:space-between;'>
                                    <span><b>{aj['conta_identificador']}</b> • {aj['tipo']}</span>
                                    <span style='color:{cor_val}; font-weight:bold;'>${aj['valor']:+,.2f}</span>
                                </div>
                                <div style='font-size:11px; color:#666;'>{aj.get('descricao', '') or '-'}</div>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Nenhum ajuste registrado.")
        else:
            st.warning("Cadastre uma conta primeiro.")

    # --- ABA 5: MONITOR DE PERFORMANCE ---
    with t5:
        st.subheader("🚀 Monitor de Grupo (Apex Engine)")
        df_c = load_contas(user)
        df_t = load_trades(user)
        df_aj = load_ajustes(user)

        if not df_c.empty:
            grps = sorted(df_c['grupo_nome'].unique())
            col_sel, col_detalhe = st.columns([1.5, 1.5])
            
            sel_g = col_sel.selectbox("Selecionar Grupo", grps)
            
            contas_g = df_c[df_c['grupo_nome'] == sel_g]
            
            lista_contas_detalhe = ["📊 VISÃO GERAL (Grupo)"] + sorted(contas_g['conta_identificador'].unique())
            sel_conta_id = col_detalhe.selectbox("Visualizar Detalhe", lista_contas_detalhe)
            
            st.markdown("---")
            
            # Filtra trades do grupo
            trades_g = df_t[df_t['grupo_vinculo'] == sel_g] if not df_t.empty else pd.DataFrame()
            
            # --- DADOS ---
            saude_final = {}
            saldo_inicial_plot = 0.0
            titulo_grafico = ""
            n_contas_calc = 1
            
            if sel_conta_id == "📊 VISÃO GERAL (Grupo)":
                titulo_grafico = f"Curva Agregada: {sel_g}"
                
                total_saldo = 0.0
                total_hwm = 0.0
                total_stop = 0.0
                total_buffer = 0.0
                contas_ativas = 0
                
                for _, conta in contas_g.iterrows():
                    if conta['status_conta'] == 'Ativa':
                        # Calcula lucro REAL desta conta
                        lucro_conta = calcular_lucro_conta(conta['id'], sel_g, df_t, df_aj)
                        
                        saldo_atual_c = float(conta['saldo_inicial']) + lucro_conta
                        hwm_prev_c = float(conta.get('pico_previo', conta['saldo_inicial']))
                        
                        res = ApexEngine.calculate_health(saldo_atual_c, hwm_prev_c, conta.get('fase_entrada', 'Fase 1'))
                        
                        total_saldo += res['saldo']
                        total_hwm += res['hwm']
                        total_stop += res['stop_atual']
                        total_buffer += res['buffer']
                        saldo_inicial_plot += float(conta['saldo_inicial'])
                        contas_ativas += 1
                
                n_contas_calc = contas_ativas if contas_ativas > 0 else 1
                
                saude_final = {
                    'saldo': total_saldo,
                    'hwm': total_hwm,
                    'status_trailing': f"Agregado ({contas_ativas} contas)",
                    'buffer': total_buffer,
                    'stop_atual': total_stop,
                    'fase': "Visão Macro",
                    'falta_para_trava': 0.0,
                    'meta_proxima': 155100.0 * n_contas_calc,
                    'falta_para_meta': max(0, (155100.0 * n_contas_calc) - total_saldo)
                }
                
            else:
                titulo_grafico = f"Curva de Patrimônio: {sel_conta_id}"
                conta_alvo = contas_g[contas_g['conta_identificador'] == sel_conta_id]
                
                if not conta_alvo.empty:
                    conta_ref = conta_alvo.iloc[0]
                    
                    # Calcula lucro REAL desta conta
                    lucro_conta = calcular_lucro_conta(conta_ref['id'], sel_g, df_t, df_aj)
                    
                    saldo_atual_est = float(conta_ref['saldo_inicial']) + lucro_conta
                    hwm_prev = float(conta_ref.get('pico_previo', conta_ref['saldo_inicial']))
                    saldo_inicial_plot = float(conta_ref['saldo_inicial'])
                    
                    saude_final = ApexEngine.calculate_health(saldo_atual_est, hwm_prev, conta_ref.get('fase_entrada', 'Fase 1'))
                else:
                    st.warning("Conta não encontrada.")
                    st.stop()

            # --- CARDS ---
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                lucro_disp = saude_final['saldo'] - saldo_inicial_plot
                card_monitor("SALDO ATUAL", f"${saude_final['saldo']:,.2f}", f"Lucro: ${lucro_disp:+,.2f}", "#00FF88" if lucro_disp >=0 else "#FF4B4B")
            with k2:
                card_monitor("HWM (TOPO)", f"${saude_final['hwm']:,.2f}", f"{saude_final['status_trailing']}", "#FFFF00")
            with k3:
                cor_buf = "#00FF88" if saude_final['buffer'] > (2000 * n_contas_calc) else "#FF4B4B"
                card_monitor("BUFFER (OXIGÊNIO)", f"${saude_final['buffer']:,.2f}", f"Stop: ${saude_final['stop_atual']:,.0f}", cor_buf)
            with k4:
                falta = saude_final.get('falta_para_trava', 0)
                lbl_fase = saude_final.get('fase', 'Fase 1')
                sub_fase = f"Falta: ${falta:,.0f}" if falta > 0 else "Travado ✅"
                card_monitor("STATUS / FASE", lbl_fase, sub_fase, "#00FF88", "#00FF88")

            st.markdown("<br>", unsafe_allow_html=True)
            
            cg, cp = st.columns([2.5, 1])

            # --- GRÁFICO ---
            with cg:
                st.markdown(f"**🌊 {titulo_grafico}**")
                if not trades_g.empty:
                    df_plot = trades_g.sort_values('created_at').copy()
                    
                    df_plot['saldo_acc'] = df_plot['resultado'].cumsum() + saldo_inicial_plot
                    df_plot['seq'] = range(1, len(df_plot)+1)
                    
                    def calc_trail_hist(saldo_momento):
                        lock_val = 155100.0 * n_contas_calc
                        stop_locked = 150100.0 * n_contas_calc
                        dd_max = 5000.0 * n_contas_calc
                        start_bal = 150000.0 * n_contas_calc
                        
                        if saldo_momento >= lock_val: return stop_locked
                        return max(start_bal - dd_max, saldo_momento - dd_max)

                    df_plot['hwm_hist'] = df_plot['saldo_acc'].cummax()
                    df_plot['stop_hist'] = df_plot['hwm_hist'].apply(calc_trail_hist)
                    
                    meta_plot_val = saude_final.get('meta_proxima', 155100.0 * n_contas_calc)
                    if saude_final['saldo'] >= meta_plot_val:
                        meta_plot_val = 161000.0 * n_contas_calc
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=df_plot['seq'], y=df_plot['saldo_acc'],
                        mode='lines', name='Patrimônio',
                        line=dict(color='#2962FF', width=2),
                        fill='tozeroy', fillcolor='rgba(41, 98, 255, 0.1)'
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=df_plot['seq'], y=df_plot['stop_hist'],
                        mode='lines', name='Trailing Stop',
                        line=dict(color='#FF4B4B', width=2, dash='solid')
                    ))

                    fig.add_hline(y=saldo_inicial_plot, line_dash="dash", line_color="#444", annotation_text="Inicial")
                    fig.add_hline(y=meta_plot_val, line_dash="dash", line_color="#00FF88", annotation_text="Meta")
                    
                    y_values = pd.concat([df_plot['saldo_acc'], df_plot['stop_hist']])
                    min_y = y_values.min()
                    max_y = y_values.max()
                    min_y = min(min_y, saldo_inicial_plot)
                    max_y = max(max_y, meta_plot_val)
                    diff = max_y - min_y
                    padding = max(1500.0, diff * 0.15)
                    
                    fig.update_layout(
                        template="plotly_dark",
                        xaxis_title="Quantidade de Trades",
                        yaxis_title="Saldo ($)",
                        height=350,
                        margin=dict(l=10, r=10, t=30, b=10),
                        legend=dict(orientation="h", y=1.1),
                        yaxis=dict(range=[min_y - padding, max_y + padding])
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Registre trades para ver a curva.")

            with cp:
                st.markdown("**🎯 Progresso da Fase**")
                meta_visual = saude_final.get('meta_proxima', 155100.0 * n_contas_calc)
                base_visual = 150000.0 * n_contas_calc
                
                if saude_final['saldo'] >= meta_visual:
                    meta_visual = 161000.0 * n_contas_calc
                
                progresso = 0.0
                total_range = meta_visual - base_visual
                ganho = saude_final['saldo'] - base_visual
                
                if total_range > 0:
                    progresso = min(1.0, max(0.0, ganho / total_range))
                
                st.progress(progresso)
                st.caption(f"Meta Próxima: ${meta_visual:,.0f}")
                
                falta_meta = meta_visual - saude_final['saldo']
                
                if progresso >= 1.0:
                    st.success("META ATINGIDA! 🚀")
                else:
                    st.write(f"Faltam: **${falta_meta:,.2f}**")
                    
                # Estimativa de trades faltantes
                if not trades_g.empty and 'resultado' in trades_g.columns:
                    wins = trades_g[trades_g['resultado'] > 0]
                    avg_win = wins['resultado'].mean() if not wins.empty else 0.0
                    
                    if avg_win > 0 and falta_meta > 0:
                        trades_left = math.ceil(falta_meta / avg_win)
                        st.caption(f"🎯 Aprox. **{trades_left} trades** (média ${avg_win:,.0f})")
                    else:
                        st.caption("Faça gains para estimar trades.")
                else:
                    st.caption("Aguardando histórico de trades para estimativas.")

        else:
            st.info("Crie um Grupo e Contas primeiro.")
