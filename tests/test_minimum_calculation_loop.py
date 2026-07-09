from __future__ import annotations

import unittest
import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rt_tetra_cover_studio.engine import calculate_coverage, calculate_link_budget
from rt_tetra_cover_studio.models import CalculationInput
from rt_tetra_cover_studio.propagation import ItuIndoorModel
from rt_tetra_cover_studio.validation import validate_input


def sample_input() -> CalculationInput:
    return CalculationInput(
        frequency_mhz=400.0,
        tx_power_dbm=40.0,
        base_antenna_gain_dbi=5.0,
        feeder_loss_db=2.0,
        connector_loss_db=1.0,
        mobile_antenna_gain_dbi=0.0,
        receiver_sensitivity_dbm=-112.0,
        base_height_m=3.0,
        mobile_height_m=1.5,
        scenario_type="underground",
        scenario_params={"distance_power_loss_coefficient": 40.0},
        engineering_margin_db=8.0,
    )


class MinimumCalculationLoopTest(unittest.TestCase):
    def test_link_budget(self) -> None:
        result = calculate_link_budget(sample_input())

        self.assertAlmostEqual(result.eirp_dbm, 42.0)
        self.assertAlmostEqual(result.max_path_loss_db, 146.0)
        self.assertEqual(len(result.steps), 2)

    def test_validation_rejects_invalid_loss(self) -> None:
        invalid = CalculationInput(
            **{**sample_input().__dict__, "feeder_loss_db": -1.0}
        )

        self.assertTrue(validate_input(invalid))

    def test_itu_indoor_model_is_monotonic(self) -> None:
        model = ItuIndoorModel()
        input_data = sample_input()

        near = model.calculate_path_loss(input_data, 100.0)
        far = model.calculate_path_loss(input_data, 1000.0)

        self.assertLess(near.path_loss_db, far.path_loss_db)
        self.assertIn("distance_term_db", far.intermediate_values)

    def test_calculate_coverage_minimum_loop(self) -> None:
        result = calculate_coverage(sample_input())

        self.assertEqual(result.model_name, "ITU Indoor")
        self.assertGreater(result.coverage_distance_m, 1000.0)
        self.assertLess(result.coverage_distance_m, 1300.0)
        self.assertLessEqual(
            result.boundary_path_loss_db,
            result.link_budget.max_path_loss_db + 0.05,
        )
        self.assertEqual(len(result.curve_points), 50)
        self.assertGreater(len(result.iteration_steps), 0)


if __name__ == "__main__":
    unittest.main()
