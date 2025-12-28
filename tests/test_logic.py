import sys
import os
import unittest
import numpy as np

# Add repo root to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.logic import ApexEngine, RiskEngine

class TestApexLogic(unittest.TestCase):
    def test_trailing_stop_movement(self):
        # Initial state
        # Balance 150k, HWM 150k. Stop 145k.
        res = ApexEngine.calculate_health(150000, 150000)
        self.assertEqual(res['stop_atual'], 145000)
        self.assertEqual(res['buffer'], 5000)

        # Profit 2k
        # Balance 152k, HWM 152k. Stop 147k.
        res = ApexEngine.calculate_health(152000, 150000)
        self.assertEqual(res['stop_atual'], 147000)
        self.assertEqual(res['buffer'], 5000)

        # Loss 1k after Profit 2k
        # Balance 151k, HWM 152k. Stop 147k.
        res = ApexEngine.calculate_health(151000, 152000)
        self.assertEqual(res['stop_atual'], 147000)
        self.assertEqual(res['buffer'], 4000) # 151k - 147k

    def test_trailing_stop_lock(self):
        # Reaching 155,100 -> Lock at 150,100
        res = ApexEngine.calculate_health(155100, 155000)
        self.assertEqual(res['stop_atual'], 150100)
        self.assertEqual(res['status_trailing'], "TRAVADO (Breakeven)")

        # Higher Balance -> Stop stays locked
        res = ApexEngine.calculate_health(160000, 155100)
        self.assertEqual(res['stop_atual'], 150100)

        # Just below lock
        res = ApexEngine.calculate_health(155099, 155000)
        # HWM becomes 155099. Stop = 155099 - 5000 = 150099.
        self.assertEqual(res['stop_atual'], 150099)
        self.assertNotEqual(res['status_trailing'], "TRAVADO (Breakeven)")

    def test_phases(self):
        # Phase 4 starts at 160k (User Request: "fase 4: ir de 160k para 161k")
        res = ApexEngine.calculate_health(160000, 160000)
        self.assertEqual(res['fase'], "Fase 4 (Saques)")

        # Phase 3 starts at 155,100 (User Request: "fase3= dobrar o valor do colchao (ir ate 160k)")
        res = ApexEngine.calculate_health(155100, 155100)
        self.assertEqual(res['fase'], "Fase 3 (Dobrar Colchão)")

    def test_risk_ruin(self):
        # Win Rate 50%, Avg Win 100, Avg Loss 100. Expected Value = 0. Ruin = 100%.
        ruin = RiskEngine.calculate_ruin(50, 100, 100, 1000)
        self.assertEqual(ruin, 100.0)

        # Win Rate 60%, Avg Win 100, Avg Loss 100. EV = 20.
        # Variance = 0.6*100^2 + 0.4*100^2 - 20^2 = 6000 + 4000 - 400 = 9600.
        # Capital 1000.
        # arg = -2 * 20 * 1000 / 9600 = -40000 / 9600 = -4.16
        # exp(-4.16) ~= 0.015
        ruin = RiskEngine.calculate_ruin(60, 100, 100, 1000)
        self.assertLess(ruin, 5.0)

if __name__ == '__main__':
    unittest.main()
