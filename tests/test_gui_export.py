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
            self.assertTrue(window.export_word_button.isEnabled())
            self.assertTrue(window.export_pdf_button.isEnabled())

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


def _save_path(path: Path):
    return staticmethod(lambda *_args, **_kwargs: (str(path), ""))


def _record_message(messages: list[tuple[str, str]]):
    def recorder(_parent, title: str, message: str) -> None:
        messages.append((title, message))

    return staticmethod(recorder)


if __name__ == "__main__":
    unittest.main()
