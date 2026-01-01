-- =============================================
-- MÓDULO ANTI-TILT - TABELAS
-- =============================================

-- 1. CHECK-IN DIÁRIO (Pré-mercado)
CREATE TABLE IF NOT EXISTS checkin_diario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario TEXT NOT NULL,
    data DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Scores (1-10)
    sono INTEGER CHECK (sono >= 1 AND sono <= 10),
    ansiedade INTEGER CHECK (ansiedade >= 1 AND ansiedade <= 10),
    clareza INTEGER CHECK (clareza >= 1 AND clareza <= 10),
    
    -- Checklist
    fez_respiracao BOOLEAN DEFAULT FALSE,
    leu_regras BOOLEAN DEFAULT FALSE,
    quer_recuperar BOOLEAN DEFAULT FALSE,
    
    -- Score calculado
    score_geral DECIMAL(3,1),
    
    -- Decisão
    liberado_operar BOOLEAN DEFAULT TRUE,
    ignorou_recomendacao BOOLEAN DEFAULT FALSE,
    
    -- Observações
    observacoes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Único check-in por dia por usuário
    UNIQUE(usuario, data)
);

-- 2. REGISTRO DE STOPS DO DIA (Para detector de tilt)
CREATE TABLE IF NOT EXISTS stops_dia (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario TEXT NOT NULL,
    data DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Contadores
    stops_count INTEGER DEFAULT 0,
    stops_consecutivos INTEGER DEFAULT 0,
    
    -- Alertas disparados
    alerta_amarelo_disparado BOOLEAN DEFAULT FALSE,
    alerta_vermelho_disparado BOOLEAN DEFAULT FALSE,
    
    -- Bloqueio
    bloqueado_ate TIMESTAMPTZ,
    
    -- Decisões do trader
    vezes_ignorou_alerta INTEGER DEFAULT 0,
    encerrou_no_protocolo BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(usuario, data)
);

-- 3. JOURNALING PÓS-MERCADO
CREATE TABLE IF NOT EXISTS journaling (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario TEXT NOT NULL,
    data DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Perguntas estruturadas
    seguiu_plano INTEGER CHECK (seguiu_plano >= 1 AND seguiu_plano <= 10),
    
    -- Textos
    oq_aconteceu_antes TEXT,
    gatilho_emocional TEXT,
    oq_fazer_diferente TEXT,
    oq_fez_certo TEXT,
    
    -- Métricas do dia (auto-preenchidas)
    total_trades INTEGER DEFAULT 0,
    total_stops INTEGER DEFAULT 0,
    pnl_dia DECIMAL(10,2) DEFAULT 0,
    seguiu_protocolo BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(usuario, data)
);

-- 4. PROTOCOLO DE STOP (Log de cada stop)
CREATE TABLE IF NOT EXISTS protocolo_stops (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario TEXT NOT NULL,
    data DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Momento do stop
    hora_stop TIMESTAMPTZ DEFAULT NOW(),
    
    -- Após o timer
    completou_timer BOOLEAN DEFAULT FALSE,
    estado_emocional INTEGER CHECK (estado_emocional >= 1 AND estado_emocional <= 10),
    quer_recuperar BOOLEAN,
    
    -- Decisão
    decisao TEXT CHECK (decisao IN ('parou', 'continuou', 'ignorou')),
    
    -- Se continuou e tomou outro stop
    resultado_apos TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. CONFIGURAÇÕES DO ANTI-TILT (Por usuário)
CREATE TABLE IF NOT EXISTS antitilt_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario TEXT NOT NULL UNIQUE,
    
    -- Limites
    max_stops_dia INTEGER DEFAULT 3,
    max_stops_consecutivos INTEGER DEFAULT 2,
    timer_apos_stop_segundos INTEGER DEFAULT 180,
    bloqueio_minutos INTEGER DEFAULT 60,
    
    -- Score mínimo pra operar
    score_minimo DECIMAL(3,1) DEFAULT 6.0,
    
    -- Regras ativas
    checkin_obrigatorio BOOLEAN DEFAULT TRUE,
    protocolo_stop_ativo BOOLEAN DEFAULT TRUE,
    bloqueio_automatico BOOLEAN DEFAULT TRUE,
    journaling_obrigatorio BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ÍNDICES
CREATE INDEX IF NOT EXISTS idx_checkin_usuario_data ON checkin_diario(usuario, data);
CREATE INDEX IF NOT EXISTS idx_stops_usuario_data ON stops_dia(usuario, data);
CREATE INDEX IF NOT EXISTS idx_journaling_usuario_data ON journaling(usuario, data);
CREATE INDEX IF NOT EXISTS idx_protocolo_usuario_data ON protocolo_stops(usuario, data);

-- TRIGGERS para updated_at
CREATE OR REPLACE FUNCTION update_antitilt_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_stops_dia_updated ON stops_dia;
CREATE TRIGGER trigger_stops_dia_updated
    BEFORE UPDATE ON stops_dia
    FOR EACH ROW
    EXECUTE FUNCTION update_antitilt_timestamp();

DROP TRIGGER IF EXISTS trigger_antitilt_config_updated ON antitilt_config;
CREATE TRIGGER trigger_antitilt_config_updated
    BEFORE UPDATE ON antitilt_config
    FOR EACH ROW
    EXECUTE FUNCTION update_antitilt_timestamp();antitilt.py
