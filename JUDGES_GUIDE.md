# 评委资料导航清单

## 下载入口

- [在线浏览项目仓库](https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design)
- [下载完整原始计算记录和中间结果](https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design/releases/tag/v2.0-complete-submission)

建议先阅读正式代码包内的本清单与核心结果。核查完整 MSA、预测数组、中间结构和逐阶段日志时，再按下表下载相应原始记录；需要完整归档时下载全部 11 个 `full-reproduction-*.zip` 压缩包。

## 比赛提交方式

附件5允许以“代码仓库或压缩包”组织代码，但实际上传方式、文件名与大小限制以比赛系统及赛道细则为准。建议在代码附件栏上传 `AI辅助设计RNA编辑器连接肽优化参赛代码（区赛）.zip`，同时附本导航清单和上述Release链接。报告、必要结果、实验附件及其他规定材料仍须上传到比赛系统对应栏目；GitHub补充资料不自动替代这些材料。只有系统明确接受仓库链接时，才按该栏要求提交网址。

## Release附件对应关系

| 文件或入口 | 用途 |
| --- | --- |
| `AI_RNA_editor_linker_optimization_regional_code.zip` | 正式代码与核心结果包的在线副本；比赛提交名为 `AI辅助设计RNA编辑器连接肽优化参赛代码（区赛）.zip` |
| 同名 `.zip.sha256` | 该代码包的完整性校验文件 |
| 代码包根目录及仓库中的 `JUDGES_GUIDE.md` | 本导航清单；本地另附中文命名副本 |
| 11个 `full-reproduction-*.zip` | 历史计算的全量中间记录，补充主代码包，不是安装好的软件环境 |
| `FULL_REPRODUCTION_ASSETS.csv`、`FULL_REPRODUCTION_SHA256SUMS.txt`、`README_FULL_REPRODUCTION.txt` | 对应上述11个分卷，不是新版主代码包的校验清单 |
| GitHub自动生成的 `Source code (zip/tar.gz)` | Release旧标签的源码快照，不等同于持续更新的正式代码附件 |

## 核验状态与边界

- 已核验：已提交结果的轻量重建、候选与结构映射、文件完整性检查；历史完整目录的汇总器测试不等同于重新运行模型。
- 待验收：在全新环境中安装全部依赖并完成设计至最终清单的端到端重跑。提供了脚本和教程，不代表已经通过该测试。
- 环境：以原总压缩包中的版本说明和历史日志为依据；不使用当前整理电脑的环境替代生产环境。完整推理环境尚未形成经干净安装验收的锁定方案。
- 湿实验：团队确认已开展；本包只提供计算证据，具体实验类型、原始数据、统计和结论尚待补入实验附件。历史计算报告中的后续实验建议不代表项目未开展实验。
- 当前核查详情与待办：`docs/REPRODUCIBILITY_STATUS.md`。`VALIDATION PASS`只代表该检查脚本覆盖的检查项通过，不是赛事合规认证。

## 项目信息

- 项目名称：AI辅助设计RNA编辑器连接肽优化
- 参赛组别：本科生组
- 参赛赛道：赛道二 AI基因编辑与核酸工具设计
- 结果性质：计算设计与筛选结果；已开展配套湿实验，实验方法、原始数据和结果由实验材料单独说明

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
| 安装与路径配置 | `REPRODUCE_FROM_ZERO.md`、`src/local_paths.example.sh` |
| 参数总表与实际调用 | `src/pipeline_config.sh`、`src/run_single_span.sh`、`results/inputs/` |
| 复现验收状态与原归档证据 | `docs/REPRODUCIBILITY_STATUS.md`、`docs/VERSIONS.md`、`provenance/ORIGINAL_ARCHIVE_AUDIT.json` |
| 模型权重获取方式 | `models/README.md`、`src/setup_external_sources.sh` |
| 核心算法代码 | `src/`、`ranker/`、`methods/` |
| 文件完整性与匿名性 | `validate_submission.py`、`provenance/` |
| 自动持续核验 | `.github/workflows/validate-submission.yml` |

## 按流程查找资料

下表中的NN为11至20，代表初始端点距离（Å），不是linker长度。正式批次的linker为10 aa；每个候选预测3个Boltz模型，不与早期L15等试运行混淆。

| 流程 | 代码包内材料 | Release补充压缩包 |
| --- | --- | --- |
| 环境、公共参考、位姿准备 | `docs/VERSIONS.md`、`references/`、`src/prepare_references.py`、`src/pose_generator.py` | `full-reproduction-common-and-early-16A.zip`中的公共方法与参考 |
| RFdiffusion骨架 | `src/run_single_span.sh`、`results/structures/rfdiffusion/`、`logs/` | 对应距离的 `full-reproduction-online-NNA.zip` |
| ProteinMPNN序列与QC | `src/pipeline_helper.py`、`results/proteinmpnn/`、`results/sequence_qc/` | 同距离压缩包中的原始MPNN输出 |
| MSA与Boltz-2 | `results/inputs/`、`results/structures/boltz2/`、`logs/` | 同距离压缩包中的MSA、预测数组及完整中间产物 |
| Linker RMSD | `results/rmsd/`、`src/pipeline_helper.py` | 同距离压缩包中的逐模型核验记录 |
| Vina与SD40评分 | `src/docking_helper.py`、`ranker/`、`results/docking/`、`results/ranking/` | 同距离压缩包中的原始对接、评分输出 |
| 跨距离汇总与图表 | `results/results.csv`、`results/results.xlsx`、`results/figures/`、`methods/` | 公共压缩包中的跨距离汇总与审计记录 |
| 早期16 Å单序列MSA对照 | `logs/16A_单序列MSA原始批次/`及对应原始附件 | `full-reproduction-common-and-early-16A.zip`；不是正式在线16 Å批次 |

每阶段不一定单独一个ZIP，原始附件按距离分批组织。精确包名、字节数、SHA256和原始目录对应见 `archive_reference/FULL_REPRODUCTION_ASSETS.csv`。公共包同时收录汇总的 `03_运行日志/`；其日志与各批次目录内的副本不应重复计为独立任务。

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

## 完整流程重跑（待端到端验收）

完整流程入口如下。`-CheckOnly`检查路径和部分前置条件，不执行模型，也不保证全部运行时依赖兼容：

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
