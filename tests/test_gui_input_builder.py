from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rt_tetra_cover_studio.engine import calculate_coverage
from rt_tetra_cover_studio.io import calculation_result_to_dict, load_json
from rt_tetra_cover_studio.ui.chart_data import extract_chart_series
from rt_tetra_cover_studio.ui.input_builder import (
    build_input_data,
    load_example_input,
    split_input_for_fields,
)


class GuiInputBuilderTest(unittest.TestCase):
    def test_build_input_data_uses_selected_scenario_defaults(self) -> None:
        config = load_json(PROJECT_DIR / "config" / "default_parameters.json")

        input_data = build_input_data(
            config=config,
            scenario_type="tunnel",
            field_values={"tx_power_dbm": 41.0},
            scenario_values={"alpha_db_per_km": 9.0},
        )

        self.assertEqual(input_data.scenario_type, "tunnel")
        self.assertEqual(input_data.tx_power_dbm, 41.0)
        self.assertEqual(input_data.scenario_params["alpha_db_per_km"], 9.0)
        self.assertIn("tunnel_width_m", input_data.scenario_params)

    def test_built_input_can_calculate(self) -> None:
        config = load_json(PROJECT_DIR / "config" / "default_parameters.json")

        input_data = build_input_data(
            config=config,
            scenario_type="ground",
            field_values={},
            scenario_values={},
        )
        result = calculate_coverage(input_data)

        self.assertEqual(result.model_name, "COST231-Walfisch-Ikegami")
        self.assertGreater(result.coverage_distance_m, 1.0)

    def test_load_example_input_for_gui(self) -> None:
        input_data = load_example_input(PROJECT_DIR / "examples", "viaduct")

        self.assertEqual(input_data.scenario_type, "viaduct")
        self.assertIn("viaduct_height_m", input_data.scenario_params)

    def test_split_input_for_fields(self) -> None:
        input_data = load_example_input(PROJECT_DIR / "examples", "tunnel")

        base_values, scenario_values = split_input_for_fields(input_data)

        self.assertEqual(base_values["frequency_mhz"], 400.0)
        self.assertEqual(base_values["engineering_margin_db"], 8.0)
        self.assertEqual(scenario_values["tunnel_width_m"], 6.0)

    def test_extract_chart_series_for_gui(self) -> None:
        config = load_json(PROJECT_DIR / "config" / "default_parameters.json")
        input_data = build_input_data(
            config=config,
            scenario_type="underground",
            field_values={},
            scenario_values={},
        )
        serialized = calculation_result_to_dict(calculate_coverage(input_data))

        series = extract_chart_series(serialized["charts"])

        self.assertEqual(50, len(series["distance_m"]))
        self.assertEqual(50, len(series["path_loss_db"]))
        self.assertEqual(50, len(series["rssi_dbm"]))
        self.assertGreater(series["boundary_distance_m"], 0)
        self.assertGreater(series["boundary_path_loss_db"], 0)


if __name__ == "__main__":
    unittest.main()
