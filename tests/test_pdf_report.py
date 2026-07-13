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
from rt_tetra_cover_studio.report.pdf import _table


class PdfReportTest(unittest.TestCase):
    def test_export_pdf_report_from_standard_example(self) -> None:
        case_data = load_example_case(PROJECT_DIR / "examples" / "underground_standard.json")
        result = calculate_coverage(case_data["calculation_input"])
        report_data = calculation_result_to_dict(result)
        output_path = PROJECT_DIR / "reports" / "test_outputs" / "pdf_report.pdf"

        saved_path = export_pdf_report(report_data, output_path)

        self.assertTrue(saved_path.exists())
        self.assertGreater(saved_path.stat().st_size, 0)
        content = saved_path.read_bytes()
        self.assertEqual(content[:4], b"%PDF")
        self.assertIn(b"/Subtype /Image", content)

    def test_report_table_wraps_long_model_substitution(self) -> None:
        from reportlab.lib import colors
        from reportlab.platypus import Paragraph

        long_substitution = (
            "f=400.00 MHz, d=2292.4 m, reference_distance_m=10.0000, "
            "reference_path_loss_db=44.4812, path_loss_exponent=3.2000, "
            "viaduct_correction_db=-2.1700, train_blockage_loss_db=0.0000"
        )
        table = _table(
            [["项目", "内容"], ["代入", long_substitution]], colors, [90, 330]
        )

        self.assertIsInstance(table._cellvalues[1][1], Paragraph)
        _width, height = table.wrap(420, 1000)
        self.assertGreater(height, 40)


if __name__ == "__main__":
    unittest.main()
