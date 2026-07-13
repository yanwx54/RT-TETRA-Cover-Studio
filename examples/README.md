# V1.0 标准算例

本目录存放 V1.0 四类场景标准输入，供测试、GUI 默认示例和报告导出复用。

| 文件 | 场景 | 模型 |
| --- | --- | --- |
| `underground_standard.json` | 地下站厅 | ITU Indoor |
| `tunnel_standard.json` | 隧道区间 | Tunnel Model |
| `ground_standard.json` | 400 MHz 地面区段 | Low-Band Calibrated Ground |
| `viaduct_standard.json` | 400 MHz 高架区段 | Low-Band Calibrated Ground + Viaduct Calibration |

每个算例包含：

- `case_id`：算例编号；
- `name`：算例名称；
- `description`：用途说明；
- `input`：可直接转换为 `CalculationInput` 的输入参数；
- `expected`：模型名和覆盖距离预期范围。

当前预期范围用于回归测试，不作为最终工程标定结果。
