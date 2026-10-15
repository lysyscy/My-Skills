# -*- coding: utf-8 -*-
"""
同材料行合并：在整理版基础上，合并「名称+规格+材质」全同且技术参数/备注无差异的行。
依据：C:\\Users\\Administrator\\WorkBuddy\\2026-10-06-11-55-10\\合并方案_待确认.md
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter as gl

SRC = r"D:\UserData\Desktop\20261005中煤鄂尔多斯火炬气治理改造项目_整理版.xlsx"
OUT = r"D:\UserData\Desktop\20261005中煤鄂尔多斯火炬气治理改造项目_合并版.xlsx"
LOG = r"C:\Users\Administrator\WorkBuddy\2026-10-06-11-55-10\合并明细.json"

ORDER = ['设备', '工程量', '配电柜', '线缆', '钢材', '灯具', '阀门', '桥架',
         '其他', '管件1', '保温', '储罐', '仪表', '风机', '泵']

# 确认合并的组：(工作表, [原行号...])  —— 行号基于整理版
GROUPS = [
    ('工程量', [12, 18, 28]),          # 防爆挠性管
    ('工程量', [13, 19, 29]),          # 防爆直通
    ('工程量', [14, 20, 30]),          # 防爆弯通
    ('工程量', [15, 21, 31]),          # 防爆三通
    ('配电柜', [8, 14]),               # A型应急照明集中电源
    ('线缆',   [6, 10]),               # 阻燃A级低压电力电缆
    ('钢材',   [6, 10]),               # 镀锌钢管 G20
    ('钢材',   [7, 11]),               # 镀锌钢管 G32
    ('钢材',   [9, 12]),               # 镀锌槽钢 10#
    ('钢材',   [41, 42]),              # 无缝钢管 DN200
    ('钢材',   [43, 44, 45, 46]),      # 无缝钢管 DN50
    ('钢材',   [47, 49]),              # 无缝钢管 DN80
    ('钢材',   [50, 51]),              # 无缝钢管 DN50 (2)
    ('管件1',  [3, 61]),               # 弯头 DN50  SCH40 vs S-40
    ('管件1',  [4, 62]),               # 弯头 DN80  SCH40 vs S-40
    ('管件1',  [7, 73]),               # 弯头 DN250 SCH30 vs S-40
    ('管件1',  [54, 55, 56, 57, 58, 59, 60]),  # 全螺纹螺柱、螺母
]

def c(ws, r, col):
    v = ws.cell(r, col).value
    return '' if v is None else str(v).strip()

def norm(s):
    return re.sub(r'\s+', '', str(s)).upper()

def isnum(s):
    return bool(re.fullmatch(r'\d+(\.\d+)?', str(s).replace(',', '').strip()))

src = load_workbook(SRC, data_only=True)

# ---- 预检：逐组核对，参数/备注必须真的无差异 ----
print("=== 合并前预检 ===")
merge_map = {}   # sheet -> {行号: 保留行号}
problems = []
for sh, rows in GROUPS:
    ws = src[sh]
    h = {ws.cell(1, i).value: i for i in range(1, ws.max_column + 1)}
    keep = rows[0]
    drop = rows[1:]
    # 名称/规格/材质必须全同
    for r in rows:
        for col in ('名称', '规格型号', '材质/牌号'):
            if norm(c(ws, r, h[col])) != norm(c(ws, keep, h[col])):
                problems.append(f'{sh}!R{r} 的{col}与首行不一致：'
                                f'[{c(ws,r,h[col])[:24]}] vs [{c(ws,keep,h[col])[:24]}]')
    # 单位必须全同
    for r in rows:
        if c(ws, r, h['单位']) != c(ws, keep, h['单位']):
            problems.append(f'{sh}!R{r} 单位不一致：[{c(ws,r,h["单位"])}] vs [{c(ws,keep,h["单位"])}]')
    # 数量必须都是数字
    for r in rows:
        if not isnum(c(ws, r, h['数量'])):
            problems.append(f'{sh}!R{r} 数量非数字，无法相加：[{c(ws, r, h["数量"])}]')
    merge_map[sh] = merge_map.get(sh, {})
    for r in drop:
        merge_map[sh][r] = keep
    qs = [c(ws, r, h['数量']) for r in rows]
    par_same = len(set(c(ws, r, h['技术参数']) for r in rows)) == 1
    note_same = len(set(c(ws, r, h['备注']) for r in rows)) == 1
    total = sum(float(q) for q in qs) if all(isnum(q) for q in qs) else None
    print(f'  {sh:<6} R{rows}  数量={qs} 合计={total:g}  '
          f'参数{"同" if par_same else "异"} 备注{"同" if note_same else "异"}  '
          f'→ 留R{keep} 删{len(drop)}行')

if problems:
    print('\n!!! 预检发现问题，终止：')
    for p in problems:
        print('   ', p)
    sys.exit(1)
print('\n预检通过，无冲突。')

# ---- 生成新表 ----
HDR_FILL = PatternFill('solid', fgColor='E8EEF7')
MERGE_FILL = PatternFill('solid', fgColor='E2EFDA')   # 合并行淡绿
HDR_FONT = Font(name='微软雅黑', size=10, bold=True, color='1F3864')
BODY_FONT = Font(name='微软雅黑', size=10)
FLAG_FONT = Font(name='微软雅黑', size=10, color='C00000')
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
FLAG_FILL = PatternFill('solid', fgColor='FFF2CC')

out = Workbook()
out.remove(out.active)
log = []
stats = []

for sh in ORDER:
    ws = src[sh]
    h = {ws.cell(1, i).value: i for i in range(1, ws.max_column + 1)}
    cols = [ws.cell(1, i).value for i in range(1, ws.max_column + 1)]
    m = merge_map.get(sh, {})

    ws2 = out.create_sheet(sh)
    ws2.append(cols)
    for j, cn in enumerate(cols, 1):
        cell = ws2.cell(1, j)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER

    newno = 0
    merged_here = set()
    for r in range(2, ws.max_row + 1):
        if r in m:                      # 被合并掉的行，跳过
            continue
        newno += 1
        vals = [c(ws, r, h['行号'])]
        for cn in cols[1:]:
            vals.append(c(ws, r, h[cn]))

        # 判断本行是否为某组合并的保留行（本组最小行号）
        all_rows = [rr for shx, rr in GROUPS if shx == sh]
        group_rows = next((g for g in all_rows if r in g), None)
        is_merge_keep = bool(group_rows) and r == min(group_rows)
        if is_merge_keep:
            rows = group_rows
            qs = [c(ws, x, h['数量']) for x in rows]
            if all(isnum(q) for q in qs):
                tot = sum(float(q) for q in qs)
                ti = cols.index('数量') + 1
                vals[ti - 1] = str(int(tot)) if tot == int(tot) else str(tot)
            merged_here.update(rows)
            log.append(dict(sheet=sh, keep_row=r, merged_rows=rows,
                            name=c(ws, r, h['名称']),
                            spec=c(ws, r, h['规格型号']),
                            qtys=qs, total=vals[cols.index('数量')]))
        ws2.append(vals)
        for j, v in enumerate(vals, 1):
            cell = ws2.cell(newno + 1, j)
            cell.font = FLAG_FONT if (j == len(cols) and v) else BODY_FONT
            cell.border = BORDER
            if j == len(cols) and v:
                cell.fill = FLAG_FILL
            elif is_merge_keep:
                cell.fill = MERGE_FILL
            if cols[j - 1] in ('技术参数', '备注', '规格型号', '材质/牌号', '类别', '设备位号'):
                cell.alignment = Alignment(vertical='top', wrap_text=True)
            else:
                cell.alignment = Alignment(vertical='top', horizontal='left')

    # 行号列重编
    for i in range(2, ws2.max_row + 1):
        ws2.cell(i, 1).value = str(i - 1)

    ws2.freeze_panes = 'A2'
    ws2.auto_filter.ref = f"A1:{gl(len(cols))}{ws2.max_row}"
    widths = {'行号': 6, '设备位号': 15, '类别': 11, '名称': 26, '规格型号': 26,
              '材质/牌号': 22, '技术参数': 52, '单位': 7, '数量': 9, '备注': 18, '待补标记': 22}
    for j, cn in enumerate(cols, 1):
        ws2.column_dimensions[gl(j)].width = widths.get(cn, 12)
    ws2.row_dimensions[1].height = 26
    nm = sum(1 for g in GROUPS if g[0] == sh for _ in g[1:] if True)
    stats.append((sh, ws2.max_row - 1, len([1 for g in GROUPS if g[0] == sh])))

out.save(OUT)

print(f"\n{'工作表':<10}{'原行数':>8}{'合并后':>8}{'合并组数':>9}")
t_src = t_out = 0
for sh, n, g in stats:
    o = src[sh].max_row - 1
    print(f'{sh:<10}{o:>8}{n:>8}{g:>9}')
    t_src += o
    t_out += n
print(f"{'合计':<10}{t_src:>8}{t_out:>8}{len(GROUPS):>9}")

import json
json.dump(log, open(LOG, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n合并明细条数:', len(log))
print('已保存:', OUT)
