import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputRoot = process.env.ADAR2_SD40_OUTPUT_ROOT || process.cwd();
const payloadPath = `${outputRoot}/00_阅读说明/workbook_payload.json`;
const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const workbook = Workbook.create();
const fontFamily = "Microsoft YaHei";
const navy = "#3F3F3F";
const blue = "#5B7F78";
const teal = "#2A9D8F";
const gold = "#E9C46A";
const light = "#F2F2F2";
const border = "#D9D9D9";
const gridBorder = { preset: "all", style: "thin", color: "#808080" };

function colName(n) {
  let s = "";
  while (n > 0) {
    n--;
    s = String.fromCharCode(65 + (n % 26)) + s;
    n = Math.floor(n / 26);
  }
  return s;
}

function recordsMatrix(records, preferredColumns = null) {
  if (!records.length) return { headers: [], rows: [] };
  const headers = preferredColumns || Object.keys(records[0]);
  const rows = records.map((record) => headers.map((key) => {
    const value = record[key];
    if (typeof value === "boolean") return value ? "是" : "否";
    return value === undefined || value === null || Number.isNaN(value) ? null : value;
  }));
  return { headers, rows };
}

function formatHeader(range) {
  range.format = {
    fill: "#FFFFFF",
    font: { name: fontFamily, size: 10, bold: true, color: "#000000" },
    verticalAlignment: "center",
    horizontalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#808080" },
  };
  range.format.rowHeight = 30;
}

function addDataSheet(name, records, options = {}) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const { headers, rows } = recordsMatrix(records, options.columns || null);
  const displayHeaders = options.displayHeaders || headers;
  if (!headers.length) return sheet;
  const lastCol = colName(headers.length);
  const title = options.title || name;
  sheet.mergeCells(`A1:${lastCol}1`);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: "#FFFFFF",
    font: { name: fontFamily, size: 16, bold: true, color: "#000000" },
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${lastCol}1`).format.rowHeight = 34;
  if (options.note) {
    sheet.mergeCells(`A2:${lastCol}2`);
    sheet.getRange("A2").values = [[options.note]];
    sheet.getRange(`A2:${lastCol}2`).format = {
      fill: "#FFFFFF",
      font: { name: fontFamily, size: 9, color: "#333333" },
      verticalAlignment: "center",
      wrapText: true,
    };
    sheet.getRange(`A2:${lastCol}2`).format.rowHeight = 28;
  }
  sheet.getRange(`A4:${lastCol}4`).values = [displayHeaders];
  formatHeader(sheet.getRange(`A4:${lastCol}4`));
  if (rows.length) {
    sheet.getRange(`A5:${lastCol}${rows.length + 4}`).values = rows;
    const body = sheet.getRange(`A5:${lastCol}${rows.length + 4}`);
    body.format.font = { name: fontFamily, size: options.fontSize || 9 };
    body.format.fill = "#FFFFFF";
    body.format.borders = gridBorder;
    body.format.rowHeight = 20;
    body.format.verticalAlignment = "center";
    body.format.wrapText = options.wrapText ?? false;
    if (options.table !== false) {
      const table = sheet.tables.add(`A4:${lastCol}${rows.length + 4}`, true, options.tableName || `${name.replace(/[^A-Za-z0-9]/g, "")}Table`);
      table.style = "TableStyleLight1";
      table.showFilterButton = true;
      body.format.fill = "#FFFFFF";
      body.format.borders = gridBorder;
      formatHeader(sheet.getRange(`A4:${lastCol}4`));
    }
  }
  sheet.freezePanes.freezeRows(4);
  sheet.freezePanes.freezeColumns(options.freezeColumns || 1);
  const used = sheet.getRange(`A4:${lastCol}${Math.min(rows.length + 4, 300)}`);
  used.format.autofitColumns();
  for (let c = 0; c < headers.length; c++) {
    const range = sheet.getRange(`${colName(c + 1)}:${colName(c + 1)}`);
    const header = headers[c];
    let width = 15;
    if (/candidate_id|relative_path|qc_reasons|usage|source/i.test(header)) width = 34;
    if (/sequence|linker/i.test(header)) width = 19;
    if (/sha256/i.test(header)) width = 24;
    if (/modified/i.test(header)) width = 22;
    if (/status|stage|batch/i.test(header)) width = 19;
    range.format.columnWidth = width;
  }
  return sheet;
}

const summary = workbook.worksheets.add("摘要");
summary.showGridLines = false;
summary.mergeCells("A1:J2");
summary.getRange("A1").values = [["ADAR2 NES SD40 Linker 设计中期结果总汇"]];
summary.getRange("A1:J2").format = {
  fill: "#FFFFFF",
  font: { name: fontFamily, size: 20, bold: true, color: "#000000" },
  verticalAlignment: "center",
  horizontalAlignment: "center",
};
summary.getRange("A4:J4").values = [["分析范围", "11–20 Å 在线 MMseqs2 批次", null, "结构预测", "每候选 3 个 Boltz-2 模型", null, "基线", "GGGGSGGGGS", null, null]];
summary.getRange("A4:J4").format = { fill: "#FFFFFF", font: { name: fontFamily, size: 10, bold: true }, verticalAlignment: "center" };
const spanRows = payload.span_summary;
const topRows = payload.top_candidates;
const uniqueTotal = spanRows.reduce((a, r) => a + Number(r.mpnn_unique || 0), 0);
const modelTotal = spanRows.reduce((a, r) => a + Number(r.boltz_models || 0), 0);
const rmsdTotal = spanRows.reduce((a, r) => a + Number(r.rmsd_pass_design || 0), 0);
const vinaTotal = spanRows.reduce((a, r) => a + Number(r.vina_pass_design || 0), 0);
const kpis = [
  ["MPNN 去重序列", uniqueTotal, "Boltz-2 模型", modelTotal, "RMSD通过候选", rmsdTotal, "Vina通过候选", vinaTotal, "优于基线", topRows.length],
];
for (let i = 0; i < 5; i++) {
  const c1 = colName(i * 2 + 1);
  const c2 = colName(i * 2 + 2);
  summary.getRange(`${c1}6:${c2}6`).merge();
  summary.getRange(`${c1}6`).values = [[kpis[0][i * 2]]];
  summary.getRange(`${c1}7:${c2}7`).merge();
  summary.getRange(`${c1}7`).values = [[kpis[0][i * 2 + 1]]];
  summary.getRange(`${c1}6:${c2}6`).format = { fill: "#FFFFFF", font: { name: fontFamily, bold: true, color: "#000000" }, horizontalAlignment: "center", verticalAlignment: "center" };
  summary.getRange(`${c1}7:${c2}7`).format = { fill: "#FFFFFF", font: { name: fontFamily, size: 18, bold: true, color: "#000000" }, horizontalAlignment: "center", verticalAlignment: "center" };
}
summary.getRange("A9:J9").merge();
summary.getRange("A9").values = [["头部候选"]];
summary.getRange("A9:J9").format = { fill: "#FFFFFF", font: { name: fontFamily, bold: true, color: "#000000" } };
summary.getRange("A10:F10").values = [["排名", "距离 Å", "Linker", "最终分", "高于基线", "Linker RMSD中位数 Å"]];
formatHeader(summary.getRange("A10:F10"));
const top10 = topRows.slice(0, 10).map((r, i) => [i + 1, r.target_span_A, r.linker_sequence, r.final_score_median, r.score_minus_baseline, r.linker_rmsd_median_A]);
summary.getRange(`A11:F${10 + top10.length}`).values = top10;
summary.getRange(`A11:F${10 + top10.length}`).format.font = { name: fontFamily, size: 10 };
summary.getRange(`A10:F${10 + top10.length}`).format.borders = gridBorder;
summary.getRange(`A11:F${10 + top10.length}`).format.verticalAlignment = "center";
summary.getRange(`A11:B${10 + top10.length}`).format.horizontalAlignment = "center";
summary.getRange(`D11:F${10 + top10.length}`).format.horizontalAlignment = "center";
summary.getRange(`D11:F${10 + top10.length}`).format.numberFormat = "0.0000";
summary.getRange("H10:J10").values = [["关键规则", "操作符", "阈值"]];
formatHeader(summary.getRange("H10:J10"));
summary.getRange("H11:J15").values = [
  ["Linker Cα RMSD", "<", "2.0 Å"],
  ["RMSD候选通过", ">=", "2/3 模型"],
  ["在线Vina", "<=", "-6.0 kcal/mol"],
  ["Vina候选通过", ">=", "2/3 模型"],
  ["候选最终分", "'=", "三个模型中位数"],
];
summary.getRange("H11:J15").format = { font: { name: fontFamily, size: 10 }, fill: "#FFFFFF", verticalAlignment: "center" };
summary.getRange("H10:J15").format.borders = gridBorder;
summary.getRange("I11:J15").format.horizontalAlignment = "center";
summary.getRange("A22:J24").merge();
summary.getRange("A22").values = [["解释边界：两个 16 Å 批次的 MSA 来源和 Vina 阈值不同，只用于批次敏感性比较；跨距离主比较统一采用在线 MMseqs2 批次。计算筛选不替代实验验证。"]];
summary.getRange("A22:J24").format = { fill: "#FFFFFF", font: { name: fontFamily, size: 10, bold: true, color: "#000000" }, wrapText: true, verticalAlignment: "center" };
summary.getRange("A:J").format.columnWidth = 15;
summary.getRange("C:C").format.columnWidth = 20;
summary.getRange("H:H").format.columnWidth = 22;
summary.freezePanes.freezeRows(4);

addDataSheet("距离漏斗", payload.span_summary, {
  title: "11–20 Å 在线批次筛选漏斗与参数",
  note: "跨距离比较统一使用在线 MMseqs2 批次；RMSD 阈值严格小于 2.0 Å，Vina 阈值不高于 -6.0 kcal/mol。",
  tableName: "SpanSummaryTable",
});
addDataSheet("优于基线", payload.top_candidates, {
  title: "最终分严格高于 GGGGSGGGGS 基线 24.1035 的候选",
  note: "按最终分从高到低排列；最终分为三个 Boltz-2 模型 Ranker 总分中位数。",
  tableName: "TopCandidatesTable",
  freezeColumns: 3,
  columns: [
    "target_span_A", "linker_sequence", "final_score_median", "score_minus_baseline",
    "model1_score", "model2_score", "model3_score", "linker_rmsd_median_A",
    "rmsd_pass_count", "vina_median_kcal_mol", "vina_pass_count",
    "sd40_rmsd_median_A", "contact_recovery_median", "clashing_atoms_median", "qc_pass",
  ],
  displayHeaders: [
    "距离 Å", "Linker序列", "最终分", "较基线增加",
    "模型1分", "模型2分", "模型3分", "Linker RMSD中位数 Å",
    "RMSD通过数", "Vina中位数", "Vina通过数",
    "SD40 RMSD中位数 Å", "接触恢复率中位数", "碰撞原子中位数", "序列QC",
  ],
});
addDataSheet("模型阅读版", payload.all_models, {
  title: "逐模型关键指标阅读版",
  note: "按距离、候选和模型号排列；同一候选的三个模型连续显示，便于核对 RMSD、Vina、Ranker 和置信度。",
  tableName: "ModelReaderTable",
  freezeColumns: 4,
  columns: [
    "target_span_A", "linker_sequence", "candidate_id", "model_index",
    "linker_ca_rmsd_A", "rmsd_model_pass", "vina_best_score_kcal_mol", "vina_model_pass",
    "total_score", "sd40_rmsd_A", "contact_recovery", "clashing_atoms",
    "confidence_score", "ptm",
  ],
  displayHeaders: [
    "距离 Å", "Linker序列", "候选ID", "模型号",
    "Linker RMSD Å", "RMSD通过", "Vina最佳分", "Vina通过",
    "Ranker总分", "SD40 RMSD Å", "接触恢复率", "碰撞原子数",
    "Boltz置信度", "pTM",
  ],
});
addDataSheet("候选总表", payload.all_candidates, {
  title: "在线批次全部候选级记录",
  note: "包含未进入最终排名的序列，用于完整呈现设计漏斗和失败原因。",
  tableName: "AllCandidatesTable",
  freezeColumns: 4,
});
addDataSheet("模型总表", payload.all_models, {
  title: "在线批次全部 Boltz-2 逐模型记录",
  note: "每个候选最多三行，合并 Linker RMSD、Vina、Ranker 和 Boltz-2 置信度字段。",
  tableName: "AllModelsTable",
  freezeColumns: 5,
});
addDataSheet("早期16A", payload.early16, {
  title: "早期 16 Å 单序列 MSA 批次",
  note: "该批次 Vina 阈值为 -7.0 kcal/mol，不能与后期在线 16 Å 直接解释为距离差异。",
  tableName: "Early16Table",
});
addDataSheet("来源统计", payload.source_stage_summary, {
  title: "全量来源文件按阶段与扩展名统计",
  note: "统计来自匿名提交包文件清单及完整结果目录。",
  tableName: "SourceStageTable",
});
addDataSheet("全量来源索引", payload.source_inventory, {
  title: "全量来源索引",
  note: "全部来源文件均纳入；大型结构、MSA、模型数组和日志不重复复制，通过相对路径与 SHA256 追溯。",
  tableName: "SourceInventoryTable",
  freezeColumns: 2,
  fontSize: 8,
  wrapText: false,
});

workbook.recalculate();
const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  maxChars: 4000,
});
await fs.mkdir(`${outputRoot}/00_阅读说明/workbook_previews`, { recursive: true });
const previews = [
  ["摘要", "A1:J24"],
  ["距离漏斗", "A1:P15"],
  ["优于基线", "A1:T20"],
  ["模型阅读版", "A1:N20"],
  ["候选总表", "A1:T20"],
  ["模型总表", "A1:T20"],
  ["早期16A", "A1:K20"],
  ["来源统计", "A1:D30"],
  ["全量来源索引", "A1:H20"],
];
for (const [sheetName, range] of previews) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(`${outputRoot}/00_阅读说明/workbook_previews/${sheetName}.png`, new Uint8Array(await preview.arrayBuffer()));
}
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
const outputPath = `${outputRoot}/02_核心数据表/ADAR2_SD40_中期结果_全量总汇.xlsx`;
await xlsx.save(outputPath);
await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });
await fs.writeFile(`${outputRoot}/00_阅读说明/workbook_validation.txt`, errorScan.ndjson || "", "utf8");
console.log(JSON.stringify({ outputPath, sheets: previews.map((x) => x[0]), errorScan: errorScan.ndjson }, null, 2));
