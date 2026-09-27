# -*- coding: utf-8 -*-
"""
tools/validate_raw_data.py  原始数据体检：运行 02 之前检查 config.yaml 列出的每个原始数据文件

为什么需要：02_build_fiscal_census.py 会把无法识别的代码、文字型数字当作缺失处理，单位写错（元与万元混用、
百分数没有除以 100）也不会报错，只会在结果里变成离谱的数值。本工具在运行 02 之前把这些问题找出来，
并给出 Excel 行号，方便对照原表改正。

在哪里运行：Mac 终端 (Terminal)
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python tools/validate_raw_data.py

检查范围：config.yaml 中 fiscal_census（县域财政、市辖区财政、各年普查、代码对照表、城区人口、住建部面板、
          土地出让、城投债务、专项债、开发区）、units（驻地点、撤县设区名单）、did 与 township 各节列出的文件。
          期望的列名在运行时从 数据/模板 中的模板读取，模板改了本工具自动跟着改。
检查内容：
  1. 编码能否读出（UTF-8 或 GB18030），模板示例行是否忘了删除
  2. 模板列是否齐全，有没有拼错的列名（给出最接近的模板列）
  3. 行政区划代码是否为 6 位（code12 为 12 位），级别是否对应（县域表不应有地级代码等），是否在 2020 年边界中
  4. 完全重复的行、同一代码年份出现多行
  5. 年份是否覆盖 config.yaml 中的分析年份，普查年份与文件是否一致
  6. share 开头的比例列是否在 0 至 1 之间（像百分数时提示除以 100），数值列有没有负数、文字型数字
  7. 量级：用粗略人口算人均支出，判断金额单位是否与 money_unit_in_raw 一致；人口是否把人与万人写反；
     税收收入是否大于一般公共预算收入；驻地点坐标是否在中国范围内、经纬度是否写反
输出：数据/中间/qa/raw_data_check.md          中文体检报告（汇总表加逐个文件的问题与提示）
      数据/中间/qa/raw_data_check_rows.csv    有问题的行（文件、Excel 行号、代码、年份、列、问题），可用 Excel 打开筛选
      终端每检查完一个文件打印一行进度。
"""
from __future__ import annotations

import difflib
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (CODE_DIR, VERSION_DIR, ChunkProgress, atomic_write_csv, atomic_write_text, get_logger,  # noqa: E402
                    load_config, norm_adcode, read_table, resolve)

LOG = get_logger("validate_raw_data")
# 模板随代码一起发布：测试时 FDT_BASE_DIR 指向的临时文件夹里没有模板，就用代码旁边的模板
TEMPLATE_DIR = next((d for d in (VERSION_DIR / "数据" / "模板", CODE_DIR.parent / "数据" / "模板") if d.exists()),
                    VERSION_DIR / "数据" / "模板")
MONEY_TO_YUAN = {"元": 1.0, "千元": 1e3, "万元": 1e4, "亿元": 1e8}
CODE_COLS = ("adcode", "pref_code", "code", "code12", "old_code", "new_code", "county_adcode", "prov_code")
PANEL_YEAR_COLS = ("year", "census_year")
OTHER_YEAR_COLS = ("change_year", "convert_year", "reform_year", "approval_year", "exit_year")
KEY_EXTRA = ("scope", "level", "category")       # 同一代码年份可以有多行、以这些列区分的表
MAX_EXAMPLES = 5
# year 列是 02、03 读取时必需的表（普查表缺 census_year 时 02 按文件对应的年份处理，不算必需）
YEAR_REQUIRED = {"fiscal_county", "fiscal_city_proper", "land_conveyance", "lgfv_debt", "special_bond", "mohurd_panel"}
HOUSING_SHARE = re.compile(r"^share_(rent|buy|self)")   # 住房来源比例（家庭户比例，各类之和应不超过 1）

# 各类文件中 02 必须用到的列（与模板取交集后使用；模板中已没有的列自动忽略）
CORE_REQUIRED = {"fiscal_county": ["gen_budget_revenue", "gen_budget_expenditure"],
                 "fiscal_city_proper": ["gen_budget_revenue", "gen_budget_expenditure"],
                 "census_county": ["pop_resident"], "seat_points": ["lon", "lat"],
                 "admin_crosswalk": ["new_code"], "land_conveyance": ["land_conv_revenue"],
                 "lgfv_debt": ["lgfv_debt"], "special_bond": ["category", "amount"],
                 "devzone": ["level", "approved_area_km2"]}


# ---------------------------------------------------------------------------
# 代码块 1：要检查的文件清单
# 目的：从 config.yaml 取出每个原始数据文件的路径，对应到模板。必需文件缺失记为问题，可选文件缺失只作说明。
# 结果：列表，每项为 (中文名称, 路径, 模板名, 是否必需, 附加信息)。
# ---------------------------------------------------------------------------
def file_specs(cfg: dict) -> list:
    fc, uc = cfg.get("fiscal_census") or {}, cfg.get("units") or {}
    did, tw = cfg.get("did") or {}, cfg.get("township") or {}
    specs = [("县域财政", fc.get("fiscal_county_file"), "fiscal_county", True, {}),
             ("市辖区财政", fc.get("fiscal_city_file"), "fiscal_city_proper", True, {})]
    for y, p in (fc.get("census_files") or {}).items():
        specs.append((f"{y} 年普查", p, "census_county", int(y) == 2020, {"census_year": int(y)}))
    specs += [("代码对照表", fc.get("crosswalk_file"), "admin_crosswalk", False, {}),
              ("城区人口", fc.get("city_urban_pop_file"), "city_urban_pop", False, {}),
              ("住建部面板", fc.get("mohurd_file"), "mohurd_panel", False, {}),
              ("土地出让", fc.get("land_conveyance_file"), "land_conveyance", False, {}),
              ("城投有息债务", fc.get("lgfv_debt_file"), "lgfv_debt", False, {}),
              ("新增专项债", fc.get("special_bond_file"), "special_bond", False, {}),
              ("开发区目录", fc.get("devzone_file"), "devzone", False, {}),
              ("驻地点", uc.get("seat_points_file"), "seat_points", bool(uc.get("require_seats")), {}),
              ("撤县设区名单", uc.get("converted_districts_file"), "converted_districts", False, {}),
              ("省直管县改革年份", did.get("pmc_file"), "pmc_reform_years", False, {}),
              ("撤县设区事件", did.get("conversion_events_file"), "county_district_conversion_events", False, {}),
              ("贫困县名单", did.get("poverty_file"), "poverty_area_counties", False, {}),
              ("易地搬迁规模", did.get("relocation_file"), "relocation_by_county", False, {})]
    for y, p in (tw.get("census_township_files") or {}).items():
        specs.append((f"{y} 年乡镇街道普查", p, "census_township", False, {"census_year": int(y)}))
    return [s for s in specs if s[1]]


def read_template(name: str):
    """模板的列名与示例行。示例值为空或为数字的列视为数值列候选。"""
    p = TEMPLATE_DIR / f"{name}_template.csv"
    if not p.exists():
        return None, None
    t = read_table(p, code_cols=())
    ex = t.iloc[0] if len(t) else pd.Series(index=t.columns, dtype=object)
    return [str(c).strip() for c in t.columns], ex


def _j(seq) -> str:
    """列表写成 2017、2018、2019 的形式。"""
    return "、".join(_fmt(x) for x in seq)


def _fmt(v) -> str:
    """整数值的浮点数（如年份 2019.0）显示为 2019。"""
    if isinstance(v, (float, np.floating)) and float(v).is_integer():
        return str(int(v))
    return str(v)


# ---------------------------------------------------------------------------
# 代码块 2：单个文件的检查记录
# 目的：统一记录问题（必须改正）与提示（请核对），并收集有问题的行（给出 Excel 行号）。
# 结果：Check 对象，报告与问题行清单都由它生成。
# ---------------------------------------------------------------------------
class Check:
    def __init__(self, label, path: Path, template: str, required: bool):
        self.label, self.path, self.template, self.required = label, path, template, required
        self.problems, self.hints, self.rows = [], [], []
        self.status, self.n_rows, self.summary = "", 0, ""

    def problem(self, msg):
        self.problems.append(msg)

    def hint(self, msg):
        self.hints.append(msg)

    def add_rows(self, df: pd.DataFrame, mask, issue: str, column: str = "", code_col=None, year_col=None, value=None):
        """把 mask 选中的行记入问题行清单，返回示例文字，形如 第 n 行（代码，年份）。"""
        idx = df.index[np.asarray(mask, dtype=bool)]
        for i in idx[:200]:
            self.rows.append({"file": self.rel(), "excel_row": int(i) + 2,
                              "code": _fmt(df.at[i, code_col]) if code_col in df else "",
                              "year": _fmt(df.at[i, year_col]) if year_col in df else "",
                              "column": column, "value": "" if value is None else value.get(i, ""), "issue": issue})
        ex = []
        for i in idx[:MAX_EXAMPLES]:
            bits = [_fmt(df.at[i, c]) for c in (code_col, year_col) if c in df and pd.notna(df.at[i, c])]
            ex.append(f"第 {int(i) + 2} 行" + (f"（{'，'.join(bits)}）" if bits else ""))
        return "、".join(ex) + (" 等" if len(idx) > MAX_EXAMPLES else "")

    def rel(self) -> str:
        try:
            return str(self.path.relative_to(VERSION_DIR))
        except ValueError:
            return str(self.path)


# ---------------------------------------------------------------------------
# 代码块 3：通用检查（编码、列名、代码、重复、比例、负数、文字型数字）
# 目的：对所有文件都适用的检查。列名与数值列都由模板决定。
# 结果：写入 Check；返回读入的 DataFrame 以及代码列、年份列名，供专项检查使用。
# ---------------------------------------------------------------------------
def detect_encoding(path: Path) -> str:
    if path.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        return "Excel"
    raw = path.read_bytes()
    try:
        raw.decode("utf-8-sig")
        return "UTF-8"
    except UnicodeDecodeError:
        pass
    try:
        raw.decode("gb18030")
        return "GB18030（GBK）"
    except UnicodeDecodeError:
        return ""


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def generic_checks(ck: Check, tcols: list, example: pd.Series, c2u_codes: set | None):
    enc = detect_encoding(ck.path)
    if not enc:
        ck.problem("文件编码无法识别（既不是 UTF-8 也不是 GB18030）。请在 Excel 中另存为 CSV UTF-8。")
        return None
    code_like = [c for c in CODE_COLS if c in tcols]
    try:
        df = read_table(ck.path, code_cols=tuple(code_like) + ("unit_id",))
    except Exception as e:  # noqa: BLE001  读不出的原因多种多样，原样报告
        ck.problem(f"文件无法读取（{str(e)[:200]}）")
        return None
    df.columns = [str(c).strip() for c in df.columns]
    ck.n_rows = len(df)
    code_col = next((c for c in ("adcode", "pref_code", "code", "code12", "old_code") if c in tcols), None)
    year_col = next((c for c in PANEL_YEAR_COLS if c in tcols), None)
    info = [f"编码 {enc}，{len(df)} 行"]

    # 3a. 模板示例行
    if len(df):
        first = pd.Series("", index=df.index, dtype="string")
        for j in range(min(2, df.shape[1])):
            first = first + " " + df.iloc[:, j].astype("string").fillna("")
        demo = first.str.contains(r"XXXXXX|ZZZZ00|示例", regex=True).fillna(False).astype(bool)
        if demo.any():
            ck.problem(f"模板中的示例行没有删除（{ck.add_rows(df, demo, '模板示例行', code_col=code_col)}）")
            df = df[~demo]

    # 3b. 列名
    missing = [c for c in tcols if c not in df.columns]
    extra = [c for c in df.columns if c not in tcols and not c.startswith("Unnamed")]
    need_year = year_col if ck.template in YEAR_REQUIRED else None
    key_missing = [c for c in [code_col, need_year] + CORE_REQUIRED.get(ck.template, []) if c and c in missing]
    if key_missing:
        ck.problem(f"缺少必需的列 {_j(key_missing)}，02 无法使用本文件。列名须与 数据/模板/{ck.template}_template.csv 一致")
    opt_missing = [c for c in missing if c not in key_missing]
    if opt_missing:
        ck.hint(f"缺少可选列 {_j(opt_missing)}，这些变量将为缺失")
    for c in (extra if tcols else []):          # 没有模板时不做列名检查
        near = difflib.get_close_matches(c, missing, n=1, cutoff=0.6)
        if near:
            ck.problem(f"列名 {c} 不在模板中，可能是 {near[0]} 拼错了，02 不会读取它")
        else:
            ck.hint(f"列 {c} 不在模板中，02 不会读取")
    if not len(df):
        ck.problem("文件没有数据行")
        return None

    # 3c. 代码
    for c in [c for c in code_like if c in df.columns]:
        raw = df[c].astype("string").str.strip()
        filled = raw.notna() & raw.ne("")
        if c == "code12":
            ok = raw.str.fullmatch(r"\d{12}").fillna(False).astype(bool)
            norm = raw.where(ok)
        else:
            norm = df[c].map(norm_adcode)
            ok = norm.notna()
            twelve = raw.str.fullmatch(r"\d{12}").fillna(False).astype(bool)
            if twelve.any():
                ck.hint(f"{c} 有 {int(twelve.sum())} 行是 12 位统计用区划代码，将取前 6 位")
        bad = filled & ~ok
        if bad.any():
            ck.problem(f"{c} 有 {int(bad.sum())} 行无法识别为 {'12' if c == 'code12' else '6'} 位代码"
                       f"（{ck.add_rows(df, bad, '代码无法识别', c, code_col, year_col)}）")
        if c == code_col and (~filled).any():
            ck.problem(f"{c} 有 {int((~filled).sum())} 行为空（{ck.add_rows(df, ~filled, '代码为空', c, code_col, year_col)}）")
        if c != "code12":
            df[c] = norm
    if code_col and code_col in df and code_col != "code12":
        codes = df[code_col].dropna()
        if ck.template == "fiscal_city_proper":
            notpref = df[code_col].notna() & ~df[code_col].fillna("").str.endswith("00")
            if notpref.any():
                ck.problem(f"pref_code 应为地级代码（后两位为 00），有 {int(notpref.sum())} 行不是"
                           f"（{ck.add_rows(df, notpref, '不是地级代码', code_col, code_col, year_col)}）")
        elif ck.template in ("fiscal_county", "census_county"):
            pref = df[code_col].notna() & df[code_col].fillna("").str.endswith("00")
            if pref.any():
                # 普查表中东莞、中山等不设区地级市按其代码保留，02 归入市辖区单元；
                # 县域财政表中的这类记录会被 02 当作与市辖区财政重复而剔除，它们的财政应录入市辖区财政表
                where = ("东莞、中山等不设区地级市的财政请录入市辖区财政表（pref_code 填其代码），"
                         "县域财政表中的这类记录会被 02 当作重复剔除" if ck.template == "fiscal_county"
                         else "东莞、中山等不设区地级市按其代码保留即可，02 会自动归入市辖区单元")
                ck.hint(f"{int(pref.sum())} 行代码以 00 结尾，是地级或省级代码。县级表只应有县级代码，{where}"
                        f"（{ck.add_rows(df, pref, '地级或省级代码', code_col, code_col, year_col)}）")
        if c2u_codes and ck.template in ("fiscal_county", "census_county", "seat_points", "land_conveyance",
                                         "lgfv_debt", "special_bond", "devzone"):
            out = df[code_col].notna() & ~df[code_col].isin(c2u_codes) & ~df[code_col].fillna("").str.endswith("00")
            if out.any():
                ck.hint(f"{df.loc[out, code_col].nunique()} 个县级代码不在 2020 年边界中，多为撤并前的旧代码，"
                        f"需要在代码对照表中写明去向（{ck.add_rows(df, out, '不在 2020 年边界中', code_col, code_col, year_col)}）")
        info.append(f"{codes.nunique()} 个代码")

    # 3d. 重复
    exact = df.duplicated(keep="first")
    if exact.any():
        ck.problem(f"{int(exact.sum())} 行与前面某行完全相同，是重复录入（{ck.add_rows(df, exact, '完全重复', '', code_col, year_col)}）")
    if code_col:
        key = [code_col] + ([year_col] if year_col and year_col in df else []) + [c for c in KEY_EXTRA if c in df]
        uniq = df[~exact]
        dupk = (uniq.duplicated(key, keep=False) & uniq[code_col].notna()).reindex(df.index, fill_value=False)
        if dupk.any():
            ck.problem(f"{int(dupk.sum())} 行的 {'、'.join(key)} 相同但内容不同，02 会把它们相加，请确认是否重复录入"
                       f"（{ck.add_rows(df, dupk, '同一代码年份多行', '', code_col, year_col)}）")

    # 3e. 年份列的取值范围
    for c in [c for c in PANEL_YEAR_COLS + OTHER_YEAR_COLS if c in df]:
        y = to_num(df[c])
        bad = df[c].notna() & (y.isna() | (y < 1949) | (y > 2035) | (y % 1 != 0))
        if bad.any():
            ck.problem(f"{c} 有 {int(bad.sum())} 行不是 1949 至 2035 之间的整数年份"
                       f"（{ck.add_rows(df, bad, '年份无效', c, code_col, year_col)}）")
    if year_col and year_col in df:
        df[year_col] = to_num(df[year_col])
        yrs = df[year_col].dropna().astype(int)
        if len(yrs):
            info.append(f"年份 {yrs.min()} 至 {yrs.max()}")

    # 3f. 数值列：文字型数字、负数、比例
    skip = set(code_like) | set(PANEL_YEAR_COLS) | set(OTHER_YEAR_COLS)
    num_cols = []
    for c in tcols:
        if c in skip or c not in df:
            continue
        exv = example.get(c) if example is not None else None
        if pd.isna(exv) or to_num(pd.Series([exv])).notna().iloc[0]:
            num_cols.append(c)
    for c in num_cols:
        s = df[c]
        txt = s.astype("string").str.strip()
        v = to_num(s)
        nonnum = txt.notna() & txt.ne("") & v.isna()
        if nonnum.any():
            sample = "、".join(txt[nonnum].drop_duplicates().head(3).tolist())
            ck.problem(f"{c} 有 {int(nonnum.sum())} 个单元格不是数字（如 {sample}），02 会把它们当作缺失。"
                       f"千分位逗号、单位、横线要去掉（{ck.add_rows(df, nonnum, '不是数字', c, code_col, year_col)}）")
        neg = v < 0
        if neg.any():
            ck.problem(f"{c} 有 {int(neg.sum())} 个负值（{ck.add_rows(df, neg, '负值', c, code_col, year_col, v)}）")
        if c.startswith("share_") or c.endswith("_share"):
            vv = v.dropna()
            if len(vv) and vv.max() > 1:
                if vv.max() <= 100 and vv.median() > 1:
                    ck.problem(f"{c} 看起来是百分数（最大 {vv.max():g}），模板要求 0 至 1 的小数，请除以 100")
                else:
                    over = v > 1
                    ck.problem(f"{c} 有 {int(over.sum())} 个值大于 1，比例应在 0 至 1 之间"
                               f"（{ck.add_rows(df, over, '比例大于 1', c, code_col, year_col, v)}）")
        df[c] = v
    ck.summary = "，".join(info) + "。"
    return df, code_col, year_col


# ---------------------------------------------------------------------------
# 代码块 4：专项检查（年份覆盖、单位量级、坐标）
# 目的：财政表检查分析年份是否齐全，并用粗略人口算人均支出判断金额单位；普查检查年份与人口单位；
#       住建部面板检查人口单位与人均公园绿地；驻地点检查坐标范围与经纬度是否写反。
# 结果：写入 Check。
# ---------------------------------------------------------------------------
def fiscal_checks(ck: Check, df, code_col, year_col, cfg, rough_pop: dict | None):
    fc = cfg["fiscal_census"]
    main = [int(y) for y in fc.get("fiscal_years_main") or []]
    other = sorted({int(y) for k in ("fiscal_years_robust", "fiscal_years_2010", "fiscal_years_2000")
                    for y in (fc.get(k) or [])} - set(main))
    have = {"gen_budget_revenue", "gen_budget_expenditure"} <= set(df.columns)
    if year_col in df and have:
        ok = df["gen_budget_revenue"].notna() & df["gen_budget_expenditure"].notna()
        n_codes = df[code_col].nunique()
        cov = df[ok].groupby(df[year_col])[code_col].nunique()
        parts = [f"{y} 年 {int(cov.get(y, 0))} 个" for y in sorted(set(main + other))]
        ck.hint(f"收入与支出都有数的代码数（共 {n_codes} 个代码），{'，'.join(parts)}")
        low = [y for y in main if cov.get(y, 0) < 0.5 * n_codes]
        if low:
            ck.problem(f"主分析期年份 {_j(low)} 有收支数据的代码不到一半，fiscal_years_main 的均值会缺失或不完整")
        miss_other = [y for y in other if cov.get(y, 0) == 0]
        if miss_other:
            ck.hint(f"稳健性或历史期年份 {_j(miss_other)} 没有收支数据，对应的 rob、y2010、y2000 变量将为缺失")
        per = df[ok & df[year_col].isin(main)].groupby(code_col)[year_col].nunique()
        part = per[per < len(main)]
        if len(part) and main:
            ck.hint(f"{len(part)} 个代码在主分析期 {_j(main)} 年中缺少部分年份，均值只用有数的年份，示例 {_j(part.index[:5])}")
    if {"tax_revenue", "gen_budget_revenue"} <= set(df.columns):
        bad = df["tax_revenue"] > df["gen_budget_revenue"] * 1.001
        if bad.any():
            ck.problem(f"{int(bad.sum())} 行税收收入大于一般公共预算收入（税收是它的一部分），多为单位或列错位"
                       f"（{ck.add_rows(df, bad, '税收大于一般公共预算收入', 'tax_revenue', code_col, year_col)}）")
    # 人均支出：优先用同行的年末户籍人口（万人），其次用 2020 年普查常住人口
    unit = fc.get("money_unit_in_raw", "万元")
    mult = MONEY_TO_YUAN.get(unit)
    if "gen_budget_expenditure" in df and mult:
        pop = df["pop_hukou_yearend"] * 1e4 if "pop_hukou_yearend" in df else pd.Series(np.nan, index=df.index)
        src = "年末户籍人口"
        if pop.notna().sum() < 10 and rough_pop:
            pop = df[code_col].map(rough_pop)
            src = "2020 年普查常住人口"
        pc = df["gen_budget_expenditure"] * mult / pop.where(pop > 0)
        pcv = pc.dropna()
        if len(pcv) >= 3:
            med = float(pcv.median())
            ck.hint(f"按{src}粗算的人均一般公共预算支出中位数为 {med:,.0f} 元（金额单位按 config 的 {unit}）")
            if med > 1e6:
                ck.problem(f"人均支出中位数 {med:,.0f} 元，大得离谱。原始数据可能以元为单位，而 config.yaml 的 "
                           f"money_unit_in_raw 写的是 {unit}，两者要一致")
            elif med < 100:
                ck.problem(f"人均支出中位数只有 {med:,.1f} 元，小得离谱。原始数据可能以亿元为单位，而 config.yaml 的 "
                           f"money_unit_in_raw 写的是 {unit}，两者要一致")
            else:
                odd = (pc < 300) | (pc > 500000)
                if odd.any():
                    ck.hint(f"{int(odd.sum())} 行人均支出低于 300 元或高于 50 万元，请核对单位与人口"
                            f"（{ck.add_rows(df, odd, '人均支出异常', 'gen_budget_expenditure', code_col, year_col, pc.round(0))}）")
    if "pop_hukou_yearend" in df:
        p = df["pop_hukou_yearend"].dropna()
        if len(p) >= 3 and p.median() > 1e4:
            ck.problem(f"pop_hukou_yearend 中位数为 {p.median():,.0f}，模板单位是万人，看起来填成了人")


def census_checks(ck: Check, df, code_col, year_col, expect_year: int | None):
    if expect_year and year_col in df:
        y = to_num(df[year_col])
        wrong = y.notna() & (y != expect_year)
        if wrong.any():
            ck.problem(f"这是 config 中 {expect_year} 年的普查文件，但有 {int(wrong.sum())} 行 {year_col} 不是 {expect_year}"
                       f"（{ck.add_rows(df, wrong, '普查年份不符', year_col, code_col, year_col)}）")
        if y.isna().all():
            ck.hint(f"{year_col} 全部为空，02 按文件对应的年份 {expect_year} 使用")
    if "pop_resident" in df:
        p = df["pop_resident"].dropna()
        if len(p) >= 3 and p.median() < 1000:
            ck.problem(f"pop_resident 中位数只有 {p.median():,.1f}，模板单位是人，看起来填成了万人")
        for c in ("hh_pop", "households", "collective_pop"):
            if c in df:
                bad = df[c] > df["pop_resident"] * 1.001
                if bad.any():
                    ck.problem(f"{int(bad.sum())} 行 {c} 大于常住人口（{ck.add_rows(df, bad, f'{c} 大于常住人口', c, code_col, year_col)}）")
    hh = [c for c in df.columns if HOUSING_SHARE.match(c)]
    if len(hh) >= 3:
        tot = df[hh].sum(axis=1, min_count=len(hh))
        bad = tot > 1.02
        if bad.any():
            ck.hint(f"{int(bad.sum())} 行住房来源比例之和大于 1（{ck.add_rows(df, bad, '住房来源比例之和大于 1', '', code_col, year_col)}）")


def mohurd_checks(ck: Check, df, code_col, year_col, cfg):
    fc = cfg["fiscal_census"]
    need = sorted({int(y) for y in (fc.get("mohurd_years_main") or [])} | ({int(fc["mohurd_stock_year"])}
                                                                         if fc.get("mohurd_stock_year") else set()))
    if year_col in df and need:
        have = set(to_num(df[year_col]).dropna().astype(int))
        miss = [y for y in need if y not in have]
        if miss:
            ck.problem(f"缺少 03 要用的年份 {_j(miss)}（mohurd_years_main 与 mohurd_stock_year）")
    if "pop_urban_10k" in df:
        p = df["pop_urban_10k"].dropna()
        if len(p) >= 3 and p.median() > 1e3:
            ck.problem(f"pop_urban_10k 中位数为 {p.median():,.0f}，模板单位是万人，看起来填成了人")
    if "park_green_pc_m2" in df:
        bad = df["park_green_pc_m2"] > 100
        if bad.any():
            ck.hint(f"{int(bad.sum())} 行人均公园绿地大于 100 m²，请核对"
                    f"（{ck.add_rows(df, bad, '人均公园绿地大于 100', 'park_green_pc_m2', code_col, year_col)}）")
        if {"park_green_area_ha", "pop_urban_10k"} <= set(df.columns):
            temp = df["pop_temp_10k"].fillna(0) if "pop_temp_10k" in df else 0
            pop = (df["pop_urban_10k"] + temp) * 1e4
            implied = df["park_green_area_ha"] * 1e4 / pop.where(pop > 0)
            ratio = (implied / df["park_green_pc_m2"].where(df["park_green_pc_m2"] > 0)).dropna()
            if len(ratio) >= 3 and not 0.5 <= ratio.median() <= 2:
                ck.problem(f"公园绿地面积除以城区人口得到的人均值，是年鉴人均公园绿地的 {ratio.median():.2g} 倍，"
                           "面积（公顷）或人口（万人）的单位可能填错")


def seat_checks(ck: Check, df, code_col):
    if not {"lon", "lat"} <= set(df.columns):
        return
    lon, lat = df["lon"], df["lat"]
    miss = lon.isna() | lat.isna()
    if miss.any():
        ck.problem(f"{int(miss.sum())} 行经纬度为空（{ck.add_rows(df, miss, '经纬度为空', 'lon', code_col)}）")
    swapped = lat.between(73, 136) & lon.between(3, 54)
    if swapped.any():
        ck.problem(f"{int(swapped.sum())} 行经度与纬度写反了（{ck.add_rows(df, swapped, '经纬度写反', 'lon', code_col)}）")
    out = ~miss & ~swapped & ~(lon.between(73, 136) & lat.between(3, 54))
    if out.any():
        ck.problem(f"{int(out.sum())} 行坐标不在中国范围内（经度 73 至 136，纬度 3 至 54）"
                   f"（{ck.add_rows(df, out, '坐标不在中国范围', 'lon', code_col)}）")
    ck.hint("本工具无法判断坐标是否为 GCJ-02 或 BD-09。高德、百度来源的坐标须先用 tools/coord_gcj02_to_wgs84.py 转换")


def crosswalk_checks(ck: Check, df):
    if "change_date" in df:
        # 与 02 相同：2020/12/1、2020.12.01、2020年12月1日 都能识别；其他写法 02 会忽略，普查年 11 月后的变更就会漏映射
        raw = df["change_date"].astype("string").str.strip()
        norm = raw.str.replace(r"[./年月]", "-", regex=True).str.replace("日", "", regex=False)
        bad = raw.fillna("").ne("") & pd.to_datetime(norm, errors="coerce", format="%Y-%m-%d").isna()
        if bad.any():
            ck.problem(f"change_date 有 {int(bad.sum())} 行无法识别，应写作 YYYY-MM-DD"
                       f"（{ck.add_rows(df, bad, '日期无法识别', 'change_date', 'old_code', 'change_year')}）")
    if "weight" in df:
        w = df["weight"]
        bad = w.notna() & ((w <= 0) | (w > 1))
        if bad.any():
            ck.problem(f"weight 应在 0 至 1 之间，有 {int(bad.sum())} 行不是（{ck.add_rows(df, bad, '权重超出范围', 'weight', 'old_code')}）")
        if "old_code" in df:
            grp = [df["old_code"]] + ([df["change_year"].fillna(-1)] if "change_year" in df else [])
            s = w.fillna(1).groupby(grp).sum()
            off = s[(s - 1).abs() > 0.01]
            if len(off):
                ck.problem(f"{len(off)} 个旧代码拆分权重之和不等于 1，示例 {_j(k if isinstance(k, str) else k[0] for k in off.index[:5])}")


# ---------------------------------------------------------------------------
# 代码块 5：写出报告
# 目的：汇总表加逐个文件的问题与提示，写成中文 Markdown；有问题的行另存 CSV。
# 结果：数据/中间/qa/raw_data_check.md 与 raw_data_check_rows.csv。
# ---------------------------------------------------------------------------
def write_report(checks: list, out_dir: Path):
    n_prob = sum(1 for c in checks if c.status in ("有问题", "缺失"))
    n_hint = sum(1 for c in checks if c.status == "有提示")
    lines = ["# 原始数据体检报告", "",
             f"生成时间 {time.strftime('%Y-%m-%d %H:%M')}。按 config.yaml 列出的路径逐个检查，列名以 数据/模板 中的模板为准。",
             f"共 {len(checks)} 个文件，有问题或必需而缺失的 {n_prob} 个，只有提示的 {n_hint} 个。"
             "问题须改正后再运行 02_build_fiscal_census.py，提示请逐条核对。行号为 Excel 中的行号（表头为第 1 行）。", "",
             "| 内容 | 文件 | 状态 | 行数 | 问题 | 提示 |", "|---|---|---|---:|---:|---:|"]
    for c in checks:
        lines.append(f"| {c.label} | {c.rel()} | {c.status} | {c.n_rows if c.n_rows else ''} | "
                     f"{len(c.problems)} | {len(c.hints)} |")
    for c in checks:
        if c.status == "未提供":
            continue
        lines += ["", f"## {c.label}", "", f"文件 {c.rel()}，模板 {c.template}。{c.summary}", ""]
        lines += [f"- 【问题】{m}" for m in c.problems]
        lines += [f"- 【提示】{m}" for m in c.hints]
        if not c.problems and not c.hints:
            lines.append("- 未发现问题。")
    optional = [c for c in checks if c.status == "未提供"]
    if optional:
        lines += ["", "## 未提供的可选文件", "",
                  "以下文件不是运行 02 的必需输入，缺失时相关变量为缺失值。"
                  + "、".join(f"{c.label}（{c.rel()}）" for c in optional) + "。"]
    atomic_write_text(out_dir / "raw_data_check.md", "\n".join(lines) + "\n")
    rows = [r for c in checks for r in c.rows]
    atomic_write_csv(pd.DataFrame(rows, columns=["file", "excel_row", "code", "year", "column", "value", "issue"]),
                     out_dir / "raw_data_check_rows.csv")


# ---------------------------------------------------------------------------
# 代码块 6：主流程
# 目的：逐个文件检查，每个文件打印一行进度；最后写报告并在终端打印汇总。
# 结果：报告文件；存在问题时退出码为 1（便于以后串在自动流程里）。
# ---------------------------------------------------------------------------
def main():
    cfg = load_config()
    specs = file_specs(cfg)
    out_dir = resolve("数据/中间/qa")
    c2u_path = resolve(cfg["units"]["out_dir"]) / "county_to_unit.csv"
    c2u_codes = set(read_table(c2u_path)["adcode"].map(norm_adcode).dropna()) if c2u_path.exists() else None
    if c2u_codes is None:
        LOG.info("没有 county_to_unit.csv（尚未运行 00），跳过代码是否在 2020 年边界中的检查")

    # 粗略人口：2020 年普查常住人口（人），用于财政表的人均支出量级检查
    rough_pop = None
    p2020 = (cfg["fiscal_census"].get("census_files") or {}).get(2020) or \
        (cfg["fiscal_census"].get("census_files") or {}).get("2020")
    if p2020 and resolve(p2020).exists():
        try:
            cz = read_table(resolve(p2020))
            if {"adcode", "pop_resident"} <= set(cz.columns):
                cz["adcode"] = cz["adcode"].map(norm_adcode)
                rough_pop = pd.to_numeric(cz["pop_resident"], errors="coerce").groupby(cz["adcode"]).sum().to_dict()
        except Exception:  # noqa: BLE001  普查表本身的问题在它自己的检查中报告
            rough_pop = None

    prog = ChunkProgress(len(specs), LOG, label="文件")
    checks = []
    for i, (label, path, tpl, required, extra) in enumerate(specs):
        p = resolve(path)
        ck = Check(label, p, tpl, required)
        checks.append(ck)
        if not p.exists():
            ck.status = "缺失" if required else "未提供"
            if required:
                ck.problem(f"找不到文件 {ck.rel()}。这是必需输入，请按 数据/模板/{tpl}_template.csv 整理后放到这里，"
                           "或修改 config.yaml 中的路径")
            prog.skip(i, f"{label}：{ck.status}")
            continue
        prog.start(i, f"{label}（{p.name}）")
        tcols, example = read_template(tpl)
        if tcols is None:
            ck.hint(f"数据/模板 中没有 {tpl}_template.csv，只做编码与读取检查")
            tcols, example = [], None
        res = generic_checks(ck, tcols, example, c2u_codes)
        if res is not None:
            df, code_col, year_col = res
            if tpl in ("fiscal_county", "fiscal_city_proper") and code_col:
                fiscal_checks(ck, df, code_col, year_col, cfg, rough_pop if tpl == "fiscal_county" else None)
            elif tpl in ("census_county", "census_township"):
                census_checks(ck, df, code_col, year_col, extra.get("census_year"))
            elif tpl == "mohurd_panel":
                mohurd_checks(ck, df, code_col, year_col, cfg)
            elif tpl == "seat_points":
                seat_checks(ck, df, code_col)
            elif tpl == "admin_crosswalk":
                crosswalk_checks(ck, df)
            elif tpl in ("land_conveyance", "lgfv_debt") and year_col in df:
                main_years = [int(y) for y in cfg["fiscal_census"].get("fiscal_years_main") or []]
                have = set(to_num(df[year_col]).dropna().astype(int))
                miss = [y for y in main_years if y not in have]
                if miss:
                    ck.problem(f"缺少主分析期年份 {_j(miss)}，02 取主分析期均值")
        ck.status = "有问题" if ck.problems else ("有提示" if ck.hints else "通过")
        LOG.info(f"    {label}：{ck.status}，问题 {len(ck.problems)} 条，提示 {len(ck.hints)} 条")
        prog.finish(i)
    write_report(checks, out_dir)
    bad = [c for c in checks if c.status in ("有问题", "缺失")]
    LOG.info(f"体检报告 → {out_dir / 'raw_data_check.md'}；有问题的行 → {out_dir / 'raw_data_check_rows.csv'}")
    if bad:
        LOG.warning(f"{len(bad)} 个文件有问题或缺失：{[c.label for c in bad]}。请先改正再运行 02。")
        sys.exit(1)
    LOG.info("全部文件通过检查（提示项请逐条核对）。")


if __name__ == "__main__":
    main()
