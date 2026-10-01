# SD40 Linker Ranker v0.1

一个面向 `ADAR2-linker-SD40` 预测结构的轻量 CLI。它将候选中的 SD40 对齐到 8TNQ 的实验 SD40，计算三项几何指标并输出可排序的 CSV。

> 本工具用于第一轮结构优先级排序，不是结合自由能、动力学或实验活性的替代品。合成回环测试证明的是软件与指标行为正确，不代表已完成生物学验证。

## v0.1 做什么

对每个候选 PDB：

1. 按序列自动寻找 SD40，不依赖 chain ID 或 residue numbering。
2. 用共有 SD40 Cα 原子做 Kabsch 最小二乘对齐。
3. 计算 SD40 RMSD。
4. 从真实 8TNQ 自动提取 SD40–CRBN 参考残基接触，并计算候选恢复率。
5. 统计候选非 SD40 重原子与 8TNQ 中 CRBN + PT-179（`MIQ`）之间 `< 2 Å` 的冲突原子数。
6. 输出总分、分项分数、过滤结果与错误报告。

默认总分：

```text
Score = 100 × (0.3 × S_RMSD + 0.3 × S_contact + 0.4 × S_clash)
S_RMSD = 1 / (1 + (RMSD / 2 Å)^2)
S_contact = recovered_reference_contacts / reference_contacts
S_clash = 1 / (1 + clashing_atoms / 10)
```

所有阈值和权重都在 `config.yaml` 中。

## 重要修正：8TNQ 不是完整 36 aa 坐标

目标序列为：

```text
LLLFCPICGFTCRQKGNLLRHINLHTGEKLFKYHLY
```

它有 36 aa，但 8TNQ chain C 的已解析 `ATOM` 坐标只包含连续末端 35 aa：

```text
LLFCPICGFTCRQKGNLLRHINLHTGEKLFKYHLY
```

即目标的首个亮氨酸没有解析坐标。v0.1 因此保留“目标序列位置 → 实际残基”的映射，并允许达到 `min_sequence_coverage`（默认 85%）的最长连续精确片段。候选若含完整 36 aa，也会只用与参考都有坐标的位置进行对齐和接触比较。

## 安装

建议 Windows 使用 WSL2 + Ubuntu，或直接使用 Linux/macOS。Python 需要 3.10 以上。

```bash
cd sd40_linker_ranker_v0_1
conda create -n sd40-ranker python=3.11 -y
conda activate sd40-ranker
pip install -e .
```

开发/测试安装：

```bash
pip install -e ".[test]"
pytest -q
```

## 使用

压缩包已附带测试时使用的 `reference/8TNQ.pdb`，因此可离线直接运行。也可以重新下载：

```bash
sd40-linker-rank prepare --config config.yaml --force
```

把预测 PDB 放进 `candidates/`，务必加入现用 linker 作为基线：

```text
candidates/
├── current_linker.pdb
├── linker_001.pdb
├── linker_002.pdb
└── linker_003.pdb
```

执行：

```bash
sd40-linker-rank rank \
  --config config.yaml \
  --candidates candidates \
  --output outputs/ranking.csv
```

主要输出：

- `outputs/ranking.csv`：有效候选，按总分由高到低。
- `outputs/ranking_errors.csv`：不能解析、找不到 SD40 等无效候选；单个坏文件不会中断整批。

`passed_filters` 默认留空，因为 `filters.enabled: false`。有了首轮实验标定后再启用过滤：

```yaml
filters:
  enabled: true
  max_rmsd_angstrom: 2.5
  min_contact_recovery: 0.70
  max_clashing_atoms: 10
```

## 自带回环样例

`examples/loopback_candidates/` 含 7 个由真实 8TNQ 可重复生成的几何样例：参考样、刚体移动样、改 chain/编号样、轻度形变、重度形变、人工冲突和无效序列。

复现：

```bash
python devtools/generate_loopback_candidates.py \
  reference/8TNQ.pdb examples/loopback_candidates

sd40-linker-rank rank \
  --config config.yaml \
  --candidates examples/loopback_candidates \
  --output examples/loopback_outputs/ranking.csv
```

详细结果见 `VALIDATION_REPORT.md`。

## 结果怎么读

- 优先比较候选是否超过 `current_linker.pdb`，不要只看绝对分数。
- 首轮可选 Top 5–10 做实验，但应保留若干结构多样性，避免全部来自同一 linker 家族。
- 对接触恢复率与 RMSD 不要当作两个完全独立证据；两者都依赖 SD40 对齐，存在相关性。
- 高 clash 是明确警报；低 clash 只表示静态几何上未发现严重穿插，不代表构象一定可达。

## 能做与不能做

适合：

- 数十至数千个同类预测 PDB 的一致、可复现初筛。
- 检查 SD40 是否保持接近 8TNQ 的构象和界面。
- 检查 SD40 对齐后，ADAR2/linker 是否明显撞入 CRBN/PT-179。
- 用现用 linker 做相对基线。

目前不能回答：

- linker 的构象熵、溶液动力学和真实可达构象占比。
- PT-179/CRBN/SD40 的结合自由能或停留时间。
- ADAR2 是否处于有利 RNA 编辑方向。
- AlphaFold/ColabFold 置信度、PAE 或多模型一致性。
- 细胞活性、剂量响应、选择性或实验成功率。

## 推荐下一步

先运行“现用 linker + 5–20 个候选”，再把分数与 PT-179 响应或其他实验 readout 配对。v0.2 再根据数据加入阈值校准、PAE/pLDDT、多构象稳健性和界面能量指标。

## 项目结构

```text
sd40_linker_ranker_v0_1/
├── README.md
├── VALIDATION_REPORT.md
├── config.yaml
├── pyproject.toml
├── candidates/
├── reference/8TNQ.pdb
├── outputs/
├── examples/
│   ├── loopback_candidates/
│   └── loopback_outputs/
├── devtools/generate_loopback_candidates.py
├── src/sd40_linker_ranker/
│   ├── cli.py
│   ├── pdb_utils.py
│   └── scoring.py
└── tests/
```

## 数据来源

- 8TNQ：RCSB PDB 公共结构文件。
- 方法学为独立轻量实现；设计思路参考结构评分 CLI、配置化过滤和流水线筛选的常见工程模式。
