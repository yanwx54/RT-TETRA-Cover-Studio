from __future__ import annotations

import unittest
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rt_tetra_cover_studio.engine import calculate_coverage
from rt_tetra_cover_studio.io import (
    calculation_result_to_dict,
    load_example_case,
    load_json,
    save_calculation_result,
)


EXAMPLE_FILES = [
    "underground_standard.json",
    "tunnel_standard.json",
    "ground_standard.json",
    "viaduct_standard.json",
]


class ExampleCasesTest(unittest.TestCase):
    def test_default_config_has_required_sections(self) -> None:
        config = load_json(PROJECT_DIR / "config" / "default_parameters.json")

        self.assertIn("wireless", config)
        self.assertIn("height", config)
        self.assertIn("solver", config)
        self.assertIn("scenario_defaults", config)
        self.assertEqual(
            {"underground", "tunnel", "ground", "viaduct"},
            set(config["scenario_defaults"]),
        )

    def test_coverage_levels_are_ordered(self) -> None:
        levels = load_json(PROJECT_DIR / "config" / "coverage_levels.json")["levels"]

        self.assertEqual(["优", "良", "可用", "边缘覆盖"], [level["name"] for level in levels])
        self.assertEqual([-85.0, -95.0, -105.0, None], [level["min_rssi_dbm"] for level in levels])

    def test_all_standard_examples_can_calculate(self) -> None:
        for filename in EXAMPLE_FILES:
            with self.subTest(filename=filename):
                case_data = load_example_case(PROJECT_DIR / "examples" / filename)
                result = calculate_coverage(case_data["calculation_input"])
                expected = case_data["expected"]
                expected_range = expected["coverage_distance_m"]

                self.assertEqual(result.model_name, expected["model_name"])
                self.assertGreaterEqual(result.coverage_distance_m, expected_range["min"])
                self.assertLessEqual(result.coverage_distance_m, expected_range["max"])
                self.assertEqual(len(result.curve_points), 50)

    def test_calculation_result_serializes_for_gui_and_report(self) -> None:
        case_data = load_example_case(PROJECT_DIR / "examples" / "underground_standard.json")
        result = calculate_coverage(case_data["calculation_input"])
        serialized = calculation_result_to_dict(result)

        self.assertEqual(
            {"input", "summary", "details", "charts", "report_sections"},
            set(serialized),
        )
        self.assertEqual(serialized["summary"]["model_name"], "ITU Indoor")
        self.assertIn("path_loss_curve", serialized["charts"])
        self.assertIn("rssi_curve", serialized["charts"])
        self.assertEqual(len(serialized["charts"]["path_loss_curve"]), 50)
        self.assertEqual(len(serialized["charts"]["rssi_curve"]), 50)
        self.assertGreaterEqual(len(serialized["report_sections"]), 5)

    def test_save_calculation_result_writes_json(self) -> None:
        case_data = load_example_case(PROJECT_DIR / "examples" / "underground_standard.json")
        result = calculate_coverage(case_data["calculation_input"])
        output_path = PROJECT_DIR / "reports" / "test_outputs" / "underground_result.json"

        saved_path = save_calculation_result(result, output_path)
        saved_data = load_json(saved_path)

        self.assertEqual(saved_data["summary"]["model_name"], "ITU Indoor")
        self.assertIn("coverage_boundary", saved_data["charts"])


if __name__ == "__main__":
    unittest.main()
