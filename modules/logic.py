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
        if saldo_atual >= 160000:
            fase_label = "Fase 4 (Saques)"
            meta_proxima = 161000 # Meta inicial de saque
        elif saldo_atual >= 155100:
            fase_label = "Fase 3 (Dobrar Colchão)"
            meta_proxima = 160000
        else:
            fase_label = fase_informada # Ex: "Fase 2 (PA)" ou "Fase 1"
            if fase_informada and "Fase 1" in fase_informada:
                meta_proxima = 159000
            else:
                meta_proxima = 155100
            
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
        if capital <= 0: return 100.0
        
        p = win_rate / 100.0
        q = 1.0 - p
        mu = (p * avg_win) - (q * avg_loss)
        
        # Se a expectativa matemática é negativa ou zero, a ruína é certa (100%) no longo prazo
        if mu <= 0: return 100.0
        
        # Variância real capturando o "dia de fúria" ou stops esticados
        variance = 0.0
        if trades_results is not None and len(trades_results) > 1:
            # Usa ddof=1 para estimativa imparcial da variância da amostra
            variance = np.var(trades_results, ddof=1)
        
        # Fallback se não houver trades suficientes ou variância for 0
        if variance == 0:
            variance = (p * (avg_win**2)) + (q * (avg_loss**2)) - (mu**2)
            
        if variance <= 0: return 0.0 # Caso impossível matematicamente se houver wins/losses, mas evita div/0
        
        # Fórmula de Risco de Ruína (Difusão Aproximada)
        # Ruin = exp(-2 * mu * Capital / Variance)
        # Onde Capital é a distância até o stop (Buffer)
        try:
            arg = -2 * mu * capital / variance
            return min(100.0, math.exp(arg) * 100.0)
        except: 
            return 100.0
            
    @staticmethod
    def calculate_system_zscore(win_rate, wins, losses):
        """
        Calcula o Z-Score do Sistema (Teste de Sequência / Runs Test).
        Avalia se a distribuição de vitórias/derrotas é aleatória ou se há dependência.
        Z > 1.96: Probabilidade de clusters (sequências) maior que o aleatório (Momentum?).
        Z < -1.96: Probabilidade de alternância maior que o aleatório (Reversão à média?).
        """
        total_trades = wins + losses
        if total_trades < 30: return 0.0 # Amostra pequena
        
        # Cálculo simplificado de Z-Score para sequências (Runs Test pode ser complexo, 
        # aqui usaremos uma aproximação baseada na probabilidade de vitórias)
        
        # Na verdade, o usuário geralmente quer saber o Z-Score da Expectativa vs Desvio Padrão?
        # Ou o Z-Score estatístico de "confiança" no sistema?
        # Vamos implementar o Z-Score clássico de performance: (Média - 0) / ErroPadrão?
        # Não, vamos usar o Z-Score de Sequência que é comum em trading.
        
        # Fórmula Z = (R - E) / S
        # R = Número total de runs (sequências de W ou L consecutivas)
        # E = Expectativa de runs = 2*W*L / (W+L) + 1
        # S = Desvio padrão dos runs
        
        # Precisaríamos da lista de trades ordenada para calcular R.
        # Como não temos a lista ordenada cronologicamente garantida aqui (apenas totais),
        # não podemos calcular o Z-Score de sequência exato sem a lista.
        
        # Vamos retornar 0 por enquanto se não tivermos a lista, 
        # mas na view podemos passar a lista.
        return 0.0

    @staticmethod
    def calculate_zscore_streak(trade_sequence):
        """
        Calcula o Z-Score baseado na sequência de trades (W/L).
        trade_sequence: Lista de resultados (positivos=Win, negativos=Loss)
        """
        if not trade_sequence or len(trade_sequence) < 30:
            return 0.0
            
        wins = sum(1 for x in trade_sequence if x > 0)
        losses = sum(1 for x in trade_sequence if x <= 0)
        N = wins + losses
        
        if wins == 0 or losses == 0: return 0.0
        
        # Contar Runs (R)
        runs = 1
        current_sign = 1 if trade_sequence[0] > 0 else -1
        for t in trade_sequence[1:]:
            sign = 1 if t > 0 else -1
            if sign != current_sign:
                runs += 1
                current_sign = sign
                
        # Expectativa (E)
        E = (2 * wins * losses) / N + 1
        
        # Desvio Padrão (S)
        numerator = (2 * wins * losses) * (2 * wins * losses - N)
        denominator = (N**2) * (N - 1)
        if denominator == 0: return 0.0
        S = math.sqrt(numerator / denominator)
        
        if S == 0: return 0.0
        
        Z = (runs - E) / S
        return Z

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
