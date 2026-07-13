from __future__ import annotations

from dataclasses import replace
import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rt_tetra_cover_studio.models import CalculationInput
from rt_tetra_cover_studio.propagation import (
    Cost231WiModel,
    ItuIndoorModel,
    LowBandGroundModel,
    TunnelModel,
    ViaductModel,
    get_model,
)
from rt_tetra_cover_studio.validation import validate_input


def base_input(**overrides: object) -> CalculationInput:
    values = {
        "frequency_mhz": 900.0,
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
        "base_height_m": 30.0,
        "mobile_height_m": 1.5,
        "scenario_type": "ground",
        "scenario_params": {
            "ground_model": "cost231_wi",
            "propagation_condition": "nlos",
            "city_type": "medium",
            "building_height_m": 20.0,
            "building_spacing_m": 50.0,
            "street_width_m": 20.0,
            "street_orientation_deg": 30.0,
            "model_correction_db": 0.0,
        },
    }
    values.update(overrides)
    return CalculationInput(**values)


def low_band_input() -> CalculationInput:
    return replace(
        base_input(),
        frequency_mhz=400.0,
        base_height_m=12.0,
        scenario_params={
            "ground_model": "low_band",
            "reference_distance_m": 10.0,
            "path_loss_exponent": 3.5,
            "model_correction_db": 2.0,
            "calibration_min_distance_m": 10.0,
            "calibration_max_distance_m": 5000.0,
            "calibration_status": "calibrated",
            "calibration_source": "independent reference fixture",
        },
    )


class PropagationReferencePointTest(unittest.TestCase):
    def test_cost231_wi_nlos_reference_point(self) -> None:
        result = Cost231WiModel().calculate_path_loss(base_input(), 1000.0)

        self.assertAlmostEqual(result.path_loss_db, 125.1717504105, places=6)
        self.assertAlmostEqual(
            result.intermediate_values["street_orientation_correction_db"],
            0.62,
            places=6,
        )
        self.assertAlmostEqual(
            result.intermediate_values["rooftop_to_street_db"],
            25.5955597058,
            places=6,
        )
        self.assertAlmostEqual(
            result.intermediate_values["multiscreen_db"],
            8.0913405159,
            places=6,
        )
        self.assertAlmostEqual(result.intermediate_values["ka"], 54.0, places=6)
        self.assertAlmostEqual(result.intermediate_values["kd"], 18.0, places=6)

    def test_cost231_wi_los_reference_point(self) -> None:
        input_data = replace(
            base_input(),
            scenario_params={
                **base_input().scenario_params,
                "propagation_condition": "los",
            },
        )

        result = Cost231WiModel().calculate_path_loss(input_data, 1000.0)

        self.assertAlmostEqual(result.path_loss_db, 101.6848501888, places=6)
        self.assertEqual(result.intermediate_values["propagation_condition"], "los")

    def test_cost231_wi_below_rooftop_reference_point(self) -> None:
        input_data = replace(
            base_input(),
            base_height_m=10.0,
            scenario_params={
                **base_input().scenario_params,
                "building_height_m": 20.0,
                "street_orientation_deg": 45.0,
                "city_type": "metropolitan",
            },
        )

        result = Cost231WiModel().calculate_path_loss(input_data, 100.0)

        self.assertAlmostEqual(result.path_loss_db, 102.5829432296, places=6)
        self.assertAlmostEqual(
            result.intermediate_values["street_orientation_correction_db"],
            3.25,
            places=6,
        )
        self.assertAlmostEqual(result.intermediate_values["ka"], 55.6, places=6)
        self.assertAlmostEqual(result.intermediate_values["kd"], 25.5, places=6)

    def test_cost231_wi_falls_back_to_free_space_loss(self) -> None:
        input_data = replace(
            base_input(),
            base_height_m=30.0,
            scenario_params={
                **base_input().scenario_params,
                "building_height_m": 3.0,
                "building_spacing_m": 100.0,
                "street_width_m": 50.0,
                "street_orientation_deg": 0.0,
            },
        )

        result = Cost231WiModel().calculate_path_loss(input_data, 20.0)

        self.assertAlmostEqual(result.path_loss_db, 57.5054501021, places=6)
        self.assertEqual(result.intermediate_values["additional_loss_db"], 0.0)

    def test_cost231_wi_rejects_distance_outside_standard_range(self) -> None:
        model = Cost231WiModel()

        with self.assertRaises(ValueError):
            model.calculate_path_loss(base_input(), 19.0)
        with self.assertRaises(ValueError):
            model.calculate_path_loss(base_input(), 5001.0)

    def test_low_band_reference_and_decade_points(self) -> None:
        model = LowBandGroundModel()
        input_data = low_band_input()

        reference = model.calculate_path_loss(input_data, 10.0)
        decade = model.calculate_path_loss(input_data, 100.0)

        self.assertAlmostEqual(reference.path_loss_db, 46.4811998266, places=6)
        self.assertAlmostEqual(decade.path_loss_db, 81.4811998266, places=6)

    def test_itu_indoor_reference_point(self) -> None:
        input_data = replace(
            low_band_input(),
            scenario_type="underground",
            scenario_params={
                "distance_power_loss_coefficient": 40.0,
                "wall_loss_db": 3.0,
                "floor_loss_db": 5.0,
            },
        )

        result = ItuIndoorModel().calculate_path_loss(input_data, 100.0)

        self.assertAlmostEqual(result.path_loss_db, 112.0411998266, places=6)

    def test_tunnel_engineering_reference_point(self) -> None:
        input_data = replace(
            low_band_input(),
            scenario_type="tunnel",
            scenario_params={
                "tunnel_width_m": 6.0,
                "tunnel_height_m": 5.5,
                "alpha_db_per_km": 8.0,
                "section_correction_db": 9.0,
                "bend_loss_db": 2.0,
                "train_blockage_loss_db": 3.0,
                "calibration_offset_db": 1.0,
                "calibration_status": "calibrated",
                "calibration_source": "independent reference fixture",
            },
        )

        result = TunnelModel().calculate_path_loss(input_data, 1000.0)

        self.assertAlmostEqual(result.path_loss_db, 107.4811998266, places=6)

    def test_viaduct_calibration_reference_point(self) -> None:
        input_data = replace(
            low_band_input(),
            scenario_type="viaduct",
            scenario_params={
                **low_band_input().scenario_params,
                "path_loss_exponent": 3.2,
                "model_correction_db": 0.0,
                "viaduct_height_m": 12.0,
                "viaduct_correction_db": -2.17,
                "train_blockage_loss_db": 3.0,
                "calibration_offset_db": 1.0,
            },
        )

        result = ViaductModel().calculate_path_loss(input_data, 100.0)

        self.assertAlmostEqual(result.path_loss_db, 78.3111998266, places=6)

    def test_ground_model_selection_is_explicit(self) -> None:
        self.assertIsInstance(get_model(low_band_input()), LowBandGroundModel)
        self.assertIsInstance(get_model(base_input()), Cost231WiModel)

    def test_cost231_wi_rejects_400_mhz(self) -> None:
        invalid = replace(base_input(), frequency_mhz=400.0)

        errors = validate_input(invalid)

        self.assertTrue(any("COST231-WI" in error and "800" in error for error in errors))

    def test_low_band_model_rejects_900_mhz(self) -> None:
        invalid = replace(low_band_input(), frequency_mhz=900.0)

        errors = validate_input(invalid)

        self.assertTrue(any("低频地面" in error for error in errors))

    def test_cost231_wi_rejects_height_outside_standard_range(self) -> None:
        invalid = replace(base_input(), base_height_m=3.0)

        errors = validate_input(invalid)

        self.assertTrue(any("基站高度" in error and "4" in error for error in errors))

    def test_low_band_rejects_invalid_calibration_range(self) -> None:
        invalid = replace(
            low_band_input(),
            scenario_params={
                **low_band_input().scenario_params,
                "calibration_min_distance_m": 100.0,
                "calibration_max_distance_m": 50.0,
            },
        )

        errors = validate_input(invalid)

        self.assertTrue(any("标定最大距离" in error for error in errors))

    def test_tunnel_requires_traceable_calibration_source(self) -> None:
        invalid = replace(
            low_band_input(),
            scenario_type="tunnel",
            scenario_params={
                "tunnel_width_m": 6.0,
                "tunnel_height_m": 5.5,
                "alpha_db_per_km": 8.0,
                "section_correction_db": 9.0,
                "calibration_status": "unverified",
                "calibration_source": "",
            },
        )

        errors = validate_input(invalid)

        self.assertTrue(any("参数或校准数据来源" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
