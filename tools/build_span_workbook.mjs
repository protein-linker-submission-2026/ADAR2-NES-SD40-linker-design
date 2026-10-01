import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const navy="#1F4E78", blue="#D9EAF7", light="#F7FBFD", green="#E2F0D9", red="#FCE4D6", white="#FFFFFF", grid="#B7C9D6";

function styleTitle(sheet, range, text) {
  sheet.mergeCells(range); const cell=range.split(":")[0]; sheet.getRange(cell).values=[[text]];
  sheet.getRange(range).format.font={name:"Arial",bold:true,color:white,size:15};
  sheet.getRange(range).format.fill=navy; sheet.getRange(range).format.rowHeight=28;
}
function styleHeader(range) {
  range.format.fill=navy; range.format.font={name:"Arial",bold:true,color:white,size:10};
  range.format.wrapText=true; range.format.rowHeight=36; range.format.verticalAlignment="center";
  range.format.borders={preset:"all",style:"thin",color:grid};
}

async function buildSpan(root, span) {
  const reports=path.join(root,"05_reports");
  const modelRows=JSON.parse(await fs.readFile(path.join(reports,"model_rows.json"),"utf8"));
  const sequenceRows=JSON.parse(await fs.readFile(path.join(reports,"sequence_rows.json"),"utf8"));
  if (modelRows.length!==90) throw new Error(`模型明细必须为90行，实际${modelRows.length}`);
  if (modelRows.some(r=>r.Linker序列==="GGGGSGGGGS")) throw new Error("baseline不得混入90行设计明细");
  const wb=Workbook.create(); const detail=wb.worksheets.add("Boltz逐模型表"); const summary=wb.worksheets.add("序列最终得分");
  for (const s of [detail,summary]) {s.showGridLines=false; s.getRange("A:Z").format.font={name:"Arial",size:10};}
  detail.tabColor=navy; summary.tabColor="#5B9BD5";
  styleTitle(detail,"A1:W1",`ADAR2–SD40 ${span} Å逐模型结果（90行；正式方案B）`);
  detail.mergeCells("A3:W3"); detail.getRange("A3").values=[["每行对应一条ProteinMPNN请求序列的一个理论Boltz-2模型位置。未进入后续步骤时保留空数值，并写明状态；联网仅用于在线MSA。"]]; detail.getRange("A3:W3").format.fill=blue; detail.getRange("A3:W3").format.wrapText=true;
  const headers=Object.keys(modelRows[0]); detail.getRangeByIndexes(3,0,1,headers.length).values=[headers]; styleHeader(detail.getRangeByIndexes(3,0,1,headers.length));
  detail.getRangeByIndexes(4,0,modelRows.length,headers.length).values=modelRows.map(r=>headers.map(h=>r[h]??null));
  detail.getRangeByIndexes(4,0,modelRows.length,headers.length).format.borders={insideHorizontal:{style:"thin",color:"#E5E7EB"}};
  detail.getRange("A5:W94").format.verticalAlignment="center"; detail.getRange("A5:W94").format.fill=light;
  detail.getRange("A:A").format.columnWidth=9; detail.getRange("B:B").format.columnWidth=24; detail.getRange("C:C").format.columnWidth=11; detail.getRange("D:D").format.columnWidth=17; detail.getRange("E:G").format.columnWidth=13; detail.getRange("H:H").format.columnWidth=34; detail.getRange("I:W").format.columnWidth=14;
  detail.getRange("L5:L94").format.numberFormat="0.0000"; detail.getRange("O5:O94").format.numberFormat="0.00"; detail.getRange("R5:V94").format.numberFormat="0.0000";
  detail.getRange("G5:G94").conditionalFormats.add("containsText",{text:"未通过",format:{fill:red,font:{color:"#9C0006",bold:true}}});
  detail.getRange("Q5:Q94").conditionalFormats.add("containsText",{text:"通过",format:{fill:green,font:{color:"#006100",bold:true}}});
  detail.freezePanes.freezeRows(4); detail.freezePanes.freezeColumns(4);

  styleTitle(summary,"A1:J1",`ADAR2–SD40 ${span} Å序列最终得分`);
  summary.mergeCells("A3:J3"); summary.getRange("A3").values=[["GGGGSGGGGS固定在第一行且只作对照。设计序列只有通过Vina 2/3门槛后才有分数。方案B：100×(0.3×S_RMSD + 0.3×S_contact + 0.4×S_clash)。"]]; summary.getRange("A3:J3").format.fill=blue; summary.getRange("A3:J3").format.wrapText=true;
  const sheaders=Object.keys(sequenceRows[0]); summary.getRangeByIndexes(3,0,1,sheaders.length).values=[sheaders]; styleHeader(summary.getRangeByIndexes(3,0,1,sheaders.length));
  summary.getRangeByIndexes(4,0,sequenceRows.length,sheaders.length).values=sequenceRows.map(r=>sheaders.map(h=>r[h]??null));
  summary.getRangeByIndexes(4,0,sequenceRows.length,sheaders.length).format.borders={insideHorizontal:{style:"thin",color:"#E5E7EB"}};
  summary.getRangeByIndexes(4,0,1,sheaders.length).format.fill=blue; if(sequenceRows.length>1) summary.getRangeByIndexes(5,0,sequenceRows.length-1,sheaders.length).format.fill=light;
  summary.getRange("A:A").format.columnWidth=13; summary.getRange("B:B").format.columnWidth=17; summary.getRange("C:C").format.columnWidth=38; summary.getRange("D:G").format.columnWidth=15; summary.getRange("H:H").format.columnWidth=20; summary.getRange("I:J").format.columnWidth=15;
  summary.getRange(`D5:G${4+sequenceRows.length}`).format.numberFormat="0.0000"; summary.freezePanes.freezeRows(4);
  wb.recalculate();
  const errors=await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",options:{useRegex:true,maxResults:100},maxChars:3000});
  const check=await wb.inspect({kind:"region",sheetId:"Boltz逐模型表",range:"A1:W94",maxChars:5000});
  await fs.mkdir(path.join(reports,"previews"),{recursive:true});
  for (const name of ["Boltz逐模型表","序列最终得分"]) {const png=await wb.render({sheetName:name,autoCrop:"all",scale:1,format:"png"}); await fs.writeFile(path.join(reports,"previews",`${name}.png`),new Uint8Array(await png.arrayBuffer()));}
  const out=path.join(reports,`ADAR2_SD40_${span}A_中文结果表.xlsx`); const blob=await SpreadsheetFile.exportXlsx(wb); await blob.save(out);
  await fs.writeFile(path.join(reports,"workbook_audit.txt"),`ROWS=${modelRows.length}\n${errors.ndjson}\n${check.ndjson}\n`,"utf8");
  console.log(`OUTPUT=${out}`);
}

async function buildCross(gameRoot) {
  const rows=[];
  try {
    const online16=JSON.parse(await fs.readFile(path.join(gameRoot,"16","05_reports","sequence_rows.json"),"utf8"));
    for(const r of online16) rows.push([16,"在线MMseqs2 MSA",r.类别,r.Linker序列,r.模型1总分,r.模型2总分,r.模型3总分,r.方案B中位数,r.最终状态]);
  } catch (error) {
    if (error?.code!=="ENOENT") throw error;
    const old=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(gameRoot,"data","05_reports","ADAR2_SD40_16A_中文结果表.xlsx")));
    for(const r of old.worksheets.getItem("序列最终得分").getRange("A5:G35").values){if(!r[1]) continue; rows.push([16,"本地单序列A3M",...r]);}
  }
  for(const span of [11,12,13,14,15,17,18,19,20]){
    const p=path.join(gameRoot,String(span),"05_reports","sequence_rows.json");
    for(const r of JSON.parse(await fs.readFile(p,"utf8"))) rows.push([span,"在线MMseqs2 MSA",r.类别,r.Linker序列,r.模型1总分,r.模型2总分,r.模型3总分,r.方案B中位数,r.最终状态]);
  }
  const wb=Workbook.create(); const s=wb.worksheets.add("跨距离序列汇总"); s.showGridLines=false; s.tabColor=navy;
  styleTitle(s,"A1:I1","ADAR2–SD40 11–20 Å跨距离序列汇总");
  s.mergeCells("A3:I3"); s.getRange("A3").values=[["11–20 Å均优先使用在线MMseqs2 MSA结果；若16 Å在线重算结果尚不存在，则回退到历史本地单序列A3M结果。"]]; s.getRange("A3:I3").format.fill=blue; s.getRange("A3:I3").format.wrapText=true;
  const headers=["距离 (Å)","MSA方法","类别","Linker序列","模型1总分","模型2总分","模型3总分","方案B中位数","最终状态"];
  s.getRange("A4:I4").values=[headers]; styleHeader(s.getRange("A4:I4")); s.getRangeByIndexes(4,0,rows.length,9).values=rows; s.getRangeByIndexes(4,0,rows.length,9).format.borders={insideHorizontal:{style:"thin",color:"#E5E7EB"}}; s.getRangeByIndexes(4,0,rows.length,9).format.fill=light;
  s.getRange("A:A").format.columnWidth=11; s.getRange("B:B").format.columnWidth=21; s.getRange("C:C").format.columnWidth=13; s.getRange("D:D").format.columnWidth=18; s.getRange("E:H").format.columnWidth=15; s.getRange("I:I").format.columnWidth=22; s.getRange(`E5:H${4+rows.length}`).format.numberFormat="0.0000"; s.freezePanes.freezeRows(4);
  wb.recalculate(); const errors=await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",options:{useRegex:true,maxResults:100},maxChars:3000});
  const png=await wb.render({sheetName:"跨距离序列汇总",range:`A1:I${Math.min(rows.length+4,80)}`,scale:1,format:"png"}); await fs.writeFile(path.join(gameRoot,"ADAR2_SD40_11-20A_跨距离总表_预览.png"),new Uint8Array(await png.arrayBuffer()));
  const out=path.join(gameRoot,"ADAR2_SD40_11-20A_跨距离总表_中文.xlsx"); const blob=await SpreadsheetFile.exportXlsx(wb); await blob.save(out); await fs.writeFile(path.join(gameRoot,"跨距离总表审计.txt"),`ROWS=${rows.length}\n${errors.ndjson}\n`,"utf8"); console.log(`OUTPUT=${out}`);
}

const [mode,arg1,arg2]=process.argv.slice(2);
if(mode==="span") await buildSpan(arg1,Number(arg2));
else if(mode==="cross") await buildCross(arg1);
else throw new Error("Usage: node build_span_workbook.mjs span <root> <span> | cross <game-root>");
