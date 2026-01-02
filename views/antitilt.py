# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from supabase import create_client
import json
import time

# --- CONEXAO ---
def get_supabase():
    if "supabase" in st.session_state:
        return st.session_state["supabase"]
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ==========================================
# FUNCOES DE DADOS
# ==========================================

def get_config(user):
    sb = get_supabase()
    res = sb.table("antitilt_config").select("*").eq("usuario", user).execute()
    
    if res.data:
        return res.data[0]
    else:
        config = {
            "usuario": user,
            "max_stops_dia": 3,
            "max_stops_consecutivos": 2,
            "timer_apos_stop_segundos": 180,
            "bloqueio_minutos": 60,
            "score_minimo": 6.0,
            "checkin_obrigatorio": True,
            "protocolo_stop_ativo": True,
            "bloqueio_automatico": True,
            "journaling_obrigatorio": True
        }
        sb.table("antitilt_config").insert(config).execute()
        return config

def get_checkin_hoje(user):
    sb = get_supabase()
    hoje = date.today().isoformat()
    res = sb.table("checkin_diario").select("*").eq("usuario", user).eq("data", hoje).execute()
    return res.data[0] if res.data else None

def salvar_checkin(user, dados):
    sb = get_supabase()
    hoje = date.today().isoformat()
    
    score = (dados['sono'] + (11 - dados['ansiedade']) + dados['clareza']) / 3
    
    config = get_config(user)
    liberado = score >= config['score_minimo'] and not dados['quer_recuperar']
    
    checkin = {
        "usuario": user,
        "data": hoje,
        "sono": dados['sono'],
        "ansiedade": dados['ansiedade'],
        "clareza": dados['clareza'],
        "fez_respiracao": dados['fez_respiracao'],
        "leu_regras": dados['leu_regras'],
        "quer_recuperar": dados['quer_recuperar'],
        "score_geral": round(score, 1),
        "liberado_operar": liberado,
        "ignorou_recomendacao": False,
        "observacoes": dados.get('observacoes', '')
    }
    
    sb.table("checkin_diario").upsert(checkin).execute()
    return checkin

def get_stops_hoje(user):
    sb = get_supabase()
    hoje = date.today().isoformat()
    res = sb.table("stops_dia").select("*").eq("usuario", user).eq("data", hoje).execute()
    
    if res.data:
        return res.data[0]
    else:
        registro = {
            "usuario": user,
            "data": hoje,
            "stops_count": 0,
            "stops_consecutivos": 0
        }
        sb.table("stops_dia").insert(registro).execute()
        return registro

def registrar_stop(user):
    sb = get_supabase()
    hoje = date.today().isoformat()
    config = get_config(user)
    
    stops = get_stops_hoje(user)
    
    novo_count = stops['stops_count'] + 1
    novo_consecutivo = stops['stops_consecutivos'] + 1
    
    alerta_amarelo = novo_consecutivo >= config['max_stops_consecutivos']
    alerta_vermelho = novo_count >= config['max_stops_dia']
    
    bloqueado_ate = None
    if alerta_vermelho and config['bloqueio_automatico']:
        bloqueado_ate = (datetime.now() + timedelta(minutes=config['bloqueio_minutos'])).isoformat()
    
    update = {
        "stops_count": novo_count,
        "stops_consecutivos": novo_consecutivo,
        "alerta_amarelo_disparado": alerta_amarelo or stops.get('alerta_amarelo_disparado', False),
        "alerta_vermelho_disparado": alerta_vermelho or stops.get('alerta_vermelho_disparado', False),
        "bloqueado_ate": bloqueado_ate
    }
    
    sb.table("stops_dia").update(update).eq("usuario", user).eq("data", hoje).execute()
    
    return {
        "stops_count": novo_count,
        "stops_consecutivos": novo_consecutivo,
        "alerta_amarelo": alerta_amarelo,
        "alerta_vermelho": alerta_vermelho,
        "bloqueado_ate": bloqueado_ate
    }

def registrar_gain(user):
    sb = get_supabase()
    hoje = date.today().isoformat()
    
    sb.table("stops_dia").update({
        "stops_consecutivos": 0
    }).eq("usuario", user).eq("data", hoje).execute()

def get_journaling_hoje(user):
    sb = get_supabase()
    hoje = date.today().isoformat()
    res = sb.table("journaling").select("*").eq("usuario", user).eq("data", hoje).execute()
    return res.data[0] if res.data else None

def salvar_journaling(user, dados):
    sb = get_supabase()
    hoje = date.today().isoformat()
    
    journaling = {
        "usuario": user,
        "data": hoje,
        "seguiu_plano": dados['seguiu_plano'],
        "oq_aconteceu_antes": dados.get('oq_aconteceu_antes', ''),
        "gatilho_emocional": dados.get('gatilho_emocional', ''),
        "oq_fazer_diferente": dados.get('oq_fazer_diferente', ''),
        "oq_fez_certo": dados.get('oq_fez_certo', ''),
        "total_trades": dados.get('total_trades', 0),
        "total_stops": dados.get('total_stops', 0),
        "pnl_dia": dados.get('pnl_dia', 0),
        "seguiu_protocolo": dados.get('seguiu_protocolo', True)
    }
    
    sb.table("journaling").upsert(journaling).execute()
    return journaling

def get_historico_mental(user, dias=30):
    sb = get_supabase()
    data_inicio = (date.today() - timedelta(days=dias)).isoformat()
    
    checkins = sb.table("checkin_diario").select("*").eq("usuario", user).gte("data", data_inicio).execute()
    journals = sb.table("journaling").select("*").eq("usuario", user).gte("data", data_inicio).execute()
    
    return {
        "checkins": checkins.data or [],
        "journals": journals.data or []
    }

def usuario_pode_operar(user):
    config = get_config(user)
    
    if config['checkin_obrigatorio']:
        checkin = get_checkin_hoje(user)
        if not checkin:
            return {"pode": False, "motivo": "checkin_pendente"}
        if not checkin['liberado_operar'] and not checkin.get('ignorou_recomendacao'):
            return {"pode": False, "motivo": "score_baixo", "score": checkin['score_geral']}
    
    stops = get_stops_hoje(user)
    if stops.get('bloqueado_ate'):
        try:
            bloqueio = datetime.fromisoformat(stops['bloqueado_ate'].replace('Z', '+00:00'))
            if datetime.now(bloqueio.tzinfo) < bloqueio:
                return {"pode": False, "motivo": "bloqueado", "ate": stops['bloqueado_ate']}
        except:
            pass
    
    return {"pode": True}

def ignorar_recomendacao(user):
    sb = get_supabase()
    hoje = date.today().isoformat()
    sb.table("checkin_diario").update({
        "ignorou_recomendacao": True
    }).eq("usuario", user).eq("data", hoje).execute()

# ==========================================
# CSS
# ==========================================

def load_styles():
    st.markdown("""
        <style>
        .checkin-card {
            background: linear-gradient(135deg, #0d0d0d 0%, #1a1a1a 100%);
            border: 1px solid #222;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
        }
        
        .score-display {
            text-align: center;
            padding: 20px;
        }
        
        .score-number {
            font-size: 64px;
            font-weight: 800;
        }
        
        .score-liberado { color: #00FF88; }
        .score-alerta { color: #FFD700; }
        .score-bloqueado { color: #FF4444; }
        
        .alerta-box {
            background-color: #1a0a0a;
            border: 2px solid #FF4444;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
        }
        
        .alerta-amarelo {
            background-color: #1a1a0a;
            border: 2px solid #FFD700;
        }
        
        .timer-box {
            background-color: #111;
            border: 2px solid #B20000;
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            margin: 20px 0;
        }
        
        .timer-number {
            font-size: 48px;
            font-weight: 800;
            color: #FF4444;
            font-family: monospace;
        }
        
        .stat-card {
            background-color: #111;
            border: 1px solid #222;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 28px;
            font-weight: 700;
        }
        
        .stat-label {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
        }
        
        .protocolo-step {
            background-color: #0d0d0d;
            border-left: 3px solid #B20000;
            padding: 15px 20px;
            margin: 10px 0;
            border-radius: 0 8px 8px 0;
        }
        
        .insight-box {
            background: linear-gradient(135deg, #0a1a0a 0%, #0d0d0d 100%);
            border: 1px solid #00FF88;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# COMPONENTES
# ==========================================

def mostrar_checkin(user):
    st.markdown("### Check-in Pre-Mercado")
    st.caption("Responda honestamente. Isso e pra te proteger.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sono = st.slider("Como voce dormiu?", 1, 10, 7, help="1 = Pessimo, 10 = Muito bem")
        ansiedade = st.slider("Nivel de ansiedade", 1, 10, 3, help="1 = Calmo, 10 = Muito ansioso")
        clareza = st.slider("Clareza mental", 1, 10, 7, help="1 = Confuso, 10 = Muito focado")
    
    with col2:
        st.markdown("#### Checklist")
        fez_respiracao = st.checkbox("Fiz minha respiracao (5 min)")
        leu_regras = st.checkbox("Li minhas regras")
        quer_recuperar = st.checkbox("Estou querendo recuperar algo de ontem", help="Se sim, melhor nao operar")
    
    st.markdown("---")
    
    observacoes = st.text_area("Observacoes (opcional)", placeholder="Como voce esta se sentindo hoje?", height=80)
    
    score = (sono + (11 - ansiedade) + clareza) / 3
    config = get_config(user)
    
    if score >= 7:
        cor = "score-liberado"
        status = "LIBERADO"
    elif score >= config['score_minimo']:
        cor = "score-alerta"
        status = "ATENCAO"
    else:
        cor = "score-bloqueado"
        status = "NAO RECOMENDADO"
    
    if quer_recuperar:
        cor = "score-bloqueado"
        status = "NAO OPERE HOJE"
    
    st.markdown(f"""
        <div class="score-display">
            <div class="score-number {cor}">{score:.1f}</div>
            <div style="font-size: 18px; color: #888;">{status}</div>
        </div>
    """, unsafe_allow_html=True)
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("COMECAR DIA", use_container_width=True, type="primary"):
            dados = {
                "sono": sono,
                "ansiedade": ansiedade,
                "clareza": clareza,
                "fez_respiracao": fez_respiracao,
                "leu_regras": leu_regras,
                "quer_recuperar": quer_recuperar,
                "observacoes": observacoes
            }
            salvar_checkin(user, dados)
            st.toast("Check-in salvo!")
            time.sleep(0.5)
            st.rerun()
    
    with col_btn2:
        if st.button("VOU DESCANSAR HOJE", use_container_width=True):
            dados = {
                "sono": sono,
                "ansiedade": ansiedade,
                "clareza": clareza,
                "fez_respiracao": fez_respiracao,
                "leu_regras": leu_regras,
                "quer_recuperar": True,
                "observacoes": "Escolheu nao operar hoje"
            }
            salvar_checkin(user, dados)
            st.toast("Boa decisao! Descanse.")
            time.sleep(0.5)
            st.rerun()

def mostrar_journaling(user):
    st.markdown("### Journaling Pos-Mercado")
    st.caption("Obrigatorio para fechar o dia. Seja honesto consigo mesmo.")
    
    st.markdown("---")
    
    seguiu_plano = st.slider("Segui meu plano hoje? (1-10)", 1, 10, 7)
    
    st.markdown("---")
    
    oq_aconteceu = st.text_area(
        "Se quebrei alguma regra, o que aconteceu ANTES de eu quebrar?",
        placeholder="Ex: Tomei 2 stops e fiquei irritado. Senti que precisava recuperar...",
        height=100
    )
    
    gatilho = st.text_area(
        "Qual foi o gatilho emocional?",
        placeholder="Ex: Raiva por ter perdido. Medo de terminar o dia negativo...",
        height=80
    )
    
    diferente = st.text_area(
        "O que vou fazer diferente amanha?",
        placeholder="Ex: Parar apos 2 stops. Fazer respiracao antes de cada trade...",
        height=80
    )
    
    certo = st.text_area(
        "Uma coisa que fiz CERTO hoje:",
        placeholder="Ex: Parei quando o alerta amarelo apareceu. Fiz o check-in...",
        height=80
    )
    
    st.markdown("---")
    
    if st.button("ENCERRAR DIA", use_container_width=True, type="primary"):
        dados = {
            "seguiu_plano": seguiu_plano,
            "oq_aconteceu_antes": oq_aconteceu,
            "gatilho_emocional": gatilho,
            "oq_fazer_diferente": diferente,
            "oq_fez_certo": certo
        }
        salvar_journaling(user, dados)
        st.toast("Journaling salvo! Descanse bem.")
        return True
    
    return False

def mostrar_dashboard_mental(user):
    historico = get_historico_mental(user, 30)
    checkins = historico['checkins']
    
    st.markdown("### Performance Mental - Ultimos 30 dias")
    
    if not checkins:
        st.info("Ainda nao ha dados. Faca o check-in diario para comecar a ver estatisticas.")
        return
    
    df_checkins = pd.DataFrame(checkins)
    
    score_medio = df_checkins['score_geral'].mean()
    dias_operados = len(df_checkins)
    dias_liberado = len(df_checkins[df_checkins['liberado_operar'] == True])
    dias_ignorou = len(df_checkins[df_checkins['ignorou_recomendacao'] == True])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cor = "#00FF88" if score_medio >= 7 else ("#FFD700" if score_medio >= 5 else "#FF4444")
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: {cor};">{score_medio:.1f}</div>
                <div class="stat-label">Score Medio</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{dias_operados}</div>
                <div class="stat-label">Dias com Check-in</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pct = (dias_liberado / dias_operados * 100) if dias_operados > 0 else 0
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #00FF88;">{pct:.0f}%</div>
                <div class="stat-label">Dias Liberado</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        cor = "#FF4444" if dias_ignorou > 3 else "#00FF88"
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: {cor};">{dias_ignorou}</div>
                <div class="stat-label">Ignorou Alerta</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if score_medio >= 7:
        insight = "Seu estado mental esta excelente! Continue assim."
        cor_insight = "#00FF88"
    elif score_medio >= 5:
        insight = "Atencao ao seu estado mental. Considere reduzir exposicao em dias < 6."
        cor_insight = "#FFD700"
    else:
        insight = "Seu estado mental esta comprometido. Priorize descanso e nao opere abaixo de 6."
        cor_insight = "#FF4444"
    
    st.markdown(f"""
        <div class="insight-box" style="border-color: {cor_insight};">
            <div style="color: {cor_insight}; font-size: 16px;">{insight}</div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# PAGINA PRINCIPAL
# ==========================================

def show(user, role):
    load_styles()
    
    st.markdown("## Anti-Tilt System")
    
    # Frase de mindset
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #0a0a0a 0%, #111 100%);
            border-left: 3px solid #B20000;
            padding: 15px 20px;
            margin-bottom: 25px;
            border-radius: 0 8px 8px 0;
        ">
            <span style="color: #666; font-size: 13px; font-style: italic;">
                "Foque em nao ser idiota. E mais facil do que tentar ser genial."
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    tab_hoje, tab_stats, tab_config = st.tabs(["Hoje", "Estatisticas", "Configuracoes"])
    
    with tab_hoje:
        checkin = get_checkin_hoje(user)
        journaling = get_journaling_hoje(user)
        stops = get_stops_hoje(user)
        
        if not checkin:
            mostrar_checkin(user)
        else:
            score_class = 'score-liberado' if checkin['liberado_operar'] else 'score-bloqueado'
            st.markdown(f"""
                <div class="checkin-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="margin: 0; color: #fff;">Check-in de Hoje</h3>
                            <p style="color: #666; margin: 5px 0;">Concluido</p>
                        </div>
                        <div class="score-display" style="padding: 0;">
                            <div class="score-number {score_class}" style="font-size: 42px;">
                                {checkin['score_geral']}
                            </div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                cor = '#FF4444' if stops['stops_count'] >= 2 else '#00FF88'
                st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: {cor};">
                            {stops['stops_count']}
                        </div>
                        <div class="stat-label">Stops Hoje</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                cor = '#FF4444' if stops['stops_consecutivos'] >= 2 else '#00FF88'
                st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: {cor};">
                            {stops['stops_consecutivos']}
                        </div>
                        <div class="stat-label">Consecutivos</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col3:
                status_txt = "Liberado" if not stops.get('bloqueado_ate') else "Bloqueado"
                cor = "#00FF88" if not stops.get('bloqueado_ate') else "#FF4444"
                st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: {cor}; font-size: 18px;">{status_txt}</div>
                        <div class="stat-label">Status</div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            if not journaling:
                st.markdown("### Encerrar o Dia")
                st.caption("Complete o journaling para fechar o dia de operacoes.")
                
                with st.expander("Preencher Journaling", expanded=False):
                    mostrar_journaling(user)
            else:
                st.success("Dia encerrado! Journaling completo.")
    
    with tab_stats:
        mostrar_dashboard_mental(user)
    
    with tab_config:
        st.markdown("### Configuracoes do Anti-Tilt")
        
        config = get_config(user)
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_stops = st.number_input("Max stops por dia", value=config['max_stops_dia'], min_value=1, max_value=10)
            max_consec = st.number_input("Max stops consecutivos", value=config['max_stops_consecutivos'], min_value=1, max_value=5)
            timer = st.number_input("Timer apos stop (segundos)", value=config['timer_apos_stop_segundos'], min_value=60, max_value=600)
        
        with col2:
            bloqueio = st.number_input("Tempo de bloqueio (minutos)", value=config['bloqueio_minutos'], min_value=30, max_value=240)
            score_min = st.number_input("Score minimo pra operar", value=float(config['score_minimo']), min_value=1.0, max_value=9.0, step=0.5)
        
        st.markdown("---")
        
        st.markdown("#### Regras Ativas")
        checkin_obg = st.checkbox("Check-in obrigatorio", value=config['checkin_obrigatorio'])
        protocolo_ativo = st.checkbox("Protocolo de stop ativo", value=config['protocolo_stop_ativo'])
        bloqueio_auto = st.checkbox("Bloqueio automatico apos max stops", value=config['bloqueio_automatico'])
        journal_obg = st.checkbox("Journaling obrigatorio", value=config['journaling_obrigatorio'])
        
        if st.button("Salvar Configuracoes", use_container_width=True):
            sb = get_supabase()
            sb.table("antitilt_config").update({
                "max_stops_dia": max_stops,
                "max_stops_consecutivos": max_consec,
                "timer_apos_stop_segundos": timer,
                "bloqueio_minutos": bloqueio,
                "score_minimo": score_min,
                "checkin_obrigatorio": checkin_obg,
                "protocolo_stop_ativo": protocolo_ativo,
                "bloqueio_automatico": bloqueio_auto,
                "journaling_obrigatorio": journal_obg
            }).eq("usuario", user).execute()
            
            st.toast("Configuracoes salvas!")
