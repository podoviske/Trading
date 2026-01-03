import streamlit as st
import json
import uuid
from supabase import create_client

# --- CONEXÃO ---
def get_supabase():
    if "supabase" in st.session_state:
        return st.session_state["supabase"]
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# --- CRUD DO PLANO ---
def load_plano(user):
    """Carrega o plano do usuário ou cria um novo"""
    sb = get_supabase()
    res = sb.table("plano_trading").select("*").eq("usuario", user).execute()
    
    if res.data:
        return res.data[0]
    else:
        # Cria plano padrão
        novo_plano = {
            "id": str(uuid.uuid4()),
            "usuario": user,
            "notas_diarias": "",
            "documento_plano": "",
            "documento_imagens": json.dumps([]),
            "fase_atual": "Fase 1 - Evaluation",
            "fases_config": json.dumps([
                {"nome": "Fase 1 - Evaluation", "micros": 30, "meta_diaria": 1000, "stop_diario": 2000, "perda_max": 1000, "parcial1_pts": "10-15", "parcial1_cts": 18, "parcial2_pts": "20-30", "parcial2_cts": 7},
                {"nome": "Fase 2 - Prop 0-5k", "micros": 10, "meta_diaria": 300, "stop_diario": 600, "perda_max": 300, "parcial1_pts": "10-15", "parcial1_cts": 6, "parcial2_pts": "20-30", "parcial2_cts": 2},
                {"nome": "Fase 3 - Prop 5k-10k", "micros": 15, "meta_diaria": 500, "stop_diario": 1000, "perda_max": 500, "parcial1_pts": "10-15", "parcial1_cts": 9, "parcial2_pts": "20-30", "parcial2_cts": 3},
                {"nome": "Fase 4 - Prop 10k+", "micros": 25, "meta_diaria": 800, "stop_diario": 1500, "perda_max": 800, "parcial1_pts": "10-15", "parcial1_cts": 15, "parcial2_pts": "20-30", "parcial2_cts": 5}
            ]),
            "contextos": json.dumps([
                {"letra": "A", "nome": "Inversão de Fluxo", "descricao": "A operação de contexto A refere-se a inversão de fluxo nos vácuos de liquidez.", "img_modelo": ""},
                {"letra": "B", "nome": "Rompimento", "descricao": "A operação de contexto B você irá pegar o rompimento quando houver clareza e alta probabilidade com: Volume, IFR, Saldo e BOP estiverem a favor da sua entrada; a chance de ir ao 161,8 de fibo é de 90% e o seu stop ter q ser rápido, curto e bem posicionado pois você está operando rompimento (70% são falsos).", "img_modelo": ""},
                {"letra": "C", "nome": "Bipolaridade", "descricao": "A operação de contexto C, estamos operando uma Bipolaridade 'desenhada' em um mercado já direcional.", "img_modelo": ""}
            ])
        }
        sb.table("plano_trading").insert(novo_plano).execute()
        return novo_plano

def save_plano(plano_id, updates):
    """Salva alterações no plano"""
    sb = get_supabase()
    sb.table("plano_trading").update(updates).eq("id", plano_id).execute()

def upload_image(file, filename):
    """Faz upload de imagem pro Supabase Storage"""
    sb = get_supabase()
    file_path = f"plano/{filename}"
    sb.storage.from_("prints").upload(file_path, file.getvalue(), {"upsert": "true"})
    return sb.storage.from_("prints").get_public_url(file_path)

# --- ESTILOS CSS ---
def load_styles():
    st.markdown("""
        <style>
        /* Cards */
        .card-dark {
            background-color: #111;
            border: 1px solid #222;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
        }
        
        .card-green {
            background-color: #0a1f0a;
            border: 1px solid #00FF88;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        
        .card-red {
            background-color: #1f0a0a;
            border: 1px solid #B20000;
            border-radius: 12px;
            padding: 20px;
        }
        
        /* Contexto Cards CLICÁVEIS */
        .contexto-card {
            background: linear-gradient(135deg, #161616 0%, #1a1a1a 100%);
            border: 1px solid #333;
            border-radius: 12px;
            padding: 25px 20px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
            height: 100%;
        }
        
        .contexto-card:hover {
            border-color: #B20000;
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(178, 0, 0, 0.3);
        }
        
        .contexto-letra {
            font-size: 52px;
            font-weight: 800;
            color: #B20000;
            margin-bottom: 5px;
        }
        
        .contexto-nome {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .contexto-hint {
            font-size: 10px;
            color: #444;
            margin-top: 10px;
        }
        
        /* Disciplina */
        .disciplina-item {
            display: flex;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #222;
        }
        
        .disciplina-pct {
            font-size: 24px;
            font-weight: 700;
            width: 80px;
        }
        
        .disciplina-100 { color: #00FF88; }
        .disciplina-60 { color: #FFD700; }
        .disciplina-40 { color: #FF6B6B; }
        
        /* Fase Table */
        .fase-row {
            display: grid;
            grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr 1.5fr 1.5fr;
            gap: 10px;
            padding: 15px;
            border-bottom: 1px solid #222;
            align-items: center;
        }
        
        .fase-row.header {
            color: #666;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .fase-row.active {
            background-color: #1a0a0a;
            border-left: 3px solid #B20000;
            border-radius: 8px;
        }
        
        /* Section Title */
        .section-title {
            font-size: 20px;
            font-weight: 700;
            color: #fff;
            margin: 30px 0 20px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        /* Meta Card */
        .meta-valor {
            font-size: 42px;
            font-weight: 800;
            color: #00FF88;
        }
        
        .meta-label {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        /* Regra Card */
        .regra-card {
            background-color: #111;
            border-left: 3px solid #B20000;
            border-radius: 0 10px 10px 0;
            padding: 18px 20px;
            margin-bottom: 12px;
        }
        
        .regra-titulo {
            font-weight: 700;
            color: #fff;
            font-size: 15px;
            margin-bottom: 8px;
        }
        
        .regra-desc {
            color: #777;
            font-size: 13px;
            line-height: 1.5;
        }
        
        /* Looping Warning */
        .looping-box {
            background: linear-gradient(135deg, #1a0000 0%, #0a0000 100%);
            border: 1px solid #B20000;
            border-radius: 12px;
            padding: 25px;
            text-align: center;
        }
        
        .looping-title {
            color: #FF4444;
            font-size: 22px;
            font-weight: 800;
            margin-bottom: 15px;
        }
        
        .looping-item {
            color: #888;
            font-size: 13px;
            padding: 8px 0;
        }
        
        /* Documento */
        .doc-content {
            background-color: #0d0d0d;
            border: 1px solid #1a1a1a;
            border-radius: 12px;
            padding: 30px;
            line-height: 1.8;
            color: #ccc;
            font-size: 14px;
        }
        
        .doc-content h1, .doc-content h2, .doc-content h3 {
            color: #fff;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        
        .doc-content img {
            max-width: 100%;
            border-radius: 8px;
            margin: 20px 0;
        }
        
        /* Operação Modelo */
        .modelo-img {
            border: 2px solid #00FF88;
            border-radius: 8px;
            margin-top: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

# --- PÁGINA PRINCIPAL ---
def show():
    load_styles()
    
    user = st.session_state.get("logged_user", "default")
    plano = load_plano(user)
    
    # Parse JSONs
    fases = json.loads(plano["fases_config"]) if isinstance(plano["fases_config"], str) else plano["fases_config"]
    contextos = json.loads(plano["contextos"]) if isinstance(plano["contextos"], str) else plano["contextos"]
    doc_imagens = json.loads(plano.get("documento_imagens", "[]")) if isinstance(plano.get("documento_imagens", "[]"), str) else plano.get("documento_imagens", [])
    
    # --- HEADER ---
    st.markdown("## 📋 Plano de Trading")
    
    # --- TABS ---
    tab_visao, tab_contextos, tab_documento, tab_fases, tab_config = st.tabs([
        "📊 Visão Geral", 
        "🎯 Contextos", 
        "📖 Meu Plano",
        "📈 Fases & Gestão", 
        "⚙️ Configurar"
    ])
    
    # ==========================================
    # TAB 1: VISÃO GERAL
    # ==========================================
    with tab_visao:
        
        # --- META MACRO ---
        col_meta, col_estrategia = st.columns([1, 2])
        
        with col_meta:
            st.markdown("""
                <div class="card-green">
                    <div class="meta-label">Meta Final por Conta</div>
                    <div class="meta-valor">$161,000</div>
                    <div style="color:#555; font-size:11px; margin-top:8px;">IMPÉRIO DE 20 CONTAS</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col_estrategia:
            st.markdown("""
                <div class="card-dark">
                    <div style="color:#00FF88; font-weight:600; margin-bottom:12px;">🎯 Estratégia de Crescimento</div>
                    <div style="color:#888; font-size:13px; line-height:1.8;">
                        • Manter meta de <span style="color:#fff;">$500/semana</span> por conta consistentemente<br>
                        • Não alavancar antes de atingir o <span style="color:#fff;">Colchão de Segurança (Fase 2)</span><br>
                        • O objetivo não é ficar rico num dia, é <span style="color:#00FF88;">construir o Império de 20 Contas</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        # --- REGRAS DE OURO ---
        st.markdown('<div class="section-title">🛡️ Regras de Ouro</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
                <div class="regra-card">
                    <div class="regra-titulo">1. Ativos & Foco</div>
                    <div class="regra-desc">
                        <b>MNQ (Micro):</b> Ativo Principal para construção de capital.<br>
                        <b>NQ (Mini):</b> APENAS com Edge confirmado e Gordura acumulada.
                    </div>
                </div>
                
                <div class="regra-card">
                    <div class="regra-titulo">2. Horário de Elite</div>
                    <div class="regra-desc">
                        Defina sua janela de foco (ex: 10:30 - 12:00).<br>
                        Não operar em horários de baixa liquidez ou notícias Tier 1.
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
                <div class="regra-card">
                    <div class="regra-titulo">3. Gestão de Lote (Vidas)</div>
                    <div class="regra-desc">
                        Siga RIGOROSAMENTE a sugestão do Dashboard.<br>
                        Alvo ideal: <b>20 Vidas</b> (Stops) de gordura.
                    </div>
                </div>
                
                <div class="regra-card">
                    <div class="regra-titulo">4. Stop Diário (Loss Limit)</div>
                    <div class="regra-desc">
                        Defina um limite financeiro de perda por dia por grupo.<br>
                        Atingiu o limite? <b>Feche a plataforma.</b> Amanhã tem mais.
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        # --- DISCIPLINA ---
        st.markdown('<div class="section-title">🧠 Níveis de Disciplina</div>', unsafe_allow_html=True)
        
        col_disc, col_loop = st.columns(2)
        
        with col_disc:
            st.markdown("""
                <div class="card-dark">
                    <div class="disciplina-item">
                        <div class="disciplina-pct disciplina-100">100%</div>
                        <div style="color:#888; font-size:13px;">Fez EXATAMENTE o que se propôs, independente de gain ou loss</div>
                    </div>
                    <div class="disciplina-item">
                        <div class="disciplina-pct disciplina-60">60%</div>
                        <div style="color:#888; font-size:13px;">Não fez o que se propôs, mas saiu no primeiro erro e ainda assim positivo</div>
                    </div>
                    <div class="disciplina-item" style="border:none;">
                        <div class="disciplina-pct disciplina-40">40%</div>
                        <div style="color:#888; font-size:13px;">Entrou em looping, mas garantiu que não perdeu tudo</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        with col_loop:
            st.markdown("""
                <div class="looping-box">
                    <div class="looping-title">⚠️ LOOPING NEGATIVO</div>
                    <div class="looping-item">Se subir a <b style="color:#FF4444;">RAIVA</b> ou o <b style="color:#FF4444;">NERVOSO</b></div>
                    <div class="looping-item">Sinto muito, mas você JÁ ENTROU no looping</div>
                    <div style="margin:15px 0; border-top:1px solid #333; padding-top:15px;">
                        <div style="color:#666; font-size:12px;">Ciclo: Toma Stop → Insiste → Toma Stop → <span style="color:#FF4444;">PERDE TUDO</span></div>
                    </div>
                    <div style="color:#FF6B6B; font-size:12px; font-style:italic;">
                        "3 minutos após um stop, se você continuar ruminando: virou roleta"
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        # --- NOTAS PESSOAIS ---
        st.markdown('<div class="section-title">📝 Notas Pessoais / Diário Mental</div>', unsafe_allow_html=True)
        
        notas = st.text_area(
            "O que você precisa lembrar hoje?",
            value=plano.get("notas_diarias", ""),
            height=150,
            placeholder="Ex: Estou ansioso hoje, operar metade da mão. Não perseguir preço...",
            key="notas_input"
        )
        
        if st.button("💾 Salvar Notas", use_container_width=True):
            save_plano(plano["id"], {"notas_diarias": notas})
            st.toast("✅ Notas salvas!", icon="💾")
    
    # ==========================================
    # TAB 2: CONTEXTOS (CLICÁVEIS)
    # ==========================================
    with tab_contextos:
        
        st.markdown('<div class="section-title">🎯 Contextos de Operação</div>', unsafe_allow_html=True)
        st.caption("Clique em um contexto para ver as operações no Histórico")
        
        # Cards dos contextos CLICÁVEIS
        cols = st.columns(3)
        
        for i, ctx in enumerate(contextos):
            with cols[i]:
                # Card visual
                st.markdown(f"""
                    <div class="contexto-card">
                        <div class="contexto-letra">{ctx['letra']}</div>
                        <div class="contexto-nome">{ctx['nome']}</div>
                        <div class="contexto-hint">🔍 Clique para ver histórico</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Botão invisível pra capturar o clique
                if st.button(f"Ver Contexto {ctx['letra']}", key=f"btn_ctx_{ctx['letra']}", use_container_width=True):
                    # Seta o filtro no session_state
                    st.session_state["filtro_contexto_historico"] = f"Contexto {ctx['letra']}"
                    st.session_state["navegar_para"] = "Histórico"
                    st.rerun()
        
        st.markdown("---")
        
        # Descrições expandidas com operação modelo
        for ctx in contextos:
            with st.expander(f"📖 Contexto {ctx['letra']} - {ctx['nome']}", expanded=False):
                st.markdown(f"""
                    <div style="color:#aaa; font-size:14px; line-height:1.7; padding:10px 0;">
                        {ctx['descricao']}
                    </div>
                """, unsafe_allow_html=True)
                
                # Operação modelo
                if ctx.get('img_modelo'):
                    st.markdown("##### 📸 Operação Modelo (Trade de Livro)")
                    st.image(ctx['img_modelo'], use_container_width=True)
                else:
                    st.info("📷 Nenhuma operação modelo configurada. Vá em 'Configurar' para adicionar.")
    
    # ==========================================
    # TAB 3: DOCUMENTO (MEU PLANO) - SISTEMA DE BLOCOS
    # ==========================================
    with tab_documento:
        
        st.markdown('<div class="section-title">Meu Plano de Trading</div>', unsafe_allow_html=True)
        
        # Carrega blocos do documento (ou cria estrutura vazia)
        try:
            blocos = json.loads(plano.get("documento_plano", "[]"))
            if not isinstance(blocos, list):
                blocos = []
        except:
            blocos = []
        
        # Toggle entre visualizar e editar
        modo = st.radio("Modo", ["Visualizar", "Editar"], horizontal=True, label_visibility="collapsed")
        
        st.markdown("---")
        
        if modo == "Editar":
            
            st.markdown("#### Editor do Plano")
            st.caption("Adicione blocos de texto e imagem para construir seu plano")
            
            # Inicializa blocos no session_state se necessario
            if "plano_blocos" not in st.session_state:
                st.session_state["plano_blocos"] = blocos.copy() if blocos else []
            
            blocos_editados = st.session_state["plano_blocos"]
            
            # Renderiza cada bloco existente
            blocos_para_remover = []
            
            for i, bloco in enumerate(blocos_editados):
                with st.container():
                    col_content, col_actions = st.columns([10, 1])
                    
                    with col_content:
                        if bloco["tipo"] == "texto":
                            # Bloco de texto
                            novo_texto = st.text_area(
                                f"Bloco {i+1} (Texto)",
                                value=bloco["conteudo"],
                                height=150,
                                key=f"bloco_texto_{i}",
                                label_visibility="collapsed"
                            )
                            blocos_editados[i]["conteudo"] = novo_texto
                            
                        elif bloco["tipo"] == "imagem":
                            # Bloco de imagem
                            st.image(bloco["conteudo"], use_container_width=True)
                            if bloco.get("legenda"):
                                st.caption(bloco["legenda"])
                    
                    with col_actions:
                        if st.button("X", key=f"del_bloco_{i}", help="Remover bloco"):
                            blocos_para_remover.append(i)
                
                st.markdown("---")
            
            # Remove blocos marcados
            for idx in sorted(blocos_para_remover, reverse=True):
                blocos_editados.pop(idx)
                st.rerun()
            
            # Botoes para adicionar blocos
            st.markdown("#### Adicionar Conteudo")
            
            col_add_texto, col_add_img = st.columns(2)
            
            with col_add_texto:
                if st.button("+ Adicionar Texto", use_container_width=True):
                    blocos_editados.append({"tipo": "texto", "conteudo": ""})
                    st.session_state["plano_blocos"] = blocos_editados
                    st.rerun()
            
            with col_add_img:
                img_upload = st.file_uploader("Adicionar Imagem", type=["png", "jpg", "jpeg"], key="img_bloco_upload", label_visibility="collapsed")
                
                if img_upload:
                    if st.button("Inserir Imagem", use_container_width=True):
                        # Upload da imagem
                        url = upload_image(img_upload, f"{user}_doc_{uuid.uuid4().hex[:8]}.png")
                        blocos_editados.append({"tipo": "imagem", "conteudo": url, "legenda": ""})
                        st.session_state["plano_blocos"] = blocos_editados
                        st.toast("Imagem adicionada!")
                        st.rerun()
            
            st.markdown("---")
            
            # Botao salvar
            if st.button("Salvar Plano", use_container_width=True, type="primary"):
                save_plano(plano["id"], {"documento_plano": json.dumps(blocos_editados)})
                st.session_state["plano_blocos"] = blocos_editados
                st.toast("Plano salvo!")
                st.rerun()
        
        else:
            # MODO VISUALIZACAO
            if not blocos:
                st.info("Seu plano esta vazio. Clique em 'Editar' para comecar a escrever.")
            else:
                for i, bloco in enumerate(blocos):
                    if bloco["tipo"] == "texto":
                        # Renderiza texto como markdown
                        st.markdown(f"""
                            <div style="
                                color: #ccc;
                                font-size: 15px;
                                line-height: 1.8;
                                margin-bottom: 20px;
                            ">
                                {bloco['conteudo'].replace(chr(10), '<br>')}
                            </div>
                        """, unsafe_allow_html=True)
                        
                    elif bloco["tipo"] == "imagem":
                        # Imagem clicavel para expandir
                        col_space1, col_img, col_space2 = st.columns([1, 6, 1])
                        with col_img:
                            st.image(bloco["conteudo"], use_container_width=True)
                            if st.button("Expandir", key=f"expand_img_{i}", use_container_width=True):
                                st.session_state["img_expandida"] = bloco["conteudo"]
                            if bloco.get("legenda"):
                                st.caption(bloco["legenda"])
        
        # Modal para imagem expandida (fora do loop)
        if st.session_state.get("img_expandida"):
            @st.dialog("Imagem Expandida", width="large")
            def mostrar_imagem_expandida():
                st.image(st.session_state["img_expandida"], use_container_width=True)
                if st.button("Fechar", use_container_width=True):
                    del st.session_state["img_expandida"]
                    st.rerun()
            
            mostrar_imagem_expandida()
    
    # ==========================================
    # TAB 4: FASES & GESTÃO
    # ==========================================
    with tab_fases:
        
        st.markdown('<div class="section-title">📈 Fases do Trading</div>', unsafe_allow_html=True)
        
        # Info das fases
        st.markdown("""
            <div class="card-dark" style="margin-bottom:20px;">
                <div style="color:#888; font-size:13px; line-height:1.8;">
                    <b style="color:#fff;">Fase 1:</b> Passar no teste (Evaluation)<br>
                    <b style="color:#fff;">Fase 2:</b> Fazer o colchão de segurança<br>
                    <b style="color:#fff;">Fase 3:</b> Dobrar o valor do colchão<br>
                    <b style="color:#fff;">Fase 4:</b> Iniciar os saques, 70% do valor feito no período
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Seletor de fase atual
        fase_nomes = [f["nome"] for f in fases]
        fase_atual_idx = 0
        for i, f in enumerate(fases):
            if f["nome"] == plano.get("fase_atual"):
                fase_atual_idx = i
                break
        
        fase_selecionada = st.selectbox("📍 Sua Fase Atual", fase_nomes, index=fase_atual_idx)
        
        if fase_selecionada != plano.get("fase_atual"):
            save_plano(plano["id"], {"fase_atual": fase_selecionada})
            st.toast("✅ Fase atualizada!", icon="📍")
            st.rerun()
        
        st.markdown("---")
        
        # Tabela de fases
        st.markdown("#### Planejamento por Fase")
        
        # Header
        st.markdown("""
            <div class="fase-row header">
                <div>FASE</div>
                <div>MICROS</div>
                <div>META DIA</div>
                <div>STOP DIA</div>
                <div>PERDA</div>
                <div>PARCIAL 1</div>
                <div>PARCIAL 2</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Linhas
        for fase in fases:
            is_active = fase["nome"] == fase_selecionada
            active_class = "active" if is_active else ""
            
            st.markdown(f"""
                <div class="fase-row {active_class}">
                    <div style="color:#fff; font-weight:{'700' if is_active else '400'};">{fase['nome']}</div>
                    <div style="color:#888;">{fase['micros']}</div>
                    <div style="color:#00FF88;">${fase['meta_diaria']:,}</div>
                    <div style="color:#FF6B6B;">${fase['stop_diario']:,}</div>
                    <div style="color:#FF4444;">${fase['perda_max']:,}</div>
                    <div style="color:#888;">{fase['parcial1_pts']}pts ({fase['parcial1_cts']} cts)</div>
                    <div style="color:#888;">{fase['parcial2_pts']}pts ({fase['parcial2_cts']} cts)</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.caption("💡 O encerramento da posição deve ser de acordo com o contexto, fazendo trailing ou alvo de acordo com o contexto.")
    
    # ==========================================
    # TAB 5: CONFIGURAR
    # ==========================================
    with tab_config:
        
        st.markdown('<div class="section-title">⚙️ Configurações do Plano</div>', unsafe_allow_html=True)
        
        # --- OPERAÇÕES MODELO ---
        st.markdown("#### 📸 Operações Modelo (Trade de Livro)")
        st.caption("Adicione uma imagem de operação perfeita para cada contexto")
        
        for i, ctx in enumerate(contextos):
            with st.expander(f"Contexto {ctx['letra']} - {ctx['nome']}"):
                
                if ctx.get('img_modelo'):
                    st.image(ctx['img_modelo'], width=400)
                    if st.button(f"🗑️ Remover imagem", key=f"rm_modelo_{i}"):
                        contextos[i]['img_modelo'] = ""
                        save_plano(plano["id"], {"contextos": json.dumps(contextos)})
                        st.toast("✅ Imagem removida!", icon="🗑️")
                        st.rerun()
                
                img_modelo = st.file_uploader(f"Upload operação modelo", type=["png", "jpg", "jpeg"], key=f"modelo_{i}")
                
                if img_modelo:
                    if st.button(f"💾 Salvar Operação Modelo {ctx['letra']}", key=f"save_modelo_{i}"):
                        url = upload_image(img_modelo, f"{user}_modelo_{ctx['letra']}.png")
                        contextos[i]['img_modelo'] = url
                        save_plano(plano["id"], {"contextos": json.dumps(contextos)})
                        st.toast("✅ Operação modelo salva!", icon="📸")
                        st.rerun()
        
        st.markdown("---")
        
        # --- EDITAR CONTEXTOS ---
        st.markdown("#### ✏️ Editar Descrição dos Contextos")
        
        contextos_editados = []
        for i, ctx in enumerate(contextos):
            with st.expander(f"Contexto {ctx['letra']} - {ctx['nome']}"):
                nome = st.text_input(f"Nome", value=ctx['nome'], key=f"ctx_nome_{i}")
                desc = st.text_area(f"Descrição", value=ctx['descricao'], key=f"ctx_desc_{i}", height=100)
                contextos_editados.append({
                    "letra": ctx['letra'],
                    "nome": nome,
                    "descricao": desc,
                    "img_modelo": ctx.get('img_modelo', '')
                })
        
        if st.button("💾 Salvar Contextos", use_container_width=True):
            save_plano(plano["id"], {"contextos": json.dumps(contextos_editados)})
            st.toast("✅ Contextos salvos!", icon="💾")
            st.rerun()
        
        st.markdown("---")
        
        # --- EDITAR FASES ---
        st.markdown("#### ✏️ Editar Fases")
        
        fases_editadas = []
        for i, fase in enumerate(fases):
            with st.expander(f"{fase['nome']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    micros = st.number_input("Micros", value=fase['micros'], key=f"fase_micros_{i}")
                    meta = st.number_input("Meta Diária ($)", value=fase['meta_diaria'], key=f"fase_meta_{i}")
                with col2:
                    stop = st.number_input("Stop Diário ($)", value=fase['stop_diario'], key=f"fase_stop_{i}")
                    perda = st.number_input("Perda Máx ($)", value=fase['perda_max'], key=f"fase_perda_{i}")
                with col3:
                    p1_cts = st.number_input("Parcial 1 (cts)", value=fase['parcial1_cts'], key=f"fase_p1cts_{i}")
                    p2_cts = st.number_input("Parcial 2 (cts)", value=fase['parcial2_cts'], key=f"fase_p2cts_{i}")
                
                fases_editadas.append({
                    "nome": fase['nome'],
                    "micros": micros,
                    "meta_diaria": meta,
                    "stop_diario": stop,
                    "perda_max": perda,
                    "parcial1_pts": fase['parcial1_pts'],
                    "parcial1_cts": p1_cts,
                    "parcial2_pts": fase['parcial2_pts'],
                    "parcial2_cts": p2_cts
                })
        
        if st.button("💾 Salvar Fases", use_container_width=True):
            save_plano(plano["id"], {"fases_config": json.dumps(fases_editadas)})
            st.toast("✅ Fases salvas!", icon="💾")
            st.rerun()
