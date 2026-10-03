import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pipeline_helper import consensus_gate, kabsch_rmsd, baseline_row
from docking_helper import vina_gate


class ReproductionMathTests(unittest.TestCase):
    def test_linker_ca_rmsd_rigid_transform(self):
        points = np.random.default_rng(5).normal(size=(10, 3))
        rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        self.assertLess(kabsch_rmsd(points, points @ rotation + [5., -3., 2.]), 1e-10)

    def test_two_angstrom_is_strict_not_inclusive(self):
        gate = consensus_gate([1.9, 2.0, 2.1])
        self.assertEqual(gate['model_pass'], [True, False, False])
        self.assertFalse(gate['candidate_pass'])
        self.assertTrue(consensus_gate([1.9, 1.99, 2.1])['candidate_pass'])

    def test_requires_three_models(self):
        with self.assertRaises(ValueError):
            consensus_gate([1.0, 1.0])
        with self.assertRaises(ValueError):
            vina_gate([-7.0])

    def test_vina_minus_six_is_inclusive(self):
        gate = vina_gate([-6.0, -6.1, -5.9])
        self.assertEqual(gate['model_pass'], [True, True, False])
        self.assertTrue(gate['candidate_pass'])

    def test_baseline_has_no_fabricated_rf_reference(self):
        baseline = baseline_row()
        self.assertFalse(baseline['rf_gate_applicable'])
        self.assertIsNone(baseline['rf_pdb_path'])
        self.assertEqual(len(baseline['full_sequence']), 439)


if __name__ == '__main__':
    unittest.main()
