# V2 批量计算前静态验收报告（历史记录）

本文件记录正式批量计算启动前的代码与输入预检，保留用于审计，不代表当前最终计算状态。最终仓库已经包含完成后的候选表、588 个 Boltz-2 结构模型及各阶段结果；当前完整性状态以仓库根目录的验证脚本、结果清单和 Release 复现附件为准。

- 日期：2026-09-12（Asia/Shanghai）
- V2单元测试：17/17 通过。
- `run_pipeline.sh --check-only`：通过。
- SnapGene：ADAR2DD(E488Q) 384 aa、NES 9 aa、SD40 36 aa均与代码常量一致。
- 5ED1：chain A residues 317–700，连续384个坐标残基，与SnapGene ADAR2DD(E488Q)序列一致。
- 8TNQ：chain C residues 16–50，共35个坐标残基，严格等于完整SD40第2–36位。
- RF输入 pose：11–20 Å 共10个，spin=0°，每个428个固定坐标残基。
- 计划网格：10 × 3 = 30个RF backbone；10条MPNN序列/backbone，最大300条。
- 候选关联：保存rf_backbone_id、rf_pdb_path、target span、design index和RF seed；3个Boltz模型逐一与自己的RF骨架比较。
- RMSD gate：A394–A403共10个Cα，严格 `<2.0 Å`，至少2/3通过；2.0恰好判失败。
- Vina静态参数：exhaustiveness 32、num_modes 9、energy_range 3；完整439-aa receptor校验、逐模型动态36-aa SD40 box和 `<=-6.0` 的2/3 gate均已实现。16 Å历史结果仍按当时的−7.0门槛解释。
- baseline：`GGGGSGGGGS`进入下游，RF RMSD明确为not_applicable。
- 当时状态（2026-09-12）：尚未启动 RFdiffusion、ProteinMPNN、Boltz-2 或 Vina 批量任务。

测试明确覆盖：首个L丢失、SD40误写35 aa、A404误计入linker、438-aa候选、固定区被ProteinMPNN修改、候选与自己的RF骨架关联、RMSD 2/3边界、baseline不伪造RMSD、截短receptor拒绝、逐模型动态box、5 Å margin、Vina 2/3边界、QC规则、ranker参考/公式及确定性Vina seed。
