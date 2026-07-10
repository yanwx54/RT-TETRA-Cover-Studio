from __future__ import annotations

from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QFontDatabase, QResizeEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
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
UI_FONT_LOADED = False


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._ensure_ui_font()
        self.setWindowTitle("RT-TETRA Cover Studio")
        self.resize(1280, 820)
        self.setMinimumSize(1080, 720)
        self.config = load_json(DEFAULT_CONFIG_PATH)
        self.base_fields: dict[str, QDoubleSpinBox] = {}
        self.scenario_fields: dict[str, dict[str, QDoubleSpinBox]] = {}
        self.scenario_buttons: dict[str, QPushButton] = {}
        self.metric_cards: list[QFrame] = []
        self.metric_columns = 4
        self.result_labels: dict[str, QLabel] = {}
        self.current_report_data: dict | None = None

        self._build_ui()
        self._populate_defaults()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("appHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        header_layout.setSpacing(12)

        brand_mark = QLabel("RT")
        brand_mark.setObjectName("brandMark")
        brand_mark.setFixedSize(38, 38)
        brand_mark.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(brand_mark)

        title = QLabel("RT-TETRA Cover Studio")
        title.setObjectName("titleLabel")
        subtitle = QLabel("轨道交通无线覆盖工程工作台")
        subtitle.setObjectName("subtitleLabel")
        header_text = QVBoxLayout()
        header_text.setSpacing(1)
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        self.current_case_label = QLabel("地下站厅标准算例")
        self.current_case_label.setObjectName("caseLabel")
        header_layout.addWidget(self.current_case_label)

        self.reset_button = QPushButton("重置")
        self.reset_button.setObjectName("secondaryButton")
        self.reset_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.reset_button.setToolTip("恢复默认参数")
        self.reset_button.clicked.connect(self._populate_defaults)

        self.export_button = QToolButton()
        self.export_button.setObjectName("secondaryButton")
        self.export_button.setText("导出报告")
        self.export_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.export_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.export_button.setPopupMode(QToolButton.InstantPopup)
        export_menu = QMenu(self.export_button)
        self.export_word_action = QAction("导出 Word", self)
        self.export_pdf_action = QAction("导出 PDF", self)
        self.export_word_action.triggered.connect(lambda: self._export_report("word"))
        self.export_pdf_action.triggered.connect(lambda: self._export_report("pdf"))
        export_menu.addAction(self.export_word_action)
        export_menu.addAction(self.export_pdf_action)
        self.export_button.setMenu(export_menu)
        self.export_button.setEnabled(False)

        self.calculate_button = QPushButton("开始计算")
        self.calculate_button.setObjectName("primaryButton")
        self.calculate_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.calculate_button.clicked.connect(self._calculate)
        header_layout.addWidget(self.reset_button)
        header_layout.addWidget(self.export_button)
        header_layout.addWidget(self.calculate_button)
        root_layout.addWidget(header)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        root_layout.addWidget(content, stretch=1)

        input_scroll = QScrollArea()
        input_scroll.setObjectName("inputScroll")
        input_scroll.setWidgetResizable(True)
        input_scroll.setMinimumWidth(310)
        input_scroll.setMaximumWidth(350)
        input_scroll.setFrameShape(QFrame.NoFrame)
        input_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        input_panel = QWidget()
        input_panel.setObjectName("inputPanel")
        input_layout = QVBoxLayout(input_panel)
        input_layout.setContentsMargins(20, 18, 20, 20)
        input_layout.setSpacing(14)
        input_layout.addWidget(self._build_scenario_section())
        input_layout.addWidget(self._divider())
        input_layout.addWidget(self._build_base_section())
        input_layout.addWidget(self._divider())
        input_layout.addWidget(self._build_scenario_parameters_section())
        input_layout.addStretch()
        input_scroll.setWidget(input_panel)
        content_layout.addWidget(input_scroll)

        result_scroll = QScrollArea()
        result_scroll.setObjectName("resultScroll")
        result_scroll.setWidgetResizable(True)
        result_scroll.setFrameShape(QFrame.NoFrame)
        result_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        result_panel = QWidget()
        result_panel.setObjectName("resultPanel")
        result_layout = QVBoxLayout(result_panel)
        result_layout.setContentsMargins(22, 18, 22, 18)
        result_layout.setSpacing(14)
        result_layout.addWidget(self._build_metric_cards())
        result_layout.addWidget(self._build_context_strip())
        result_layout.addWidget(self._build_charts_panel(), stretch=3)
        result_layout.addWidget(self._build_steps_panel(), stretch=2)
        result_scroll.setWidget(result_panel)
        content_layout.addWidget(result_scroll, stretch=1)

        footer = QFrame()
        footer.setObjectName("appFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 5, 18, 5)
        footer_layout.setSpacing(8)
        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("statusLabel")
        self.footer_context_label = QLabel("模型：待计算")
        self.footer_context_label.setObjectName("footerContext")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.footer_context_label)
        root_layout.addWidget(footer)

        self.setCentralWidget(root)
        self._connect_input_change_handlers()
        self._apply_styles()

    def _build_scenario_section(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._section_title("场景"))

        self.scenario_combo = QComboBox()
        for scenario_type, label in SCENARIO_LABELS.items():
            self.scenario_combo.addItem(label, scenario_type)
        self.scenario_combo.currentIndexChanged.connect(self._on_scenario_changed)
        self.scenario_combo.setVisible(False)

        segmented = QWidget()
        segmented_layout = QHBoxLayout(segmented)
        segmented_layout.setContentsMargins(0, 0, 0, 0)
        segmented_layout.setSpacing(6)
        scenario_group = QButtonGroup(self)
        scenario_group.setExclusive(True)
        for index, (scenario_type, label) in enumerate(SCENARIO_LABELS.items()):
            scenario_button = QPushButton(label)
            scenario_button.setObjectName("scenarioButton")
            scenario_button.setCheckable(True)
            scenario_button.setProperty("scenarioType", scenario_type)
            scenario_button.clicked.connect(
                lambda _checked=False, value=index: self.scenario_combo.setCurrentIndex(value)
            )
            scenario_group.addButton(scenario_button, index)
            segmented_layout.addWidget(scenario_button)
            self.scenario_buttons[scenario_type] = scenario_button
        layout.addWidget(segmented)

        example_layout = QHBoxLayout()
        example_layout.setSpacing(8)
        self.example_combo = QComboBox()
        for scenario_type, (label, _) in EXAMPLE_CASES.items():
            self.example_combo.addItem(label, scenario_type)
        self.example_combo.currentIndexChanged.connect(self._on_example_selected)
        self.load_example_button = QPushButton("加载算例")
        self.load_example_button.setObjectName("compactButton")
        self.load_example_button.clicked.connect(self._load_selected_example)
        example_layout.addWidget(self.example_combo)
        example_layout.addWidget(self.load_example_button)
        layout.addLayout(example_layout)
        return section

    def _build_base_section(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._section_title("基础参数"))

        wireless_form = self._form_layout()
        wireless_fields = [
            ("frequency_mhz", "工作频率", 100.0, 1000.0, 1.0, "MHz"),
            ("tx_power_dbm", "发射功率", -20.0, 120.0, 1.0, "dBm"),
            ("base_antenna_gain_dbi", "基站天线增益", -20.0, 80.0, 0.5, "dBi"),
            ("feeder_loss_db", "馈线损耗", 0.0, 80.0, 0.5, "dB"),
            ("connector_loss_db", "接头损耗", 0.0, 80.0, 0.5, "dB"),
            ("mobile_antenna_gain_dbi", "手台天线增益", -20.0, 30.0, 0.5, "dBi"),
            ("receiver_sensitivity_dbm", "接收灵敏度", -150.0, -1.0, 1.0, "dBm"),
        ]
        self._add_fields(wireless_form, wireless_fields)
        layout.addLayout(wireless_form)

        layout.addWidget(self._subsection_title("高度与工程"))
        engineering_form = self._form_layout()
        engineering_fields = [
            ("base_height_m", "基站高度", 0.1, 200.0, 0.5, "m"),
            ("mobile_height_m", "手台高度", 0.1, 20.0, 0.1, "m"),
            ("engineering_margin_db", "工程裕度", 0.0, 80.0, 0.5, "dB"),
        ]
        self._add_fields(engineering_form, engineering_fields)
        layout.addLayout(engineering_form)
        return section

    def _build_scenario_parameters_section(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._section_title("场景参数"))

        self.scenario_stack = QStackedWidget()
        for scenario_type in SCENARIO_LABELS:
            page = QWidget()
            form = self._form_layout(page)
            self.scenario_fields[scenario_type] = {}
            for key, value in self.config["scenario_defaults"][scenario_type].items():
                widget = self._spin_box(0.0, 10000.0, 0.5)
                widget.setValue(float(value))
                self.scenario_fields[scenario_type][key] = widget
                form.addRow(SCENARIO_PARAM_LABELS.get(key, key), widget)
            self.scenario_stack.addWidget(page)
        layout.addWidget(self.scenario_stack)
        return section

    def _build_metric_cards(self) -> QWidget:
        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.metric_layout = layout
        items = [
            ("coverage_distance_m", "最大覆盖距离", "#1769aa", "覆盖边界"),
            ("coverage_level", "覆盖等级", "#2d8a57", "设计评价"),
            ("max_path_loss_db", "最大路径损耗", "#d09022", "含工程裕度"),
            ("boundary_rssi_dbm", "边界 RSSI", "#c74343", "接收电平"),
        ]
        for index, (key, title, accent, note) in enumerate(items):
            card = QFrame()
            card.setObjectName("metricCard")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 14, 0)
            card_layout.setSpacing(12)
            accent_bar = QFrame()
            accent_bar.setFixedWidth(4)
            accent_bar.setStyleSheet(f"background: {accent}; border-radius: 2px;")
            card_layout.addWidget(accent_bar)
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 12, 0, 10)
            text_layout.setSpacing(2)
            title_label = QLabel(title)
            title_label.setObjectName("metricTitle")
            value = QLabel("-")
            value.setObjectName("metricValue")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            note_label = QLabel(note)
            note_label.setObjectName("metricNote")
            self.result_labels[key] = value
            text_layout.addWidget(title_label)
            text_layout.addWidget(value)
            text_layout.addWidget(note_label)
            card_layout.addLayout(text_layout, stretch=1)
            self.metric_cards.append(card)
            layout.addWidget(card, 0, index)
        return container

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        columns = 2 if event.size().width() < 1180 else 4
        if columns == self.metric_columns or not hasattr(self, "metric_layout"):
            return
        self.metric_columns = columns
        for card in self.metric_cards:
            self.metric_layout.removeWidget(card)
        for index, card in enumerate(self.metric_cards):
            self.metric_layout.addWidget(card, index // columns, index % columns)

    def _ensure_ui_font(self) -> None:
        global UI_FONT_LOADED
        if UI_FONT_LOADED:
            return
        font_path = Path(r"C:\Windows\Fonts\msyh.ttc")
        if font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families and QApplication.instance() is not None:
                QApplication.instance().setFont(QFont(families[0], 10))
        UI_FONT_LOADED = True

    def _build_context_strip(self) -> QFrame:
        strip = QFrame()
        strip.setObjectName("contextStrip")
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)
        layout.addWidget(self._context_label("传播模型"))
        model_value = QLabel("-")
        model_value.setObjectName("contextValue")
        self.result_labels["model_name"] = model_value
        layout.addWidget(model_value)
        layout.addSpacing(18)
        layout.addWidget(self._context_label("EIRP"))
        eirp_value = QLabel("-")
        eirp_value.setObjectName("contextValue")
        self.result_labels["eirp_dbm"] = eirp_value
        layout.addWidget(eirp_value)
        layout.addStretch()
        self.result_state_label = QLabel("等待计算")
        self.result_state_label.setObjectName("resultState")
        layout.addWidget(self.result_state_label)
        return strip

    def _build_charts_panel(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.path_loss_figure = Figure(figsize=(5, 3), tight_layout=True)
        self.path_loss_canvas = FigureCanvasQTAgg(self.path_loss_figure)
        self.rssi_figure = Figure(figsize=(5, 3), tight_layout=True)
        self.rssi_canvas = FigureCanvasQTAgg(self.rssi_figure)
        layout.addWidget(
            self._chart_panel("Path Loss 曲线", "路径损耗随距离变化", self.path_loss_canvas),
            stretch=1,
        )
        layout.addWidget(
            self._chart_panel("RSSI 曲线", "接收电平随距离变化", self.rssi_canvas),
            stretch=1,
        )
        self._plot_empty_charts()
        return container

    def _build_steps_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contentPanel")
        panel.setMinimumHeight(210)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("计算过程")
        title.setObjectName("panelTitle")
        self.iteration_label = QLabel("等待计算")
        self.iteration_label.setObjectName("panelMeta")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.iteration_label)
        layout.addLayout(header)

        self.steps_table = QTableWidget(0, 4)
        self.steps_table.setHorizontalHeaderLabels(["步骤", "公式", "代入", "结果"])
        self.steps_table.setObjectName("stepsTable")
        self.steps_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.steps_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.steps_table.setAlternatingRowColors(False)
        self.steps_table.verticalHeader().setVisible(False)
        self.steps_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.steps_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.steps_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.steps_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.steps_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.steps_table, stretch=2)

        self.warning_text = QTextEdit()
        self.warning_text.setReadOnly(True)
        self.warning_text.setObjectName("warningText")
        self.warning_text.setPlaceholderText("计算提示")
        self.warning_text.setMaximumHeight(58)
        layout.addWidget(self.warning_text)
        return panel

    def _chart_panel(self, title: str, subtitle: str, canvas: FigureCanvasQTAgg) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contentPanel")
        panel.setMinimumHeight(260)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("panelTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("panelMeta")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(canvas, stretch=1)
        return panel

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def _subsection_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("subsectionTitle")
        return label

    def _context_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("contextLabel")
        return label

    def _divider(self) -> QFrame:
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.HLine)
        return divider

    def _form_layout(self, parent: QWidget | None = None) -> QFormLayout:
        form = QFormLayout(parent)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return form

    def _add_fields(
        self,
        form: QFormLayout,
        fields: list[tuple[str, str, float, float, float, str]],
    ) -> None:
        for key, label, minimum, maximum, step, unit in fields:
            widget = self._spin_box(minimum, maximum, step, unit)
            self.base_fields[key] = widget
            form.addRow(label, widget)

    def _populate_defaults(self) -> None:
        for section in ("wireless", "height"):
            for key, value in self.config[section].items():
                self.base_fields[key].setValue(float(value))
        self.base_fields["engineering_margin_db"].setValue(
            float(self.config["engineering_margin_db"])
        )
        self._on_scenario_changed()
        self.result_state_label.setText("等待计算")
        self.status_label.setText("已恢复默认参数")
        self.footer_context_label.setText("模型：待计算")

    def _on_scenario_changed(self) -> None:
        self.scenario_stack.setCurrentIndex(self.scenario_combo.currentIndex())
        scenario_type = self.scenario_combo.currentData()
        self.scenario_buttons[scenario_type].setChecked(True)
        example_index = self.example_combo.findData(scenario_type)
        if example_index >= 0:
            self.example_combo.blockSignals(True)
            self.example_combo.setCurrentIndex(example_index)
            self.example_combo.blockSignals(False)
        self.current_case_label.setText(EXAMPLE_CASES[scenario_type][0])
        self._invalidate_report_data()

    def _on_example_selected(self) -> None:
        scenario_type = self.example_combo.currentData()
        scenario_index = self.scenario_combo.findData(scenario_type)
        if scenario_index >= 0:
            self.scenario_combo.blockSignals(True)
            self.scenario_combo.setCurrentIndex(scenario_index)
            self.scenario_stack.setCurrentIndex(scenario_index)
            self.scenario_combo.blockSignals(False)
            self.scenario_buttons[scenario_type].setChecked(True)
        self.current_case_label.setText(self.example_combo.currentText())
        self._invalidate_report_data()

    def _load_selected_example(self) -> None:
        input_data = load_example_input(EXAMPLES_DIR, self.example_combo.currentData())
        self._apply_input_data(input_data)
        self._invalidate_report_data()
        self.current_case_label.setText(self.example_combo.currentText())
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
        self.result_state_label.setText("输入有误")
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
        self.iteration_label.setText(
            f"{len(serialized['details']['iteration_steps'])} 次迭代"
        )
        self.result_state_label.setText("计算完成")
        self.footer_context_label.setText(
            f"模型：{summary['model_name']} · {serialized['input']['frequency_mhz']:.0f} MHz"
        )
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
        if hasattr(self, "result_state_label"):
            self.result_state_label.setText("参数已更新")
        if hasattr(self, "status_label"):
            self.status_label.setText("参数已更新，请重新计算")

    def _set_export_buttons_enabled(self, enabled: bool) -> None:
        self.export_button.setEnabled(enabled)
        self.export_word_action.setEnabled(enabled)
        self.export_pdf_action.setEnabled(enabled)

    def _plot_empty_charts(self) -> None:
        self._draw_chart(
            self.path_loss_figure,
            self.path_loss_canvas,
            x_values=[],
            y_values=[],
            y_label="Path Loss (dB)",
            line_color="#1769aa",
        )
        self._draw_chart(
            self.rssi_figure,
            self.rssi_canvas,
            x_values=[],
            y_values=[],
            y_label="RSSI (dBm)",
            line_color="#2d8a57",
        )

    def _plot_charts(self, charts: dict) -> None:
        series = extract_chart_series(charts)
        self._draw_chart(
            self.path_loss_figure,
            self.path_loss_canvas,
            x_values=series["distance_m"],
            y_values=series["path_loss_db"],
            y_label="Path Loss (dB)",
            line_color="#1769aa",
            boundary_x=series["boundary_distance_m"],
            boundary_y=series["boundary_path_loss_db"],
        )
        self._draw_chart(
            self.rssi_figure,
            self.rssi_canvas,
            x_values=series["distance_m"],
            y_values=series["rssi_dbm"],
            y_label="RSSI (dBm)",
            line_color="#2d8a57",
            boundary_x=series["boundary_distance_m"],
            boundary_y=series["boundary_rssi_dbm"],
        )

    def _draw_chart(
        self,
        figure: Figure,
        canvas: FigureCanvasQTAgg,
        *,
        x_values: list[float],
        y_values: list[float],
        y_label: str,
        line_color: str,
        boundary_x: float | None = None,
        boundary_y: float | None = None,
    ) -> None:
        figure.clear()
        figure.patch.set_facecolor("#ffffff")
        axis = figure.add_subplot(111)
        axis.set_facecolor("#ffffff")
        axis.set_xlabel("Distance (m)")
        axis.set_ylabel(y_label)
        axis.grid(True, color="#e5eaee", linestyle="-", linewidth=0.8)
        axis.tick_params(axis="both", colors="#667681", labelsize=8)
        axis.xaxis.label.set_color("#667681")
        axis.yaxis.label.set_color("#667681")
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_color("#9aa8b2")
        axis.spines["bottom"].set_color("#9aa8b2")

        if x_values and y_values:
            axis.plot(x_values, y_values, color=line_color, linewidth=2.0)
        else:
            axis.text(
                0.5,
                0.5,
                "Waiting for calculation",
                transform=axis.transAxes,
                ha="center",
                va="center",
                color="#8a98a3",
                fontsize=10,
            )
        if boundary_x is not None and boundary_y is not None:
            axis.axvline(boundary_x, color="#c74343", linestyle="--", linewidth=1.2)
            axis.scatter([boundary_x], [boundary_y], color="#c74343", zorder=3)
            axis.text(
                0.98,
                0.96,
                "Coverage boundary",
                transform=axis.transAxes,
                horizontalalignment="right",
                verticalalignment="top",
                fontsize=9,
                color="#c74343",
            )

        canvas.draw_idle()

    def _spin_box(
        self, minimum: float, maximum: float, step: float, unit: str = ""
    ) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setDecimals(3)
        widget.setSingleStep(step)
        if unit:
            widget.setSuffix(f" {unit}")
        widget.setKeyboardTracking(False)
        widget.setAlignment(Qt.AlignRight)
        return widget

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 12px;
                color: #1d2b35;
            }
            #appRoot, #resultScroll, #resultPanel {
                background: #f3f5f6;
            }
            #appHeader {
                background: #ffffff;
                border-bottom: 1px solid #d7dee3;
            }
            #brandMark {
                background: #1769aa;
                color: #ffffff;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 700;
            }
            #titleLabel {
                font-size: 17px;
                font-weight: 700;
            }
            #subtitleLabel {
                color: #687681;
                font-size: 10px;
            }
            #caseLabel {
                color: #52616d;
                padding-right: 10px;
            }
            QPushButton, QToolButton {
                min-height: 32px;
                padding: 0 13px;
                border-radius: 5px;
                font-weight: 500;
            }
            #primaryButton {
                min-width: 96px;
                background: #1769aa;
                color: #ffffff;
                border: 1px solid #1769aa;
                font-weight: 700;
            }
            #primaryButton:hover {
                background: #125b95;
                border-color: #125b95;
            }
            #primaryButton:pressed {
                background: #0f4d7e;
            }
            #secondaryButton, #compactButton {
                background: #ffffff;
                color: #33424d;
                border: 1px solid #cfd8df;
            }
            #secondaryButton:hover, #compactButton:hover {
                background: #f4f7f9;
                border-color: #9eb0bc;
            }
            #secondaryButton:disabled {
                color: #9aa7b0;
                background: #f2f4f5;
                border-color: #dce2e6;
            }
            #compactButton {
                min-width: 72px;
                padding: 0 10px;
            }
            QMenu {
                background: #ffffff;
                border: 1px solid #cfd8df;
                padding: 5px;
            }
            QMenu::item {
                min-width: 120px;
                padding: 7px 22px 7px 10px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #e8f2fa;
                color: #1769aa;
            }
            #inputScroll, #inputPanel {
                background: #ffffff;
                border: none;
            }
            #inputScroll {
                border-right: 1px solid #d9e0e5;
            }
            #sectionTitle {
                font-size: 13px;
                font-weight: 700;
                color: #1d2b35;
            }
            #subsectionTitle {
                font-size: 11px;
                font-weight: 700;
                color: #50606b;
                padding-top: 5px;
            }
            #divider {
                color: #e1e6e9;
                background: #e1e6e9;
                max-height: 1px;
                border: none;
            }
            #scenarioButton {
                min-width: 0;
                min-height: 30px;
                padding: 0 8px;
                background: #f6f7f8;
                color: #5d6a74;
                border: 1px solid #e0e5e8;
                border-radius: 4px;
            }
            #scenarioButton:hover {
                border-color: #b8cad7;
            }
            #scenarioButton:checked {
                background: #e8f2fa;
                color: #1769aa;
                border-color: #b8d4e8;
                font-weight: 700;
            }
            QComboBox, QDoubleSpinBox {
                min-height: 31px;
                background: #ffffff;
                color: #1f2d37;
                border: 1px solid #d3dbe2;
                border-radius: 4px;
                padding: 0 8px;
                selection-background-color: #dcecf8;
            }
            QComboBox:hover, QDoubleSpinBox:hover {
                border-color: #9eb4c3;
            }
            QComboBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #1769aa;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                border: 1px solid #cfd8df;
                selection-background-color: #e8f2fa;
                selection-color: #1769aa;
                outline: none;
            }
            #metricCard, #contentPanel {
                background: #ffffff;
                border: 1px solid #dce3e8;
                border-radius: 6px;
            }
            #metricCard {
                min-height: 84px;
            }
            #metricTitle, #metricNote, #panelMeta, #contextLabel {
                color: #687681;
            }
            #metricTitle, #metricNote, #panelMeta {
                font-size: 10px;
            }
            #metricValue {
                color: #14212b;
                font-size: 20px;
                font-weight: 700;
            }
            #contextStrip {
                background: #eef2f4;
                border: 1px solid #dde4e8;
                border-radius: 5px;
            }
            #contextValue {
                color: #263640;
                font-weight: 700;
            }
            #resultState {
                background: #e7f4ec;
                color: #2d7b50;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 700;
            }
            #panelTitle {
                color: #17242e;
                font-size: 13px;
                font-weight: 700;
            }
            #stepsTable {
                background: #ffffff;
                alternate-background-color: #ffffff;
                border: none;
                gridline-color: #edf0f2;
                selection-background-color: #e8f2fa;
                selection-color: #1d2b35;
            }
            #stepsTable::item {
                padding: 6px;
                border-bottom: 1px solid #edf0f2;
            }
            QHeaderView::section {
                background: #f3f5f6;
                color: #65737e;
                border: none;
                border-bottom: 1px solid #dce3e8;
                padding: 7px;
                font-weight: 700;
            }
            #warningText {
                background: #f1f7f4;
                color: #2d7b50;
                border: 1px solid #d8ebe0;
                border-radius: 4px;
                padding: 5px 8px;
            }
            #appFooter {
                background: #eef2f4;
                border-top: 1px solid #dce3e8;
            }
            #statusLabel {
                color: #2d8a57;
                font-size: 10px;
                font-weight: 700;
            }
            #footerContext {
                color: #677681;
                font-size: 10px;
            }
            QScrollBar:vertical {
                width: 10px;
                background: transparent;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                min-height: 28px;
                background: #c8d2d9;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QToolTip {
                color: #ffffff;
                background: #26343d;
                border: 1px solid #26343d;
                padding: 5px;
            }
            """
        )


def run() -> int:
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
