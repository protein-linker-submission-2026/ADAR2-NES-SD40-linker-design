# ADAR2–SD40 Linker Pipeline V2 源码验收报告

日期：2026-09-12。结论：清单34项源码要求全部落实；17项V2单元测试、Python编译、Bash语法、PowerShell语法和加强版`--check-only`均通过。本报告是源码/静态验收，不代表已经执行30次RFdiffusion或任何Boltz/Vina批量任务。

| 检查项 | 结论 | 实现证据 |
|---|---|---|
| 11–20 Å真实几何 | PASS | A393 NES末端Cα到输入A394（完整SD40第2位）Cα；实际PDB误差小于0.002 Å |
| 10 span×3 RF=30 | PASS | 固定循环11–20；design index/确定性seed均为0、1、2并写入backbone manifest |
| 10-aa linker和首L | PASS | RF `/11/` 后处理为A394–A403 linker+A404 LEU；强制A1–A439和完整SD40序列 |
| MPNN位置/数量/bias | PASS | 只设计394–403；10条/backbone；仅C−0.30、K/R−0.10非零 |
| Sequence QC | PASS | C≥2、5窗KR≥4、5窗ILVMFWY≥4、同聚物≥5；比例/电荷仅记录 |
| 判重 | PASS | `(rf_backbone_id, linker_sequence)` |
| Boltz关联和RMSD | PASS | 候选保存自己的rf_pdb_path；每个3模型取A394–A403十个Cα，严格`<2.0`且至少2/3 |
| 完整receptor | PASS | docking前强制连续A1–A439并核对ADAR/NES/SD40固定序列 |
| 动态box | PASS | 每个模型单独从A404–A439全部重原子计算，margin 5 Å/side；少一个残基即失败 |
| Vina | PASS | 32/9/3；确定性seed；每模型best score `<=−6.0`，候选至少2/3；16 Å历史结果保留原门槛说明 |
| ranker | PASS | active reference仍为8TNQ；正式公式已按后续决策更新为方案B（0.3/0.3/0.4），未增加新的评分项 |
| baseline | PASS | `GGGGSGGGGS`进入Boltz/docking/ranker，RF RMSD明确记录为not_applicable |
| 固定全扫描 | PASS | V2主源码无TARGET_PASS；legacy目录中的旧值不参与V2 |
| 测试覆盖 | PASS | 包含编号、QC边界、自己的RF关联、严格2/3、截短受体、动态box、margin、Vina边界、baseline和ranker正式方案B权重 |

执行边界：Linux端完成RF/MPNN/Boltz和RF RMSD；Windows端`run_docking.ps1`调用本机MGLTools/Vina；随后Linux端`--run-expensive ranker`收集通过Vina gate的模型。任何大计算都需要显式参数，不会由`--check-only`触发。
