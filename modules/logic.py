import math
import numpy as np
import pandas as pd

class ApexEngine:
    @staticmethod
    def calculate_health(saldo_atual, hwm_previo, fase_informada="Fase 2"):
        """
        Calcula a saúde respeitando a regra Apex: Stop trava em 150.100 apenas ao atingir 155.100.
        """
        SALDO_INICIAL = 150000.0
        MAX_DRAWDOWN = 5000.0
        TRAVA_PROFIT = 150100.0 
        GATILHO_TRAVA = 155100.0 # Meta Apex para travar o stop
        
        # 1. MARCAR O HWM (High Water Mark) - Prioridade 1
        hwm_atual = max(saldo_atual, hwm_previo, SALDO_INICIAL)
        
        # 2. MOSTRAR FASE E BUFFER REAL - Prioridade 2
        # Lógica Apex: O stop só trava se o PICO atingiu o gatilho
        if hwm_atual >= GATILHO_TRAVA:
            stop_atual = TRAVA_PROFIT
            status_trail = "TRAVADO (Breakeven)"
        else:
            stop_atual = hwm_atual - MAX_DRAWDOWN
            status_trail = "MÓVEL (Trailing)"
            
        buffer = saldo_atual - stop_atual
        
        # Definição das Metas Customizadas (Fases 3 e 4)
        if saldo_atual >= 161000:
            fase_label = "Fase 4 (Saques)"
            meta_proxima = 162000
        elif saldo_atual >= 160000:
            fase_label = "Fase 3 (Dobrar Colchão)"
            meta_proxima = 161000
        else:
            fase_label = fase_informada # Ex: "Fase 2 (PA)"
            meta_proxima = 160000
            
        return {
            "saldo": saldo_atual,
            "hwm": hwm_atual,
            "stop_atual": stop_atual,
            "buffer": max(0.1, buffer),
            "fase": fase_label,
            "meta_proxima": meta_proxima,
            "status_trailing": status_trail,
            "falta_para_trava": max(0.0, GATILHO_TRAVA - hwm_atual)
        }

class RiskEngine:
    @staticmethod
    def calculate_lives(total_buffer, custo_stop, contas_ativas):
        if custo_stop <= 0: return 0.0
        risco_total = custo_stop * (contas_ativas if contas_ativas > 0 else 1)
        return total_buffer / risco_total

    @staticmethod
    def calculate_ruin(win_rate, avg_win, avg_loss, capital, trades_results=None):
        """
        3. CALIBRAR RISCO RUÍNA - Prioridade 3
        Usa o Scan Atômico (Variância Real) para refletir o perigo do buffer.
        """
        if capital <= 100: return 100.0 
        p, q = win_rate / 100.0, 1.0 - (win_rate / 100.0)
        mu = (p * avg_win) - (q * avg_loss)
        
        if mu <= 0: return 100.0
        
        # Variância real capturando o "dia de fúria" ou stops esticados
        if trades_results and len(trades_results) > 1:
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
        """
        4. CALIBRAR Z-SCORE / KELLY - Prioridade 4
        """
        if payoff <= 0 or risco_por_trade <= 0: return 1, 1, 0.0
        w = win_rate / 100.0
        kelly_safe = (w - ((1.0 - w) / payoff)) / 2.0
        if kelly_safe <= 0: return 1, 1, 0.0
        lote_sug = (capital * kelly_safe) / risco_por_trade
        return max(1, int(lote_sug * 0.8)), max(1, int(lote_sug * 1.2)), kelly_safe
