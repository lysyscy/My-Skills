# -*- coding: utf-8 -*-
"""
逐表整理：15 张工作表各自独立整理，不合并不删行不重编原序号。
依据：C:\\Users\\Administrator\\WorkBuddy\\2026-10-06-11-55-10\\重构方案_待确认.md
"""
import sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter as gl

SRC = r"D:\UserData\Desktop\20261005中煤鄂尔多斯火炬气治理改造项目.xlsx"
OUT = r"D:\UserData\Desktop\20261005中煤鄂尔多斯火炬气治理改造项目_整理版.xlsx"
REPORT = r"C:\Users\Administrator\WorkBuddy\2026-10-06-11-55-10\拆列复核清单.json"

# ---------- 通用工具 ----------
def c(ws, r, col):
    v = ws.cell(r, col).value
    if v is None:
        return ''
    return str(v).replace('\r\n', '\n').strip()

def colidx(letter):
    from openpyxl.utils import column_index_from_string
    return column_index_from_string(letter)

# ---------- 材质 / 牌号 / 标准号 抽取 ----------
MAT_RES = [
    r'20-GB/T\d+',
    r'06Cr19Ni10\s*GB/T\s*\d+',
    r'L245\s*GB/T\s*\d+\s*PSL\d*',
    # 标准号必须整体匹配到词尾，避免吃掉尾部小数点或后缀字母
    r'\d{2}\s*GB/T\s*\d{3,5}(?:\.\d+)?[A-Z]?',
    r'NB/T\s*\d+(?:\.\d+)?[A-Z]?',
    r'GB/T\s*\d{3,5}(?:\.\d+)?[A-Z]?(?![0-9A-Za-z])',
    r'HG/T\s*\d+(?:\.\d+)?[A-Z]?(?![0-9A-Za-z])',
    r'Q\d{3}[A-Z]?(?:/GALV)?',
    r'\b316SS\b|\b304SS\b|\b316L\b|\b304S\b|\b316\b|\b304\b',
    r'A\d{3}(?:\(C?<=\d\.\d\))?',
    r'\bWCB\b',
    r'(?<![A-Za-z])CS(?![A-Za-z])',
    r'\bSMLS\b',
    r'(?<![A-Za-z])PE(?![A-Za-z])',
    r'\bQDR\b',
]
MAT_RE = re.compile('|'.join(MAT_RES))
SCH_RE = re.compile(r'\bSCH\s*\d+\b', re.I)
DIM_RE = re.compile(r'(Φ|φ|Ф|DN|VN)\s*[=＝]?\s*[\d\w×x\*\.\-]+')

PLACEHOLDER = re.compile(r'\bhold\b|\bTBD\b|\bxxx+\b|待定|待填|（待|未定', re.I)

def extract_mat(text):
    """从文本中抽出材质/标准号，返回(剩余文本, 材质串)"""
    if not text:
        return '', ''
    found = []
    for m in MAT_RE.finditer(text):
        s = re.sub(r'\s+', ' ', m.group(0)).strip()
        if s and s not in found:
            found.append(s)
    rest = MAT_RE.sub(' ', text)
    rest = re.sub(r'[ \t　]+', ' ', rest)
    # 清理被抽空后残留的孤立标点
    rest = re.sub(r'[,，、;；:：]{2,}', '，', rest)
    rest = re.sub(r'(^|[ ，,、;；:：])[,，、;；:：]', r'\1', rest)
    rest = re.sub(r'[,，、;；:：]\s*$', '', rest)
    rest = rest.strip(' ，,、;；:：\n')
    return rest, '，'.join(found)

def clean(t):
    if t is None:
        return ''
    t = str(t)
    t = re.sub(r'[ \t　]+', ' ', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip(' ，,、;；\n')

def split_text_as_spec(text, force_param=False):
    """把一个规格类单元格拆成 (规格型号, 材质/牌号, 技术参数)"""
    if not text:
        return '', '', ''
    rest, mat = extract_mat(text)
    sch = SCH_RE.findall(rest)
    rest2 = SCH_RE.sub(' ', rest)
    rest2 = clean(rest2)
    if sch:
        mat = clean(mat + '，' + '，'.join(sch))
    has_nl = '\n' in text or '\n' in rest
    looks_param = force_param or has_nl or ('：' in rest and len(rest) > 30) or len(rest) > 60
    if looks_param:
        spec = ''
        param = rest2
    else:
        spec = rest2
        param = ''
    return spec, mat, param

# ---------- 设备类：技术参数块合并 + 规格提取 ----------
def merge_device(name, spec_lines, first_text, extra_first=None):
    """
    name: 名称
    spec_lines: 参数行文本列表
    first_text: 首行规格文本
    返回 (规格型号, 技术参数)
    """
    params = []
    for t in spec_lines:
        t = clean(t)
        if t:
            params.append(t)
    first = clean(first_text)
    # 规格型号：首行含尺寸型规格则取首行；否则在首行+参数中找含 Φ/DN/VN 的子句
    spec = ''
    if first and DIM_RE.search(first):
        spec = first
    if not spec:
        for t in ([first] + params):
            if t and DIM_RE.search(t):
                spec = t
                break
    pool = []
    if first:
        pool.append(first)
    pool.extend(params)
    param = '\n'.join([p for p in pool if p and p != spec])
    return spec, clean(param)

# ---------- 待补标记 ----------
def mark(flag, spec, mat, param, qty, unit, name, no_spec_ok=False):
    if not qty:
        flag.append('缺数量')
    if not unit:
        flag.append('缺单位')
    if not spec and not no_spec_ok:
        flag.append('缺规格' if (not mat and not param) else '规格无型号')
    blob = ' '.join([str(x) for x in (spec, mat, param, name) if x])
    if PLACEHOLDER.search(blob):
        flag.append('占位符未填')
    return '、'.join(flag)

# ---------- 读源 ----------
wb = load_workbook(SRC, data_only=True)
sheets = {}   # 表名 -> list[dict]
audit = []    # 复核清单

def add(sheet, name, spec, mat, param, unit, qty, note, cat='', tag='', flag_extra=None, no_spec_ok=False):
    flag = []
    if flag_extra:
        flag.extend(flag_extra)
    sheets.setdefault(sheet, []).append(dict(
        name=clean(name), spec=clean(spec), mat=clean(mat), param=clean(param),
        unit=clean(unit), qty=clean(qty), note=clean(note), cat=clean(cat), tag=clean(tag),
        flag=mark(flag, spec, mat, param, qty, unit, name, no_spec_ok)))

def audit_add(sheet, row, name, raw, out_spec, out_mat, out_param):
    audit.append(dict(sheet=sheet, row=row, name=clean(name)[:30],
                      raw=clean(raw)[:160], spec=out_spec[:60], mat=out_mat[:60], param=out_param[:60]))

# ===== 1. 设备 =====
ws = wb['设备']
cat = ''
EQUIP = [  # (行, 类别值或None)
    (3, None), (6, None), (17, None), (19, None), (20, None), (22, None), (23, None), (25, None),
]
groups = {3: [4, 5], 6: list(range(7, 16)), 17: [18], 19: [], 20: [], 22: [], 23: [], 25: []}
for r, _ in EQUIP:
    nm = c(ws, r, 3)
    first = c(ws, r, 4)
    mat = c(ws, r, 5)
    unit = c(ws, r, 6)
    qty = c(ws, r, 7)
    note = c(ws, r, 8)
    # 材质从首行规格里抽（如 组合件）
    if mat in ('组合件', '碳钢+防腐'):
        mat_keep = mat
    else:
        mat_keep = mat
    spec, param = merge_device(nm, [c(ws, x, 4) for x in groups[r]], first)
    # 参数行里可能带材质（如 20-GB/T3087），抽出并入材质
    rest, m2 = extract_mat(param)
    if m2:
        mat_keep = clean(mat_keep + '，' + m2) if mat_keep else m2
        param = clean(rest)
    add('设备', nm, spec, mat_keep, param, unit, qty, note, cat=cat, tag=c(ws, r, 2))
    audit_add('设备', r, nm, first, spec, mat_keep, param)

# 分类行 -> 类别
CATROWS = {2: '工业炉类', 16: '其它类', 21: '小型设备', 24: '电动葫芦'}
# 重建：按行序插入类别
seq = []
cur = ''
for r in range(2, 42):
    if r in CATROWS:
        cur = CATROWS[r]
        continue
    seq.append((r, cur))
# 覆盖之前的 add（重做一遍，带类别）
sheets['设备'] = []
for r, cat in seq:
    if r >= 26:
        continue
    nm = c(ws, r, 3)
    if not nm:
        continue
    first = c(ws, r, 4)
    mat = c(ws, r, 5)
    unit = c(ws, r, 6)
    qty = c(ws, r, 7)
    note = c(ws, r, 8)
    nxt = [x for x in range(r + 1, 26) if c(ws, x, 3)]
    end = nxt[0] - 1 if nxt else 25
    params = [c(ws, x, 4) for x in range(r + 1, end + 1)]
    spec, param = merge_device(nm, params, first)
    rest, m2 = extract_mat(param)
    mat = clean(mat + '，' + m2) if (m2 and mat) else (m2 or mat)
    param = clean(rest)
    add('设备', nm, spec, mat, param, unit, qty, note, cat=cat, tag=c(ws, r, 2))
    audit_add('设备', r, nm, first, spec, mat, param)

# 控制段 R26-R41：合并单元格向下填充
sysnames = {}
for r in range(26, 42):
    v = c(ws, r, 3)
    if v:
        for rr in range(r, 42):
            if not c(ws, rr, 3):
                pass
# 明确分组
CTRL = [('DCS控制系统', 26, 29), ('SIS控制系统', 30, 32), ('GDS控制系统', 33, 34)]
idx = 26
for sysname, a, b in CTRL:
    for r in range(a, b + 1):
        d = c(ws, r, 4)
        nm = (sysname + ' ' + d) if d else sysname
        add('设备', nm, '', '', '', c(ws, r, 5), c(ws, r, 6), '', cat='控制点', tag='', no_spec_ok=True)
        audit_add('设备', r, nm, d, '', '', '')
for r in range(35, 42):
    d = c(ws, r, 4)
    if not d:
        continue
    add('设备', d, '', '', '', c(ws, r, 5), c(ws, r, 6), '', cat='控制设备', tag='', no_spec_ok=True)
    audit_add('设备', r, d, d, '', '', '')

# ===== 2. 工程量 =====
ws = wb['工程量']
for r in range(3, 40):
    nm = c(ws, r, 2)
    raw = c(ws, r, 3)
    if not nm and not raw:
        continue
    spec, mat, param = split_text_as_spec(raw)
    add('工程量', nm, spec, mat, param, c(ws, r, 4), c(ws, r, 5), c(ws, r, 6), cat='工程量')
    audit_add('工程量', r, nm, raw, spec, mat, param)

# ===== 3. 配电柜 =====
ws = wb['配电柜']
for r in range(2, 18):
    if r <= 10:
        nm, raw, unit, qty, note = c(ws, r, 3), c(ws, r, 4), c(ws, r, 5), c(ws, r, 6), c(ws, r, 7)
    else:
        nm, raw, unit, qty, note = c(ws, r, 4), c(ws, r, 5), c(ws, r, 6), c(ws, r, 7), c(ws, r, 8)
    if not nm and not raw:
        continue
    spec, mat, param = split_text_as_spec(raw)
    add('配电柜', nm, spec, mat, param, unit, qty, note, cat='配电柜')
    audit_add('配电柜', r, nm, raw, spec, mat, param)

# ===== 4. 线缆 =====
ws = wb['线缆']
for r in range(1, 39):
    nm, raw = c(ws, r, 4), c(ws, r, 5)
    if not nm:
        continue
    spec, mat, param = split_text_as_spec(raw)
    add('线缆', nm, spec, mat, param, c(ws, r, 6), c(ws, r, 7), c(ws, r, 8), cat='线缆')
    audit_add('线缆', r, nm, raw, spec, mat, param)

# ===== 5. 钢材 =====
ws = wb['钢材']
for r in range(3, 59):
    nm, raw = c(ws, r, 5), c(ws, r, 6)
    if r <= 27:
        unit, qty, eng = c(ws, r, 7), c(ws, r, 8), ''
    else:
        unit, qty, eng = c(ws, r, 12), c(ws, r, 13), c(ws, r, 7)
    if not nm and not raw:
        continue
    if eng:
        rest, m2 = extract_mat(eng)
        sch = SCH_RE.findall(rest)
        rest = clean(SCH_RE.sub(' ', rest))
        spec = clean(raw + (' ' + ' '.join(sch) if sch else ''))
        mat = m2
        param = rest
    else:
        spec, mat, param = split_text_as_spec(raw)
    add('钢材', nm, spec, mat, param, unit, qty, '', cat='钢材')
    audit_add('钢材', r, nm, (raw + ' || ' + eng), spec, mat, param)

# ===== 6. 灯具 =====
ws = wb['灯具']
for r in range(4, 9):
    nm, raw = c(ws, r, 5), c(ws, r, 6)
    if not nm:
        continue
    spec, mat, param = split_text_as_spec(raw)
    add('灯具', nm, spec, mat, param, c(ws, r, 7), c(ws, r, 8), c(ws, r, 9), cat='灯具')
    audit_add('灯具', r, nm, raw, spec, mat, param)

# ===== 7. 阀门 =====
ws = wb['阀门']
for r in range(4, 15):
    nm, raw = c(ws, r, 5), c(ws, r, 6)
    if not nm:
        continue
    spec, mat, param = split_text_as_spec(raw)
    add('阀门', nm, spec, mat, param, c(ws, r, 7), c(ws, r, 8), c(ws, r, 9), cat='阀门')
    audit_add('阀门', r, nm, raw, spec, mat, param)

# ===== 8. 桥架 =====
ws = wb['桥架']
for r in range(4, 7):
    nm, raw = c(ws, r, 4), c(ws, r, 5)
    if not nm:
        continue
    spec, mat, param = split_text_as_spec(raw)
    add('桥架', nm, spec, mat, param, c(ws, r, 6), c(ws, r, 7), c(ws, r, 8), cat='桥架')
    audit_add('桥架', r, nm, raw, spec, mat, param)

# ===== 9. 其他 =====
ws = wb['其他']
for r in range(2, 24):
    nm, raw = c(ws, r, 5), c(ws, r, 6)
    if not nm:
        continue
    spec, mat, param = split_text_as_spec(raw)
    add('其他', nm, spec, mat, param, c(ws, r, 7), c(ws, r, 8), c(ws, r, 9), cat='其他')
    audit_add('其他', r, nm, raw, spec, mat, param)

# ===== 10. 管件1 =====
ws = wb['管件1']
for r in range(2, 89):
    nm, raw, eng = c(ws, r, 3), c(ws, r, 4), c(ws, r, 5)
    if not nm and not raw:
        continue
    spec = clean(raw)
    rest, m2 = extract_mat(eng)
    mat = m2
    param = clean(rest)
    if not spec and not mat and not param:
        continue
    add('管件1', nm, spec, mat, param, c(ws, r, 10), c(ws, r, 11), '', cat='管件')
    audit_add('管件1', r, nm, (raw + ' || ' + eng), spec, mat, param)

# ===== 11. 保温 =====
ws = wb['保温']
for r in range(2, 8):
    nm, raw, desc = c(ws, r, 4), c(ws, r, 5), c(ws, r, 6)
    if not nm:
        continue
    rest, m2 = extract_mat(desc)
    spec = clean(raw)
    add('保温', nm, spec, m2, rest, c(ws, r, 11), c(ws, r, 12), '', cat='保温')
    audit_add('保温', r, nm, (raw + ' || ' + desc), spec, m2, rest)

# ===== 12. 储罐 =====
ws = wb['储罐']
starts = [3, 8, 13, 18]
for i, r in enumerate(starts):
    end = (starts[i + 1] - 1) if i + 1 < len(starts) else 22
    nm = c(ws, r, 4)
    first = c(ws, r, 5)
    mat = c(ws, r, 6)
    unit = c(ws, r, 7)
    qty = c(ws, r, 8)
    note = c(ws, r, 9)
    params = [c(ws, x, 5) for x in range(r + 1, end + 1)]
    spec, param = merge_device(nm, params, first)
    rest, m2 = extract_mat(param)
    mat = clean(mat + '，' + m2) if (m2 and mat) else (m2 or mat)
    param = clean(rest)
    add('储罐', nm, spec, mat, param, unit, qty, note, cat='储罐类', tag=c(ws, r, 3))
    audit_add('储罐', r, nm, first, spec, mat, param)

# ===== 13. 仪表 =====
ws = wb['仪表']
for r in range(9, 21):
    nm, raw = c(ws, r, 2), c(ws, r, 3)
    if not nm:
        continue
    spec, mat, param = split_text_as_spec(raw)
    add('仪表', nm, spec, mat, param, c(ws, r, 4), c(ws, r, 5), '', cat='仪表')
    audit_add('仪表', r, nm, raw, spec, mat, param)

# ===== 14. 风机 =====
ws = wb['风机']
fstarts = [3, 7, 12, 19]
for i, r in enumerate(fstarts):
    end = (fstarts[i + 1] - 1) if i + 1 < len(fstarts) else 24
    nm = c(ws, r, 5)
    first = c(ws, r, 6)
    mat = c(ws, r, 7)
    unit = c(ws, r, 8)
    qty = c(ws, r, 9)
    note = c(ws, r, 10)
    params = [c(ws, x, 6) for x in range(r + 1, end + 1)]
    spec, param = merge_device(nm, params, first)
    rest, m2 = extract_mat(param)
    mat = clean(mat + '，' + m2) if (m2 and mat) else (m2 or mat)
    param = clean(rest)
    add('风机', nm, spec, mat, param, unit, qty, note, cat='风机', tag=c(ws, r, 4))
    audit_add('风机', r, nm, first, spec, mat, param)

# ===== 15. 泵 =====
ws = wb['泵']
nm = c(ws, 2, 6)
params = [c(ws, x, 7) for x in range(3, 7)]
spec, param = merge_device(nm, params, c(ws, 2, 7))
rest, m2 = extract_mat(param)
mat = clean(c(ws, 2, 8) + '，' + m2) if m2 else c(ws, 2, 8)
add('泵', nm, spec, mat, clean(rest), c(ws, 2, 9), c(ws, 2, 10), '', cat='泵', tag=c(ws, 2, 5))
audit_add('泵', 2, nm, c(ws, 2, 7), spec, mat, clean(rest))

# ---------- 写新表 ----------
ORDER = ['设备', '工程量', '配电柜', '线缆', '钢材', '灯具', '阀门', '桥架',
         '其他', '管件1', '保温', '储罐', '仪表', '风机', '泵']
WITH_TAG = {'设备', '储罐', '风机', '泵'}

HDR_FILL = PatternFill('solid', fgColor='E8EEF7')
HDR_FONT = Font(name='微软雅黑', size=10, bold=True, color='1F3864')
BODY_FONT = Font(name='微软雅黑', size=10)
FLAG_FONT = Font(name='微软雅黑', size=10, color='C00000')
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
FLAG_FILL = PatternFill('solid', fgColor='FFF2CC')

out = Workbook()
out.remove(out.active)
stats = []
for name in ORDER:
    rows = sheets.get(name, [])
    cols = ['行号']
    if name in WITH_TAG:
        cols.append('设备位号')
    cols += ['类别', '名称', '规格型号', '材质/牌号', '技术参数', '单位', '数量', '备注', '待补标记']
    ws2 = out.create_sheet(name)
    ws2.append(cols)
    for j, cn in enumerate(cols, 1):
        cell = ws2.cell(1, j)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER
    for i, d in enumerate(rows, 1):
        vals = [i]
        if name in WITH_TAG:
            vals.append(d['tag'])
        vals += [d['cat'], d['name'], d['spec'], d['mat'], d['param'],
                 d['unit'], d['qty'], d['note'], d['flag']]
        ws2.append(vals)
        for j, v in enumerate(vals, 1):
            cell = ws2.cell(i + 1, j)
            cell.font = FLAG_FONT if (j == len(cols) and v) else BODY_FONT
            cell.border = BORDER
            if j == len(cols) and v:
                cell.fill = FLAG_FILL
            if cols[j - 1] in ('技术参数', '备注'):
                cell.alignment = Alignment(vertical='top', wrap_text=True)
            elif cols[j - 1] in ('规格型号', '材质/牌号', '类别', '设备位号'):
                cell.alignment = Alignment(vertical='top', wrap_text=True)
            else:
                cell.alignment = Alignment(vertical='top', horizontal='left')
    ws2.freeze_panes = 'A2'
    ws2.auto_filter.ref = f"A1:{gl(len(cols))}{len(rows)+1}"
    widths = {'行号': 6, '设备位号': 15, '类别': 11, '名称': 26, '规格型号': 26,
              '材质/牌号': 22, '技术参数': 52, '单位': 7, '数量': 9, '备注': 18, '待补标记': 22}
    for j, cn in enumerate(cols, 1):
        ws2.column_dimensions[gl(j)].width = widths.get(cn, 12)
    ws2.row_dimensions[1].height = 26
    flagcnt = sum(1 for d in rows if d['flag'])
    stats.append((name, len(rows), flagcnt))

out.save(OUT)

print(f"{'工作表':<10}{'行数':>6}{'待补行':>8}")
tot = tf = 0
for n, cnt, f in stats:
    print(f"{n:<10}{cnt:>6}{f:>8}")
    tot += cnt
    tf += f
print(f"{'合计':<10}{tot:>6}{tf:>8}")

json.dump(audit, open(REPORT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n复核清单条数:', len(audit))
print('已保存:', OUT)
