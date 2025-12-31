import math
import numpy as np
import pandas as pd

class ApexEngine:
    """
    Motor de cálculo de saúde das contas Apex.
    Implementa a lógica de Trailing Drawdown das mesas proprietárias.
    
    REGRAS DAS FASES:
    - Fase 1 (Avaliação): Meta $159k → passa na prova, ganha conta PA
    - Fase 2 (Conta PA): Meta $155.100 → construir colchão de $5k
    - Fase 3 (Colchão OK): Meta $160k → dobrar colchão para $10k
    - Fase 4 (Saque): Meta $161k → libera saque de $1k/mês
    
    TRAILING STOP (IGUAL para todas as fases):
    - Sobe junto com HWM até HWM atingir $155.100
    - Quando HWM >= $155.100, trava em $150.100 (imortalidade técnica)
    - Nunca mais sobe depois de travado
    """
    
    # Constantes globais da Apex
    SALDO_INICIAL = 150000.0
    MAX_DRAWDOWN = 5000.0
    TRAVA_HWM = 155100.0       # Quando HWM chega aqui, stop trava
    STOP_TRAVADO = 150100.0    # Valor do stop após travar
    
    # Metas por fase
    METAS = {
        "Fase 1": 159000.0,    # Avaliação (prova)
        "Fase 2": 155100.0,    # Construir colchão 5k
        "Fase 3": 160000.0,    # Dobrar colchão (10k)
        "Fase 4": 161000.0     # Saque liberado ($1k/mês)
    }
    
    @staticmethod
    def calculate_health(saldo_atual, hwm_previo, fase_informada="Fase 1"):
        """
        Calcula a saúde da conta respeitando a regra de Trailing da Apex.
        
        Args:
            saldo_atual: Saldo atual da conta
            hwm_previo: High Water Mark (pico) anterior registrado
            fase_informada: Fase atual da conta ("Fase 1", "Fase 2", "Fase 3", "Fase 4")
        
        Returns:
            dict: Dicionário com métricas de saúde da conta
        """
        
        # 1. Define o verdadeiro HWM (maior entre atual, anterior e inicial)
        hwm_atual = max(saldo_atual, hwm_previo, ApexEngine.SALDO_INICIAL)
        
        # 2. Cálculo do Stop (Trailing) - IGUAL PARA TODAS AS FASES
        if hwm_atual >= ApexEngine.TRAVA_HWM:
            # HWM atingiu $155.100 → Stop trava em $150.100
            stop_atual = ApexEngine.STOP_TRAVADO
            travado = True
        else:
            # Stop ainda móvel (sobe junto com HWM)
            stop_atual = hwm_atual - ApexEngine.MAX_DRAWDOWN
            travado = False
        
        # 3. Buffer Real (oxigênio disponível)
        buffer = saldo_atual - stop_atual
        
        # 4. Meta da fase atual
        meta_proxima = ApexEngine.METAS.get(fase_informada, 155100.0)
        falta_para_meta = max(0.0, meta_proxima - saldo_atual)
        
        # 5. Falta para travar o stop (se ainda não travou)
        if travado:
            falta_para_trava = 0.0
        else:
            falta_para_trava = max(0.0, ApexEngine.TRAVA_HWM - hwm_atual)
        
        # 6. Status visual
        status_trailing = f"Travado em ${ApexEngine.STOP_TRAVADO:,.0f}" if travado else "Móvel (Subindo)"
        
        return {
            "saldo": saldo_atual,
            "hwm": hwm_atual,
            "stop_atual": stop_atual,
            "buffer": max(0.0, buffer),
            "fase": fase_informada,
            "meta_proxima": meta_proxima,
            "falta_para_meta": falta_para_meta,
            "falta_para_trava": falta_para_trava,
            "status_trailing": status_trailing,
            "travado": travado
        }


class RiskEngine:
    """
    Motor de cálculo de risco operacional.
    Implementa Probabilidade de Ruína, Z-Score Serial e Vidas Reais.
    """
    
    @staticmethod
    def calculate_lives(total_buffer, custo_stop, contas_ativas):
        """
        Calcula quantas 'vidas' (tentativas) restam baseadas no custo médio do stop.
        
        Args:
            total_buffer: Buffer total disponível ($)
            custo_stop: Custo médio de um stop ($)
            contas_ativas: Número de contas ativas no grupo
        
        Returns:
            float: Número de vidas restantes
        """
        if custo_stop <= 0: 
            return 0.0
        risco_grupo = custo_stop * (contas_ativas if contas_ativas > 0 else 1)
        return total_buffer / risco_grupo

    @staticmethod
    def calculate_ruin(win_rate, avg_win, avg_loss, capital, trades_results=None):
        """
        🔥 APEX-SHIELD PROTOCOL (Risco de Ruína v2.1 - Calibrado) 🔥
        
        Calcula a Probabilidade de Ruína Operacional com ajustes de realidade:
        1. Penalidade por Baixa Amostragem (Suavizada para 80% confiança)
        2. Volatilidade das Perdas (Suavizada para 0.3 StdDev)
        3. Sequência de Agrupamento (Trigger em -1.2 Z-Score)
        
        Args:
            win_rate: Taxa de acerto (%)
            avg_win: Ganho médio ($)
            avg_loss: Perda média ($) - valor positivo
            capital: Capital/Buffer disponível ($)
            trades_results: Lista de resultados dos trades ($)
        
        Returns:
            float: Probabilidade de ruína (0-100%)
        """
        if capital <= 0: 
            return 100.0
        if avg_loss == 0 and avg_win == 0: 
            return 0.0
        
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
                loss_input += (std_dev_loss * 0.3)

        # Recalcula Mu (Vantagem) com os dados ajustados
        mu_stress = (p_adjusted * avg_win) - (q_adjusted * loss_input)
        
        # Se a vantagem desaparecer no cenário de estresse, risco é total
        if mu_stress <= 0: 
            return 100.0
        
        # Variância do Sistema Estressado
        variance_stress = (p_adjusted * (avg_win**2)) + (q_adjusted * (loss_input**2)) - (mu_stress**2)
        if variance_stress <= 0: 
            return 0.0

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
            multiplier = 1 + abs(z_score)
            prob_final = prob_base * multiplier

        return min(100.0, prob_final)

    @staticmethod
    def calculate_z_score_serial(trades_results):
        """
        Calcula o Z-Score Serial (Wald-Wolfowitz Runs Test).
        
        Mede a aleatoriedade da distribuição de vitórias e derrotas.
        - Z < -1.96: Agrupamento significativo (Hot/Cold Streaks) → PERIGO
        - Z > +1.96: Alternância excessiva → Suspeito
        - -1.96 < Z < +1.96: Distribuição aleatória normal → OK
        
        Args:
            trades_results: Lista de resultados dos trades ($)
        
        Returns:
            float: Z-Score da sequência
        """
        if not trades_results or len(trades_results) < 2:
            return 0.0

        # 1. Converter sequência para binário (ignora empates)
        binary_sequence = []
        for r in trades_results:
            if r > 0: 
                binary_sequence.append(1)
            elif r < 0: 
                binary_sequence.append(-1)
        
        n = len(binary_sequence)
        if n < 2: 
            return 0.0

        # 2. Contar Wins e Losses
        n_plus = binary_sequence.count(1)
        n_minus = binary_sequence.count(-1)

        if n_plus == 0 or n_minus == 0:
            return 0.0 

        # 3. Contar 'Runs' (sequências ininterruptas)
        runs = 1
        for i in range(1, n):
            if binary_sequence[i] != binary_sequence[i-1]:
                runs += 1

        # 4. Estatística (Wald-Wolfowitz)
        # Média esperada de runs
        mu = (2 * n_plus * n_minus) / n + 1

        # Variância
        variance_numerator = (mu - 1) * (mu - 2)
        variance_denominator = n - 1
        
        if variance_denominator <= 0: 
            return 0.0
        
        sigma = math.sqrt(variance_numerator / variance_denominator)

        if sigma == 0: 
            return 0.0

        # Z-Score
        z = (runs - mu) / sigma
        
        return z


class PositionSizing:
    """
    Motor de cálculo de tamanho de posição.
    Implementa a regra de "Vidas Reais" e Kelly Fracionário.
    """
    
    # Risco padrão MNQ: 15 pontos x $2 = $30
    RISK_MNQ = 30.0
    
    @staticmethod
    def calculate_limits(win_rate, payoff, capital, risco_por_trade):
        """
        Calcula Lote Tático para MNQ (Micro Nasdaq).
        
        Regra de Ouro: Manter sempre entre 15 a 20 vidas (tentativas) de buffer.
        - 20 vidas = Conservador (mais seguro)
        - 15 vidas = Agressivo (mais risco)
        
        Args:
            win_rate: Taxa de acerto (%)
            payoff: Razão Ganho/Perda
            capital: Buffer disponível ($)
            risco_por_trade: Risco por trade (não usado atualmente)
        
        Returns:
            tuple: (lote_min, lote_max, kelly_safe)
        """
        if capital <= 0: 
            return 0, 0, 0.0

        # 1. Cálculo Baseado em Vidas (Sobrevivência)
        # Lote Conservador (20 vidas)
        lote_min = int((capital / 20) / PositionSizing.RISK_MNQ)
        
        # Lote Agressivo (15 vidas)
        lote_max = int((capital / 15) / PositionSizing.RISK_MNQ)
        
        # Garante que seja pelo menos 1 contrato
        lote_min = max(1, lote_min)
        lote_max = max(1, lote_max)

        # 2. Kelly como referência estatística (Quarter Kelly)
        kelly_safe = 0.0
        if payoff > 0 and win_rate > 0:
            w = win_rate / 100.0
            kelly_full = w - ((1.0 - w) / payoff)
            kelly_safe = max(0.0, kelly_full / 4.0)

        return lote_min, lote_max, kelly_safe
