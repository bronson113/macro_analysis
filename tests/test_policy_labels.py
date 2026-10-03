import unittest
from macro_matrix import MacroMatrixEngine


class TestPolicyLabels(unittest.TestCase):
    def test_neutral_is_available_and_has_specific_gate_reason(self):
        result = MacroMatrixEngine().classify_situation('NEUTRAL', 'SCARCE')
        self.assertEqual(result['rates_label'], 'Policy stance: Neutral (relative to inflation and r-star)')
        self.assertNotIn('unavailable', result['rates_label'].lower())
        self.assertIn('Policy is neutral inside the neutral band', result['description'])
        self.assertNotIn('missing', result['description'])

    def test_unavailable_is_not_neutral(self):
        result = MacroMatrixEngine().classify_situation(None, None)
        self.assertEqual(result['rates_label'], 'Policy stance: Unavailable')
        self.assertEqual(result['bs_label'], 'Reserve Liquidity: Unavailable')

    def test_quality_gate_preserves_restrictive_level(self):
        result = MacroMatrixEngine().classify_situation('RESTRICTIVE', 'NEUTRAL', quality='STALE')
        self.assertEqual(result['rates_label'], 'Policy stance: Restrictive')
        self.assertEqual(result['bs_label'], 'Reserve Liquidity: Neutral')
        self.assertIn('STALE', result['description'])
