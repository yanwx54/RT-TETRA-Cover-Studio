from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from rt_tetra_cover_studio.engine import calculate_coverage
from rt_tetra_cover_studio.io import calculation_result_to_dict, load_json
from rt_tetra_cover_studio.ui.input_builder import (
    SCENARIO_LABELS,
    SCENARIO_PARAM_LABELS,
    build_input_data,
)


PROJECT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_DIR / "config" / "default_parameters.json"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RT-TETRA Cover Studio")
        self.resize(1180, 760)
        self.config = load_json(DEFAULT_CONFIG_PATH)
        self.base_fields: dict[str, QDoubleSpinBox] = {}
        self.scenario_fields: dict[str, dict[str, QDoubleSpinBox]] = {}
        self.result_labels: dict[str, QLabel] = {}

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
        header_layout.addWidget(self.calculate_button)
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
        result_layout.addWidget(self._build_steps_group(), stretch=1)
        content_layout.addWidget(result_panel, stretch=1)

        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("statusLabel")
        root_layout.addWidget(self.status_label)

        self.setCentralWidget(root)
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

    def _calculate(self) -> None:
        try:
            scenario_type = self.scenario_combo.currentData()
            field_values = {key: widget.value() for key, widget in self.base_fields.items()}
            scenario_values = {
                key: widget.value()
                for key, widget in self.scenario_fields[scenario_type].items()
            }
            input_data = build_input_data(
                config=self.config,
                scenario_type=scenario_type,
                field_values=field_values,
                scenario_values=scenario_values,
            )
            result = calculate_coverage(input_data)
            serialized = calculation_result_to_dict(result)
        except Exception as exc:
            QMessageBox.warning(self, "计算失败", str(exc))
            self.status_label.setText("计算失败")
            return

        self._show_result(serialized)
        self.status_label.setText("计算完成")

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
