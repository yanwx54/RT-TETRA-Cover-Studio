from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rt_tetra_cover_studio.engine import calculate_coverage
from rt_tetra_cover_studio.io import load_json
from rt_tetra_cover_studio.ui.input_builder import build_input_data


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


if __name__ == "__main__":
    unittest.main()
