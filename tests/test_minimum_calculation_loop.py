from __future__ import annotations

import unittest
import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rt_tetra_cover_studio.engine import calculate_coverage, calculate_link_budget
from rt_tetra_cover_studio.models import CalculationInput
from rt_tetra_cover_studio.propagation import Cost231WiModel, ItuIndoorModel, TunnelModel, ViaductModel
from rt_tetra_cover_studio.validation import validate_input


def sample_input() -> CalculationInput:
    return CalculationInput(
        frequency_mhz=400.0,
        base_tx_power_w=25.0,
        mobile_tx_power_w=1.0,
        base_antenna_gain_dbi=9.0,
        base_feeder_loss_db=2.0,
        base_other_loss_db=3.0,
        mobile_antenna_gain_dbi=0.0,
        body_loss_db=3.0,
        mobile_receiver_sensitivity_dbm=-103.0,
        base_receiver_sensitivity_dbm=-112.0,
        base_diversity_gain_db=0.0,
        shadow_fading_std_db=8.0,
        edge_coverage_probability_pct=95.0,
        interference_margin_db=2.0,
        penetration_loss_db=10.0,
        base_height_m=3.0,
        mobile_height_m=1.5,
        scenario_type="underground",
        scenario_params={"distance_power_loss_coefficient": 40.0},
    )


def tunnel_input() -> CalculationInput:
    return CalculationInput(
        **{
            **sample_input().__dict__,
            "scenario_type": "tunnel",
            "scenario_params": {
                "tunnel_width_m": 6.0,
                "tunnel_height_m": 5.5,
                "alpha_db_per_km": 8.0,
                "section_correction_db": 9.0,
                "calibration_status": "unverified",
                "calibration_source": "test fixture",
            },
        }
    )


def ground_input() -> CalculationInput:
    return CalculationInput(
        **{
            **sample_input().__dict__,
            "frequency_mhz": 900.0,
            "base_height_m": 25.0,
            "scenario_type": "ground",
            "scenario_params": {
                "ground_model": "cost231_wi",
                "propagation_condition": "nlos",
                "city_type": "medium",
                "building_height_m": 18.0,
                "building_spacing_m": 40.0,
                "street_width_m": 20.0,
                "street_orientation_deg": 30.0,
                "model_correction_db": 0.0,
                "calibration_status": "unverified",
                "calibration_source": "test fixture",
            },
        }
    )


def viaduct_input() -> CalculationInput:
    return CalculationInput(
        **{
            **sample_input().__dict__,
            "scenario_type": "viaduct",
            "scenario_params": {
                "ground_model": "low_band",
                "reference_distance_m": 10.0,
                "path_loss_exponent": 3.2,
                "model_correction_db": 0.0,
                "calibration_min_distance_m": 10.0,
                "calibration_max_distance_m": 5000.0,
                "calibration_status": "unverified",
                "calibration_source": "test fixture",
                "building_height_m": 18.0,
                "building_spacing_m": 40.0,
                "street_width_m": 20.0,
                "viaduct_height_m": 12.0,
                "curve_radius_m": 600.0,
                "viaduct_correction_db": -2.17,
            },
        }
    )


class MinimumCalculationLoopTest(unittest.TestCase):
    def test_link_budget(self) -> None:
        result = calculate_link_budget(sample_input())

        self.assertAlmostEqual(result.base_eirp_dbm, 47.9794, places=4)
        self.assertAlmostEqual(result.mobile_eirp_dbm, 27.0)
        self.assertAlmostEqual(result.max_path_loss_db, 117.8412, places=4)
        self.assertEqual(result.limiting_link, "上行")
        self.assertEqual(len(result.steps), 5)

    def test_validation_rejects_invalid_loss(self) -> None:
        invalid = CalculationInput(
            **{**sample_input().__dict__, "base_feeder_loss_db": -1.0}
        )

        self.assertTrue(validate_input(invalid))

    def test_itu_indoor_model_is_monotonic(self) -> None:
        model = ItuIndoorModel()
        input_data = sample_input()

        near = model.calculate_path_loss(input_data, 100.0)
        far = model.calculate_path_loss(input_data, 1000.0)

        self.assertLess(near.path_loss_db, far.path_loss_db)
        self.assertIn("distance_term_db", far.intermediate_values)

    def test_tunnel_model_is_monotonic(self) -> None:
        model = TunnelModel()
        input_data = tunnel_input()

        near = model.calculate_path_loss(input_data, 100.0)
        far = model.calculate_path_loss(input_data, 1000.0)

        self.assertLess(near.path_loss_db, far.path_loss_db)
        self.assertIn("section_correction_db", far.intermediate_values)

    def test_cost231_wi_model_is_monotonic(self) -> None:
        model = Cost231WiModel()
        input_data = ground_input()

        near = model.calculate_path_loss(input_data, 100.0)
        far = model.calculate_path_loss(input_data, 1000.0)

        self.assertLess(near.path_loss_db, far.path_loss_db)
        self.assertIn("multiscreen_db", far.intermediate_values)

    def test_viaduct_model_adds_correction(self) -> None:
        model = ViaductModel()
        input_data = viaduct_input()

        result = model.calculate_path_loss(input_data, 1000.0)

        self.assertEqual(
            result.model_name,
            "Low-Band Calibrated Ground + Viaduct Calibration",
        )
        self.assertIn("viaduct_correction_db", result.intermediate_values)

    def test_calculate_coverage_minimum_loop(self) -> None:
        result = calculate_coverage(sample_input())

        self.assertEqual(result.model_name, "ITU Indoor")
        self.assertGreater(result.coverage_distance_m, 200.0)
        self.assertLess(result.coverage_distance_m, 400.0)
        self.assertLessEqual(
            result.boundary_path_loss_db,
            result.link_budget.max_path_loss_db + 0.05,
        )
        self.assertEqual(len(result.curve_points), 50)
        self.assertGreater(len(result.iteration_steps), 0)

    def test_calculate_coverage_for_all_v1_scenarios(self) -> None:
        cases = [
            ("ITU Indoor", sample_input()),
            ("Tunnel Model", tunnel_input()),
            ("COST231-Walfisch-Ikegami", ground_input()),
            ("Low-Band Calibrated Ground + Viaduct Calibration", viaduct_input()),
        ]

        for expected_model_name, input_data in cases:
            with self.subTest(scenario=input_data.scenario_type):
                result = calculate_coverage(input_data)

                self.assertEqual(result.model_name, expected_model_name)
                self.assertGreaterEqual(result.coverage_distance_m, 1.0)
                self.assertEqual(len(result.curve_points), 50)

    def test_validation_rejects_missing_scenario_params(self) -> None:
        invalid = CalculationInput(
            **{**tunnel_input().__dict__, "scenario_params": {"tunnel_width_m": 6.0}}
        )

        errors = validate_input(invalid)

        self.assertTrue(any("tunnel_height_m" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
