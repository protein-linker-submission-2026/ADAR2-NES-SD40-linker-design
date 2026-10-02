# 在线MSA服务与版本记录

本节说明正式11至20 Å批次使用的在线序列检索步骤。MSA为多序列比对；此步骤由Boltz客户端调用ColabFold的MMseqs2服务生成输入特征，结构预测则在GPU环境执行，不是网页搜索或在线Boltz结构预测。

## 已记录的调用信息

| 项目 | 记录 | 证据位置 |
| --- | --- | --- |
| 本地客户端 | Boltz Python包2.2.1；结构预测模型Boltz-2 | `docs/VERSIONS.md`、`THIRD_PARTY_SOFTWARE.md` |
| 在线服务 | ColabFold MMseqs2 API | `src/pipeline_config.sh`、各批次Boltz日志 |
| 端点 | `https://api.colabfold.com` | `results/inputs/11A/run_parameters.txt`，其他在线批次同类参数文件 |
| 输入 | 每个候选的完整439-aa融合蛋白序列，单个蛋白实体；不是只提交10-aa linker | 各批次输入YAML及Boltz日志 |
| 启用方式 | `--use_msa_server --msa_server_url "$MSA_SERVER_URL"` | `src/run_single_span.sh` |
| 配对策略参数 | `--msa_pairing_strategy greedy` | 同一脚本及日志的 `MSA pairing strategy: greedy`；记录参数不意味着单链任务发生了多链配对 |
| 使用时间 | 正式批次为2026年9月；具体批次与执行记录见 `logs/` | 保留日志中已有日期、批次ID及任务ID；不能以文件修改时间代替API调用时间 |
| 提交和重试过程 | 日志保存SUBMIT、PENDING、RUNNING、COMPLETE及部分网络重试输出 | `logs/11-20A_在线MSA批次/`内各距离的 `04_logs/boltz2/` |
| 返回结果 | 原始MSA及相关中间文件保留在Release对应距离的完整记录ZIP中 | `archive_reference/FULL_REPRODUCTION_ASSETS.csv` |

可直接核查的示例日志：

`logs/11-20A_在线MSA批次/11A/04_logs/boltz2/span11A_design_0_s01_SLPTLFEEGE.log`

其中记录了服务地址、单个蛋白实体、配对策略与服务完成状态。但该任务日志并未为每一次API提交提供绝对时间戳，不能从相对进度时间推导精确调用日期。应与批处理总控记录联合阅读，不补造缺失的时间戳。

## 未核实的历史版本

- 服务端MMseqs2程序版本/构建号：本次检查的归档记录中未找到可核实信息。
- 服务端ColabFold部署版本/提交号：未找到可核实信息。
- 服务端检索数据库的精确版本及快照日期：未找到可核实信息。

Boltz 2.2.1是客户端版本，不是上述服务器或数据库的版本。当前官网或当前服务公布的版本不能追填为2026年9月的实际部署版本。数据库文件名或命中序列ID也不能单独证明完整数据库快照版本。此处如实标为未知，而非擅自指定版本。

## 历史输入复核

1. 按候选ID确定距离，下载对应的 `full-reproduction-online-NNA.zip`（NN为11至20）。
2. 先按 `FULL_REPRODUCTION_SHA256SUMS.txt` 验证ZIP，再按 `FULL_REPRODUCTION_ASSETS.csv` 和包内目录定位该候选的输入YAML、返回MSA与日志。
3. 公共包 `full-reproduction-common-and-early-16A.zip` 中的原归档 `文件清单.csv` 与 `SHA256SUMS.txt` 提供文件级溯源；包级SHA256用于确认下载内容未变，不用于证明服务端版本。
4. 核对候选ID、输入序列及MSA查询序列的一致性。已有归档MSA是复核历史输入的依据；重新联网生成的MSA应另存为新运行记录，不覆盖旧文件。

完整流水线当前仍使用在线MSA调用。若改为读取归档MSA，需要另行配置输入并验证流程，不能把资料归档误写为已完成离线重跑。固定MSA也不能保证不同GPU或数值环境得到逐位相同的结构。

## 软件方法参考

- Boltz的MSA服务调用与预计算MSA输入说明：https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md
- ColabFold项目：https://github.com/sokrypton/ColabFold

上述链接用于说明软件方法，不作为历史服务部署版本的证据。
