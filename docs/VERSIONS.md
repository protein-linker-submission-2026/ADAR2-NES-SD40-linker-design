# 实际环境版本（2026-09-12）

来源：原总包中的同名版本说明与历史运行日志，不是当前整理电脑的环境检测。版本说明属于归档记录，不能等同于已导出全部传递依赖的环境锁文件；原包内部关于“包含权重”的旧表述已在 `REPRODUCIBILITY_STATUS.md` 中更正。

| 组件 | 版本/修订 |
|---|---|
| Ubuntu | 22.04.5 LTS（WSL2；提供方核查说明补充确认） |
| RFdiffusion | git `86507b6538f51fce57b5a72477165f03999ed7ae` |
| ProteinMPNN | git `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57` |
| boltz Python package | 2.2.1 |
| 实际预测模型 | Boltz-2（`--model boltz2`） |
| 在线MSA客户端 | Boltz 2.2.1；ColabFold MMseqs2服务调用 |
| MSA服务端软件/数据库版本 | 历史构建号与数据库快照未核实；服务地址、参数和归档MSA见 `ONLINE_MSA_PROVENANCE.md` |
| RFdiffusion/ProteinMPNN与Boltz Python | 3.11.16（两个Linux环境，提供方核查说明） |
| PyTorch | 2.5.1+cu124 |
| DGL | 1.1.3+cu121 |
| AutoDock Vina | 1.1.2 |
| MGLTools / AutoDockTools | 补充核查报告记载项目指定目录实测1.5.7；历史安装连续性未确认 |
| 11-20 Å正式主批次GPU | NVIDIA GeForce RTX 4070 Laptop GPU（由主批次日志记录） |
| 主批次GPU显存 | 8188 MiB（由批处理总控日志记录） |
| 早期本地核验GPU | NVIDIA GeForce RTX 4060 Laptop GPU；不与正式主批次混写 |
| NVIDIA驱动补充记录 | 核查报告称2026-09-10安装记录及当前查询均为610.62；不能断言所有正式批次使用同一版本 |
| 正式批次CUDA驱动接口 | 待原执行环境证据核实；与下列PyTorch CUDA构建版本区分 |
| PyTorch CUDA构建 | 12.4（PyTorch 2.5.1+cu124） |
| WSL资源上限 | 20 GB RAM、28逻辑处理器、32 GB swap |

2026-10-02提供方核查报告记载原路径环境仍存在，历史锁文件与当前清单除打包工具外一致；Ubuntu为22.04.5 LTS，MGLTools所用Python为2.7.11（32位）。团队于2026-10-03确认据此补充历史主要环境版本。所述完整依赖清单和工作区差异原件未收录，不将报告摘要表述为逐项独立复核的历史环境锁。详见 `ENVIRONMENT_VERIFICATION_SUPPLEMENT.md` 及 `../provenance/HISTORICAL_ENVIRONMENT_REPORTED_20261002.json`。独立复现测试使用另一套环境，见 `FRESH_ENVIRONMENT_TEST_20261003.md`。

正式11-20 Å批次日志反复记录RTX 4070 Laptop GPU；早期本地核验曾使用RTX 4060 Laptop GPU，因此两类硬件证据分别披露。Boltz 的可选 cuequivariance kernel 因本环境 cuBLAS 版本约束而关闭，使用官方 `--no_kernels` 路径。完整批次的逐任务运行时间保留在 `logs/` 和完整复现附件的阶段日志中；不以单一总耗时替代这些记录。第三方权重和 Conda 环境不打包，应依据 `THIRD_PARTY_SOFTWARE.md` 中的官方来源获取。
