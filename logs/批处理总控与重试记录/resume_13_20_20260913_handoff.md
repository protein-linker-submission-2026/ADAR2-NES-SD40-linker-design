# 13–20 Å 接续运行记录

- 启动时间：2026-09-13 02:22:34 +08:00。
- Windows 调度器 PID：41824（后续必须核对命令行与进程，PID可能复用）。
- 启动包装：`${PROJECT_ROOT}\_batch_control\resume_13_20_20260913.ps1`。
- 原调度器参数：`-Spans @(13,14,15,17,18,19,20)`，进入17前执行16历史重评分。
- stdout：`${PROJECT_ROOT}\_batch_control\resume_13_20_20260913_022234_stdout.log`。
- stderr：`${PROJECT_ROOT}\_batch_control\resume_13_20_20260913_022234_stderr.log`。
- 13 Å 运行前完整目录备份：`${PROJECT_ROOT}\_batch_control\backup_13_before_resume_20260913_022206`。
- 启动前未发现活动旧计算进程；13 Å 原生dry-run通过；16A_protected_before.sha256逐文件校验通过。
- 13 Å 清单26个设计候选及1个基线；首候选3个模型和RMSD评估已存在；恢复后日志确认第2/27项使用已处理输入启动Boltz。
- 没有改变科学参数或原流水线源码，只新增固定批次启动包装。现有流水线负责数值计算和报告生成。
- 当前任务监控：adar2-11-20，已迁到01a096d5-1065-7053-bb0c-09c878531651。工具将间隔规范化为20分钟。现有有限重试耗尽或调度器退出时报告并暂停监控，不自动无限恢复。
- 结果尚未全部完成；完成标记不能替代候选/模型完整性、RMSD/Vina/排名一致性及Excel公式/视觉验收。报告使用既有artifact-tool生成器；本轮已登记预计9个xlsx输出。后续验收按Spreadsheets技能检查生成文件，不重设计模板。
- 全部完成后核验16A_protected_before/after.sha256一致、跨距离汇总和各距离产物，再交付并暂停监控。
