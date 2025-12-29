import math
import numpy as np
import pandas as pd

class ApexEngine:
    @staticmethod
    def calculate_health(saldo_atual, hwm_previo, fase_informada="Fase 1"):
        """
        Calcula a saúde respeitando a regra de Trailing da Apex.
        Retorna também status visuais para o Monitor de Performance.
        """
        SALDO_INICIAL_REGRA = 150000.0
        MAX_DRAWDOWN = 5000.0
        TRAVA_PROFIT = 150100.0 
        
        # 1. Define o verdadeiro HWM
        hwm_atual = max(saldo_atual, hwm_previo, SALDO_INICIAL_REGRA)
        
        # 2. Cálculo do Stop (Trailing)
        if fase_informada == "Fase 2":
            stop_base = hwm_atual - MAX_DRAWDOWN
            # Regra PA: Se subiu $5.100 (155.100), trava.
            if hwm_atual >= (SALDO_INICIAL_REGRA + 5100):
                stop_atual = TRAVA_PROFIT
            else:
                stop_atual = stop_base
        else:
            # Regra Eval: Trava em 150.100
            stop_calc = hwm_atual - MAX_DRAWDOWN
            stop_atual = min(stop_calc, SALDO_INICIAL_REGRA + 100.0)
        
        # 3. Buffer Real
        buffer = saldo_atual - stop_atual
        
        # 4. Status Visuais
        travado = stop_atual >= TRAVA_PROFIT
        status_trailing = f"Travado em ${stop_atual:,.0f}" if travado else "Móvel (Subindo)"
        
        falta_para_trava = 0.0
        if not travado:
            target_hwm = SALDO_INICIAL_REGRA + 5100
            falta_para_trava = target_hwm - hwm_atual

        return {
            "saldo": saldo_atual,
            "hwm": hwm_atual,
            "stop_atual": stop_atual,
            "buffer": max(0.0, buffer),
            "fase": fase_informada,
            "status_trailing": status_trailing,
            "falta_para_trava": max(0.0, falta_para_trava)
        }

class RiskEngine:
    @staticmethod
    def calculate_lives(total_buffer, custo_stop, contas_ativas):
        """Calcula quantas 'vidas' restam baseadas no custo médio do stop."""
        if custo_stop <= 0: return 0.0
        risco_grupo = custo_stop * (contas_ativas if contas_ativas > 0 else 1)
        return total_buffer / risco_grupo

    @staticmethod
    def calculate_ruin(win_rate, avg_win, avg_loss, capital, trades_results=None):
        """
        🔥 APEX-SHIELD PROTOCOL (Risco de Ruína v2.1 - Calibrado) 🔥
        Calcula a Probabilidade de Ruína Operacional com ajustes de realidade:
        1. Penalidade por Baixa Amostragem (Suavizada para 80% confiança).
        2. Volatilidade das Perdas (Suavizada para 0.3 StdDev).
        3. Sequência de Agrupamento (Trigger em -1.2 Z-Score).
        """
        if capital <= 0: return 100.0
        if avg_loss == 0 and avg_win == 0: return 0.0
        
        n_trades = len(trades_results) if trades_results else 0
        wr_raw = win_rate / 100.0
        
        # --- AJUSTE 1: PENALIDADE DE AMOSTRAGEM (Confidence Penalty) ---
        # Reduzimos de 1.96 (muito rígido) para 1.28 (padrão de mercado para <100 trades)
        if 0 < n_trades < 100:
            margin_error = 1.28 * math.sqrt((wr_raw * (1 - wr_raw)) / n_trades)
            p_adjusted = max(0.1, wr_raw - margin_error)
        else:
            p_adjusted = wr_raw

        q_adjusted = 1.0 - p_adjusted

        # --- AJUSTE 2: STRESS LOSS (Volatilidade de Perda) ---
        loss_input = abs(avg_loss)
        
        if trades_results:
            losses_only = [x for x in trades_results if x < 0]
            if len(losses_only) > 1:
                std_dev_loss = np.std(losses_only, ddof=1)
                # Consideramos apenas 30% do desvio padrão como "gordura" de risco extra
                # Antes estava 100% (muito pessimista)
                loss_input += (std_dev_loss * 0.3)

        # Recalcula Mu (Vantagem) com os dados ajustados
        mu_stress = (p_adjusted * avg_win) - (q_adjusted * loss_input)
        
        # Se a vantagem desaparecer no cenário de estresse, risco é total
        if mu_stress <= 0: return 100.0
        
        # Variância do Sistema Estressado
        variance_stress = (p_adjusted * (avg_win**2)) + (q_adjusted * (loss_input**2)) - (mu_stress**2)
        if variance_stress <= 0: return 0.0

        # --- FÓRMULA DE DIFUSÃO ---
        try:
            arg = -2 * mu_stress * capital / variance_stress
            prob_base = math.exp(arg) * 100.0
        except:
            prob_base = 100.0

        # --- AJUSTE 3: Z-SCORE MULTIPLIER (Panic Factor) ---
        prob_final = prob_base
        z_score = RiskEngine.calculate_z_score_serial(trades_results)
        
        # Só ativa o multiplicador de pânico se o agrupamento for real (Z < -1.2)
        if z_score < -1.2:
            multiplier = 1 + (abs(z_score)) 
            prob_final = prob_base * multiplier

        return min(100.0, prob_final)

    @staticmethod
    def calculate_z_score_serial(trades_results):
        """
        Calcula o Z-Score Serial (Runs Test) para detectar sequências.
        """
        if not trades_results or len(trades_results) < 2:
            return 0.0

        # 1. Converter sequência para binário
        binary_sequence = []
        for r in trades_results:
            if r > 0: binary_sequence.append(1)
            elif r < 0: binary_sequence.append(-1)
        
        n = len(binary_sequence)
        if n < 2: return 0.0

        # 2. Contar Wins e Losses
        n_plus = binary_sequence.count(1)
        n_minus = binary_sequence.count(-1)

        if n_plus == 0 or n_minus == 0:
            return 0.0 

        # 3. Contar 'Runs'
        runs = 1
        for i in range(1, n):
            if binary_sequence[i] != binary_sequence[i-1]:
                runs += 1

        # 4. Estatística
        mu = (2 * n_plus * n_minus) / n + 1

        variance_numerator = (mu - 1) * (mu - 2)
        variance_denominator = n - 1
        
        if variance_denominator <= 0: return 0.0
        
        sigma = math.sqrt(variance_numerator / variance_denominator)

        if sigma == 0: return 0.0

        z = (runs - mu) / sigma
        
        return z

class PositionSizing:
    @staticmethod
    def calculate_limits(win_rate, payoff, capital, risco_por_trade):
        """Calcula sugestão de lote baseada em Half-Kelly."""
        if payoff <= 0 or win_rate <= 0: return 0, 0, 0.0
        w = win_rate / 100.0
        kelly_full = w - ((1.0 - w) / payoff)
        
        if kelly_full <= 0: return 0, 0, 0.0
        
        kelly_safe = kelly_full / 2.0
        risk_cash = capital * kelly_safe
        
        if risco_por_trade <= 0: return 0, 0, 0.0
        
        lote_ideal = risk_cash / risco_por_trade
        lote_min = max(1, int(lote_ideal * 0.8))
        lote_max = max(1, int(lote_ideal * 1.2))
        
        return lote_min, lote_max, kelly_safe
