import pandas as pd
import math

def calcular_saude_apex(saldo_inicial, pico_previo, trades_df):
    """
    Motor Apex v300: Calcula HWM, Trailing Stop e Fases.
    """
    try:
        s_ini = float(saldo_inicial)
        p_prev = float(pico_previo) if pico_previo is not None else s_ini
    except: s_ini = 150000.0; p_prev = 150000.0

    # 1. Regras (Hardcoded Lookup)
    if s_ini >= 250000:   # 300k
        dd_max = 7500.0; meta_trava = s_ini + dd_max + 100.0; meta_f3 = s_ini + 15000.0
    elif s_ini >= 100000: # 150k
        dd_max = 5000.0; meta_trava = 155100.0; meta_f3 = 161000.0
    elif s_ini >= 50000:  # 50k
        dd_max = 2500.0; meta_trava = 52600.0; meta_f3 = 56000.0
    else:                 # 25k
        dd_max = 1500.0; meta_trava = 26600.0; meta_f3 = 28000.0
        
    lucro_acc = trades_df['resultado'].sum() if not trades_df.empty else 0.0
    saldo_atual = s_ini + lucro_acc
    
    # HWM Calculation
    candidatos_pico = [s_ini, p_prev]
    if not trades_df.empty:
        trades_sorted = trades_df.sort_values('created_at')
        equity_curve = trades_sorted['resultado'].cumsum() + s_ini
        candidatos_pico.append(equity_curve.max())
    pico_real = max(candidatos_pico)

    # Trava Stop
    stop_travado = s_ini + 100.0
    if pico_real >= meta_trava:
        stop_atual = stop_travado; status_stop = "TRAVADO"
    else:
        stop_atual = pico_real - dd_max; status_stop = "TRAILING"
        
    buffer = max(0.0, saldo_atual - stop_atual)
    
    # Fases
    if stop_atual == stop_travado:
        if saldo_atual < meta_f3:
            fase = "Fase 3 (Blindagem)"; meta = meta_f3; dist = meta_f3 - saldo_atual
        else:
            fase = "Fase 4 (Império)"; meta = 999999.0; dist = 0.0
    else:
        fase = "Fase 2 (Colchão)"; meta = meta_trava; dist = meta_trava - saldo_atual
    
    return {
        "saldo_atual": saldo_atual, "stop_atual": stop_atual, "buffer": buffer,
        "hwm": pico_real, "meta": meta, "dist_meta": dist, 
        "dd_max": dd_max, "fase": fase, "status_stop": status_stop
    }

def calcular_risco_ruina(win_rate, avg_win, avg_loss, buffer_total, expectancy):
    """Calcula probabilidade de ruína baseada em movimento browniano."""
    if buffer_total <= 0: return 100.0, "QUEBRADO"
    if expectancy <= 0: return 100.0, "EDGE NEGATIVO"
    
    p = win_rate
    q = 1 - p
    variancia = (p * (avg_win - expectancy)**2) + (q * (-avg_loss - expectancy)**2)
    
    if variancia > 0:
        arg_exp = -2 * expectancy * buffer_total / variancia
        try: 
            prob = math.exp(arg_exp) * 100
            prob = min(max(prob, 0.0), 100.0)
            return prob, "Calculado"
        except: return 0.0, "Erro Math"
    return 0.0, "Sem Variância"
