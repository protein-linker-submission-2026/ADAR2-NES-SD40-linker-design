# 运行环境补充核查说明

来源：团队提供的《核查说明.md》，正文标注2026-10-02（Asia/Shanghai）。本文件为面向评审的脱敏摘要，不是本次重新执行环境检测所得的记录。原报告含本机路径，未原样公开。

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

- 已收到并阅读：团队核查说明，本脱敏摘要据此补充。
- 尚未随说明交付：两份历史锁文件、安装记录、两套环境导出与Git工作区差异。收到后需脱敏、检查安装来源并建立文件清单。
- 未完成：全新环境端到端运行验收。原报告明确未执行重新安装或正式计算。

旧结论“原总压缩包中未找到完整环境导出”仅针对当时的包内内容，不应扩大为“原执行机器没有保存依赖清单”。依据新报告，应表述为“已报告找到原环境与历史锁文件，待补充原始附件完成独立复核”。
