# -*- coding: utf-8 -*-
"""严格合并后，列出「只差一个非关键字段」的疑似重复组，供人工判断。"""
import xlrd, re, sys, io
from collections import defaultdict, Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC = r"D:\UserData\Documents\xwechat_files\wxid_ofdozq3goua321_291d\msg\file\2026-10\锌粉、熔铸车间设备、材料非标制作询价表.xls"
sh = xlrd.open_workbook(SRC).sheet_by_index(0)
def sv(r, c):
    v = sh.cell_value(r, c)
    return "" if v in (None, "") else (str(v).strip() if isinstance(v, str) else v)
def T(v):
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    return str(v).strip()
def nz(t): return re.sub(r"[\s；;，,、]", "", str(t))
def canonPN(s):
    s = str(s).replace("＝", "=").replace("，", ",")
    s = re.sub(r"\s+", "", s)
    return re.sub(r"PN\s*=\s*", "PN", s, flags=re.I).upper()

recs = []
for r in range(2, sh.nrows):
    name, spec, mat, unit, qty, note, extra = (sv(r, c) for c in range(1, 8))
    name, spec, mat, unit, note, extra = T(name), T(spec), T(mat), T(unit), T(note), T(extra)
    if not name: name, spec = spec, ""
    nf = (note + "；" + extra) if (note and extra) else (note or extra)
    q = float(qty); q = int(q) if q == int(q) else q
    recs.append(dict(er=r + 1, name=name, spec=spec, mat=mat, unit=unit, q=q, note=nf))

STRICT = lambda x: (x["name"], nz(x["spec"]), x["mat"], x["unit"], x["note"])
g = defaultdict(list)
for x in recs: g[STRICT(x)].append(x)
strict_ids = {k for k, v in g.items()}

print("=" * 100)
print("【1】未合并：只差备注（其余 名称/规格/材质/单位 全同）")
print("=" * 100)
L1 = lambda x: (x["name"], nz(x["spec"]), x["mat"], x["unit"])
g1 = defaultdict(list)
for x in recs: g1[L1(x)].append(x)
n1 = 0
for k, v in g1.items():
    if len({STRICT(x) for x in v}) > 1:
        n1 += 1
        print(f"\n  {v[0]['name']} | {v[0]['spec']!r} | 材质={v[0]['mat']!r} | {v[0]['unit']}")
        for x in v:
            print(f"      R{x['er']:<4} 数量={x['q']!r:<7} 备注={x['note']!r}")
print(f"\n  共 {n1} 组")

print()
print("=" * 100)
print("【2】未合并：只差规格型号写法（PN= / PN、全半角），其余全同")
print("=" * 100)
L2 = lambda x: (x["name"], canonPN(x["spec"]), x["mat"], x["unit"], nz(x["note"]))
g2 = defaultdict(list)
for x in recs: g2[L2(x)].append(x)
n2 = 0
for k, v in g2.items():
    if len({STRICT(x) for x in v}) > 1:
        n2 += 1
        tot = sum(x["q"] for x in v)
        print(f"\n  {v[0]['name']} | 材质={v[0]['mat']!r} | {v[0]['unit']} | 合并后数量={tot}")
        for x in v:
            print(f"      R{x['er']:<4} 规格={x['spec']!r:<22} 数量={x['q']!r:<7} 备注={x['note'][:24]!r}")
print(f"\n  共 {n2} 组")

print()
print("=" * 100)
print("【3】未合并：只差材质（其余全同，材质一空一填）")
print("=" * 100)
L3 = lambda x: (x["name"], nz(x["spec"]), x["unit"], x["note"])
g3 = defaultdict(list)
for x in recs: g3[L3(x)].append(x)
n3 = 0
for k, v in g3.items():
    mats = {x["mat"] for x in v}
    if len({STRICT(x) for x in v}) > 1 and "" in mats and len(mats) > 1:
        n3 += 1
        tot = sum(x["q"] for x in v)
        print(f"\n  {v[0]['name']} | {v[0]['spec']!r} | {v[0]['unit']} | 合并后数量={tot}")
        for x in v:
            print(f"      R{x['er']:<4} 材质={x['mat']!r:<8} 数量={x['q']!r:<7} 备注={x['note'][:24]!r}")
print(f"\n  共 {n3} 组")

print()
print("=" * 100)
print("【4】合并明细（已合并的 27 组按类别分布）")
print("=" * 100)
# 重新按类别
NAME_CAT_other = None
import subprocess
cnt = Counter()
for k, v in g.items():
    if len(v) > 1:
        cnt[len(v)] += 1
print("  按组大小:", dict(sorted(cnt.items())))
print(f"  合计 {sum(cnt.values())} 组，消除 {sum((s-1)*c for s, c in cnt.items())} 行")
