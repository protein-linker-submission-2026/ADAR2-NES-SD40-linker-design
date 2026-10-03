# AI辅助设计RNA编辑器连接肽优化
## 评审资料阅读与复核指南

本科生组 | 赛道二：AI基因编辑与核酸工具设计

本指南用于定位计算方法、候选结果、结构文件与复核证据。文中路径均相对于代码包根目录。阅读结果无需安装GPU软件；重新执行模型预测与对接时才需要完整计算环境。

## 一、资料入口

- [项目仓库：代码、方法与核心结果](https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design)
- [Release：正式代码附件与完整原始计算记录](https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design/releases/tag/v2.0-complete-submission)

| 文件或入口 | 内容 |
| --- | --- |
| `AI辅助设计RNA编辑器连接肽优化参赛代码（区赛）.zip` | 中文命名的参赛代码与核心结果包 |
| `AI_RNA_editor_linker_optimization_regional_code.zip` | Release中正式代码包的英文下载名称；以同名校验文件确认版本 |
| 同名 `.zip.sha256` | 对应代码ZIP的SHA256校验值 |
| `00_评委资料导航清单.md` / `JUDGES_GUIDE.md` | 根目录中的同一份阅读指南（中文名副本与英文名副本）；不同修订版请与对应代码包一同使用 |
| 11个 `full-reproduction-*.zip` | 按批次组织的原始计算记录与中间产物，详见第五节 |
| `FULL_REPRODUCTION_ASSETS.csv`、`FULL_REPRODUCTION_SHA256SUMS.txt`、`README_FULL_REPRODUCTION.txt` | 原始记录包的目录映射、校验值与合并解压说明 |

GitHub自动生成的 `Source code (zip/tar.gz)` 对应Release标签的源码快照，可能早于正式代码附件；`historical-before-*` 附件为历史备份。请勿混用代码ZIP与原始记录包的校验文件。

## 二、建议阅读顺序

1. `README.md`：研究范围、主要结果和目录结构。
2. `results/report.pdf`：计算方法、图表、筛选结果与解释边界。
3. `results/results.xlsx`及`results/results.csv`：结果工作簿与标准化候选清单。
4. `MODEL_CARD.md`：模型用途、输入输出、排序依据与已知局限。
5. `docs/VERSIONS.md`、`docs/ENVIRONMENT_VERIFICATION_SUPPLEMENT.md`及`REPRODUCE_FROM_ZERO.md`：环境证据和复现方法。
6. `SUBMISSION_COMPLIANCE.md`：附件5要求与材料位置的对应关系。
7. `docs/REPRODUCTION_TEST_20261003.md`：独立复现测试范围、实测通过步骤、入口修正及尚未验证的步骤；预检通过不等于端到端通过。
8. `environments/README.md`、`docs/FRESH_ENVIRONMENT_TEST_20261003.md`：RF/MPNN、Boltz及Windows工具的分别固定依赖、额外SE3源码版本、安装入口与独立依赖环境验收；不能将测试环境清单当作历史环境原件。

## 三、结果范围与编号

正式在线MMseqs2批次覆盖11至20 Å的初始端点距离，linker长度为10 aa。文件名中的 `11A` 至 `20A` 表示距离，不是linker长度。进入Boltz阶段的候选按每个候选3个结构模型组织；未进入该阶段的候选保留筛选记录。

| 记录层级 | 数量与位置 |
| --- | --- |
| 全部候选级记录 | 302条，`results/all_candidate_records.csv` |
| Boltz模型级记录 | 588条，`results/all_model_records.csv` |
| 正式候选清单 | 114条，`results/results.csv`；每行含RF骨架与3个Boltz模型的相对路径 |
| 高于基线的候选 | 22条，`results/top_candidates_above_baseline.csv` |
| Boltz结构 | 588个PDB，`results/structures/boltz2/` |

早期16 Å单序列MSA批次与正式在线16 Å批次分别保存，不合并为同一次计算。Vina分数为内部筛选指标，不等同于实验结合自由能；计算结构与排序不单独证明编辑活性。团队已开展配套湿实验，实验方法、原始数据、统计与结论由独立实验材料说明，不包含在本计算证据包内。

## 四、按流程定位资料

| 复核环节 | 代码、参数与结果位置 |
| --- | --- |
| 参考结构与初始位姿 | `references/`、`src/prepare_references.py`、`src/pose_generator.py` |
| RFdiffusion骨架生成 | `src/run_single_span.sh`、`results/structures/rfdiffusion/`、`logs/` |
| ProteinMPNN序列设计与QC | `src/pipeline_helper.py`、`results/proteinmpnn/`、`results/sequence_qc/` |
| MSA与Boltz-2预测 | `results/inputs/`、`results/structures/boltz2/`、`logs/`；完整MSA与数组见原始附件 |
| 在线MSA服务版本与调用溯源 | `docs/ONLINE_MSA_PROVENANCE.md`：客户端版本、服务端点、调用参数、时间记录边界及归档MSA对应 |
| Linker Cα RMSD | `results/rmsd/`、`src/pipeline_helper.py` |
| PT-179/MIQ对接与Vina门控 | `results/docking/`、`src/docking_helper.py` |
| SD40几何评分 | `ranker/`、`results/ranking/`、`results/results.csv` |
| 参数、随机种子与状态 | `src/pipeline_config.sh`、`results/inputs/`、`results/state/`、`logs/` |
| 跨距离筛选漏斗与图表 | `results/span_summary.csv`、`results/figures/`、`methods/` |
| 数据来源与第三方工具 | `data/README.md`、`DATA_SOURCES.md`、`THIRD_PARTY_SOFTWARE.md` |
| 模型权重获取与安装 | `models/README.md`、`src/setup_external_sources.sh`、`REPRODUCE_FROM_ZERO.md` |
| 环境证据与复现边界 | `docs/VERSIONS.md`、`docs/ENVIRONMENT_VERIFICATION_SUPPLEMENT.md`、`docs/REPRODUCIBILITY_STATUS.md` |
| 独立测试环境安装 | `environments/README.md`、`src/install_gpu_environment.sh`、`provenance/FRESH_ENVIRONMENT_TEST_20261003.json`；包括Python、GPU依赖、系统库与实际安装检查 |
| 文件完整性与来源 | `provenance/`、`validate_submission.py` |

## 五、完整原始记录下载对应

原始附件按距离分批，而非每个软件单独一个ZIP。查阅具体候选时，可先从结果清单确定距离与候选ID，再下载对应批次。

| 原始附件 | 内容 |
| --- | --- |
| `full-reproduction-online-11A.zip` 至 `full-reproduction-online-20A.zip`（10包） | 对应距离的RFdiffusion、ProteinMPNN、MSA、Boltz及后续筛选的原始产物与中间记录 |
| `full-reproduction-common-and-early-16A.zip`（1包） | 公共方法、环境版本说明、参考结构、早期16 Å单序列MSA批次、跨距离汇总及集中日志 |

精确文件名、大小、SHA256与原始目录对应见 `archive_reference/FULL_REPRODUCTION_ASSETS.csv`。完整归档复核时下载全部11包，校验后按 `archive_reference/README.md` 解压到同一空目录。集中日志与各批次内的索引副本不是额外独立任务。

原始附件不含第三方预训练权重、安装好的Conda环境、完整软件安装目录及私人身份材料。新环境核查报告所述导出文件与这些既有原始附件应区别对待，收录状态见下一节。

## 六、环境证据与复核范围

原归档提供主要软件版本、源码修订、参数与历史日志。2026-10-02团队补充核查报告记载：已定位原脚本指定环境，找到两份历史Python依赖锁文件，导出当前Conda与pip清单，并核实项目指定目录的MGLTools 1.5.7和Vina 1.1.2。

在线MSA使用Boltz 2.2.1调用ColabFold MMseqs2服务；服务地址与参数有记录，但未核实当时服务端软件和数据库快照版本。该版本不等同于Boltz版本，历史输入可通过归档MSA复核。详见 `docs/ONLINE_MSA_PROVENANCE.md`。

本次已收录报告的脱敏摘要。报告所述锁文件、环境导出及Git工作区差异等原始附件尚未随本次说明交付，不能据摘要独立验证全部依赖条目。当前导出也不等于计算当日的逐次快照。详细证据边界见 `docs/ENVIRONMENT_VERIFICATION_SUPPLEMENT.md`。

已提交结果的轻量重建、结构映射与文件检查已通过。2026-10-03进一步在新建RF/MPNN及Boltz依赖环境完成独立小样本端到端，覆盖RF、MPNN、在线MSA、6个Boltz模型、RMSD、6次Vina对接、Ranker和CSV/XLSX。环境安装、实际系统库、版本逐条核对、脱敏日志和小样本统计均已入包，见 `environments/README.md`、`docs/FRESH_ENVIRONMENT_TEST_20261003.md` 及 `provenance/FRESH_ENVIRONMENT_*_20261003.json`。

这轮复用基础解释器、操作系统、驱动和权重，不等于新机器、全量在线安装或全部历史批次重跑；历史锁文件原件仍待补交。在线MSA服务、GPU和数值内核变化可能影响新采样结果，不承诺坐标与评分逐位相同。

## 七、轻量结果复核

解压正式代码包，在包含 `README.md` 的目录打开终端。以下步骤不运行GPU模型。

Windows PowerShell：

```powershell
py -3 -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Linux或WSL：

```bash
python -m pip install -r requirements.txt
bash run.sh
```

成功时显示 `VALIDATION PASS`，并核对候选与模型记录、结构路径及相关文件。该结果仅代表检查脚本覆盖的项目通过，不等于重新运行模型或赛事官方验收。GitHub Actions执行同类轻量检查。

## 八、完整计算流程复核

按 `REPRODUCE_FROM_ZERO.md` 配置软件、权重与本地路径后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_full.ps1 -CheckOnly
powershell -ExecutionPolicy Bypass -File .\run_full.ps1 -Spans 15 -SmokeTest -OutputRoot 'E:\ADAR2_smoke_test'
```

完整入口覆盖：参考结构准备 → 初始位姿 → RFdiffusion → ProteinMPNN → 序列QC → MSA → Boltz-2 → Linker RMSD → Vina → SD40评分 → 标准化结果清单。

上面第二条为独立小样本：1个RF骨架、10条MPNN序列，选1条QC通过设计加baseline，每条3个Boltz模型。确需重跑完整距离批次时，再执行 `powershell -ExecutionPolicy Bypass -File .\run_full.ps1`。小样本与完整批次使用不同输出目录。在线MSA会向公共服务提交输入序列，运行前请确认允许提交；只阅读和轻量复核无需提交序列。

`-CheckOnly`仅检查路径与部分前置条件，不执行模型。所需资源、安装方法与当前验收边界以复现手册和环境说明为准。

入口默认发行版名为 `Ubuntu-22.04`。本次独立测试使用 `Ubuntu-26.04`，使用该环境时两条命令均需加 `-WslDistribution Ubuntu-26.04`；其他电脑以实际发行版名为准。多个Windows Python并存时，使用 `-WindowsPython` 指定已安装轻量依赖的解释器。
