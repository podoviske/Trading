import math

# ==============================================================================
# 1. MOTOR APEX (Regra Fixa 150k)
# ==============================================================================
class ApexEngine:
    """
    Motor especialista na regra de 150k da Apex.
    """
    STARTING_BALANCE = 150000.0
    MAX_DRAWDOWN = 5000.0
    LOCK_THRESHOLD = 155100.0  
    LOCKED_STOP_VALUE = 150100.0

    @staticmethod
    def calculate_health(saldo_atual, hwm_previo):
        hwm_real = max(saldo_atual, hwm_previo)
        
        # Lógica de Trava (Lock)
        if hwm_real >= ApexEngine.LOCK_THRESHOLD:
            stop_atual = ApexEngine.LOCKED_STOP_VALUE
            status_trailing = "TRAVADO (Fixo)"
            falta = 0.0
        else:
            stop_atual = hwm_real - ApexEngine.MAX_DRAWDOWN
            status_trailing = "MÓVEL (Trailing)"
            falta = ApexEngine.LOCK_THRESHOLD - hwm_real
            
        buffer = max(0.0, saldo_atual - stop_atual)
        
        # Fases
        if saldo_atual < ApexEngine.LOCK_THRESHOLD:
            fase = "Fase 2 (Colchão)"
            meta_prox = ApexEngine.LOCK_THRESHOLD
        elif saldo_atual < 161000.0:
            fase = "Fase 3 (Blindagem)"
            meta_prox = 161000.0
        else:
            fase = "Fase 4 (Império)"
            meta_prox = 1000000.0
            
        return {
            "saldo": saldo_atual,
            "hwm": hwm_real,
            "stop_atual": stop_atual,
            "buffer": buffer,
            "fase": fase,
            "status_trailing": status_trailing,
            "falta_para_trava": max(0.0, falta),
            "meta_proxima": meta_prox
        }

# ==============================================================================
# 2. MOTOR DE RISCO (Ruína e Vidas) - ATUALIZADO
# ==============================================================================
class RiskEngine:
    
    @staticmethod
    def calculate_lives(buffer_total, risco_por_trade, qtd_contas=1):
        """
        Calcula quantas 'Vidas' (Stops Cheios) o trader tem.
        
        Lógica:
        - O risco financeiro é multiplicado pelo número de contas (Copy Trading).
        - Se você tem $5k de buffer e opera 10 contas com risco de $100 cada:
          Seu risco real é $1.000 por trade. Você tem 5 vidas, não 50.
        """
        # Proteção contra divisão por zero
        if risco_por_trade <= 0: 
            return 999.0 
            
        risco_total_grupo = risco_por_trade * max(1, qtd_contas)
        
        if risco_total_grupo <= 0:
            return 999.0
            
        vidas = buffer_total / risco_total_grupo
        return vidas

    @staticmethod
    def calculate_ruin(win_rate_percent, avg_win, avg_loss, total_buffer):
        if total_buffer <= 0: return 100.0
        if avg_loss == 0: return 0.0
        
        p = win_rate_percent / 100.0
        q = 1.0 - p
        ev = (p * avg_win) - (q * avg_loss)
        
        if ev <= 0: return 100.0
        
        s2 = (p * (avg_win - ev)**2) + (q * (-avg_loss - ev)**2)
        if s2 == 0: return 0.0
        
        try:
            arg = -2 * ev * total_buffer / s2
            ruin = math.exp(arg) * 100.0
        except OverflowError:
            ruin = 0.0
            
        return min(100.0, max(0.0, ruin))

# ==============================================================================
# 3. MOTOR KELLY
# ==============================================================================
class PositionSizing:
    @staticmethod
    def calculate_limits(win_rate_percent, payoff, total_buffer, risk_unit_dollars):
        if payoff <= 0 or total_buffer <= 0:
            return 0, 0, 0.0
            
        wr = win_rate_percent / 100.0
        kelly_full = wr - ((1 - wr) / payoff)
        kelly_half = max(0.0, kelly_full / 2)
        
        if kelly_half <= 0: return 0, 0, 0.0
            
        risk_budget = total_buffer * kelly_half
        
        if risk_unit_dollars > 0:
            contracts_max = int(risk_budget / risk_unit_dollars)
            contracts_min = int(contracts_max * 0.7)
        else:
            contracts_max = 0
            contracts_min = 0
            
        # Hard Cap em 50 contratos (Um pouco mais seguro que 100)
        HARD_CAP = 50 
        contracts_max = min(contracts_max, HARD_CAP)
        contracts_min = min(contracts_min, HARD_CAP)
            
        return contracts_min, contracts_max, kelly_half
