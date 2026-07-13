from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault(
    "MPLCONFIGDIR", str(PROJECT_DIR / "reports" / "test_outputs" / "matplotlib_cache")
)
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
from docx import Document

from rt_tetra_cover_studio.ui import main_window as main_window_module
from rt_tetra_cover_studio.ui.main_window import MainWindow


class GuiExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_export_buttons_create_word_and_pdf_from_current_result(self) -> None:
        window = MainWindow()
        output_dir = PROJECT_DIR / "reports" / "test_outputs"
        word_path = output_dir / "gui_export.docx"
        pdf_path = output_dir / "gui_export.pdf"
        messages: list[tuple[str, str]] = []

        original_get_save_file_name = main_window_module.QFileDialog.getSaveFileName
        original_information = main_window_module.QMessageBox.information
        original_warning = main_window_module.QMessageBox.warning
        try:
            main_window_module.QMessageBox.information = _record_message(messages)
            main_window_module.QMessageBox.warning = _record_message(messages)

            window._calculate()

            self.assertIsNotNone(window.current_report_data)
            self.assertTrue(window.export_button.isEnabled())
            self.assertTrue(window.export_word_action.isEnabled())
            self.assertTrue(window.export_pdf_action.isEnabled())

            main_window_module.QFileDialog.getSaveFileName = _save_path(word_path)
            window._export_report("word")
            main_window_module.QFileDialog.getSaveFileName = _save_path(pdf_path)
            window._export_report("pdf")
        finally:
            main_window_module.QFileDialog.getSaveFileName = original_get_save_file_name
            main_window_module.QMessageBox.information = original_information
            main_window_module.QMessageBox.warning = original_warning
            window.close()

        self.assertTrue(word_path.exists())
        self.assertGreater(word_path.stat().st_size, 0)
        self.assertTrue(pdf_path.exists())
        self.assertGreater(pdf_path.stat().st_size, 0)
        self.assertEqual([message[0] for message in messages], ["导出完成", "导出完成"])

    def test_segmented_scenario_button_switches_parameter_page(self) -> None:
        window = MainWindow()
        try:
            window.scenario_buttons["tunnel"].click()
            self.app.processEvents()

            self.assertEqual(window.scenario_combo.currentData(), "tunnel")
            self.assertEqual(window.scenario_stack.currentIndex(), 1)
            self.assertTrue(window.scenario_buttons["tunnel"].isChecked())
            self.assertEqual(window.current_case_label.text(), "隧道区间标准算例")
        finally:
            window.close()

    def test_engineering_inputs_and_detailed_calculation_layout(self) -> None:
        window = MainWindow()
        try:
            self.assertIn("base_tx_power_w", window.base_fields)
            self.assertIn("mobile_receiver_sensitivity_dbm", window.base_fields)
            self.assertEqual(window.base_fields["base_tx_power_w"].suffix(), "")

            window._calculate()

            detail_text = window.calculation_details.toPlainText()
            self.assertIn("1. 有效全向辐射功率", detail_text)
            self.assertIn("3. 最大允许路径损耗", detail_text)
            self.assertIn("5. 覆盖距离求解", detail_text)
            self.assertEqual(window.result_labels["limiting_link"].text(), "上行")
        finally:
            window.close()

    def test_ground_model_switch_updates_fields_and_model(self) -> None:
        window = MainWindow()
        try:
            window.scenario_buttons["ground"].click()
            model_field = window.scenario_fields["ground"]["ground_model"]
            model_field.setCurrentIndex(model_field.findData("cost231_wi"))
            window.base_fields["frequency_mhz"].setValue(900.0)
            window.base_fields["base_height_m"].setValue(25.0)

            self.assertTrue(
                window.scenario_fields["ground"]["path_loss_exponent"].isHidden()
            )
            self.assertFalse(
                window.scenario_fields["ground"]["street_orientation_deg"].isHidden()
            )

            window._calculate()

            self.assertEqual(
                window.current_report_data["summary"]["model_name"],
                "COST231-Walfisch-Ikegami",
            )
        finally:
            window.close()

    def test_all_standard_examples_calculate_plot_and_export(self) -> None:
        scenarios = {
            "underground": ("ITU Indoor", 220.0, 222.0),
            "tunnel": ("Tunnel Model", 2191.0, 2193.0),
            "ground": ("Low-Band Calibrated Ground", 1246.0, 1248.0),
            "viaduct": (
                "Low-Band Calibrated Ground + Viaduct Calibration",
                2291.0,
                2294.0,
            ),
        }
        window = MainWindow()
        output_dir = PROJECT_DIR / "reports" / "test_outputs" / "release_acceptance"
        messages: list[tuple[str, str]] = []
        original_get_save_file_name = main_window_module.QFileDialog.getSaveFileName
        original_information = main_window_module.QMessageBox.information
        original_warning = main_window_module.QMessageBox.warning
        try:
            main_window_module.QMessageBox.information = _record_message(messages)
            main_window_module.QMessageBox.warning = _record_message(messages)

            for scenario_type, expected in scenarios.items():
                with self.subTest(scenario_type=scenario_type):
                    example_index = window.example_combo.findData(scenario_type)
                    window.example_combo.setCurrentIndex(example_index)
                    window._load_selected_example()
                    window._calculate()

                    report_data = window.current_report_data
                    self.assertIsNotNone(report_data)
                    summary = report_data["summary"]
                    self.assertEqual(summary["model_name"], expected[0])
                    self.assertGreaterEqual(summary["coverage_distance_m"], expected[1])
                    self.assertLessEqual(summary["coverage_distance_m"], expected[2])
                    self.assertEqual(summary["calibration_status"], "unverified")
                    self.assertEqual(window.result_state_label.text(), "计算完成")

                    path_loss_curve = report_data["charts"]["path_loss_curve"]
                    rssi_curve = report_data["charts"]["rssi_curve"]
                    self.assertEqual(len(path_loss_curve), 50)
                    self.assertEqual(len(rssi_curve), 50)
                    self.assertTrue(
                        all(
                            left["path_loss_db"] < right["path_loss_db"]
                            for left, right in zip(path_loss_curve, path_loss_curve[1:])
                        )
                    )
                    self.assertTrue(
                        all(
                            left["rssi_dbm"] > right["rssi_dbm"]
                            for left, right in zip(rssi_curve, rssi_curve[1:])
                        )
                    )
                    self.assertEqual(
                        len(window.path_loss_figure.axes[0].lines[0].get_xdata()), 50
                    )
                    self.assertEqual(
                        len(window.rssi_figure.axes[0].lines[0].get_xdata()), 50
                    )

                    word_path = output_dir / f"{scenario_type}_report.docx"
                    pdf_path = output_dir / f"{scenario_type}_report.pdf"
                    main_window_module.QFileDialog.getSaveFileName = _save_path(word_path)
                    window._export_report("word")
                    main_window_module.QFileDialog.getSaveFileName = _save_path(pdf_path)
                    window._export_report("pdf")

                    document = Document(word_path)
                    document_text = "\n".join(
                        paragraph.text for paragraph in document.paragraphs
                    )
                    self.assertIn("详细计算过程", document_text)
                    self.assertIn("覆盖曲线图", document_text)
                    self.assertGreaterEqual(len(document.inline_shapes), 2)

                    pdf_content = pdf_path.read_bytes()
                    self.assertEqual(pdf_content[:4], b"%PDF")
                    self.assertGreaterEqual(pdf_content.count(b"/Subtype /Image"), 2)
        finally:
            main_window_module.QFileDialog.getSaveFileName = original_get_save_file_name
            main_window_module.QMessageBox.information = original_information
            main_window_module.QMessageBox.warning = original_warning
            window.close()

        self.assertEqual([message[0] for message in messages], ["导出完成"] * 8)


def _save_path(path: Path):
    return staticmethod(lambda *_args, **_kwargs: (str(path), ""))


def _record_message(messages: list[tuple[str, str]]):
    def recorder(_parent, title: str, message: str) -> None:
        messages.append((title, message))

    return staticmethod(recorder)


if __name__ == "__main__":
    unittest.main()
