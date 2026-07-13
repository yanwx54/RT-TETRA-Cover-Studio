from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rt_tetra_cover_studio.engine import calculate_coverage
from rt_tetra_cover_studio.models import CalculationInput
from rt_tetra_cover_studio.validation import validate_input


def underground_input(**overrides: object) -> CalculationInput:
    data = {
        "frequency_mhz": 400.0,
        "base_tx_power_w": 25.0,
        "mobile_tx_power_w": 1.0,
        "base_antenna_gain_dbi": 9.0,
        "base_feeder_loss_db": 2.0,
        "base_other_loss_db": 3.0,
        "mobile_antenna_gain_dbi": 0.0,
        "body_loss_db": 3.0,
        "mobile_receiver_sensitivity_dbm": -103.0,
        "base_receiver_sensitivity_dbm": -112.0,
        "base_diversity_gain_db": 0.0,
        "shadow_fading_std_db": 8.0,
        "edge_coverage_probability_pct": 95.0,
        "interference_margin_db": 2.0,
        "penetration_loss_db": 10.0,
        "base_height_m": 3.0,
        "mobile_height_m": 1.5,
        "scenario_type": "underground",
        "scenario_params": {"distance_power_loss_coefficient": 40.0},
    }
    data.update(overrides)
    return CalculationInput(**data)


class BoundaryConditionsTest(unittest.TestCase):
    def test_no_effective_coverage_returns_min_distance_warning(self) -> None:
        input_data = underground_input(
            base_tx_power_w=0.001,
            mobile_tx_power_w=0.001,
            base_antenna_gain_dbi=0.0,
            mobile_receiver_sensitivity_dbm=-10.0,
            base_receiver_sensitivity_dbm=-10.0,
            shadow_fading_std_db=0.0,
            edge_coverage_probability_pct=50.0,
            interference_margin_db=0.0,
            penetration_loss_db=0.0,
        )

        result = calculate_coverage(input_data)

        self.assertEqual(result.coverage_distance_m, 1.0)
        self.assertTrue(any("最小计算距离" in warning for warning in result.warnings))
        self.assertEqual(result.iteration_steps[0].iteration, 0)

    def test_reaches_search_upper_bound_returns_warning(self) -> None:
        input_data = underground_input(
            base_tx_power_w=1_000_000_000.0,
            mobile_tx_power_w=1_000_000_000.0,
            base_antenna_gain_dbi=20.0,
            mobile_receiver_sensitivity_dbm=-140.0,
            base_receiver_sensitivity_dbm=-140.0,
            shadow_fading_std_db=0.0,
            edge_coverage_probability_pct=50.0,
            interference_margin_db=0.0,
            penetration_loss_db=0.0,
        )

        result = calculate_coverage(input_data, max_distance_m=5000.0)

        self.assertEqual(result.coverage_distance_m, 5000.0)
        self.assertTrue(any("距离上限" in warning for warning in result.warnings))
        self.assertEqual(result.iteration_steps[0].iteration, 0)

    def test_invalid_scenario_type_is_rejected(self) -> None:
        input_data = underground_input(scenario_type="space")

        errors = validate_input(input_data)

        self.assertTrue(any("场景类型" in error for error in errors))
        with self.assertRaises(ValueError):
            calculate_coverage(input_data)

    def test_negative_scenario_parameter_is_rejected(self) -> None:
        input_data = underground_input(
            scenario_params={"distance_power_loss_coefficient": -1.0}
        )

        errors = validate_input(input_data)

        self.assertTrue(any("必须大于 0" in error for error in errors))
        with self.assertRaises(ValueError):
            calculate_coverage(input_data)

    def test_curve_points_are_monotonic(self) -> None:
        result = calculate_coverage(underground_input())
        distances = [point.distance_m for point in result.curve_points]
        path_losses = [point.path_loss_db for point in result.curve_points]
        rssis = [point.rssi_dbm for point in result.curve_points]

        self.assertTrue(
            all(left < right for left, right in zip(distances, distances[1:]))
        )
        self.assertTrue(
            all(left <= right for left, right in zip(path_losses, path_losses[1:]))
        )
        self.assertTrue(all(left >= right for left, right in zip(rssis, rssis[1:])))


if __name__ == "__main__":
    unittest.main()
