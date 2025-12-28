import math
import numpy as np
import pandas as pd

class ApexEngine:
    @staticmethod
    def calculate_health(saldo_atual, hwm_previo, fase_informada="Fase 1"):
        """
        Calcula a saúde respeitando a regra de Trailing da Apex.
        Saldo Atual: Dinheiro que você tem AGORA.
        HWM Previo: O maior saldo que o banco de dados já viu.
        """
        SALDO_INICIAL_REGRA = 150000.0
        MAX_DRAWDOWN = 5000.0
        TRAVA_PROFIT = 150100.0 
        
        # 1. Define o verdadeiro HWM (Maior entre o histórico e o agora)
        hwm_atual = max(saldo_atual, hwm_previo, SALDO_INICIAL_REGRA)
        
        # 2. Cálculo do Stop (Trailing)
        if fase_informada == "Fase 2":
            # Na PA, se tocou no objetivo, o stop trava.
            stop_base = hwm_atual - MAX_DRAWDOWN
            # Se já passou de 155.100 (Saldo Inicial + 5100), trava em 150.100
            if hwm_atual >= (SALDO_INICIAL_REGRA + 5100):
                stop_atual = TRAVA_PROFIT
            else:
                stop_atual = stop_base
        else:
            # Fase 1: Stop sobe até 150.100 e para.
            stop_calc = hwm_atual - MAX_DRAWDOWN
            stop_atual = min(stop_calc, SALDO_INICIAL_REGRA + 100.0)
        
        # 3. Buffer Real (Onde estou - Onde morro)
        buffer = saldo_atual - stop_atual
        
        return {
            "saldo": saldo_atual,
            "hwm": hwm_atual,
            "stop_atual": stop_atual,
            "buffer": max(0.0, buffer), # Buffer não pode ser negativo visualmente
            "fase": fase_informada
        }

class RiskEngine:
    @staticmethod
    def calculate_lives(total_buffer, custo_stop, contas_ativas):
        if custo_stop <= 0: return 0.0
        # O risco é multiplicado pelo número de contas (Copy Trading)
        risco_grupo = custo_stop * (contas_ativas if contas_ativas > 0 else 1)
        return total_buffer / risco_grupo

    @staticmethod
    def calculate_ruin(win_rate, avg_win, avg_loss, capital, trades_results=None):
        """
        Scan Atômico: Usa variância real dos últimos trades.
        """
        if capital <= 0: return 100.0
        if avg_loss == 0 and avg_win == 0: return 0.0
        
        p = win_rate / 100.0
        q = 1.0 - p
        mu = (p * avg_win) - (q * avg_loss)
        
        # Se a expectativa matemática é negativa, a ruína é certa (100%) no longo prazo
        if mu <= 0: return 100.0
        
        # Usa a variância real (volatilidade da sua mão) se tiver dados
        if trades_results is not None and len(trades_results) > 2:
            variance = np.var(trades_results, ddof=1)
        else:
            # Fallback para modelo teórico se tiver poucos trades
            variance = (p * (avg_win**2)) + (q * (avg_loss**2)) - (mu**2)
            
        if variance <= 0: return 0.0
        
        try:
            # Fórmula da Ruína baseada em Movimento Browniano
            arg = -2 * mu * capital / variance
            return min(100.0, math.exp(arg) * 100.0)
        except: return 100.0

class PositionSizing:
    @staticmethod
    def calculate_limits(win_rate, payoff, capital, risco_por_trade):
        if payoff <= 0 or win_rate <= 0: return 0, 0, 0.0
        w = win_rate / 100.0
        # Fórmula de Kelly
        kelly_full = w - ((1.0 - w) / payoff)
        if kelly_full <= 0: return 0, 0, 0.0
        
        # Half-Kelly (Segurança Psicológica)
        kelly_safe = kelly_full / 2.0
        risk_cash = capital * kelly_safe
        
        if risco_por_trade <= 0: return 0, 0, 0.0
        
        lote_ideal = risk_cash / risco_por_trade
        # Pisos e Tetos de Lote
        lote_min = max(1, int(lote_ideal * 0.8))
        lote_max = max(1, int(lote_ideal * 1.2))
        
        return lote_min, lote_max, kelly_safe
