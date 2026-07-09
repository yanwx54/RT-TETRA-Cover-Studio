from __future__ import annotations

from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from rt_tetra_cover_studio.engine import calculate_coverage
from rt_tetra_cover_studio.io import calculation_result_to_dict, load_json
from rt_tetra_cover_studio.paths import project_dir, resource_path
from rt_tetra_cover_studio.report import export_pdf_report, export_word_report
from rt_tetra_cover_studio.ui.chart_data import extract_chart_series
from rt_tetra_cover_studio.ui.input_builder import (
    EXAMPLE_CASES,
    SCENARIO_LABELS,
    SCENARIO_PARAM_LABELS,
    build_input_data,
    load_example_input,
    split_input_for_fields,
)
from rt_tetra_cover_studio.validation import validate_input


PROJECT_DIR = project_dir()
DEFAULT_CONFIG_PATH = resource_path("config", "default_parameters.json")
EXAMPLES_DIR = resource_path("examples")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RT-TETRA Cover Studio")
        self.resize(1280, 820)
        self.config = load_json(DEFAULT_CONFIG_PATH)
        self.base_fields: dict[str, QDoubleSpinBox] = {}
        self.scenario_fields: dict[str, dict[str, QDoubleSpinBox]] = {}
        self.result_labels: dict[str, QLabel] = {}
        self.current_report_data: dict | None = None

        self._build_ui()
        self._populate_defaults()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        header_layout = QHBoxLayout()
        title = QLabel("RT-TETRA Cover Studio")
        title.setObjectName("titleLabel")
        subtitle = QLabel("V1.0 单基站覆盖计算原型")
        subtitle.setObjectName("subtitleLabel")
        header_text = QVBoxLayout()
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        self.calculate_button = QPushButton("计算")
        self.calculate_button.clicked.connect(self._calculate)
        self.reset_button = QPushButton("重置默认")
        self.reset_button.clicked.connect(self._populate_defaults)
        self.export_word_button = QPushButton("导出 Word")
        self.export_word_button.setEnabled(False)
        self.export_word_button.clicked.connect(lambda: self._export_report("word"))
        self.export_pdf_button = QPushButton("导出 PDF")
        self.export_pdf_button.setEnabled(False)
        self.export_pdf_button.clicked.connect(lambda: self._export_report("pdf"))
        header_layout.addWidget(self.calculate_button)
        header_layout.addWidget(self.reset_button)
        header_layout.addWidget(self.export_word_button)
        header_layout.addWidget(self.export_pdf_button)
        root_layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        root_layout.addLayout(content_layout, stretch=1)

        input_scroll = QScrollArea()
        input_scroll.setWidgetResizable(True)
        input_scroll.setMinimumWidth(390)
        input_panel = QWidget()
        input_layout = QVBoxLayout(input_panel)
        input_layout.addWidget(self._build_base_group())
        input_layout.addWidget(self._build_scenario_group())
        input_layout.addStretch()
        input_scroll.setWidget(input_panel)
        content_layout.addWidget(input_scroll)

        result_panel = QWidget()
        result_layout = QVBoxLayout(result_panel)
        result_layout.addWidget(self._build_summary_group())
        result_layout.addWidget(self._build_charts_group(), stretch=2)
        result_layout.addWidget(self._build_steps_group(), stretch=1)
        content_layout.addWidget(result_panel, stretch=1)

        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("statusLabel")
        root_layout.addWidget(self.status_label)

        self.setCentralWidget(root)
        self._connect_input_change_handlers()
        self._apply_styles()

    def _build_base_group(self) -> QGroupBox:
        group = QGroupBox("基础参数")
        layout = QFormLayout(group)

        fields = [
            ("frequency_mhz", "工作频率 MHz", 100.0, 1000.0, 1.0),
            ("tx_power_dbm", "发射功率 dBm", -20.0, 120.0, 1.0),
            ("base_antenna_gain_dbi", "基站天线增益 dBi", -20.0, 80.0, 0.5),
            ("feeder_loss_db", "馈线损耗 dB", 0.0, 80.0, 0.5),
            ("connector_loss_db", "接头损耗 dB", 0.0, 80.0, 0.5),
            ("mobile_antenna_gain_dbi", "手台天线增益 dBi", -20.0, 30.0, 0.5),
            ("receiver_sensitivity_dbm", "接收灵敏度 dBm", -150.0, -1.0, 1.0),
            ("base_height_m", "基站高度 m", 0.1, 200.0, 0.5),
            ("mobile_height_m", "手台高度 m", 0.1, 20.0, 0.1),
            ("engineering_margin_db", "工程裕度 dB", 0.0, 80.0, 0.5),
        ]
        for key, label, minimum, maximum, step in fields:
            widget = self._spin_box(minimum, maximum, step)
            self.base_fields[key] = widget
            layout.addRow(label, widget)

        return group

    def _build_scenario_group(self) -> QGroupBox:
        group = QGroupBox("场景参数")
        layout = QVBoxLayout(group)

        self.scenario_combo = QComboBox()
        for scenario_type, label in SCENARIO_LABELS.items():
            self.scenario_combo.addItem(label, scenario_type)
        self.scenario_combo.currentIndexChanged.connect(self._on_scenario_changed)
        layout.addWidget(self.scenario_combo)

        example_layout = QHBoxLayout()
        self.example_combo = QComboBox()
        for scenario_type, (label, _) in EXAMPLE_CASES.items():
            self.example_combo.addItem(label, scenario_type)
        self.example_combo.currentIndexChanged.connect(self._on_example_selected)
        self.load_example_button = QPushButton("加载算例")
        self.load_example_button.clicked.connect(self._load_selected_example)
        example_layout.addWidget(self.example_combo)
        example_layout.addWidget(self.load_example_button)
        layout.addLayout(example_layout)

        self.scenario_stack = QStackedWidget()
        for scenario_type in SCENARIO_LABELS:
            page = QWidget()
            form = QFormLayout(page)
            self.scenario_fields[scenario_type] = {}
            for key, value in self.config["scenario_defaults"][scenario_type].items():
                widget = self._spin_box(0.0, 10000.0, 0.5)
                widget.setValue(float(value))
                self.scenario_fields[scenario_type][key] = widget
                form.addRow(SCENARIO_PARAM_LABELS.get(key, key), widget)
            self.scenario_stack.addWidget(page)
        layout.addWidget(self.scenario_stack)

        return group

    def _build_summary_group(self) -> QGroupBox:
        group = QGroupBox("计算结果")
        layout = QGridLayout(group)
        items = [
            ("coverage_distance_m", "最大覆盖距离"),
            ("coverage_level", "覆盖等级"),
            ("model_name", "传播模型"),
            ("eirp_dbm", "EIRP"),
            ("max_path_loss_db", "最大允许路径损耗"),
            ("boundary_rssi_dbm", "边界 RSSI"),
        ]
        for row, (key, label_text) in enumerate(items):
            label = QLabel(label_text)
            value = QLabel("-")
            value.setObjectName("resultValue")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.result_labels[key] = value
            layout.addWidget(label, row, 0)
            layout.addWidget(value, row, 1)
        return group

    def _build_steps_group(self) -> QGroupBox:
        group = QGroupBox("计算过程")
        layout = QVBoxLayout(group)

        self.steps_table = QTableWidget(0, 4)
        self.steps_table.setHorizontalHeaderLabels(["步骤", "公式", "代入", "结果"])
        self.steps_table.horizontalHeader().setStretchLastSection(True)
        self.steps_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.steps_table, stretch=2)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)

        self.warning_text = QTextEdit()
        self.warning_text.setReadOnly(True)
        self.warning_text.setPlaceholderText("计算提示和告警")
        self.warning_text.setMaximumHeight(110)
        layout.addWidget(self.warning_text)

        return group

    def _build_charts_group(self) -> QGroupBox:
        group = QGroupBox("覆盖曲线")
        layout = QVBoxLayout(group)

        self.chart_tabs = QTabWidget()
        self.path_loss_figure = Figure(figsize=(5, 3), tight_layout=True)
        self.path_loss_canvas = FigureCanvasQTAgg(self.path_loss_figure)
        self.rssi_figure = Figure(figsize=(5, 3), tight_layout=True)
        self.rssi_canvas = FigureCanvasQTAgg(self.rssi_figure)
        self.chart_tabs.addTab(self.path_loss_canvas, "Path Loss")
        self.chart_tabs.addTab(self.rssi_canvas, "RSSI")
        layout.addWidget(self.chart_tabs)

        self._plot_empty_charts()
        return group

    def _populate_defaults(self) -> None:
        for section in ("wireless", "height"):
            for key, value in self.config[section].items():
                self.base_fields[key].setValue(float(value))
        self.base_fields["engineering_margin_db"].setValue(
            float(self.config["engineering_margin_db"])
        )
        self._on_scenario_changed()

    def _on_scenario_changed(self) -> None:
        self.scenario_stack.setCurrentIndex(self.scenario_combo.currentIndex())
        scenario_type = self.scenario_combo.currentData()
        example_index = self.example_combo.findData(scenario_type)
        if example_index >= 0:
            self.example_combo.blockSignals(True)
            self.example_combo.setCurrentIndex(example_index)
            self.example_combo.blockSignals(False)
        self._invalidate_report_data()

    def _on_example_selected(self) -> None:
        scenario_type = self.example_combo.currentData()
        scenario_index = self.scenario_combo.findData(scenario_type)
        if scenario_index >= 0:
            self.scenario_combo.blockSignals(True)
            self.scenario_combo.setCurrentIndex(scenario_index)
            self.scenario_stack.setCurrentIndex(scenario_index)
            self.scenario_combo.blockSignals(False)
        self._invalidate_report_data()

    def _load_selected_example(self) -> None:
        input_data = load_example_input(EXAMPLES_DIR, self.example_combo.currentData())
        self._apply_input_data(input_data)
        self._invalidate_report_data()
        self.status_label.setText("已加载标准算例")

    def _calculate(self) -> None:
        try:
            input_data = self._build_current_input()
            validation_errors = validate_input(input_data)
            if validation_errors:
                self._invalidate_report_data()
                self._show_validation_errors(validation_errors)
                return
            result = calculate_coverage(input_data)
            serialized = calculation_result_to_dict(result)
        except Exception as exc:
            self._invalidate_report_data()
            QMessageBox.warning(self, "计算失败", str(exc))
            self.status_label.setText("计算失败")
            return

        self._show_result(serialized)
        self.current_report_data = serialized
        self._set_export_buttons_enabled(True)
        self.status_label.setText("计算完成")

    def _build_current_input(self):
        scenario_type = self.scenario_combo.currentData()
        field_values = {key: widget.value() for key, widget in self.base_fields.items()}
        scenario_values = {
            key: widget.value()
            for key, widget in self.scenario_fields[scenario_type].items()
        }
        return build_input_data(
            config=self.config,
            scenario_type=scenario_type,
            field_values=field_values,
            scenario_values=scenario_values,
        )

    def _apply_input_data(self, input_data) -> None:
        scenario_index = self.scenario_combo.findData(input_data.scenario_type)
        if scenario_index >= 0:
            self.scenario_combo.setCurrentIndex(scenario_index)
        base_values, scenario_values = split_input_for_fields(input_data)
        for key, value in base_values.items():
            if key in self.base_fields:
                self.base_fields[key].setValue(float(value))
        for key, value in scenario_values.items():
            field = self.scenario_fields[input_data.scenario_type].get(key)
            if field is not None:
                field.setValue(float(value))

    def _show_validation_errors(self, errors: list[str]) -> None:
        message = "\n".join(errors)
        self.warning_text.setPlainText(message)
        self.status_label.setText("输入参数有误")
        QMessageBox.warning(self, "输入参数有误", message)

    def _show_result(self, serialized: dict) -> None:
        summary = serialized["summary"]
        self.result_labels["coverage_distance_m"].setText(
            f"{summary['coverage_distance_m']:.1f} m"
        )
        self.result_labels["coverage_level"].setText(str(summary["coverage_level"]))
        self.result_labels["model_name"].setText(str(summary["model_name"]))
        self.result_labels["eirp_dbm"].setText(f"{summary['eirp_dbm']:.2f} dBm")
        self.result_labels["max_path_loss_db"].setText(
            f"{summary['max_path_loss_db']:.2f} dB"
        )
        self.result_labels["boundary_rssi_dbm"].setText(
            f"{summary['boundary_rssi_dbm']:.2f} dBm"
        )

        steps = serialized["details"]["calculation_steps"]
        self.steps_table.setRowCount(len(steps))
        for row, step in enumerate(steps):
            values = [
                step["name"],
                step["formula"],
                step["substitution"],
                f"{step['result']:.2f} {step['unit']}",
            ]
            for column, value in enumerate(values):
                self.steps_table.setItem(row, column, QTableWidgetItem(str(value)))
        self.steps_table.resizeColumnsToContents()

        warnings = summary["warnings"]
        self.warning_text.setPlainText("\n".join(warnings) if warnings else "无告警")
        self._plot_charts(serialized["charts"])

    def _export_report(self, report_type: str) -> None:
        if self.current_report_data is None:
            QMessageBox.warning(self, "无法导出", "请先完成一次计算。")
            return

        if report_type == "word":
            title = "导出 Word 报告"
            default_name = "rt_tetra_cover_report.docx"
            file_filter = "Word 文档 (*.docx)"
            suffix = ".docx"
            exporter = export_word_report
        else:
            title = "导出 PDF 报告"
            default_name = "rt_tetra_cover_report.pdf"
            file_filter = "PDF 文件 (*.pdf)"
            suffix = ".pdf"
            exporter = export_pdf_report

        default_path = str(PROJECT_DIR / "reports" / default_name)
        selected_path, _ = QFileDialog.getSaveFileName(self, title, default_path, file_filter)
        if not selected_path:
            return
        output_path = Path(selected_path)
        if output_path.suffix.lower() != suffix:
            output_path = output_path.with_suffix(suffix)

        try:
            saved_path = exporter(self.current_report_data, output_path)
        except Exception as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            self.status_label.setText("导出失败")
            return

        QMessageBox.information(self, "导出完成", f"报告已保存：{saved_path}")
        self.status_label.setText(f"报告已导出：{saved_path.name}")

    def _connect_input_change_handlers(self) -> None:
        for field in self.base_fields.values():
            field.valueChanged.connect(self._invalidate_report_data)
        for fields in self.scenario_fields.values():
            for field in fields.values():
                field.valueChanged.connect(self._invalidate_report_data)

    def _invalidate_report_data(self, *_unused: object) -> None:
        self.current_report_data = None
        self._set_export_buttons_enabled(False)

    def _set_export_buttons_enabled(self, enabled: bool) -> None:
        self.export_word_button.setEnabled(enabled)
        self.export_pdf_button.setEnabled(enabled)

    def _plot_empty_charts(self) -> None:
        self._draw_chart(
            self.path_loss_figure,
            self.path_loss_canvas,
            title="Path Loss - Distance",
            x_values=[],
            y_values=[],
            y_label="Path Loss (dB)",
        )
        self._draw_chart(
            self.rssi_figure,
            self.rssi_canvas,
            title="RSSI - Distance",
            x_values=[],
            y_values=[],
            y_label="RSSI (dBm)",
        )

    def _plot_charts(self, charts: dict) -> None:
        series = extract_chart_series(charts)
        self._draw_chart(
            self.path_loss_figure,
            self.path_loss_canvas,
            title="Path Loss - Distance",
            x_values=series["distance_m"],
            y_values=series["path_loss_db"],
            y_label="Path Loss (dB)",
            boundary_x=series["boundary_distance_m"],
            boundary_y=series["boundary_path_loss_db"],
        )
        self._draw_chart(
            self.rssi_figure,
            self.rssi_canvas,
            title="RSSI - Distance",
            x_values=series["distance_m"],
            y_values=series["rssi_dbm"],
            y_label="RSSI (dBm)",
            boundary_x=series["boundary_distance_m"],
            boundary_y=series["boundary_rssi_dbm"],
        )

    def _draw_chart(
        self,
        figure: Figure,
        canvas: FigureCanvasQTAgg,
        *,
        title: str,
        x_values: list[float],
        y_values: list[float],
        y_label: str,
        boundary_x: float | None = None,
        boundary_y: float | None = None,
    ) -> None:
        figure.clear()
        axis = figure.add_subplot(111)
        axis.set_title(title)
        axis.set_xlabel("Distance (m)")
        axis.set_ylabel(y_label)
        axis.grid(True, linestyle="--", alpha=0.35)

        if x_values and y_values:
            axis.plot(x_values, y_values, color="#1769aa", linewidth=1.8)
        if boundary_x is not None and boundary_y is not None:
            axis.axvline(boundary_x, color="#c62828", linestyle="--", linewidth=1.1)
            axis.scatter([boundary_x], [boundary_y], color="#c62828", zorder=3)
            axis.annotate(
                "Boundary",
                xy=(boundary_x, boundary_y),
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=9,
                color="#c62828",
            )

        canvas.draw_idle()

    def _spin_box(self, minimum: float, maximum: float, step: float) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setDecimals(3)
        widget.setSingleStep(step)
        widget.setAlignment(Qt.AlignRight)
        return widget

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 13px;
            }
            #titleLabel {
                font-size: 20px;
                font-weight: 600;
            }
            #subtitleLabel, #statusLabel {
                color: #59636e;
            }
            QGroupBox {
                font-weight: 600;
                border: 1px solid #c8d0d8;
                border-radius: 6px;
                margin-top: 12px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                min-width: 96px;
                min-height: 32px;
            }
            #resultValue {
                font-weight: 600;
            }
            """
        )


def run() -> int:
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
