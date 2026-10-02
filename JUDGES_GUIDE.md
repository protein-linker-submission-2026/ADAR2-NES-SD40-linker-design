# 评委资料导航清单

## 下载入口

- [直接下载参赛代码与核心结果 ZIP](https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design/archive/refs/heads/main.zip)
- [在线浏览项目仓库](https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design)
- [下载完整原始计算记录和中间结果](https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design/releases/tag/v2.0-complete-submission)

建议先下载“参赛代码与核心结果 ZIP”。只有需要核查完整 MSA、预测数组、中间结构和逐阶段日志时，才需要进入 Release 下载全部 11 个 `full-reproduction-*.zip` 分卷。

## 项目信息

- 项目名称：AI辅助设计RNA编辑器连接肽优化
- 参赛组别：本科生组
- 参赛赛道：赛道二 AI基因编辑与核酸工具设计
- 结果性质：计算设计与筛选结果，未开展湿实验验证

本页是评审入口。阅读核心结果不需要安装GPU软件；只有重新执行RFdiffusion、ProteinMPNN、Boltz-2和Vina时，才需要完整计算环境。

## 建议阅读顺序

1. `README.md`：项目结论、目录结构、快速核验命令和主要门控规则。
2. `results/report.pdf`：按论文形式整理的方法、图表、结果与限制。
3. `results/results.xlsx`：完整可读工作簿。
4. `results/results.csv`：附件5要求的标准化候选清单；每行对应一个候选、一个RFdiffusion骨架和三个Boltz-2结构。
5. `MODEL_CARD.md`：模型用途、输入输出、创新贡献与已知局限。
6. `REPRODUCE_FROM_ZERO.md`：从一台新机器开始安装并重跑完整流程。
7. `SUBMISSION_COMPLIANCE.md`：附件5逐条要求与仓库证据的对应表。

## 评委常见核验任务

| 要核验的内容 | 对应材料 |
| --- | --- |
| 最终候选、排序和指标 | `results/results.xlsx`、`results/results.csv` |
| 全部候选与全部模型 | `results/all_candidate_records.csv`、`results/all_model_records.csv` |
| 三维结构 | `results/structures/rfdiffusion/`、`results/structures/boltz2/` |
| Linker Cα RMSD门控 | `results/rmsd/` |
| PT-179/MIQ对接与Vina门控 | `results/docking/` |
| 每个距离的筛选漏斗 | `results/span_summary.csv` |
| 图表 | `results/figures/` |
| 参数、随机种子和运行记录 | `logs/`、`results/inputs/`、`results/state/` |
| 数据来源和许可 | `data/README.md`、`DATA_SOURCES.md` |
| 第三方软件、模型和版本 | `THIRD_PARTY_SOFTWARE.md`、`docs/VERSIONS.md` |
| 模型权重获取方式 | `models/README.md`、`src/setup_external_sources.sh` |
| 核心算法代码 | `src/`、`ranker/`、`methods/` |
| 文件完整性与匿名性 | `validate_submission.py`、`provenance/` |
| 自动持续核验 | `.github/workflows/validate-submission.yml` |

## 五分钟快速核验

Windows PowerShell：

```powershell
git clone https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design.git
cd ADAR2-NES-SD40-linker-design
py -3 -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Linux或WSL：

```bash
git clone https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design.git
cd ADAR2-NES-SD40-linker-design
python -m pip install -r requirements.txt
bash run.sh
```

成功时会显示 `VALIDATION PASS`，并核对候选记录、模型记录、588个Boltz-2 PDB、结构路径和匿名信息。该快速核验重建最终候选表，不重复消耗数十小时至数天的GPU计算。

GitHub Actions会在主分支更新时自动执行同一套轻量核验。由于托管运行器没有项目所需GPU、第三方权重和Windows MGLTools，Actions不运行完整模型流程；完整流程仍以 `run_full.ps1` 为准。

## 完整从零复现

完整复现入口是：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_full.ps1 -CheckOnly
powershell -ExecutionPolicy Bypass -File .\run_full.ps1
```

运行前必须按 `REPRODUCE_FROM_ZERO.md` 安装并固定RFdiffusion、ProteinMPNN、Boltz-2、AutoDock Vina和MGLTools路径。完整入口执行：

`参考结构准备 → 初始位姿 → RFdiffusion → ProteinMPNN → 序列QC → 在线MSA → Boltz-2三模型预测 → Linker Cα RMSD门控 → Vina对接门控 → SD40几何评分 → results.csv/results.xlsx`

## 完整原始附件

GitHub主分支包含代码、最终清单、最终结构、关键日志和完整性材料。非重复的全量中间记录分成11个压缩卷，位于：

https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design/releases/tag/v2.0-complete-submission

下载全部 `full-reproduction-*.zip` 和校验文件后，按 `archive_reference/README.md` 验证SHA256并解压到同一空目录。第三方预训练权重、Conda环境、软件缓存、重复文件和含身份信息的源文件不在附件中；模型权重应按官方来源重新获取。
