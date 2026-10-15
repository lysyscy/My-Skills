# -*- coding: utf-8 -*-
"""从现有询价表生成「空白模板」：只留标题行 + 表头 + 1 行示例 + 合计行，样式原样保留。

用法:  python make_blank_template.py <现有询价表路径> [输出路径]

用途：把某个项目的询价单沉淀成**不含业务数据**的通用模板，放进 assets/ 反复复用。
⚠️ 生成物必须确认为空模板（不得残留原项目数据 / 项目名 / 地址）。
"""
import sys, io, os
from copy import copy
from openpyxl import Workbook, load_workbook

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

TPL = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(TPL)[0] + "_空白模板.xlsx"

tpl = load_workbook(TPL)
tws = tpl[tpl.sheetnames[0]]


def snap(cell):
    """快照真实样式对象 —— 跨工作簿不能搬 cell._style（源簿样式表索引，会 IndexError）。"""
    return dict(font=copy(cell.font), fill=copy(cell.fill), border=copy(cell.border),
                alignment=copy(cell.alignment), number_format=cell.number_format,
                protection=copy(cell.protection))


def apply(cell, s):
    cell.font = copy(s["font"]); cell.fill = copy(s["fill"])
    cell.border = copy(s["border"]); cell.alignment = copy(s["alignment"])
    cell.number_format = s["number_format"]; cell.protection = copy(s["protection"])


ST = {
    "title": snap(tws.cell(1, 1)),
    "hdr":   [snap(tws.cell(2, c)) for c in range(1, 12)],
    "dat":   [snap(tws.cell(3, c)) for c in range(1, 12)],
    "tot_a": snap(tws.cell(tws.max_row, 1)),
    "tot_k": snap(tws.cell(tws.max_row, 11)),
}
WIDTHS = {"A": 6, "B": 11, "C": 26, "D": 26, "E": 22, "F": 50,
          "G": 7, "H": 9, "I": 16, "J": 12, "K": 14}
HDR = ["序号", "类别", "名称", "规格型号", "材质/牌号", "技术参数",
       "单位", "数量", "备注", "单价", "合价"]

wb = Workbook()
ws = wb.active
ws.title = "类别名"

# R1 标题（占位符，交付前必须替换为真实项目名与地址）
for c in range(1, 12):
    apply(ws.cell(1, c), ST["title"])
ws.cell(1, 1).value = "项目名称\n材料计划\n（含13%增值税含运费，货到付款，地址：＿＿＿＿＿）"
ws.merge_cells("A1:K1")
ws.row_dimensions[1].height = 78

# R2 表头
for c, v in enumerate(HDR, start=1):
    cell = ws.cell(2, c); apply(cell, ST["hdr"][c - 1]); cell.value = v
ws.row_dimensions[2].height = 30

# R3 示例行（留空，仅供看格式）
for c in range(1, 12):
    apply(ws.cell(3, c), ST["dat"][c - 1])
ws.cell(3, 1).value = 1
ws.cell(3, 2).value = "类别名"
ws.cell(3, 11).value = '=IF(J3="","",H3*J3)'
ws.row_dimensions[3].height = 33

# R4 合计行
for c in range(1, 9):
    apply(ws.cell(4, c), ST["tot_a"])
ws.cell(4, 1).value = "合计"
apply(ws.cell(4, 11), ST["tot_k"])
ws.cell(4, 11).value = "=SUM(K3:K3)"
ws.merge_cells("A4:H4")

for c, w in WIDTHS.items():
    ws.column_dimensions[c].width = w
ws.freeze_panes = "A3"
ws.auto_filter.ref = "A2:K4"
ws.sheet_format.defaultRowHeight = 13.5
ws.sheet_format.defaultColWidth = 9

wb.save(OUT)

# 自检：确认无原项目残留
chk = load_workbook(OUT)
text = " ".join(str(chk.active.cell(r, c).value or "")
                for r in range(1, 5) for c in range(1, 12))
leak = [w for w in ("中煤", "鄂尔多斯", "锌粉", "熔铸", "豫光", "济源") if w in text]
print(f"已生成空白模板: {OUT}")
print(f"  残留检查: {'干净 ✅' if not leak else '❌ 含原项目字样 ' + str(leak)}")
print(f"  结构: {chk.active.dimensions} | 冻结 {chk.active.freeze_panes} | 筛选 {chk.active.auto_filter.ref}")
assert not leak, "生成物残留原项目数据，已中止"
