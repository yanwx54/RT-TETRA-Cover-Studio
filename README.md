# RT-TETRA Cover Studio

轨道交通 TETRA 单基站覆盖距离计算与分析软件。

本项目面向地铁、市域铁路、轻轨、有轨电车等轨道交通通信场景，目标是提供一套轻量、专业、计算过程透明的 TETRA 覆盖分析工具，用于工程设计、方案论证、招投标技术交流和设计计算书生成。

> 当前状态：V1.0 双向链路预算、工程参数 GUI 和五段详细报告已完成，待重新打包并执行人工启动验收。

---

## 1. 项目目标

V1.0 聚焦单基站、单场景、单次计算，计划支持：

- 链路预算计算；
- 路径损耗计算；
- 最大覆盖距离计算；
- 接收电平与 RSSI 计算；
- RSSI 随距离变化曲线；
- 覆盖距离与路径损耗曲线；
- 覆盖等级评价；
- 参数敏感性分析；
- 全过程计算展示；
- Word/PDF 计算报告生成。

单次计算目标时间不超过 3 秒。

---

## 2. 适用范围

支持频段：

- 350 MHz
- 380 MHz
- 400 MHz
- 800 MHz
- 860 MHz

计划支持场景：

| 场景 | 传播模型 |
| --- | --- |
| 地下站厅、站台 | ITU Indoor |
| 隧道 | Tunnel Model |
| 地面 | COST231-Walfisch-Ikegami |
| 高架 | COST231-WI + 高架修正 |

---

## 3. 当前项目状态

已完成：

- 项目基础目录创建；
- 产品需求文档初稿；
- 系统总体设计文档；
- 03-12 专题文档初稿；
- 项目总控台 `PROJECT_INDEX.md`；
- README 初稿；
- V1.0 技术栈确认；
- `requirements.txt` 依赖清单；
- 最小计算闭环；
- 四类传播模型初版；
- 默认配置；
- 四类标准算例；
- 计算结果序列化接口；
- 边界和异常测试；
- GUI 原型初版；
- GUI 工程控制台视觉重构；
- 基站/手台发射功率 W 输入及内部 dBm 换算；
- 基站/手台双向 EIRP、接收灵敏度、MAPL 与受限链路计算；
- 以单侧正态分布地点概率计算边缘覆盖阴影衰落余量；
- GUI 五段详细计算过程展示；
- Path Loss / RSSI 曲线展示；
- 标准算例加载、重置默认值、输入校验提示；
- Word 报告模板和 Word 导出；
- PDF 报告导出；
- GUI 接入 Word/PDF 导出按钮；
- Word/PDF 报告嵌入 Path Loss / RSSI 曲线图片；
- Word/PDF 报告补充页眉页脚和工程信息；
- 完整 PySide6 环境中的 GUI 导出交互测试；
- V1.0 Windows 打包方案、PyInstaller spec 和构建脚本；
- V1.0 Windows onedir 构建产物生成验证；
- 31 个核心、示例、GUI 数据、报告导出和 GUI 交互测试。

尚未完成：

- 可运行程序。

当前项目已有双向链路预算、四类传播模型、统一标准算例、结果序列化、工程控制台 GUI 和 Word/PDF 详细报告。下一步应重新构建 Windows onedir 程序，执行 GUI 计算与报告导出的人工启动验收。

---

## 4. V1.0 技术栈

| 项目 | 选型 | 说明 |
| --- | --- | --- |
| Python 版本 | Python 3.13 | 当前处于官方 bugfix 支持期，兼顾稳定性和生命周期 |
| GUI 框架 | PySide6 + Qt Widgets | 适合 Windows 桌面工程工具，界面稳定，控件成熟 |
| 绘图库 | Matplotlib | 生成 RSSI 曲线和 Path Loss 曲线，可嵌入 Qt，也可导出图片用于报告 |
| Word 导出 | python-docx | 生成可编辑 Word 计算报告 |
| PDF 导出 | ReportLab | 直接生成 PDF，避免依赖 Microsoft Word 或 Word COM |
| 测试框架 | pytest | 用于核心公式、传播模型、求解算法和异常输入测试 |

说明：

- GUI 使用 Qt Widgets，不使用 Qt Quick/QML，降低 V1.0 实现复杂度。
- 核心计算模块不得依赖 PySide6，必须可在无 GUI 环境下测试。
- Word/PDF 导出共享同一个 `CalculationResult`，报告模块不得重新计算。

---

## 5. 环境准备

当前开发环境需要先安装 Python 3.13。

Windows PowerShell 示例：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

验证依赖：

```powershell
python -m pytest --version
python -c "import PySide6, matplotlib, docx, reportlab; print('ok')"
```

运行当前核心测试：

```powershell
python -m unittest discover -s tests
```

启动 GUI 原型：

```powershell
python scripts/run_gui.py
```

执行 Windows 打包：

```powershell
.\scripts\build_windows.ps1
```

如果当前机器没有 `python` 命令，可显式指定解释器：

```powershell
.\scripts\build_windows.ps1 -Python "C:\Path\To\python.exe"
```

若本地环境尚未安装 GUI 依赖，实际启动 GUI 前需先执行：

```powershell
python -m pip install -r requirements.txt
```

---

## 6. 项目目录

```text
RT-TETRA-Cover-Studio/
├── assets/              # 图片、模板、静态资源
├── config/              # 参数配置、默认值配置
├── docs/                # 项目文档
├── examples/            # 示例输入、示例输出
├── packaging/           # 打包配置
├── reports/             # 生成的报告文件
├── scripts/             # 辅助脚本
├── src/                 # 源码
├── tests/               # 测试用例
├── .gitignore
├── PROJECT_INDEX.md     # 项目总控台
├── README.md
└── requirements.txt     # Python 依赖清单
```

---

## 7. 文档导航

建议阅读顺序：

1. [`PROJECT_INDEX.md`](PROJECT_INDEX.md)：查看当前进度、下一步任务、版本状态和里程碑。
2. [`docs/01_产品开发项目需求书.md`](docs/01_产品开发项目需求书.md)：确认产品目标、功能范围和 V1.0 边界。
3. [`docs/02_系统总体设计.md`](docs/02_系统总体设计.md)：确认系统架构、模块职责和开发原则。
4. [`docs/07_开发任务清单.md`](docs/07_开发任务清单.md)：后续用于拆解开发任务。
5. [`docs/09_测试用例.md`](docs/09_测试用例.md)：后续用于记录计算、边界和异常输入测试。
6. [`docs/13_V1.0打包方案.md`](docs/13_V1.0打包方案.md)：查看 Windows 可运行程序打包方式。

`docs/` 目录当前已建立完整文档结构，03-13 专题文档已完成初稿，后续随实现细节持续校准。

---

## 8. 计划架构

系统总体设计采用分层架构：

```text
GUI 界面层
  ↓
业务逻辑层
  ↓
计算引擎
  ↓
传播模型库
  ↓
公共基础库
```

报告导出模块由业务逻辑层调用。所有计算必须通过计算引擎统一调度，GUI 不直接调用传播模型。

---

## 9. V1.0 不包含内容

V1.0 暂不支持：

- GIS 地图；
- 多站联合覆盖；
- 覆盖热力图；
- 自动站址优化；
- 数据库；
- 项目管理功能。

这些能力可作为后续版本扩展方向，不进入当前最小闭环。

---

## 10. 开发约定

- 开始任务前，先查看 `PROJECT_INDEX.md`。
- 需求边界以 `docs/01_产品开发项目需求书.md` 为准。
- 架构和模块边界以 `docs/02_系统总体设计.md` 为准。
- 若需求文档与设计文档冲突，先更新文档，再进入编码。
- V1.0 优先完成可验证的最小计算闭环，不提前开发复杂扩展能力。
- 新增计算逻辑时，应同步补充测试用例。

---

## 11. 下一步

建议按以下顺序推进：

1. 重新构建打包程序并执行人工启动验收，确认 `dist/RT-TETRA-Cover-Studio/RT-TETRA-Cover-Studio.exe` 可完成双向链路计算和报告导出。
2. 补充用户手册中的实际 GUI 操作截图和报告导出步骤。
3. 执行 V1.0 验收前的完整回归测试。

---

## 12. 版本状态

| 项目项 | 当前状态 |
| --- | --- |
| 当前版本 | V1.0 |
| 文档 | V1.0 文档体系初稿已完成 |
| 技术栈 | Python 3.13、PySide6、Matplotlib、python-docx、ReportLab、pytest |
| 工程目录 | 已创建 |
| 源码 | 双向链路预算、边缘覆盖率和四类传播模型已实现 |
| 配置 | 默认参数和覆盖等级配置已完成 |
| 示例 | 四类标准算例已完成 |
| 序列化 | 计算结果可输出 GUI/报告复用数据字典 |
| GUI | W 功率输入、双向链路结果、五段详细过程、双曲线和导出菜单已完成 |
| 报告导出 | Word/PDF 已包含五段详细过程、曲线、页眉页脚和工程信息 |
| 打包 | Windows onedir 打包方案、PyInstaller spec、构建脚本和构建产物生成验证已完成 |
| 测试 | 31 个核心、示例、GUI 数据、报告导出和 GUI 交互测试已通过 |
| 可运行程序 | 已生成 onedir exe，待人工启动验收 |
| 远程仓库 | 已推送至 GitHub |

GitHub 仓库：

<https://github.com/yanwx54/RT-TETRA-Cover-Studio>
