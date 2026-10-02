# 实际环境版本（2026-09-12）

来源：原总包中的同名版本说明与历史运行日志，不是当前整理电脑的环境检测。版本说明属于归档记录，不能等同于已导出全部传递依赖的环境锁文件；原包内部关于“包含权重”的旧表述已在 `REPRODUCIBILITY_STATUS.md` 中更正。

| 组件 | 版本/修订 |
|---|---|
| Ubuntu | 22.04（WSL2；安装位置由使用者自行配置） |
| RFdiffusion | git `86507b6538f51fce57b5a72477165f03999ed7ae` |
| ProteinMPNN | git `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57` |
| boltz Python package | 2.2.1 |
| 实际预测模型 | Boltz-2（`--model boltz2`） |
| Boltz Python | 3.11.16 |
| PyTorch | 2.5.1+cu124 |
| DGL | 1.1.3+cu121 |
| AutoDock Vina | 1.1.2 |
| 11-20 Å正式主批次GPU | NVIDIA GeForce RTX 4070 Laptop GPU（由主批次日志记录） |
| 主批次GPU显存 | 8188 MiB（由批处理总控日志记录） |
| 早期本地核验GPU | NVIDIA GeForce RTX 4060 Laptop GPU；不与正式主批次混写 |
| 正式批次NVIDIA驱动 | 待原执行环境证据核实；不以整理电脑的驱动代替 |
| 正式批次CUDA驱动接口 | 待原执行环境证据核实；与下列PyTorch CUDA构建版本区分 |
| PyTorch CUDA构建 | 12.4（PyTorch 2.5.1+cu124） |
| WSL资源上限 | 20 GB RAM、28逻辑处理器、32 GB swap |

正式11-20 Å批次日志反复记录RTX 4070 Laptop GPU；早期本地核验曾使用RTX 4060 Laptop GPU，因此两类硬件证据分别披露。Boltz 的可选 cuequivariance kernel 因本环境 cuBLAS 版本约束而关闭，使用官方 `--no_kernels` 路径。完整批次的逐任务运行时间保留在 `logs/` 和完整复现附件的阶段日志中；不以单一总耗时替代这些记录。第三方权重和 Conda 环境不打包，应依据 `THIRD_PARTY_SOFTWARE.md` 中的官方来源获取。
