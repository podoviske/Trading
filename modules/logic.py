import math
import numpy as np
import pandas as pd

class ApexEngine:
    @staticmethod
    def calculate_health(saldo_atual, hwm_previo):
        """
        Calcula a saúde da conta baseada na regra de Trailing do Apex/Prop Firms.
        Regra: O Trailing Stop sobe junto com o saldo até o 'lock' (ex: +$100 acima do inicial).
        """
        # Configurações Padrão (Podem virar dinâmicas no futuro)
        SALDO_INICIAL = 150000.0
        MAX_DRAWDOWN = 5000.0
        TRAVA_PROFIT = 150100.0 # Onde o stop para de subir (geralmente Saldo Inicial + 100)
        
        # 1. Definição do HWM (High Water Mark) - O pico histórico
        # O HWM nunca pode ser menor que o saldo inicial
        hwm_atual = max(saldo_atual, hwm_previo, SALDO_INICIAL)
        
        # 2. Cálculo do Trailing Stop
        # Se o HWM for menor que a trava, o stop é HWM - DD
        # Se o HWM for maior que a trava, o stop trava em (Saldo Inicial - DD) + (Trava - Saldo Inicial)?
        # Simplificação Apex: O stop sobe até o Breakeven+100 e para.
        
        stop_loss_teorico = hwm_atual - MAX_DRAWDOWN
        stop_locked = TRAVA_PROFIT - MAX_DRAWDOWN # Ex: 150100 - 5000 = 145100? Não.
        # Correção da Regra Apex Comum:
        # O Drawdown Trailing para de subir quando atinge o Saldo Inicial (ou Saldo Inicial + 100).
        stop_maximo = SALDO_INICIAL + 100.0
        
        # O stop atual é o MÍNIMO entre (HWM - 5000) e (Stop Travado Máximo)
        # Mas ele nunca desce. Assumimos que o hwm_previo já traz o histórico.
        # Aqui recalculamos o stop baseado no pico atual.
        stop_atual = min(stop_maximo, hwm_atual - MAX_DRAWDOWN)
        
        # 3. Buffer (Oxigênio)
        buffer = saldo_atual - stop_atual
        
        # 4. Fase e Status
        fase = "Fase 1 (Construção)"
        falta_para_trava = 0.0
        
        if stop_atual < stop_maximo:
            fase = "Fase 1 (Subindo Stop)"
            falta_para_trava = (stop_maximo + MAX_DRAWDOWN) - hwm_atual
        elif saldo_atual >= 155100: # Exemplo de meta fase 2
            fase = "Fase 3 (Aprovado?)"
            falta_para_trava = 0
        elif saldo_atual > stop_maximo + MAX_DRAWDOWN:
            fase = "Fase 2 (Colchão)"
            
        return {
            "saldo": saldo_atual,
            "hwm": hwm_atual,
            "stop_atual": stop_atual,
            "buffer": buffer,
            "fase": fase,
            "status_trailing": f"Travado em ${stop_atual:,.0f}" if stop_atual >= stop_maximo else "Móvel (Subindo)",
            "falta_para_trava": max(0.0, falta_para_trava)
        }

class RiskEngine:
    @staticmethod
    def calculate_lives(total_buffer, custo_stop, contas_ativas):
        """
        Calcula quantas 'Vidas' (stops cheios) o trader tem.
        """
        if custo_stop <= 0: return 0.0
        # Se tiver mais de uma conta, o risco se multiplica se for Copy Trading
        risco_total = custo_stop * (contas_ativas if contas_ativas > 0 else 1)
        return total_buffer / risco_total

    @staticmethod
    def calculate_ruin(win_rate, avg_win, avg_loss, capital, trades_results=None):
        """
        Calcula Probabilidade de Ruína baseada em Brownian Motion.
        AGORA COM SCAN ATÔMICO: Se 'trades_results' for passado, usa o Desvio Padrão Real.
        """
        if capital <= 0: return 100.00
        if avg_loss == 0 and avg_win == 0: return 0.00
        if avg_loss == 0: return 0.00 # Só ganha
        
        p = win_rate / 100.0
        q = 1.0 - p
        
        # 1. Expectativa Matemática (Drift)
        # Quanto ganha por trade na média
        mu = (p * avg_win) - (q * avg_loss)
        
        # Se a expectativa for negativa, a ruína é certa (100%) no longo prazo
        if mu <= 0: return 100.00
        
        # 2. Variância (Volatilidade) - O SCAN ATÔMICO
        variance = 0.0
        
        if trades_results is not None and len(trades_results) > 1:
            # MODO PRECISO: Calcula a variância real do histórico
            # Isso captura aquele loss gigante que a média esconde
            variance = np.var(trades_results, ddof=1) # ddof=1 para amostra
        else:
            # MODO ESTIMADO (Fallback): Usa a fórmula binária
            # E[X^2] - (E[X])^2
            e_x2 = (p * (avg_win**2)) + (q * (avg_loss**2))
            variance = e_x2 - (mu**2)
            
        if variance == 0: return 0.0
        
        # 3. Fórmula da Ruína (Brownian Motion com Drift)
        # R = e^(-2 * mu * Z / sigma^2)
        try:
            arg = -2 * mu * capital / variance
            ruin = math.exp(arg)
            return min(100.0, ruin * 100.0)
        except OverflowError:
            return 0.0

class PositionSizing:
    @staticmethod
    def calculate_limits(win_rate, payoff, capital, risco_por_trade):
        """
        Calcula Kelly Criterion e sugere lotes.
        """
        if payoff == 0: return 0, 0, 0.0
        
        # Kelly = W - (1-W)/R
        w = win_rate / 100.0
        kelly_full = w - ((1.0 - w) / payoff)
        
        if kelly_full <= 0: return 0, 0, 0.0
        
        # Usamos Half-Kelly para segurança (fracional)
        kelly_safe = kelly_full / 2.0
        
        # Valor monetário do risco sugerido
        risk_cash = capital * kelly_safe
        
        # Conversão para Lotes (Estimada)
        # Se risco_por_trade (1 lote) custa X, quantos lotes cabem em risk_cash?
        risco_unitario = risco_por_trade # Custo de 1 lote (stop padrao)
        
        if risco_unitario <= 0: return 0, 0, 0.0
        
        lote_sug = risk_cash / risco_unitario
        
        lote_min = max(1, int(lote_sug * 0.8))
        lote_max = max(1, int(lote_sug * 1.2))
        
        return lote_min, lote_max, kelly_safe
