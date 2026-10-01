# 实际环境版本（2026-09-12）

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
| WSL资源上限 | 20 GB RAM、28逻辑处理器、32 GB swap |

Boltz 的可选 cuequivariance kernel 因本环境 cuBLAS 版本约束而关闭，使用官方 `--no_kernels` 路径。权重在 `weights/` 内；Conda 环境本身不打包。
