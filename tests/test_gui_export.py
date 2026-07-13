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


def _save_path(path: Path):
    return staticmethod(lambda *_args, **_kwargs: (str(path), ""))


def _record_message(messages: list[tuple[str, str]]):
    def recorder(_parent, title: str, message: str) -> None:
        messages.append((title, message))

    return staticmethod(recorder)


if __name__ == "__main__":
    unittest.main()
