# -*- coding: utf-8 -*-
"""【形态 A 参考实现】把一张大清单按分类拆分 / 合并输出 xlsx，格式照抄用户提供的询价单模板。

⚠️ 本脚本来自真实案例，文件头「配置区」硬编码了该案例的路径与分类映射。
   复用时按实际文件改写：SRC / TPL / OUT / CATS / NAME_CAT / NAME_ORDER / TITLE_LINES / EMPTY_NAME_ROWS。

用法:  python split_by_category_example.py [strict|loose] [multi|single]
  strict (默认) 只合并「除数量外各列逐字全等」的行
  loose        额外归一：PN=/PN 同型、备注顿号差异、图集号材质视为空（详见说明）
  multi (默认) 每个类别一个独立 .xlsx
  single       所有类别合并进一个 .xlsx，每类别一张工作表（对外询价用这份）

行序：类别内 = 品类逻辑序 → 规格口径升序 → 材质 → 技术参数 → 备注。
（口径取自规格型号里的 DN 数字；无 DN 时退化为该串的数字序列，属数值近似排序）
输出目录随口径自动分开，互不覆盖。
"""
import xlrd, re, sys, io, os
from copy import copy
from collections import Counter, OrderedDict, defaultdict
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

MODE = (sys.argv[1] if len(sys.argv) > 1 else "strict").lower().strip()
assert MODE in ("strict", "loose"), f"未知口径 {MODE!r}，只支持 strict / loose"
LAYOUT = (sys.argv[2] if len(sys.argv) > 2 else "multi").lower().strip()
assert LAYOUT in ("multi", "single"), f"未知输出形态 {LAYOUT!r}，只支持 multi / single"

SRC = r"D:\UserData\Documents\xwechat_files\wxid_ofdozq3goua321_291d\msg\file\2026-10\锌粉、熔铸车间设备、材料非标制作询价表.xls"
TPL = r"D:\工作\材料\询价\中煤鄂尔多斯\20261005中煤鄂尔多斯火炬气治理改造项目材料计划（管件）.xlsx"
OUT = (r"D:\UserData\Documents\Workbuddy\2026-10-12-15-43-34\锌粉熔铸车间_分类拆分"
       + ("" if MODE == "strict" else "_宽松"))
print(f"=== 口径: {MODE} | 输出: {OUT} ===\n")

CATS = ["钢材", "管件", "阀门", "桥架", "配电柜", "线缆", "其他", "设备", "仪表"]

# ---------- 96 个去重名称的显式归类 ----------
NAME_CAT = {
    # 管件
    "316不锈钢快速接头(公头)": "管件", "316不锈钢快速接头(母头)": "管件",
    "45°弯头": "管件", "45°斜三通": "管件", "90°弯头": "管件",
    "PVC-U塑料排水管": "管件", "Y型三通": "管件", "三通": "管件",
    "偏心异径管": "管件", "同心异径管": "管件", "单管吊架": "管件",
    "可曲挠柔性接头": "管件", "可曲挠橡胶接头": "管件", "地漏": "管件",
    "平管支架": "管件", "异径三通": "管件", "异径接头": "管件",
    "悬臂支架": "管件", "正三通": "管件", "泄水丝堵": "管件",
    "泄水管": "管件", "盲板": "管件", "管卡": "管件",
    "管道支架、支座、管托": "管件", "钢骨架塑料复合管": "管件",
    "顺水三通": "管件", "高压管道配套管件、法兰、管道支架，": "管件",
    "高压虹吸管圈": "管件", "高压软管": "管件",
    # 钢材
    "不锈钢管": "钢材", "压缩空无缝钢管": "钢材", "压缩空气无缝钢管": "钢材",
    "方管": "钢材", "无缝钢管": "钢材", "钢材": "钢材", "钢板、型钢": "钢材",
    # 阀门
    "Y型过滤器": "阀门", "倒流器": "阀门", "倒流器组(带水表)": "阀门",
    "减压阀": "阀门", "双活塞式蝶式多功能水泵控制阀": "阀门", "可调式减压阀": "阀门",
    "截止阀": "阀门", "数字锁定静态平衡阀": "阀门", "止回阀": "阀门",
    "法兰式不锈钢球阀": "阀门", "法兰式高压止回阀": "阀门", "球形污水止回阀": "阀门",
    "球阀": "阀门", "自力式二通温控阀": "阀门", "自动排气阀(带截止阀)": "阀门",
    "蝶阀": "阀门", "配套:球阀": "阀门", "泄水阀": "阀门",
    # 仪表
    "压力表": "仪表", "弹簧压力表": "仪表", "温度计": "仪表",
    "磁助电接点压力表": "仪表", "水表": "仪表",
    # 设备
    "储气罐": "设备", "冷气机": "设备", "电动葫芦": "设备",
    "移动式蒸发型冷风机": "设备", "蒸发型冷风机": "设备", "潜水泵": "设备",
    "洗地机": "设备", "边墙式排风机": "设备",
    "边墙式送风机（风机壳体环氧树脂喷涂）": "设备",
    "钢制联箱管耐腐蚀型散热器": "设备", "无缝钢铝高压耐腐蚀散热器": "设备",
    "暖通其他设备": "设备",
    # 其他
    "卸灰罩（放灰口位置）": "其他", "单层百叶风口": "其他",
    "感应式冲洗阀壁挂式小便器": "其他", "方形散流器": "其他", "暖通材料": "其他",
    "柔性闭孔橡塑泡沫": "其他", "检测孔": "其他", "污水盆(乙型)": "其他",
    "洗脸盆": "其他", "液压油": "其他", "液压脚踩冲洗阀蹲式大便器": "其他",
    "湿冶管道材料": "其他", "玻璃钢格栅": "其他", "给排水系统材料": "其他",
    "观察口、清灰口": "其他", "设备标示、安全标识牌": "其他", "设备标示牌": "其他",
    "设备润滑油": "其他", "超细离心玻璃棉": "其他", "铝箔保护层": "其他",
    "镀锌网格栅": "其他", "除尘风管": "其他", "风管": "其他",
    "风管软连接": "其他", "埋刮板机检修平台": "其他",
}
# 名称为空、系统名写在规格型号列的行（Excel 行号）→ 归设备
EMPTY_NAME_ROWS = {19: "设备", 20: "设备", 21: "设备"}

# ---------- 类别内的「品类逻辑序」（供应商阅读序）----------
# 排序思路：按现场安装/加工顺序 —— 管材 → 弯头 → 三通 → 异径管 → 接头 → 附件 → 支架。
# 未列入的名称排在末尾（按名称字符串），便于日后新增名称时不致出错。
NAME_ORDER = {
    "钢材": [
        "无缝钢管", "压缩空气无缝钢管", "压缩空无缝钢管", "不锈钢管",
        "方管", "钢板、型钢", "钢材",
    ],
    "管件": [
        # 管材
        "PVC-U塑料排水管", "钢骨架塑料复合管", "泄水管", "高压软管",
        # 弯头
        "90°弯头", "45°弯头",
        # 三通
        "三通", "正三通", "异径三通", "45°斜三通", "Y型三通", "顺水三通",
        # 异径管 / 接头
        "同心异径管", "偏心异径管", "异径接头",
        "可曲挠柔性接头", "可曲挠橡胶接头",
        "316不锈钢快速接头(公头)", "316不锈钢快速接头(母头)",
        # 附件
        "盲板", "泄水丝堵", "地漏",
        # 高压系统
        "高压虹吸管圈", "高压管道配套管件、法兰、管道支架，",
        # 支架
        "管道支架、支座、管托", "平管支架", "单管吊架", "悬臂支架", "管卡",
    ],
    "阀门": [
        "截止阀", "蝶阀",
        "球阀", "配套:球阀", "法兰式不锈钢球阀",
        "止回阀", "法兰式高压止回阀", "球形污水止回阀",
        "减压阀", "可调式减压阀",
        "Y型过滤器", "自动排气阀(带截止阀)", "数字锁定静态平衡阀",
        "自力式二通温控阀", "双活塞式蝶式多功能水泵控制阀",
        "泄水阀", "倒流器", "倒流器组(带水表)",
    ],
    "仪表": ["压力表", "弹簧压力表", "磁助电接点压力表", "温度计", "水表"],
    "设备": [
        "储气罐", "电动葫芦",
        "边墙式排风机", "边墙式送风机（风机壳体环氧树脂喷涂）",
        "蒸发型冷风机", "移动式蒸发型冷风机", "冷气机",
        "钢制联箱管耐腐蚀型散热器", "无缝钢铝高压耐腐蚀散热器",
        "潜水泵", "洗地机", "暖通其他设备",
        "除尘系统（PC-1）", "排风系统（P-1）",
        "高压水泵房送、排风系统系统（P-4、P-5、S-1、卫生间排风）",
    ],
    "其他": [
        # 卫生器具
        "洗脸盆", "污水盆(乙型)",
        "液压脚踩冲洗阀蹲式大便器", "感应式冲洗阀壁挂式小便器",
        # 通风空调
        "风管", "除尘风管", "风管软连接",
        "单层百叶风口", "方形散流器", "检测孔",
        # 除尘附件 / 平台
        "观察口、清灰口", "卸灰罩（放灰口位置）", "埋刮板机检修平台",
        # 格栅
        "玻璃钢格栅", "镀锌网格栅",
        # 保温
        "柔性闭孔橡塑泡沫", "超细离心玻璃棉", "铝箔保护层",
        # 标识
        "设备标示牌", "设备标示、安全标识牌",
        # 油品
        "液压油", "设备润滑油",
        # 汇总性条目
        "暖通材料", "湿冶管道材料", "给排水系统材料",
    ],
}
NAME_RANK = {(cat, nm): i for cat, names in NAME_ORDER.items() for i, nm in enumerate(names)}

TITLE_LINES = [
    "15 万吨/年锌基材料绿色智造工程锌粉车间、熔铸车间工艺设备安装及非标制作",
    "材料计划",
    "（含13%增值税含运费，货到付款，地址：济源市莲东村北河南豫光锌业有限公司厂区内）",
]

# ---------- 读源文件 ----------
bk = xlrd.open_workbook(SRC)
sh = bk.sheet_by_index(0)
assert sh.ncols == 8, sh.ncols

def sx(r, c):
    v = sh.cell_value(r, c)
    return "" if v in (None, "") else (str(v).strip() if isinstance(v, str) else v)

def txt(v):
    """文本列规范化：源表把材质 304/316 存成了数字 304.0，须还原为文本 '304'。"""
    if v is None or v == "":
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()

DELIMS = ["；", ";", "\n", "，", ",", " "]

def spec_split(spec):
    """把混在一起的一格拆成「规格型号」+「技术参数」。

    触发条件（长参数描述）：含换行 / 含全角冒号 / 去换行后长度≥30。
    触发后：若开头能切出一个"型号/规格短码"（≤25 字符、不含中文、含字母或数字），
    则留在「规格型号」，其余进「技术参数」；否则整格进「技术参数」。
    未触发的（短尺寸码如 DN40，PN40MPa）原样留在「规格型号」。
    恒等式：规格型号 + 技术参数 ≡ 源规格型号（校验脚本会验证）。
    """
    raw = str(spec)
    s = "\n".join(ln.strip() for ln in raw.split("\n") if ln.strip()).strip()
    if not s:
        return "", ""
    if not ("\n" in raw or "：" in s or len(s.replace("\n", "")) >= 30):
        return s, ""
    pos = [i for i in (s.find(d) for d in DELIMS) if i > 0]
    if pos:
        i = min(pos)
        head = s[:i].strip()
        rest = s[i + 1:].strip()
        probe = re.sub(r"^(型号|规格型号|规格)[:：]?", "", head).strip()   # 仅用于判断，不改原文
        if (0 < len(probe) <= 25 and not re.search(r"[\u4e00-\u9fff]", probe)
                and re.search(r"[A-Za-z0-9]", probe) and rest):
            return head, rest
    return "", s

rows = []          # (cat, 名称, 规格型号, 材质, 技术参数, 单位, 数量, 备注)
unmatched, placeholder_rows, ascii_colon, moved = [], [], [], []
for r in range(2, sh.nrows):
    excel_row = r + 1
    name = sx(r, 1); spec = sx(r, 2); mat = sx(r, 3)
    unit = sx(r, 4); qty = sx(r, 5); note = sx(r, 6); extra = sx(r, 7)
    name, spec, mat, unit = txt(name), txt(spec), txt(mat), txt(unit)
    note, extra = txt(note), txt(extra)

    if name:
        cat = NAME_CAT.get(name)
        if cat is None:
            unmatched.append((excel_row, name)); continue
    else:
        cat = EMPTY_NAME_ROWS.get(excel_row)
        if cat is None:
            unmatched.append((excel_row, "<空名称>")); continue
        placeholder_rows.append(excel_row)
        name, spec = spec, ""          # 系统名从规格型号列移回名称列

    spec_v, param_v = spec_split(spec)
    # 硬断言：拆分不得丢字（去掉空白与分隔符后必须与源规格型号等长同文）
    _nz = lambda t: re.sub(r"[\s；;，,\n]", "", str(t))
    if _nz(spec_v) + _nz(param_v) != _nz(spec):
        raise AssertionError(f"R{excel_row} 拆列丢字: {spec!r} -> {spec_v!r} + {param_v!r}")
    if param_v:
        moved.append((excel_row, name, spec_v, param_v))
    if ":" in str(spec_v) and "：" not in str(spec_v):
        ascii_colon.append((excel_row, spec_v))

    note_full = str(note).strip()
    if str(extra).strip():
        note_full = (note_full + "；" + str(extra).strip()) if note_full else str(extra).strip()

    q = qty
    if isinstance(q, float) and q.is_integer():
        q = int(q)

    # 末位 excel_row 仅用于审计/追溯，不参与去重比对
    rows.append((cat, name, spec_v, mat, param_v, unit, q, note_full, excel_row))

print("源表数据行:", sh.nrows - 2, "| 归类成功:", len(rows), "| 未匹配:", unmatched)
print("空名称行(系统名回填):", placeholder_rows)
print("规格型号含半角冒号:", ascii_colon)
print(f"\n拆列命中(规格型号 -> 技术参数) 共 {len(moved)} 行:")
for er, nm, sv, pv in moved:
    print(f"  R{er} | {nm} | 规格={sv[:32]!r} | 参数={pv[:46]!r}")
assert not unmatched, unmatched
assert len(rows) == sh.nrows - 2
SRC_ROWS = list(rows)          # 去重前快照（供审计与校验）
# 行结构: (类别, 名称, 规格型号, 材质, 技术参数, 单位, 数量, 备注, 源Excel行号)

def _n(t):
    f = float(str(t).replace(",", ""))
    return int(f) if f == int(f) else f

# ---------- 宽松口径的归一化器（仅 loose 使用）----------
def _canon_txt(s):
    """去空白、全角标点转半角、PN= 视同 PN。用于 规格型号 与 技术参数。"""
    t = str(s).replace("＝", "=").replace("，", ",").replace("：", ":")
    t = re.sub(r"\s+", "", t)
    return re.sub(r"PN\s*=\s*", "PN", t, flags=re.I)

_ATLAS = re.compile(r"^\d{2}[A-Za-z]\d{3}$")      # 标准图集号，如 04S301 / 10S416（不是材质牌号）
def _canon_mat(m):
    t = str(m).strip()
    return "" if _ATLAS.match(t) else t

def _canon_note(note, mat):
    """去空白与顿号/逗号/分号差异；备注与材质重复（录入冗余）视为空。"""
    t = re.sub(r"[\s、，,；;]", "", str(note))
    if t and t == re.sub(r"\s+", "", str(mat)):
        return ""
    return t

def _pick(vals):
    """组内取出现次数最多的原文；并列取首次出现。"""
    c = Counter(vals)
    best = max(c.values())
    for v in vals:
        if c[v] == best:
            return v
    return vals[0]

def _merge(members, show_key):
    """把一组同身份行并成 1 行（数量求和，代表值取多数原文）。"""
    rep_spec = _pick([x[2] for x in members])
    src = next(x for x in members if x[2] == rep_spec)     # 取该规格对应的原始技术参数，避免二次拆分
    raw_mats = [str(x[3]).strip() for x in members if str(x[3]).strip()]
    rep = list(members[0])
    rep[2], rep[4] = src[2], src[4]
    rep[3] = _pick(raw_mats) if raw_mats else ""
    rep[7] = _pick([x[7] for x in members])
    rep[6] = sum(_n(x[6]) for x in members)
    return tuple(rep)

def dedup(rows, mode):
    """返回 (新行列表, 合并组列表)；合并组 = (代表行, 成员行, 合计数量, 口径内是否合并)。"""
    if mode == "strict":
        key = lambda x: (x[0], x[1], x[2], x[3], x[4], x[5], x[7])
        buckets = OrderedDict()
        for x in rows:
            buckets.setdefault(key(x), []).append(x)
    else:
        # 宽松：先按 (类别,名称,规格(归一),技术参数(归一),备注(归一),单位) 粗分组
        # 注意：技术参数必须参与身份判定 —— 长参数描述行（如散热器 15/20/25 片、排风机两种工况）
        # 的差异恰恰全在技术参数列，漏掉它会误合并成不同规格的料。
        coarse = OrderedDict()
        for x in rows:
            coarse.setdefault((x[0], x[1], _canon_txt(x[2]), _canon_txt(x[4]),
                               _canon_note(x[7], x[3]), x[5]),
                              []).append(x)
        buckets = OrderedDict()
        for ck, grp in coarse.items():
            nonempty = sorted({_canon_mat(x[3]) for x in grp if _canon_mat(x[3])})
            if len(nonempty) <= 1:
                # 至多一种非空材质 → 空材质/图集号吸附进来，整组合并
                buckets[ck] = grp
            else:
                # 出现多种真实材质 → 保守：按材质各自成组，空材质不吸附
                for x in grp:
                    bk = ck + (_canon_mat(x[3]),)
                    buckets.setdefault(bk, []).append(x)

    out, groups = [], []
    for k, g in buckets.items():
        if len(g) == 1:
            out.append(g[0]); continue
        # 防呆：合并组内成员的「身份四要素」必须完全一致（曾因漏掉技术参数而误合并散热器/风机）
        _sig = {(x[1], _canon_txt(x[2]) if mode == "loose" else x[2],
                 _canon_txt(x[4]) if mode == "loose" else x[4], x[5]) for x in g}
        assert len(_sig) == 1, f"合并组身份不一致(模式={mode}): {_sig}"
        rep = _merge(g, k)
        out.append(rep); groups.append((rep, g, rep[6]))
    return out, groups

rows_strict, groups_strict = dedup(SRC_ROWS, "strict")
merged_groups = []
if MODE == "strict":
    rows, merged_groups = rows_strict, groups_strict
else:
    rows, merged_groups = dedup(SRC_ROWS, "loose")
    # 对比：宽松相比严格多合了哪些
    strict_keys = {frozenset(x[8] for x in g) for _, g, _ in groups_strict}
    extra = [(rep, g) for rep, g, _ in merged_groups
             if frozenset(x[8] for x in g) not in strict_keys]

_qsum_src = sum(_n(x[6]) for x in SRC_ROWS)
_qsum_new = sum(_n(x[6]) for x in rows)
print(f"\n去重合并: {len(SRC_ROWS)} 行 -> {len(rows)} 行 "
      f"(合并 {len(merged_groups)} 组, 消除 {len(SRC_ROWS) - len(rows)} 行)")
print(f"  数量总和: 合并前 {_qsum_src} = 合并后 {_qsum_new}")
assert _qsum_src == _qsum_new, "合并后数量总和不符，中止"
for _rep, _grp, _total in merged_groups:
    print(f"  [{len(_grp)}行→1] {_rep[1]} | {_rep[2][:30]} | 材质={_rep[3]} | {_rep[5]} | "
          f"{'+'.join(str(x[6]) for x in _grp)} = {_total} | 源行 {[x[8] for x in _grp]}")

if MODE == "loose":
    _es = len(SRC_ROWS) - len(rows_strict)
    _el = len(SRC_ROWS) - len(rows)
    print(f"\n宽松 vs 严格: 合并组 {len(groups_strict)} -> {len(merged_groups)}; "
          f"消除行 {_es} -> {_el} (净多消除 {_el - _es} 行); 总行 {len(rows_strict)} -> {len(rows)}")
    print(f"以下 {len(extra)} 组的成员构成与严格口径不同（全量列出，便于复核）:")
    for _rep, _grp in extra:
        print(f"  [{len(_grp)}行→1] {_rep[1]} | {_rep[2][:30]} | 材质={_rep[3]} | {_rep[5]} | "
              f"{'+'.join(str(x[6]) for x in _grp)} = {_rep[6]}")
        for x in _grp:
            print(f"        R{x[8]:<4} 规格={x[2]!r:<22} 材质={x[3]!r:<8} 数量={x[6]!r:<7} 备注={x[7][:28]!r}")

# ---------- 类别内排序：品类逻辑序 → 规格口径升序 → 材质 → 参数 → 备注 ----------
_DN = re.compile(r"DN\s*(\d+)", re.I)
_NUM = re.compile(r"\d+(?:\.\d+)?")
# 管件型号里的角度前缀（90E(S) / 45E(L) / 90°）与壁厚系列（Sch40）都不是"口径"，排序时须剥掉
_ANGLE = re.compile(r"^\s*(?:45|60|90|180)\s*(?:°|度)?\s*[A-Za-z]{0,3}\s*(?:\([A-Za-z]\))?")
_SCH = re.compile(r"Sch\s*\d+", re.I)

def dim_key(spec):
    """规格口径排序键（规范）：
    ① 含 DN → 取全部 DN 数字（DN50XDN32 → (50,32)）；
    ② 否则剥掉角弯的角度前缀与 Sch 壁厚系列后取剩余数字（90E(S)100-Sch40 → (100,)）。
    全部按数值比较，避免字符串序把 DN100 排在 DN65 前面。"""
    t = str(spec)
    dns = _DN.findall(t)
    if dns:
        return tuple(int(x) for x in dns)
    t = _SCH.sub("", _ANGLE.sub("", t))
    return tuple(float(x) for x in _NUM.findall(t))

def row_sort_key(x):
    return (NAME_RANK.get((x[0], x[1]), 10 ** 6), x[1],
            dim_key(x[2]), str(x[3]), str(x[4]), str(x[7]), str(x[2]))

_prev_pos = {x[8]: i for i, x in enumerate(rows)}
rows = sorted(rows, key=row_sort_key)
_moved = sum(1 for i, x in enumerate(rows) if _prev_pos[x[8]] != i)
print(f"\n排序(品类逻辑序 + 口径升序): 共重排 {_moved}/{len(rows)} 行")
for _c in CATS:
    _seq = list(dict.fromkeys(x[1] for x in rows if x[0] == _c))
    if _seq:
        print(f"  {_c}({len(_seq)}种): " + " → ".join(_seq))

cnt = Counter(x[0] for x in rows)
print("\n分类统计:")
for c in CATS:
    print(f"  {c}: {cnt.get(c,0)}")
print("  合计:", sum(cnt.values()))

# ---------- 样式取自模板 ----------
# 注意：不能直接搬 _style（StyleArray），其内部是模板工作簿的样式表索引，
# 跨工作簿赋值会 IndexError。必须搬真实样式对象。
tpl = load_workbook(TPL)
tws = tpl.active

def snap(cell):
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

def fill_sheet(ws, cat, data):
    """把一类数据铺成模板格式的一张工作表：R1 标题 / R2 表头 / 数据行 / 合计行。"""
    last = 2 + len(data) + 1                      # 合计行行号

    # R1 标题
    for c in range(1, 12):
        apply(ws.cell(1, c), ST["title"])
    ws.cell(1, 1).value = "\n".join(TITLE_LINES)
    ws.merge_cells("A1:K1")
    ws.row_dimensions[1].height = 78

    # R2 表头
    for c, v in enumerate(HDR, start=1):
        cell = ws.cell(2, c); apply(cell, ST["hdr"][c - 1]); cell.value = v
    ws.row_dimensions[2].height = 30

    # 数据行（序号在本工作表内 1..N 连续）
    for i, (_, name, sp, mat, param, unit, qty, note, _er) in enumerate(data):
        r = 3 + i
        vals = [i + 1, cat, name, sp, mat, param, unit, qty, note, None,
                f'=IF(J{r}="","",H{r}*J{r})']
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(r, c)
            apply(cell, ST["dat"][c - 1])
            if v is not None:
                cell.value = v
        ws.row_dimensions[r].height = 33

    # 合计行
    for c in range(1, 9):
        apply(ws.cell(last, c), ST["tot_a"])
    ws.cell(last, 1).value = "合计"
    apply(ws.cell(last, 11), ST["tot_k"])
    ws.cell(last, 11).value = f"=SUM(K3:K{last-1})"
    ws.merge_cells(f"A{last}:H{last}")

    for c, w in WIDTHS.items():
        ws.column_dimensions[c].width = w
    ws.freeze_panes = "A3"
    ws.auto_filter.ref = f"A2:K{last}"
    ws.sheet_format.defaultRowHeight = 13.5
    ws.sheet_format.defaultColWidth = 9

os.makedirs(OUT, exist_ok=True)
base = os.path.splitext(os.path.basename(SRC))[0]
made = []

if LAYOUT == "multi":
    for cat in CATS:
        data = [x for x in rows if x[0] == cat]
        if not data:
            continue
        wb = Workbook(); ws = wb.active; ws.title = cat
        fill_sheet(ws, cat, data)
        fp = os.path.join(OUT, f"{base}（{cat}）.xlsx")
        wb.save(fp); made.append((cat, len(data), fp))
        print(f"  写出 {cat}: {len(data)} 行 -> {os.path.basename(fp)}")
else:
    wb = Workbook()
    wb.remove(wb.active)                        # 去掉默认空表，避免出现多余 Sheet
    for cat in CATS:
        data = [x for x in rows if x[0] == cat]
        if not data:
            continue
        ws = wb.create_sheet(cat)
        fill_sheet(ws, cat, data)
        made.append((cat, len(data), None))
        print(f"  写入工作表 {cat}: {len(data)} 行")
    fp = os.path.join(OUT, f"{base}（全类别汇总）.xlsx")
    wb.save(fp)
    print(f"  合并文件 -> {os.path.basename(fp)}  ({len(wb.sheetnames)} 张工作表)")

# ---------- 审计 TSV ----------
_merge_cnt = {}                       # 首现行号 -> 该组由几行合并而来
for _key, _grp, _t in merged_groups:
    _merge_cnt[_grp[0][8]] = len(_grp)
with open(os.path.join(OUT, "_分类审计.tsv"), "w", encoding="utf-8-sig", newline="") as f:
    f.write("类别\t名称\t规格型号\t材质\t技术参数\t单位\t数量\t备注\t合并行数\t源Excel行号\n")
    for row in rows:
        f.write("\t".join(str(x).replace("\n", "⏎") for x in row)
                + f"\t{_merge_cnt.get(row[8], 1)}\t{row[8]}\n")

# ---------- 合并明细 TSV（供人工复核）----------
with open(os.path.join(OUT, "_合并明细.tsv"), "w", encoding="utf-8-sig", newline="") as f:
    f.write("类别\t名称\t规格型号\t材质\t技术参数\t单位\t合并前数量\t合并后数量\t源Excel行号\n")
    for _rep, _grp, _total in merged_groups:
        b = _rep
        f.write("\t".join([str(b[0]), str(b[1]), str(b[2]).replace("\n", "⏎"), str(b[3]),
                           str(b[4]).replace("\n", "⏎"), str(b[5]),
                           "+".join(str(x[6]) for x in _grp), str(_total),
                           ",".join(str(x[8]) for x in _grp)]) + "\n")
print("合并明细:", len(merged_groups), "组 -> _合并明细.tsv")

print("\n输出目录:", OUT)
print("生成文件数:", len(made))
