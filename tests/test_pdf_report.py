from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rt_tetra_cover_studio.engine import calculate_coverage
from rt_tetra_cover_studio.io import calculation_result_to_dict, load_example_case
from rt_tetra_cover_studio.report import export_pdf_report


class PdfReportTest(unittest.TestCase):
    def test_export_pdf_report_from_standard_example(self) -> None:
        case_data = load_example_case(PROJECT_DIR / "examples" / "underground_standard.json")
        result = calculate_coverage(case_data["calculation_input"])
        report_data = calculation_result_to_dict(result)
        output_path = PROJECT_DIR / "reports" / "test_outputs" / "pdf_report.pdf"

        saved_path = export_pdf_report(report_data, output_path)

        self.assertTrue(saved_path.exists())
        self.assertGreater(saved_path.stat().st_size, 0)
        with saved_path.open("rb") as file:
            self.assertEqual(file.read(4), b"%PDF")


if __name__ == "__main__":
    unittest.main()
