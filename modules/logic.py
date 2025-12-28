import pandas as pd
import math

def calcular_saude_apex(saldo_inicial, pico_previo, trades_df):
    """
    Motor Apex v300 (Turbo): Calcula HWM, Trailing Stop, Fases Empire e Metas.
    """
    try:
        s_ini = float(saldo_inicial)
        # Se pico_previo for None ou 0, assume s_ini
        p_prev = float(pico_previo) if pico_previo and float(pico_previo) > 0 else s_ini
    except:
        s_ini = 150000.0; p_prev = 150000.0

    # 1. Regras por Tamanho de Conta (Dinâmico)
    if s_ini >= 250000:   # 300k
        dd_max = 7500.0; meta_trava = s_ini + dd_max + 100.0; meta_f3 = s_ini + 15000.0
    elif s_ini >= 100000: # 150k
        dd_max = 5000.0; meta_trava = 155100.0; meta_f3 = 161000.0
    elif s_ini >= 50000:  # 50k
        dd_max = 2500.0; meta_trava = 52600.0; meta_f3 = 56000.0
    else:                 # 25k
        dd_max = 1500.0; meta_trava = 26600.0; meta_f3 = 28000.0
        
    # 2. Calcular Saldo e Curva Real
    lucro_acc = trades_df['resultado'].sum() if not trades_df.empty else 0.0
    saldo_atual = s_ini + lucro_acc
    
    # --- LÓGICA DO PICO (HWM) ---
    candidatos_pico = [s_ini, p_prev]
    
    if not trades_df.empty:
        trades_sorted = trades_df.sort_values('created_at')
        equity_curve = trades_sorted['resultado'].cumsum() + s_ini
        pico_grafico = equity_curve.max()
        candidatos_pico.append(pico_grafico)
        
    pico_real = max(candidatos_pico)

    # 3. Lógica Trailing (Lock/Trava)
    stop_travado = s_ini + 100.0
    
    if pico_real >= meta_trava:
        stop_atual = stop_travado
        status_stop = "TRAVADO (LOCK)"
    else:
        stop_atual = pico_real - dd_max
        status_stop = "MÓVEL (TRAILING)"
        
    buffer = max(0.0, saldo_atual - stop_atual)
    
    # 4. Fases Empire Builder
    if stop_atual == stop_travado:
        if saldo_atual < meta_f3:
            fase_nome = "Fase 3 (Blindagem)"; status_fase = "Rumo aos 161k"
            meta_global = meta_f3; distancia_meta = meta_f3 - saldo_atual
        else:
            fase_nome = "Fase 4 (Império)"; status_fase = "Liberado Saque"
            meta_global = 999999.0; distancia_meta = 0.0
    else:
        fase_nome = "Fase 2 (Colchão)"; status_fase = "Buscando Trava Stop"
        meta_global = meta_trava; distancia_meta = meta_trava - saldo_atual
    
    return {
        "saldo_atual": saldo_atual, "stop_atual": stop_atual, "buffer": buffer,
        "hwm": pico_real, "meta_global": meta_global, "distancia_meta": distancia_meta, 
        "dd_max": dd_max, "lock_threshold": meta_trava, "stop_travado": stop_travado,
        "fase_nome": fase_nome, "status_fase": status_fase, "status_stop": status_stop
    }

def calcular_risco_ruina(win_rate, avg_win, avg_loss, buffer_total, expectancy):
    """Calcula probabilidade de ruína (Movimento Browniano)"""
    if buffer_total <= 0: return 100.0, "QUEBRADO"
    if expectancy <= 0: return 100.0, "EDGE NEGATIVO"
    
    p = win_rate
    q = 1 - p
    
    # Variância do sistema
    variancia = (p * (avg_win - expectancy)**2) + (q * (-avg_loss - expectancy)**2)
    
    if variancia > 0:
        arg_exp = -2 * expectancy * buffer_total / variancia
        try: 
            prob = math.exp(arg_exp) * 100
            prob = min(max(prob, 0.0), 100.0)
            status = "Zona de Segurança" if prob < 1 else ("Risco Moderado" if prob < 5 else "CRÍTICO")
            return prob, status
        except: return 0.0, "Erro Cálculo"
    return 0.0, "Sem Variância"
