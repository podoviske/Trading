import math

# ==============================================================================
# 1. MOTOR APEX (Regra Fixa 150k)
# ==============================================================================
class ApexEngine:
    """
    Motor especialista na regra de 150k da Apex.
    Centraliza toda a lógica de Trailing Stop e Fases.
    """
    STARTING_BALANCE = 150000.0
    MAX_DRAWDOWN = 5000.0
    # O Trailing Stop sobe até o saldo atingir (150k + 5k + 100).
    # Nesse ponto, o stop trava em (150k + 100).
    LOCK_THRESHOLD = 155100.0  
    LOCKED_STOP_VALUE = 150100.0

    @staticmethod
    def calculate_health(saldo_atual, hwm_previo):
        """
        Calcula a saúde (Buffer e Stop) dado o saldo atual e o HWM (Pico Histórico).
        """
        # Garante que o HWM nunca é menor que o saldo atual
        hwm_real = max(saldo_atual, hwm_previo)
        
        # --- Lógica do Trailing Stop Apex ---
        # Se o HWM já tocou a zona de trava ($155.100+), o stop morre em $150.100
        if hwm_real >= ApexEngine.LOCK_THRESHOLD:
            stop_atual = ApexEngine.LOCKED_STOP_VALUE
            status_trailing = "TRAVADO (Fixo)"
        else:
            # Caso contrário, o stop vem arrastando (HWM - 5k)
            stop_atual = hwm_real - ApexEngine.MAX_DRAWDOWN
            status_trailing = "MÓVEL (Trailing)"
            
        # Buffer: Quanto dinheiro real temos até quebrar
        buffer = max(0.0, saldo_atual - stop_atual)
        
        # Definição de Fases para o Dashboard
        if saldo_atual < ApexEngine.LOCK_THRESHOLD:
            fase = "Fase 2 (Colchão)"
            meta_prox = ApexEngine.LOCK_THRESHOLD
            falta = meta_prox - saldo_atual
        else:
            fase = "Fase 3 (Blindagem)"
            meta_prox = 160000.0 # Próxima meta simbólica (10k lucro)
            falta = 0.0 # Já travou o stop, "game over" do risco inicial
            
        return {
            "saldo": saldo_atual,
            "hwm": hwm_real,
            "stop_atual": stop_atual,
            "buffer": buffer,
            "fase": fase,
            "status_trailing": status_trailing,
            "falta_para_trava": max(0.0, falta)
        }

# ==============================================================================
# 2. MOTOR DE RISCO (Probabilidade de Ruína)
# ==============================================================================
class RiskEngine:
    @staticmethod
    def calculate_ruin(win_rate_percent, avg_win, avg_loss, total_buffer):
        """
        Calcula a chance matemática de perder TODO o Buffer disponível.
        Baseado na fórmula de Ruína com Drift (Random Walk).
        """
        # Se não tem buffer, já quebrou
        if total_buffer <= 0: return 100.0
        if avg_loss == 0: return 0.0 # Se não perde nunca, ruína é 0
        
        p = win_rate_percent / 100.0
        q = 1.0 - p
        
        # Expectativa Matemática por Trade (EV)
        ev = (p * avg_win) - (q * avg_loss)
        
        # Se o sistema tem expectativa negativa, a ruína é 100% no longo prazo
        if ev <= 0: return 100.0
        
        # Variância dos retornos
        s2 = (p * (avg_win - ev)**2) + (q * (-avg_loss - ev)**2)
        if s2 == 0: return 0.0
        
        # Fórmula: Ruína = e^(-2 * EV * Banca / Variância)
        try:
            arg = -2 * ev * total_buffer / s2
            ruin = math.exp(arg) * 100.0
        except OverflowError:
            ruin = 0.0 # Matematicamente tende a zero se o argumento for muito negativo
            
        return min(100.0, max(0.0, ruin))

# ==============================================================================
# 3. MOTOR KELLY (Dimensionamento de Posição)
# ==============================================================================
class PositionSizing:
    @staticmethod
    def calculate_limits(win_rate_percent, payoff, total_buffer, risk_unit_dollars):
        """
        Retorna (Lote Min, Lote Max, % Kelly).
        Usa Half-Kelly para ser conservador.
        """
        if payoff <= 0 or total_buffer <= 0:
            return 0, 0, 0.0
            
        wr = win_rate_percent / 100.0
        
        # Fórmula de Kelly: W - ((1-W)/R)
        kelly_full = wr - ((1 - wr) / payoff)
        
        # Usamos Half-Kelly (metade do risco ideal) para evitar volatilidade extrema
        kelly_half = max(0.0, kelly_full / 2)
        
        if kelly_half <= 0:
            return 0, 0, 0.0
            
        # Quanto $ podemos arriscar neste trade?
        risk_budget = total_buffer * kelly_half
        
        # Traduz $ em Contratos (Lotes)
        # Ex: Risco Unitário de 1 Lote = $300 (Stop Médio)
        if risk_unit_dollars > 0:
            contracts_max = int(risk_budget / risk_unit_dollars)
            # Define um range (70% a 100% da sugestão)
            contracts_min = int(contracts_max * 0.7)
        else:
            contracts_max = 0
            contracts_min = 0
            
        # Hard Cap de Segurança (Ninguém deve operar 500 lotes do nada)
        HARD_CAP = 100
        contracts_max = min(contracts_max, HARD_CAP)
        contracts_min = min(contracts_min, HARD_CAP)
            
        return contracts_min, contracts_max, kelly_half
