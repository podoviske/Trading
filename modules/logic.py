import math
import numpy as np
import pandas as pd

class ApexEngine:
    @staticmethod
    def calculate_health(saldo_atual, hwm_previo, fase_informada="Fase 1"):
        """
        Calcula a saúde respeitando a regra de Trailing da Apex e a FASE INFORMADA.
        """
        SALDO_INICIAL = 150000.0
        MAX_DRAWDOWN = 5000.0
        TRAVA_PROFIT = 150100.0 
        
        # 1. Definição do HWM (Pico)
        hwm_atual = max(saldo_atual, hwm_previo, SALDO_INICIAL)
        
        # 2. LÓGICA DE FASE CALIBRADA (A mudança cirúrgica aqui)
        if fase_informada == "Fase 2":
            # Na Fase 2 (PA), o stop TRAVA no breakeven+100 assim que o HWM atinge saldo_inicial + DD
            stop_base = hwm_atual - MAX_DRAWDOWN
            stop_atual = max(stop_base, TRAVA_PROFIT) 
            
            # Se o HWM ainda não subiu 5k desde o início, ele ainda é móvel
            if hwm_atual < (SALDO_INICIAL + MAX_DRAWDOWN):
                stop_atual = hwm_atual - MAX_DRAWDOWN
        else:
            # Fase 1: O stop máximo é 150.100.
            stop_maximo = SALDO_INICIAL + 100.0
            stop_atual = min(stop_maximo, hwm_atual - MAX_DRAWDOWN)
        
        # 3. Buffer (Oxigênio Real)
        buffer = saldo_atual - stop_atual
        
        # 4. Status para o Monitor
        falta_para_trava = 0.0
        if stop_atual < (SALDO_INICIAL + 100.0):
            fase_label = "Fase 1 (Subindo Stop)"
            falta_para_trava = (SALDO_INICIAL + MAX_DRAWDOWN) - hwm_atual
        elif saldo_atual >= 155100:
            fase_label = "Fase 3 (Aprovado?)"
        else:
            fase_label = fase_informada if fase_informada != "Fase 1" else "Fase 2 (Colchão)"
            
        return {
            "saldo": saldo_atual,
            "hwm": hwm_atual,
            "stop_atual": stop_atual,
            "buffer": max(0.1, buffer),
            "fase": fase_label,
            "status_trailing": f"Travado em ${stop_atual:,.0f}" if stop_atual >= (SALDO_INICIAL + 100.0) else "Móvel (Subindo)",
            "falta_para_trava": max(0.0, falta_para_trava)
        }

class RiskEngine:
    @staticmethod
    def calculate_lives(total_buffer, custo_stop, contas_ativas):
        if custo_stop <= 0: return 0.0
        risco_total = custo_stop * (contas_ativas if contas_ativas > 0 else 1)
        return total_buffer / risco_total

    @staticmethod
    def calculate_ruin(win_rate, avg_win, avg_loss, capital, trades_results=None):
        """Calcula ruína com Scan Atômico (Variância Real)."""
        if capital <= 100: return 100.0 # Buffer crítico = Ruína 100%
        if avg_loss == 0 and avg_win == 0: return 0.0
        
        p = win_rate / 100.0
        q = 1.0 - p
        mu = (p * avg_win) - (q * avg_loss)
        
        if mu <= 0: return 100.0
        
        if trades_results is not None and len(trades_results) > 1:
            variance = np.var(trades_results, ddof=1)
        else:
            variance = (p * (avg_win**2)) + (q * (avg_loss**2)) - (mu**2)
            
        if variance <= 0: return 0.0
        
        try:
            arg = -2 * mu * capital / variance
            return min(100.0, math.exp(arg) * 100.0)
        except: return 100.0

class PositionSizing:
    @staticmethod
    def calculate_limits(win_rate, payoff, capital, risco_por_trade):
        if payoff <= 0: return 1, 1, 0.0
        w = win_rate / 100.0
        kelly_full = w - ((1.0 - w) / payoff)
        if kelly_full <= 0: return 1, 1, 0.0
        kelly_safe = kelly_full / 2.0
        risk_cash = capital * kelly_safe
        if risco_por_trade <= 0: return 1, 1, 0.0
        lote_sug = risk_cash / risco_por_trade
        return max(1, int(lote_sug * 0.8)), max(1, int(lote_sug * 1.2)), kelly_safe
