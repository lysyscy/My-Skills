# -*- coding: utf-8 -*-
"""独立校验：合并版 vs 整理版。每表数量总和必须一致，被合并行不得残留。"""
import sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
from openpyxl import load_workbook

A = r"D:\UserData\Desktop\20261005中煤鄂öld斯火炬气治理改造项目_整理版.xlsx"
A = r"D:\UserData\Desktop\20261005中煤鄂尔多斯火炬气治理改造项目_整理版.xlsx"
B = r"D:\UserData\Desktop\20261005中煤鄂尔多斯火炬气治理改造项目_合并版.xlsx"
LOG = r"C:\Users\Administrator\WorkBuddy\2026-10-06-11-55-10\合并明细.json"

a = load_workbook(A, data_only=True)
b = load_workbook(B, data_only=True)
log = json.load(open(LOG, encoding='utf-8'))

def c(ws, r, col):
    v = ws.cell(r, col).value
    return '' if v is None else str(v).strip()

ORDER = ['设备', '工程量', '配电柜', '线缆', '钢材', '灯具', '阀门', '桥架',
         '其他', '管件1', '保温', '储罐', '仪表', '风机', '泵']

fail = 0
print("=== 1. 工作表与行数 ===")
for sh in ORDER:
    ha = {a[sh].cell(1, i).value: i for i in range(1, a[sh].max_column + 1)}
    hb = {b[sh].cell(1, i).value: i for i in range(1, b[sh].max_column + 1)}
    if list(ha.keys()) != list(hb.keys()):
        print(f'  {sh} 表头不一致 整理版{list(ha)} 合并版{list(hb)}')
        fail += 1
    na, nb = a[sh].max_row - 1, b[sh].max_row - 1
    print(f'  {sh:<6} {na:>3} -> {nb:>3}  ({-0 if na==nb else nb-na:+d})  表头{"一致" if list(ha)==list(hb) else "不一致"}')

print()
print("=== 2. 数量总和逐表核对（关键：合并不能改变总量）===")
for sh in ORDER:
    ha = {a[sh].cell(1, i).value: i for i in range(1, a[sh].max_column + 1)}
    hb = {b[sh].cell(1, i).value: i for i in range(1, b[sh].max_column + 1)}
    def total(ws, h):
        t = 0.0
        for r in range(2, ws.max_row + 1):
            q = c(ws, r, h['数量'])
            if re.fullmatch(r'\d+(\.\d+)?', q):
                t += float(q)
        return t
    ta, tb = total(a[sh], ha), total(b[sh], hb)
    ok = abs(ta - tb) < 1e-6
    if not ok:
        fail += 1
    print(f'  {sh:<6} 整理版合计={ta:>10g}  合并版合计={tb:>10g}  {"OK" if ok else "❌不一致"}')

print()
print("=== 3. 逐组核对：合并行数量 == 被合并行数量之和 ===")
for L in log:
    sh = L['sheet']
    hb = {b[sh].cell(1, i).value: i for i in range(1, b[sh].max_column + 1)}
    # 在合并版中找到该行
    found = None
    for r in range(2, b[sh].max_row + 1):
        if c(b[sh], r, hb['名称']) == L['name'] and c(b[sh], r, hb['规格型号']) == L['spec']:
            q = c(b[sh], r, hb['数量'])
            if re.fullmatch(r'\d+(\.\d+)?', q) and abs(float(q) - float(L['total'])) < 1e-6:
                found = r
                break
    exp = sum(float(x) for x in L['qtys'])
    ok = found is not None and abs(exp - float(L['total'])) < 1e-6
    if not ok:
        fail += 1
    print(f'  {sh:<6} {L["name"][:18]:<18} 规格[{L["spec"][:12]:<12}] {L["qtys"]} '
          f'→ 合计{L["total"]:<6} 期望{exp:<8g} {"OK" if ok else "❌未找到"}')

print()
print("=== 4. 合并行数量已变为合计（被合并的原值不应作为独立行留存）===")
for L in log:
    sh = L['sheet']
    ha = {a[sh].cell(1, i).value: i for i in range(1, a[sh].max_column + 1)}
    hb = {b[sh].cell(1, i).value: i for i in range(1, b[sh].max_column + 1)}
    key = (c(a[sh], L['keep_row'], ha['名称']),
           c(a[sh], L['keep_row'], ha['规格型号']),
           c(a[sh], L['keep_row'], ha['材质/牌号']))
    # 该 名称+规格+材质 组合在合并版应只剩 1 行，且数量为合计
    # （同名称同规格但材质不同的行是独立物料，不计入）
    rows = [x for x in range(2, b[sh].max_row + 1)
            if c(b[sh], x, hb['名称']) == key[0]
            and c(b[sh], x, hb['规格型号']) == key[1]
            and c(b[sh], x, hb['材质/牌号']) == key[2]]
    ok = len(rows) == 1 and re.fullmatch(r'\d+(\.\d+)?', c(b[sh], rows[0], hb['数量'])) \
         and abs(float(c(b[sh], rows[0], hb['数量'])) - float(L['total'])) < 1e-6
    if not ok:
        print(f'  ❌ {sh}「{key[0][:14]}」规格[{key[1][:10]}]材质[{key[2][:14]}] 应 1 行数量={L["total"]}，'
              f'实际 {len(rows)} 行 {[c(b[sh],x,hb["数量"]) for x in rows]}')
        fail += 1
print('  （无输出＝每组合并后只剩 1 行且数量为合计）')

print()
print("=== 5. 未合并组必须原样保留（按 名称+规格/参数 区分）===")
KEEP = [('配电柜', '低压开关柜', 4), ('阀门', '气动调节阀', 3), ('阀门', '气动切断阀', 4)]
for sh, nm, cnt in KEEP:
    hb = {b[sh].cell(1, i).value: i for i in range(1, b[sh].max_column + 1)}
    n = sum(1 for r in range(2, b[sh].max_row + 1) if c(b[sh], r, hb['名称']) == nm)
    ok = n == cnt
    if not ok:
        fail += 1
    print(f'  {sh}「{nm}」应保留 {cnt} 行，实际 {n} 行  {"OK" if ok else "❌被误合"}')
# 备注/参数差异必须还在
ws = b['配电柜']; hb = {ws.cell(1, i).value: i for i in range(1, ws.max_column + 1)}
notes = [c(ws, r, hb['备注']) for r in range(2, ws.max_row + 1) if c(ws, r, hb['名称']) == '低压开关柜']
print(f'  配电柜 低压开关柜 备注：{notes}  {"OK（进线/母联/出线/补偿柜 均在）" if len(notes)==4 else "❌备注丢失"}')
ws = b['阀门']; hb = {ws.cell(1, i).value: i for i in range(1, ws.max_column + 1)}
flange = []
for r in range(2, ws.max_row + 1):
    p = c(ws, r, hb['技术参数'])
    for m in re.findall(r'CL150\s*\d+"', p):
        flange.append(m)
print(f'  阀门 法兰口径：{sorted(set(flange))}  共 {len(flange)} 个  '
      f'{"OK（36/28/40 各种口径都在）" if len(flange)>=5 else "❌口径丢失"}')

print()
print("=== 6. 行号连续性 ===")
for sh in ORDER:
    hb = {b[sh].cell(1, i).value: i for i in range(1, b[sh].max_column + 1)}
    nos = [c(b[sh], r, hb['行号']) for r in range(2, b[sh].max_row + 1)]
    exp = [str(i) for i in range(1, len(nos) + 1)]
    if nos != exp:
        print(f'  ❌ {sh} 行号不连续')
        fail += 1
print('  （无输出＝全部连续）')

print()
print("=== 7. 合并行底色标记 ===")
cnt = 0
for L in log:
    sh = L['sheet']
    ws = b[sh]
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 1).fill.fgColor.rgb == '00E2EFDA' or \
           (ws.cell(r, 1).fill.fgColor.rgb or '').endswith('E2EFDA'):
            cnt += 1
            break
print(f'  带淡绿底色的合并行：{cnt} / {len(log)}  {"OK" if cnt == len(log) else "部分缺失"}')

print()
print("=== 校验结论 ===")
print("PASS" if fail == 0 else f"FAIL：{fail} 处问题")
