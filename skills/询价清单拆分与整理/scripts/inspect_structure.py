# -*- coding: utf-8 -*-
"""结构摸底：判断清单属于「形态 A 单表拆分」还是「形态 B 多表复原」。

用法:  python inspect_structure.py <文件路径>

输出：每张工作表的规模、每列的非空数/首个非空行/首个非空值、合并单元格范围，
      以及"首行是否像表头"的初判。

判据（脚本末尾会给提示）：
  · 少数几张表 + 首行是表头 + 列位齐整        → 形态 A（单表拆分）
  · 多数表无表头 + 起始列从 B/C/D 各不相同    → 形态 B（多表复原）

⚠️ 不要相信通用 table 检查器 —— 它会把第一行当表头，对这类文件必然误判。
"""
import sys, io, os, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 表头字段名线索（用于初判首行是不是表头）
HDR_HINT = re.compile(r"序号|名称|规格|材质|牌号|单位|数量|备注|单价|合价|型号|参数|图号|类别")


def col_letter(i):
    """1 → A, 27 → AA"""
    s = ""
    while i > 0:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def sheets_xlsx(path):
    from openpyxl import load_workbook
    wb = load_workbook(path)
    out = []
    for name in wb.sheetnames:
        ws = wb[name]
        cells = [[ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
                 for r in range(1, ws.max_row + 1)]
        merged = [str(m) for m in ws.merged_cells.ranges]
        out.append((name, cells, merged))
    return out


def sheets_xls(path):
    import xlrd
    bk = xlrd.open_workbook(path)
    out = []
    for sh in bk.sheets():
        cells = [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]
        merged = []
        try:
            for rlo, rhi, clo, chi in sh.merged_cells:
                merged.append(f"{col_letter(clo + 1)}{rlo + 1}:{col_letter(chi)}{rhi}")
        except Exception:
            pass
        out.append((sh.name, cells, merged))
    return out


def is_blank(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        sys.exit(1)

    print(f"文件: {path}")
    print(f"大小: {os.path.getsize(path)} bytes | 读取器: "
          f"{'openpyxl' if path.lower().endswith(('.xlsx', '.xlsm')) else 'xlrd'}")

    sheets = sheets_xlsx(path) if path.lower().endswith((".xlsx", ".xlsm")) else sheets_xls(path)

    nonempty, hdr_like, first_cols = [], [], []

    for name, cells, merged in sheets:
        nrow = len(cells)
        ncol = len(cells[0]) if cells else 0
        nfilled = sum(1 for row in cells for v in row if not is_blank(v))
        print(f"\n{'=' * 70}\n=== 工作表 '{name}' | {nrow} 行 × {ncol} 列 | "
              f"非空单元格 {nfilled} | 合并区 {len(merged)} ===")
        if nfilled == 0:
            print("    (空表)")
            continue
        nonempty.append(name)

        for c in range(ncol):
            vals = [(r + 1, cells[r][c]) for r in range(nrow) if not is_blank(cells[r][c])]
            if vals:
                print(f"  {col_letter(c + 1):>2} 非空{len(vals):>4}  "
                      f"首行R{vals[0][0]:<5} {repr(vals[0][1])[:44]}")

        if merged:
            print(f"   合并区({len(merged)}): {merged[:10]}{' ...' if len(merged) > 10 else ''}")

        # 表头行检测：在数据区之前的前 5 行里找最像表头的一行。
        # ⚠️ 本类文件 R1 常是标题行、表头在 R2，因此不能只看首行。
        best_row, best_hits = None, 0
        for r in range(min(5, nrow)):
            vals = [str(v).strip() for v in cells[r] if not is_blank(v)]
            hits = sum(1 for v in vals if HDR_HINT.search(v))
            if hits > best_hits:
                best_hits, best_row = hits, r + 1
        looks_hdr = best_hits >= 3
        if looks_hdr:
            hdr_like.append(name)
            print(f"   表头行: R{best_row}  (命中字段名 {best_hits} 个)")
            if best_row > 1:
                print(f"   ↑ 前 {best_row - 1} 行是标题/说明行，数据自 R{best_row + 1} 起")
        else:
            print(f"   表头行: 未识别到  (前 5 行最多命中字段名 {best_hits} 个)")

        # 首个非空列（形态 B 的典型信号：各表起始列不同）
        for c in range(ncol):
            if any(not is_blank(cells[r][c]) for r in range(nrow)):
                first_cols.append((name, col_letter(c + 1)))
                break

    # ---------- 判定提示 ----------
    print(f"\n{'=' * 70}")
    print(f"非空工作表 {len(nonempty)} 张: {nonempty}")
    if first_cols:
        spread = sorted({c for _, c in first_cols})
        print(f"各表首个非空列: {first_cols}")
        print(f"起始列分布: {spread}")

    print("\n判据提示：")
    n_sheet, n_hdr = len(nonempty), len(hdr_like)
    spread = {c for _, c in first_cols}
    if n_sheet and n_hdr >= max(1, (n_sheet + 1) // 2) and len(spread) <= 2:
        print("  → 倾向【形态 A 单表拆分】：表头行齐备、起始列一致")
        print("     下一步读 references/A-单表拆分.md")
    elif n_sheet and n_hdr <= n_sheet // 2 and len(spread) > 1:
        print("  → 倾向【形态 B 多表复原】：多数表无表头、各表起始列不相同")
        print("     下一步读 references/B-多表复原.md")
    else:
        print("  → 特征混合或信号不足：先 B 后 A（先逐表理顺，再按类别重组）")
        print("     两份 reference 都读；或先把上面的列清单发给用户确认")

    print("\n还要查的：① 序号是否跨表重号 ② 是否存在'一台设备占多行'的合并区")
    print("          ③ 源表把数值型文本列存成了数字（如材质 304.0）")


if __name__ == "__main__":
    main()
