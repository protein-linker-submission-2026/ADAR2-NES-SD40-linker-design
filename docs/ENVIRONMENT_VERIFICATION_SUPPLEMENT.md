# 运行环境补充核查说明

来源：团队转交的《核查说明.md》，正文标注2026-10-02（Asia/Shanghai）；团队于2026-10-03确认采用其中的环境记录。本文件作为提供方确认的历史环境说明收录，不是整理方重新执行历史环境检测所得的记录。原报告含本机路径，未原样公开。

原说明文件SHA256：`1c8dc072aa056ff6441dcfa9f8a780553ed66f316a7d395c18c46bab0a88ade2`。校验值仅用于识别本次依据的文件，不独立证明报告内容或历史运行状态。机器可读记录见 `../provenance/HISTORICAL_ENVIRONMENT_REPORTED_20261002.json`。

## 补充证据

报告称在原脚本指定的Ubuntu-22.04环境中找到设计与Boltz环境，未以另建的复验环境替代。此前保存的 `design_requirements.lock.txt`、`boltz_requirements.lock.txt` 和 `installation_status.md` 被复制至 `historical_evidence`。这些是报告所述证据名称，不表示原始文件已包含在当前代码包中。

| 项目 | 报告记录 | 证据边界 |
| --- | --- | --- |
| Python（两个Linux环境） | 3.11.16 | 当前读取与原版本表一致 |
| PyTorch / DGL | 2.5.1+cu124 / 1.1.3+cu121（设计环境） | 报告称历史锁文件与当前包清单一致 |
| Boltz | 2.2.1，模型Boltz-2 | 历史版本表、脚本与当前清单 |
| RFdiffusion / ProteinMPNN | 与 `VERSIONS.md` 的源码修订一致 | 另存 `working-tree.txt`；HEAD一致不证明工作区无修改 |
| MGLTools / AutoDockTools | 1.5.7；Python 2.7.11，32位 | 项目指定目录的版本文件与导入结果；更细构建号及历史安装连续性未确认 |
| AutoDock Vina | 1.1.2（May 11, 2011） | 原版本表与当前可执行文件输出一致 |
| NVIDIA驱动 | 610.62 | 正文标注2026-09-10的安装记录及当前查询一致；不是每个正式批次的驱动快照 |
| GPU | RTX 4070 Laptop GPU，8188 MiB | 报告称安装验收与当前查询一致；正式批次日志亦记录该GPU |
| Ubuntu | 22.04.5 LTS / WSL2 | 当前读取与历史安装记录相符 |

## 新导出记录的含义

报告称两个环境各导出 `environment.yml`、`conda-explicit.txt`、`conda-list.json`、`pip-freeze-all.txt`、`pip-list.json`、`conda-history.txt` 和 `python-version.txt`。与原有依赖锁文件相比，仅增加 `freeze --all` 所列的pip、setuptools、wheel三项，其余条目一致。此结论来自报告描述，本次尚未获得原始文件逐项复核。

当前导出不是计算当日快照。Conda显式清单仅覆盖Conda管理的包，pip包需另行记录；Git、editable和本地wheel引用仍依赖源码或安装文件。因此环境清单不等于离线一键重建包，亦不证明完整流程重新安装运行通过。

## 收录与核验状态

- 已收录：经团队确认的提供方历史环境记录，包含上表主要版本、源码修订、硬件与报告中的核验结论。
- 本包未收录的底层文件：两份历史锁文件、安装记录、两套环境导出与Git工作区差异。团队目前仅持有转交的说明，故不将这些文件列为已交付附件，也不据主要版本编造完整依赖锁。
- 原报告未执行重新安装或正式计算。另行完成的独立依赖环境小样本测试见 `FRESH_ENVIRONMENT_TEST_20261003.md`；该测试环境与历史环境不同，不替代历史证据。

旧结论“原总压缩包中未找到完整环境导出”仅针对包内内容，不表示历史文件丢失或原执行机器没有保存依赖清单。当前正式表述为：历史主要环境版本已依据提供方核查说明及团队确认补充；完整依赖及工作区差异的底层原件未收录，未进行逐项独立复核。复现安装请使用 `../environments/README.md` 的已测试方案，不把本报告摘要当作可直接安装的锁文件。
