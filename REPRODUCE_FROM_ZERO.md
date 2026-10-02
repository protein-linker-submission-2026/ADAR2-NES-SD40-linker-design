# 从零复现完整流程

## 目的与复现边界

本手册对应项目“AI辅助设计RNA编辑器连接肽优化”，用于从一台新机器重建计算环境并执行完整的设计、优化、结构预测、门控和排序流程。项目没有自行训练或微调模型，因而不存在训练入口、训练集划分或自训练权重；RFdiffusion、ProteinMPNN和Boltz-2使用公开预训练模型，Vina用于对接筛选。

仓库不重复分发第三方软件、预训练权重、Conda环境和缓存。附件5允许提供模型权重或调用方式；本仓库固定第三方版本、提供官方获取脚本、记录关键参数，并保留实际输出和日志。在线MMseqs2服务、GPU型号和底层CUDA差异可能造成浮点级或采样级差异，因此复现目标是得到相同流程、字段、门控逻辑和可比较候选，不承诺每个坐标和分数逐位相同。

## 1 计算机要求

- Windows 10或11，启用WSL2和Ubuntu 22.04。
- NVIDIA GPU；正式11至20 Å批次记录为RTX 4070 Laptop GPU 8188 MiB。
- 建议至少20 GB内存、32 GB交换空间和68 GiB可用磁盘空间。
- WSL内能够访问GitHub、模型权重地址和 `https://api.colabfold.com`。
- Windows侧安装PowerShell、Python 3、AutoDock Vina 1.1.2和MGLTools 1.5.x。

实际生产环境与版本见 `docs/VERSIONS.md`。如果只核验已提交结果，无需GPU，执行根目录 `run.ps1` 或 `run.sh` 即可。

## 2 获取项目

在Windows PowerShell中执行：

```powershell
git clone https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design.git
cd ADAR2-NES-SD40-linker-design
```

不要把仓库放在C盘空间不足的位置。可直接克隆到D盘或E盘，例如：

```powershell
cd E:\
git clone https://github.com/protein-linker-submission-2026/ADAR2-NES-SD40-linker-design.git
```

## 3 安装WSL与GPU支持

管理员PowerShell：

```powershell
wsl --install -d Ubuntu-22.04
wsl --update
```

重启后进入Ubuntu并检查：

```bash
nvidia-smi
lsb_release -a
```

必须先让 `nvidia-smi` 在WSL中正确显示GPU，再安装模型环境。本项目不会在WSL中另装Windows显卡驱动。

## 4 安装Miniconda或Mambaforge

在WSL中安装Conda后，确认：

```bash
conda --version
python --version
```

建议为RFdiffusion和Boltz-2分别使用独立环境，避免DGL、PyTorch和CUDA依赖互相覆盖。

## 5 获取固定版本源码和RFdiffusion权重

进入克隆后的仓库目录，然后执行：

```bash
cd <repository-directory>
bash src/setup_external_sources.sh
```

脚本执行以下操作：

- RFdiffusion固定到提交 `86507b6538f51fce57b5a72477165f03999ed7ae`；
- ProteinMPNN固定到提交 `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57`；
- 下载RFdiffusion正式流程使用的 `Base_ckpt.pt`；
- 检查ProteinMPNN的 `v_48_020.pt`。

网络中断时可重复运行，RFdiffusion权重下载支持续传。所有来源和许可见 `THIRD_PARTY_SOFTWARE.md`。

## 6 建立RFdiffusion环境

按固定提交中的官方环境文件安装：

```bash
cd external/RFdiffusion
conda env create -f env/SE3nv.yml -n rfdiffusion
conda activate rfdiffusion
cd env/SE3Transformer
python -m pip install --no-cache-dir -r requirements.txt
python setup.py install
cd ../..
python -m pip install -e .
python scripts/run_inference.py --help
```

ProteinMPNN在本次实际流程中复用这个已验证的PyTorch环境：

```bash
cd ../ProteinMPNN
python protein_mpnn_run.py --help
```

若固定提交的官方环境安装说明与本机CUDA不兼容，应保留固定源码和权重不变，仅调整PyTorch/CUDA构建，并在复现记录中注明偏差。

## 7 建立Boltz-2环境

```bash
conda create -n boltz python=3.11 -y
conda activate boltz
python -m pip install "boltz[cuda]==2.2.1"
boltz predict --help
```

首次预测会把Boltz-2模型和分子缓存下载到 `BOLTZ_CACHE`。完整流程使用：

- `--model boltz2`
- `--recycling_steps 3`
- `--sampling_steps 200`
- `--diffusion_samples 3`
- `--max_parallel_samples 1`
- `--write_full_pae`
- `--use_potentials`
- `--no_kernels`
- `--use_msa_server`
- MMseqs2地址 `https://api.colabfold.com`

## 8 配置WSL本机路径

```bash
cp src/local_paths.example.sh src/local_paths.sh
nano src/local_paths.sh
```

至少核对以下变量：

```bash
RFDIFFUSION_DIR="$PACKAGE_ROOT/external/RFdiffusion"
RFDIFFUSION_PYTHON="$HOME/miniconda3/envs/rfdiffusion/bin/python"
PROTEIN_MPNN_DIR="$PACKAGE_ROOT/external/ProteinMPNN"
PROTEIN_MPNN_PYTHON="$RFDIFFUSION_PYTHON"
BOLTZ_PYTHON="$HOME/miniconda3/envs/boltz/bin/python"
BOLTZ_EXE="$HOME/miniconda3/envs/boltz/bin/boltz"
BOLTZ_CACHE="$PACKAGE_ROOT/cache/boltz"
```

`src/local_paths.sh` 已加入 `.gitignore`，不会把个人目录上传到仓库。

## 9 安装Windows对接工具

安装AutoDock Vina 1.1.2和MGLTools 1.5.x。把Vina目录加入Windows `PATH`，并在每个新PowerShell窗口设置：

```powershell
$env:ADT_PYTHON='C:\Program Files (x86)\MGLTools-1.5.7\python.exe'
$env:ADT_UTILITIES='C:\Program Files (x86)\MGLTools-1.5.7\Lib\site-packages\AutoDockTools\Utilities24'
$env:VINA_EXE='vina.exe'

vina.exe --help
Test-Path $env:ADT_PYTHON
Test-Path $env:ADT_UTILITIES
```

如安装目录不同，按实际路径修改。对接准备必须使用完整的A1至A439受体；脚本会拒绝残缺结构。每个Boltz模型都以36个SD40残基的重原子范围加每侧5 Å边距构建独立盒子。

## 10 预检

在仓库根目录的Windows PowerShell中执行：

```powershell
py -3 -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\run_full.ps1 -CheckOnly
```

预检检查WSL发行版、GPU、磁盘、固定参考结构、RFdiffusion、ProteinMPNN、Boltz、Windows Python、Vina和MGLTools。任何一项失败都应先修正，不要直接启动批量计算。

## 11 完整运行

默认扫描11至20 Å：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_full.ps1
```

把结果放到E盘：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_full.ps1 `
  -OutputRoot 'E:\ADAR2_reproduction_runs'
```

先复现单个距离：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_full.ps1 `
  -Spans 15 `
  -OutputRoot 'E:\ADAR2_reproduction_test'
```

完整入口顺序执行：

1. 验证并准备5ED1 ADAR2DD(E488Q)、NES、8TNQ SD40和MIQ参考结构。
2. 生成11至20 Å、spin 0°的初始位姿。
3. 每个距离运行3个RFdiffusion骨架。
4. 每个骨架由ProteinMPNN生成10条linker序列，只设计A394至A403。
5. 去重并执行K/R比例、疏水比例、净电荷等序列QC。
6. 通过在线MMseqs2生成MSA。
7. 每条候选由Boltz-2生成3个完整融合蛋白模型。
8. 以linker Cα RMSD严格小于2.0 Å为单模型门槛，3个模型至少2个通过。
9. 用Vina对PT-179/MIQ进行对接，best score不高于−6.0 kcal/mol，3个模型至少2个通过。
10. 计算SD40 RMSD、接触恢复和原子冲突，按0.3、0.3、0.4权重评分。
11. 生成标准化 `results.csv`、`results.xlsx`、全候选表、全模型表和距离汇总表。

脚本按输出文件和完成标记断点续跑。不要删除已经完成的跨度目录；重复执行同一命令会复用已完成的中间产物。

## 12 输出位置

默认输出在：

```text
reproduction_runs/
  11/ ... 20/                 每个距离的完整阶段产物
  _shared/                    在线MSA基准结构复用目录
  final/
    results.csv               标准化最终候选清单
    results.xlsx              阅读版工作簿
    all_candidate_records.csv 全候选级记录
    all_model_records.csv     全模型级记录
    span_summary.csv          各距离筛选漏斗
```

每个距离目录保存输入、RFdiffusion、ProteinMPNN、MSA、Boltz-2、RMSD、Vina、Ranker和日志，不依赖个人绝对路径解释结果。

## 13 快速核验已提交结果

如果评委只需要确认上传材料内部一致性：

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

该命令重建 `results/results.csv` 并运行完整性和匿名性检查。它不会重新执行GPU模型，因此通常在5分钟内完成。

## 14 结果解释与限制

- RFdiffusion和Boltz-2结构是计算模型，不是实验结构。
- Linker RMSD表示Boltz预测与RF骨架的一致性，不等于编辑活性。
- Vina分数用于内部筛选，不是实验结合自由能。
- 候选排序不能证明表达、稳定性、定位、编辑效率、特异性或安全性。
- 本代码包用于复现计算设计与筛选流程，不包含湿实验操作或原始实验数据；计算指标不得脱离配套实验材料单独写成已验证疗效或机制。
