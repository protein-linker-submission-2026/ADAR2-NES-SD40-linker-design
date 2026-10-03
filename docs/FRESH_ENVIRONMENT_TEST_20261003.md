# 独立依赖环境验收（2026-10-03）

本文补充上一轮 `REPRODUCTION_TEST_20261003.md`，不改写原有测试或历史生产记录。

## 验收范围

在独立磁盘目录新建RF/MPNN和Boltz两个venv，不启用system-site-packages。使用已安装的精确版本Python作为基础解释器，从原始wheel安装包重新安装依赖；没有复制旧环境的site-packages。安装曾中断，保留日志并续装，最终状态以完成检查及实际推理记录为准。

复用现有操作系统、Windows NVIDIA驱动、基础Python解释器、固定提交的外部源码、已下载预训练权重和Windows对接工具。因此这不是新操作系统/驱动安装验收，也不是完全离线的新机器验收。正常Conda创建解释器及全部依赖联网下载分支未完整实测。历史主要版本已按提供方核查说明及团队确认另行收录，历史生产依赖锁原件未收录；见 `ENVIRONMENT_VERIFICATION_SUPPLEMENT.md`。

## 文件与环境对应

| 文件 | 用途 |
| --- | --- |
| `environments/rfdiffusion-test-pins.txt` | RF/MPNN独立测试依赖，Python 3.9.23 |
| `environments/boltz-test-pins.txt` | Boltz独立测试依赖，Python 3.11.16 |
| `environments/windows_review_venv-test-pins.txt` | Windows轻量核验、汇总与排序依赖，Python 3.12.14 |
| `src/install_gpu_environment.sh` | 独立环境安装入口；拒绝覆盖已有环境 |
| `src/check_environment_isolation.py` | 关键模块导入来源、CUDA、pip依赖一致性及系统库检查 |

这些是本次测试版本清单，不是历史生产锁文件。RF和SE3Transformer通过固定源码提交安装；Conda、驱动、软件安装目录、模型权重及wheel二进制不打入参赛代码ZIP。

## DGL构建核对

缓存中的DGL与当前官方同版本文件大小不同，因此不能只凭版本号断定构建一致。本次先保留缓存构建的安装记录，随后从官方地址重新下载并替换测试环境的DGL，再做检查和推理。依赖清单对该官方文件加入SHA256，离线安装入口也核对这一哈希。

- 官方URL：`https://data.dgl.ai/wheels/torch-2.4/cu121/dgl-2.4.0%2Bcu121-cp39-cp39-manylinux1_x86_64.whl`
- 文件大小：355172350字节。
- SHA256：`c2e9f089e52f6788553a6478fe9872cd96728a61f66f603356dc46fcb254efcf`。

其余依赖目前为版本固定清单，不应将其称作所有平台的完整二进制哈希锁。安装包清单仅描述测试时可用的原始wheel池，不代表每个包都装入每个环境。

## 实测状态

RF及Boltz两个新依赖环境均已通过安装、关键模块隔离检查、pip check及CUDA张量运算；RF还完成了官方DGL替换后的重复检查。逐条核对76项RF依赖与96项Boltz依赖均符合版本清单。额外源码安装包、pip/setuptools/wheel的实际版本也记录在快照中。

证据：`provenance/FRESH_ENVIRONMENT_TEST_20261003.json`、`provenance/FRESH_INSTALL_rfdiffusion_20261003.txt`、`provenance/FRESH_INSTALL_boltz_20261003.txt`。可用wheel池记录在 `provenance/TEST_WHEELHOUSE_INVENTORY_20261003.json`，其中旧缓存DGL不是最终推理所用的官方文件；实际采用的官方文件在前述环境证据中单独列明。

独立小样本端到端已通过，完整入口退出码为0，显示 `FULL PIPELINE COMPLETE`。中途会话中断后从本次独立目录续跑，复用的是这一轮刚算出的结果，不是历史正式批次。

| 环节 | 实测结果 |
| --- | --- |
| RFdiffusion | 新生成1个骨架，50步，5.71分钟，校验为439 aa |
| ProteinMPNN及QC | 新生成10条去重序列，4条通过QC，选首条通过设计加baseline |
| 在线MSA及Boltz | 两条输入，每条3模型、200采样步，合计6模型；num_workers=0 |
| RMSD与Vina | 新设计3模型均通过RMSD和Vina门控；合计完成6模型对接 |
| Ranker与汇总 | 6模型评分，生成CSV/XLSX；1条测试候选、11条候选记录和6条模型记录 |
| 回归检查 | 17项单元测试通过，包含安装清单、DGL错误内容拒绝、局部环境排除扫描及原有流程/数学检查 |

测试设计 `span15A_design_0_s01_EEEKKEKEEK` 的linker Cα RMSD分别为0.93015、0.74548、0.36592 Å，Vina分数为−7.9、−6.5、−7.6 kcal/mol，Ranker中位数为44.1515。机器可读统计及产物校验值见 `provenance/FRESH_ENVIRONMENT_SMOKE_20261003.json`。这条测试设计未并入原114条正式候选。

当前证据支持“独立Python依赖环境重建和小样本计算流程通过”，不支持“所有操作系统/驱动与在线安装分支均验证”“历史环境原件齐全”或“全部历史距离批次逐位重现”。上述未验证事项仍应保留披露。
