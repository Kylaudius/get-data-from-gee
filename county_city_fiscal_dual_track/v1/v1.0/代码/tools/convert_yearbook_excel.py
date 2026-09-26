# -*- coding: utf-8 -*-
"""
tools/convert_yearbook_excel.py  把统计数据库导出的 Excel 或 CSV 转成 数据/模板 的格式

为什么需要：模板要求约 2800 个县级单位、多个财政年份和三期普查的数据。EPS 中国县市数据库、CNKI 年鉴库等可以
批量导出，但导出表的表头、单位、年份排列（一行一年或一列一年）各不相同。本工具按 外部参数/column_map.yaml
的映射，把这些表统一成模板列名、模板单位和一行一个代码年份的长表，直接供 02_build_fiscal_census.py 读取。

在哪里运行：Mac 终端 (Terminal)
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python tools/convert_yearbook_excel.py --inspect 数据/原始/导出/某文件.xlsx --job eps_county_fiscal
                                            # 第一步：看表头，以及每个表头按映射对应哪个模板列（不写任何文件）
    python tools/convert_yearbook_excel.py  # 第二步：转换 column_map.yaml 中 enabled 为 true 的全部 job
    python tools/convert_yearbook_excel.py --jobs eps_county_fiscal   # 只运行指定 job（逗号分隔）
    python tools/convert_yearbook_excel.py --force                    # 忽略转换记录，全部重新转换

输入：外部参数/column_map.yaml（映射与写法说明见该文件开头），各 job 的 input 所指的 xlsx、xlsm、csv 文件
      （.xls 旧格式需要 pip install xlrd，或在 Excel 中另存为 .xlsx）。
输出：各 job 的 output（模板格式 CSV，UTF-8）。输出文件已存在且不是本工具上次写出的，改写到同名加 _转换结果
      的文件，不覆盖手工录入的数据。
      数据/中间/convert/<job>_未匹配代码.csv   代码无法识别或按名称查不到代码的行（Excel 行号、名称、原因）
      数据/中间/convert/<输出名>_冲突.csv       同一代码年份在不同文件或不同列中取值不一致的记录（保留先读到的值）
      数据/中间/convert/convert_state.json      已转换文件的记录（文件指纹与映射指纹）

断点续跑：每转换完一个文件就记录一次。重新运行时，文件内容和映射都没变的文件直接读取上次的结果，
          每个文件打印一行进度。
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import io
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (CODE_DIR, VERSION_DIR, ChunkProgress, atomic_write_csv, atomic_write_json, get_logger,  # noqa: E402
                    load_config, norm_adcode, read_table, resolve, sha256_of)

LOG = get_logger("convert_yearbook_excel")
MAP_PATH = VERSION_DIR / "外部参数" / "column_map.yaml"
# 模板随代码一起发布：测试时 FDT_BASE_DIR 指向的临时文件夹里没有模板，就用代码旁边的模板
TEMPLATE_DIR = next((d for d in (VERSION_DIR / "数据" / "模板", CODE_DIR.parent / "数据" / "模板") if d.exists()),
                    VERSION_DIR / "数据" / "模板")

# ---------------------------------------------------------------------------
# 代码块 1：单位换算表
# 目的：同一类单位之间换算（源单位 → 模板单位）。金额的模板单位默认取 config.yaml 的 money_unit_in_raw。
# 结果：unit_factor() 返回乘数；单位不认识或类别不同时报错说明。
# ---------------------------------------------------------------------------
UNITS = {
    "money": {"元": 1, "千元": 1e3, "万元": 1e4, "百万元": 1e6, "亿元": 1e8},
    "people": {"人": 1, "万人": 1e4},
    "households": {"户": 1, "万户": 1e4},
    "area": {"平方米": 1, "m2": 1, "m²": 1, "万平方米": 1e4, "公顷": 1e4, "平方公里": 1e6, "km2": 1e6,
             "km²": 1e6, "亩": 10000 / 15},
    "length": {"米": 1, "m": 1, "公里": 1e3, "千米": 1e3, "km": 1e3},
    "count": {"个": 1, "张": 1, "所": 1, "处": 1},
    "ratio": {"小数": 1, "%": 0.01, "‰": 0.001},
}
UNIT_FAMILY = {u: fam for fam, d in UNITS.items() for u in d}
MUNICIPALITIES = {"110000", "120000", "310000", "500000"}


def unit_factor(spec: dict, tcol: str, money_unit: str) -> float:
    if "factor" in spec:
        return float(spec["factor"])
    unit = spec.get("unit")
    if unit is None:
        return 1.0
    unit = str(unit).strip()
    fam = UNIT_FAMILY.get(unit)
    if fam is None:
        raise ValueError(f"{tcol} 的单位 {unit} 不认识，可用 {sorted(UNIT_FAMILY)}，或直接写 factor")
    target = spec.get("target_unit") or (money_unit if fam == "money" else None)
    if target is None:
        raise ValueError(f"{tcol} 的单位 {unit} 不是金额，请写 target_unit（模板要求的单位，见模板 note 列）")
    target = str(target).strip()
    if UNIT_FAMILY.get(target) != fam:
        raise ValueError(f"{tcol} 的单位 {unit} 与 target_unit {target} 不是同一类，无法换算")
    return UNITS[fam][unit] / UNITS[fam][target]


# ---------------------------------------------------------------------------
# 代码块 2：读取模板与映射
# 目的：模板列名在运行时从 数据/模板/<template>_template.csv 读取（模板改了，本工具自动跟着改）；
#       检查映射中的模板列是否存在、年份写法是否唯一、单位能否换算。
# 结果：Job 对象，含模板列、代码列名、年份列名、每个模板列的正则与乘数。
# ---------------------------------------------------------------------------
def template_columns(name: str) -> list:
    p = TEMPLATE_DIR / f"{name}_template.csv"
    if not p.exists():
        avail = sorted(x.name.replace("_template.csv", "") for x in TEMPLATE_DIR.glob("*_template.csv"))
        raise ValueError(f"找不到模板 {p.name}，可用的模板有 {avail}")
    return [str(c).strip() for c in read_table(p).columns]


class Job:
    def __init__(self, d: dict, money_unit: str):
        self.raw = d
        self.name = str(d.get("job") or "未命名")
        self.template = str(d.get("template", ""))
        self.tcols = template_columns(self.template)
        self.code_t = (d.get("code") or {}).get("target") or next(
            (c for c in ("adcode", "pref_code", "code", "code12", "old_code") if c in self.tcols), None)
        if self.code_t is None:
            raise ValueError(f"模板 {self.template} 没有代码列，请在 code 下写 target")
        self.year_t = (d.get("year") or {}).get("target") or next(
            (c for c in ("year", "census_year") if c in self.tcols), None)
        y = d.get("year") or {}
        modes = [k for k in ("column", "from_header", "value", "from_filename") if y.get(k) is not None]
        if self.year_t and len(modes) != 1:
            raise ValueError("year 下须且只能写 column、from_header、value、from_filename 中的一种，"
                             f"现在写了 {modes or '没有'}")
        self.year_mode = modes[0] if modes else None
        self.year_spec = y.get(self.year_mode) if self.year_mode else None
        self.code_spec = d.get("code") or {}
        self.name_re = (d.get("name") or {}).get("column")
        self.columns = {}
        bad = [c for c in (d.get("columns") or {}) if c not in self.tcols]
        if bad:
            raise ValueError(f"columns 中的 {bad} 不是模板 {self.template} 的列。模板列为 {self.tcols}")
        for tcol, spec in (d.get("columns") or {}).items():
            spec = spec if isinstance(spec, dict) else {"pattern": str(spec)}
            if not spec.get("pattern"):
                raise ValueError(f"{tcol} 没有写 pattern")
            self.columns[tcol] = {"pattern": re.compile(str(spec["pattern"])),
                                  "exclude": re.compile(str(spec["exclude"])) if spec.get("exclude") else None,
                                  "factor": unit_factor(spec, tcol, money_unit)}
        if not self.columns:
            raise ValueError("columns 为空，至少要映射一个模板列")
        self.fixed = {k: v for k, v in (d.get("fixed") or {}).items()}
        badf = [c for c in self.fixed if c not in self.tcols]
        if badf:
            raise ValueError(f"fixed 中的 {badf} 不是模板列")
        self.sheet = d.get("sheet", 0)
        self.header_row = int(d.get("header_row", 1))
        self.header_rows = int(d.get("header_rows", 1))
        self.drop_prov = bool(d.get("drop_province_rows", True))
        self.source = d.get("source")
        inp = d.get("input")
        self.inputs = [inp] if isinstance(inp, str) else list(inp or [])
        self.output = resolve(d["output"]) if d.get("output") else None
        if self.output is None:
            raise ValueError("没有写 output")
        tpl_sig = hashlib.sha256(",".join(self.tcols).encode()).hexdigest()[:12]
        self.signature = hashlib.sha256((json.dumps(d, ensure_ascii=False, sort_keys=True, default=str)
                                         + money_unit + tpl_sig).encode("utf-8")).hexdigest()[:16]

    def files(self) -> list:
        out = []
        for pat in self.inputs:
            out += [Path(p) for p in sorted(glob.glob(str(resolve(pat))))]
        return [p for p in dict.fromkeys(out) if p.suffix.lower() in (".xlsx", ".xlsm", ".xls", ".csv", ".txt")
                and not p.name.startswith("~$")]


# ---------------------------------------------------------------------------
# 代码块 3：读取源表并识别表头
# 目的：把源文件读成不带表头的网格，再按 header_row、header_rows 拼出表头（多行表头的上行向右填充合并单元格）。
#       CSV 的编码识别顺序与 common.read_table 相同（先 UTF-8，再 GB18030）。这里不直接用 read_table，
#       因为导出表的表头往往不在第一行，标题行的列数也常与数据行不同，read_table 会把标题当作表头或报错。
# 结果：(表头列表, 数据网格 DataFrame, 数据第一行的 Excel 行号)。
# ---------------------------------------------------------------------------
def clean_text(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    s = unicodedata.normalize("NFKC", str(x))
    return re.sub(r"\s+", " ", s).strip()


def read_grid(path: Path, sheet=0) -> pd.DataFrame:
    suf = path.suffix.lower()
    if suf in (".xlsx", ".xlsm", ".xls"):
        try:
            return pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
        except ImportError:
            raise ValueError(".xls 旧格式需要 xlrd：运行 pip install xlrd，或在 Excel 中另存为 .xlsx")
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"无法识别 {path.name} 的编码")
    rows = [[c if c.strip() else None for c in r] for r in csv.reader(io.StringIO(text))]
    width = max((len(r) for r in rows), default=0)
    return pd.DataFrame([r + [None] * (width - len(r)) for r in rows], dtype=object)


def headers_of(grid: pd.DataFrame, header_row: int, header_rows: int):
    h0 = header_row - 1
    if h0 < 0 or h0 + header_rows > len(grid):
        raise ValueError(f"header_row={header_row}、header_rows={header_rows} 超出表格行数 {len(grid)}")
    rows = [[clean_text(v) for v in grid.iloc[h0 + r].tolist()] for r in range(header_rows)]
    for r in range(header_rows - 1):           # 上面几行是合并单元格，空格向右填充为左边的值
        last = ""
        for j, v in enumerate(rows[r]):
            last = v or last
            rows[r][j] = last
    headers = []
    for j in range(grid.shape[1]):
        parts = []
        for r in range(header_rows):
            if rows[r][j] and rows[r][j] not in parts:
                parts.append(rows[r][j])
        headers.append("|".join(parts))
    return headers, grid.iloc[h0 + header_rows:].reset_index(drop=True), h0 + header_rows + 1


def find_col(headers: list, pattern) -> int | None:
    if not pattern:
        return None
    rx = re.compile(str(pattern))
    hits = [j for j, h in enumerate(headers) if h and rx.search(h)]
    return hits[0] if hits else None


def year_of(x) -> float:
    m = re.search(r"(?:19|20)\d{2}", clean_text(x))
    return float(m.group(0)) if m else np.nan


def to_number(s: pd.Series) -> pd.Series:
    t = s.map(clean_text).str.replace(",", "", regex=False).str.replace("%", "", regex=False)
    t = t.replace({"": None, "-": None, "--": None, "—": None, "——": None, "…": None, "...": None, "..": None,
                   "#N/A": None, "NA": None, "N/A": None, "nan": None, "None": None, "/": None, "×": None})
    return pd.to_numeric(t, errors="coerce")


# ---------------------------------------------------------------------------
# 代码块 4：名称查代码（可选）
# 目的：年鉴表没有代码列时，按名称到查询表中找 6 位代码。只采用唯一匹配；可用 lookup_prov 限定省份。
# 结果：名称 → 代码 的字典，以及重名的名称集合。
# ---------------------------------------------------------------------------
def build_lookup(spec: dict):
    f = spec.get("lookup_file")
    if not f:
        return None, set()
    p = resolve(f)
    if not p.exists():
        raise ValueError(f"找不到名称查询表 {p}")
    cc, nc = spec.get("lookup_code_col", "adcode"), spec.get("lookup_name_col", "name")
    t = read_table(p, code_cols=(cc,))
    if cc not in t or nc not in t:
        raise ValueError(f"名称查询表 {p.name} 须有 {cc} 与 {nc} 两列，现有列为 {list(t.columns)}")
    t = pd.DataFrame({"code": t[cc].map(norm_adcode), "name": t[nc].map(clean_text)}).dropna()
    prov = spec.get("lookup_prov")
    if prov:
        provs = {str(x)[:2] for x in (prov if isinstance(prov, list) else [prov])}
        t = t[t["code"].str[:2].isin(provs)]
    t = t.drop_duplicates()
    counts = t["name"].value_counts()
    dup = set(counts[counts > 1].index)
    return dict(zip(t.loc[~t["name"].isin(dup), "name"], t.loc[~t["name"].isin(dup), "code"])), dup


# ---------------------------------------------------------------------------
# 代码块 5：转换一个文件
# 目的：识别代码、名称、年份与数值列 → 按单位换算 → 宽表转长表 → 再按 代码、年份 汇成模板宽表。
#       同一代码年份被多个源列映射到同一模板列且数值不同时，保留第一个并记为冲突。
# 结果：(模板格式的 DataFrame, 未匹配行 DataFrame, 冲突行 DataFrame, 映射说明列表)。
# ---------------------------------------------------------------------------
def map_headers(job: Job, headers: list, skip: set):
    """每个表头对应的 (模板列, 年份)。年份来自表头时，表头须同时含年份。"""
    out, notes = {}, []
    yr = re.compile(str(job.year_spec)) if job.year_mode == "from_header" else None
    for j, h in enumerate(headers):
        if j in skip or not h:
            continue
        for tcol, spec in job.columns.items():
            if spec["pattern"].search(h) and not (spec["exclude"] and spec["exclude"].search(h)):
                year = None
                if yr is not None:
                    m = yr.search(h)
                    if not m:
                        notes.append(f"表头 {h} 匹配 {tcol}，但没有提取到年份，未使用")
                        break
                    year = year_of(m.group(1) if m.groups() else m.group(0))
                out[j] = (tcol, year)
                break
    return out, notes


def convert_file(job: Job, path: Path):
    grid = read_grid(path, job.sheet)
    headers, data, first_row = headers_of(grid, job.header_row, job.header_rows)
    data = data.dropna(how="all").copy()
    excel_row = data.index.to_numpy() + first_row
    ci = find_col(headers, job.code_spec.get("column"))
    ni = find_col(headers, job.name_re)
    lookup, dup = build_lookup(job.code_spec)
    if ci is None and lookup is None:
        raise ValueError(f"没有找到代码列（code.column = {job.code_spec.get('column')}），也没有设置 lookup_file。"
                         f"表头为 {[h for h in headers if h][:30]}")
    names = data.iloc[:, ni].map(clean_text) if ni is not None else pd.Series("", index=data.index)
    raw_code = data.iloc[:, ci].map(clean_text) if ci is not None else pd.Series("", index=data.index)
    code = raw_code.map(norm_adcode)
    reason = pd.Series("", index=data.index)
    if lookup is not None:
        need = code.isna()
        by_name = names[need].map(lookup)
        code[need] = by_name
        reason[need & names.isin(dup)] = "名称在查询表中重名"
        reason[need & code.isna() & reason.eq("")] = "名称在查询表中查不到"
    reason[code.isna() & reason.eq("")] = "代码无法识别（须为 6 位或 12 位数字）"
    if job.drop_prov:
        is_prov = code.fillna("").str.endswith("0000") & ~code.isin(MUNICIPALITIES)
        code[is_prov] = None
        reason[is_prov] = "省级汇总行（已剔除）"
    unmatched = pd.DataFrame({"file": path.name, "excel_row": excel_row, "name": names.to_numpy(),
                              "raw_code": raw_code.to_numpy(), "reason": reason.to_numpy()})[code.isna().to_numpy()]
    # 空行、注释行（没有名称也没有代码）不列入未匹配清单
    unmatched = unmatched[((unmatched["name"] != "") | (unmatched["raw_code"] != ""))
                          & ~unmatched["name"].str.match(r"^(注|资料来源|数据来源|说明)")]

    # 年份
    yi = find_col(headers, job.year_spec) if job.year_mode == "column" else None
    if job.year_mode == "column" and yi is None:
        raise ValueError(f"没有找到年份列（year.column = {job.year_spec}）")
    if job.year_mode == "column":
        row_year = data.iloc[:, yi].map(year_of)
    elif job.year_mode == "value":
        row_year = pd.Series(float(job.year_spec), index=data.index)
    elif job.year_mode == "from_filename":
        m = re.search(str(job.year_spec), path.name)
        if not m:
            raise ValueError(f"文件名 {path.name} 中没有找到年份（year.from_filename = {job.year_spec}）")
        row_year = pd.Series(year_of(m.group(1) if m.groups() else m.group(0)), index=data.index)
    else:
        row_year = pd.Series(np.nan, index=data.index)

    skip = {j for j in (ci, ni, yi) if j is not None}
    mapping, notes = map_headers(job, headers, skip)
    if not mapping:
        raise ValueError(f"没有任何表头匹配 columns 中的 pattern。表头为 {[h for h in headers if h][:40]}")
    notes = [f"{headers[j]} → {t}{'（' + str(int(y)) + ' 年）' if y == y and y is not None else ''}"
             for j, (t, y) in mapping.items()] + notes
    unused = [tc for tc in job.columns if tc not in {t for t, _ in mapping.values()}]
    if unused:
        notes.append(f"这些模板列在本文件中没有匹配到表头：{unused}")

    ok = code.notna()
    parts = []
    for j, (tcol, y) in mapping.items():
        vals = to_number(data.iloc[:, j]) * job.columns[tcol]["factor"]
        yy = row_year if y is None else pd.Series(y, index=data.index)
        parts.append(pd.DataFrame({"code": code[ok], "year": yy[ok], "tcol": tcol, "value": vals[ok], "col": j}))
    long = pd.concat(parts, ignore_index=True)
    if job.year_t:
        bad_year = long["year"].isna() & long["value"].notna()
        if bad_year.any():
            notes.append(f"{int(bad_year.sum())} 个数值没有年份，未使用")
        long = long[long["year"].notna()]
    else:
        long["year"] = 0.0
    # 同一代码、年份、模板列有多个源值：保留第一个非空值，数值不同的记为冲突
    n_keys = len(long[["code", "year"]].drop_duplicates())
    vals = long.dropna(subset=["value"]).sort_values("col", kind="stable")
    if len(vals):
        g = vals.groupby(["code", "year", "tcol"])["value"]
        nun = g.nunique()
        conflicts = nun[nun > 1].reset_index()[["code", "year", "tcol"]]
        wide = g.first().unstack("tcol").reset_index()
        wide.columns.name = None
    else:
        conflicts = pd.DataFrame(columns=["code", "year", "tcol"])
        wide = pd.DataFrame(columns=["code", "year"])
    if n_keys > len(wide):
        notes.append(f"{n_keys - len(wide)} 个代码年份没有任何数值，未写出")
    for tcol in job.columns:
        if tcol not in wide:
            wide[tcol] = np.nan
    first_name = pd.DataFrame({"code": code[ok], "name": names[ok]})
    first_name = first_name[first_name["name"] != ""].drop_duplicates("code")
    wide = wide.merge(first_name, on="code", how="left")
    for k, v in job.fixed.items():
        wide[k] = v
    if "source" in job.tcols:
        wide["source"] = job.source or f"{path.name}（convert_yearbook_excel.py 转换）"
    wide = wide.rename(columns={"code": job.code_t})
    if job.year_t:
        wide[job.year_t] = wide.pop("year").astype("Int64")
    else:
        wide = wide.drop(columns="year")
    conflicts = conflicts.rename(columns={"code": job.code_t, "tcol": "column"})
    conflicts["note"] = f"{path.name} 中多列或多行取值不同"
    if job.year_t:
        conflicts = conflicts.rename(columns={"year": job.year_t})
    else:
        conflicts = conflicts.drop(columns="year")
    stats = {"rows_in": int(len(data)), "rows_out": int(len(wide)), "unmatched": int(len(unmatched)),
             "conflicts": int(len(conflicts)), "n_cols": len({t for t, _ in mapping.values()})}
    return wide, unmatched, conflicts, notes, stats


# ---------------------------------------------------------------------------
# 代码块 6：合并同一输出的全部文件，写出模板格式
# 目的：同一 output 可能来自多个 job、多个文件（例如一个指标一个文件）。按 代码、年份 合并，每列取先读到的非空值，
#       不同文件取值不一致的写入冲突清单。列与列序按模板；输出已被手工改过时另存，不覆盖。
# 结果：output 文件；state 中记录它的指纹。
# ---------------------------------------------------------------------------
def assemble(output: Path, parts: list, jobs: list, state: dict, conv_dir: Path) -> Path | None:
    job = jobs[0]
    key = [job.code_t] + ([job.year_t] if job.year_t else [])
    inner = [read_table(p.with_name(p.stem + "_conflicts.csv"), code_cols=(job.code_t,))
             for p in parts if p.with_name(p.stem + "_conflicts.csv").exists()]
    inner = [f for f in inner if len(f)]
    frames = [read_table(p, code_cols=(job.code_t,)) for p in parts if p.exists()]
    frames = [f for f in frames if len(f)]
    if not frames:
        LOG.warning(f"{output.name}：没有可合并的数据")
        return None
    allw = pd.concat(frames, ignore_index=True)
    num_cols = sorted({c for j in jobs for c in j.columns})
    nun = allw.groupby(key)[num_cols].nunique()
    conf = nun[(nun > 1).any(axis=1)]
    rows = [(k if isinstance(k, tuple) else (k,)) + (c, "不同文件取值不同")
            for k, r in conf.iterrows() for c in num_cols if r[c] > 1]
    pieces = ([pd.DataFrame(rows, columns=key + ["column", "note"])] if rows else []) + inner
    cdf = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
    cpath = conv_dir / f"{output.stem}_冲突.csv"
    if len(cdf):
        atomic_write_csv(cdf, cpath)
        LOG.warning(f"{output.name}：{len(cdf)} 处同一代码年份取值不一致，保留先读到的值，清单见 {cpath.name}")
    elif cpath.exists():
        cpath.unlink()
    out = allw.groupby(key, sort=True).first().reset_index()
    tcols = job.tcols
    extra = [c for c in out.columns if c not in tcols]
    if extra:
        LOG.warning(f"{output.name}：{extra} 不是模板列，未写出")
    out = out.reindex(columns=tcols)
    if job.year_t:
        out[job.year_t] = pd.to_numeric(out[job.year_t], errors="coerce").astype("Int64")
        yrs = out[job.year_t].dropna()
        odd = yrs[(yrs < 1949) | (yrs > 2035)]
        if len(odd):
            LOG.warning(f"{output.name}：{len(odd)} 行年份不在 1949 至 2035 之间，请检查年份写法")
    rel = str(output.relative_to(VERSION_DIR)) if output.is_relative_to(VERSION_DIR) else str(output)
    target = output
    if output.exists() and state.get("outputs", {}).get(rel) != sha256_of(output):
        target = output.with_name(output.stem + "_转换结果" + output.suffix)
        LOG.warning(f"{output.name} 已存在，且不是本工具上次写出的（可能手工录入或修改过）。为免覆盖，结果写到 "
                    f"{target.name}。确认可以替换后，把原文件改名或删除，再运行一次。")
    atomic_write_csv(out, target)
    if target == output:
        state.setdefault("outputs", {})[rel] = sha256_of(output)
    LOG.info(f"已写出 {target}：{len(out)} 行，{out[job.code_t].nunique()} 个代码"
             + (f"，年份 {sorted(out[job.year_t].dropna().unique().tolist())}" if job.year_t else ""))
    return target


# ---------------------------------------------------------------------------
# 代码块 7：检查表头（--inspect）
# 目的：不写任何文件，只打印前几行原文、拼好的表头，以及每个表头按映射对应的模板列，方便修改 column_map.yaml。
# 结果：终端输出。
# ---------------------------------------------------------------------------
def inspect(path: Path, job: Job | None, sheet, header_row: int, header_rows: int):
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        xl = pd.ExcelFile(path)
        print(f"工作表：{xl.sheet_names}")
    grid = read_grid(path, sheet)
    print(f"\n前 8 行原文（行号为 Excel 行号），共 {len(grid)} 行 {grid.shape[1]} 列：")
    for i in range(min(8, len(grid))):
        vals = [clean_text(v) for v in grid.iloc[i].tolist()]
        print(f"  第 {i + 1} 行 | " + " | ".join(v for v in vals[:15]) + (" | ..." if len(vals) > 15 else ""))
    headers, data, first = headers_of(grid, header_row, header_rows)
    print(f"\n按 header_row={header_row}、header_rows={header_rows} 拼出的表头（数据从第 {first} 行开始）：")
    if job is None:
        for j, h in enumerate(headers):
            print(f"  第 {j + 1} 列  {h}")
        print("\n加 --job <名称> 可以看到每个表头按该 job 的映射对应哪个模板列。")
        return
    ci = find_col(headers, job.code_spec.get("column"))
    ni = find_col(headers, job.name_re)
    yi = find_col(headers, job.year_spec) if job.year_mode == "column" else None
    mapping, notes = map_headers(job, headers, {j for j in (ci, ni, yi) if j is not None})
    for j, h in enumerate(headers):
        if j == ci:
            tag = f"代码列 → {job.code_t}"
        elif j == ni:
            tag = "名称列 → name"
        elif j == yi:
            tag = f"年份列 → {job.year_t}"
        elif j in mapping:
            t, y = mapping[j]
            tag = f"→ {t}" + (f"（{int(y)} 年）" if y is not None and y == y else "")
        else:
            tag = "（未使用）"
        print(f"  第 {j + 1} 列  {h or '（空）'}  {tag}")
    for n in notes:
        print("  提示：" + n)
    if ci is None and not job.code_spec.get("lookup_file"):
        print("  提示：没有找到代码列，请修改 code.column 或设置 lookup_file")
    if job.year_mode == "column" and yi is None:
        print("  提示：没有找到年份列，请修改 year.column")


# ---------------------------------------------------------------------------
# 代码块 8：主流程
# 目的：逐个文件转换（每个文件一行进度，已转换且未变的跳过）→ 按 output 合并写出 → 汇总提示。
# 结果：各 output 文件、未匹配清单、冲突清单与 convert_state.json。
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="数据库导出表格转为模板格式")
    ap.add_argument("--map", default=str(MAP_PATH), help="映射文件（默认 外部参数/column_map.yaml）")
    ap.add_argument("--jobs", help="只运行这些 job（逗号分隔），不论 enabled 是否为 true")
    ap.add_argument("--force", action="store_true", help="忽略转换记录，全部重新转换")
    ap.add_argument("--inspect", help="只查看这个文件的表头，不写文件")
    ap.add_argument("--job", help="与 --inspect 同用：按这个 job 的设置读表头并显示映射")
    ap.add_argument("--sheet", help="与 --inspect 同用：工作表序号或名称")
    ap.add_argument("--header-row", type=int, help="与 --inspect 同用：表头所在 Excel 行号")
    ap.add_argument("--header-rows", type=int, help="与 --inspect 同用：表头行数")
    args = ap.parse_args()

    cfg = load_config()
    money_unit = cfg["fiscal_census"].get("money_unit_in_raw", "万元")
    mpath = Path(args.map).expanduser().resolve()
    if not mpath.exists():
        raise SystemExit(f"找不到映射文件 {mpath}")
    cmap = yaml.safe_load(mpath.read_text(encoding="utf-8")) or {}
    job_dicts = cmap.get("jobs") or []

    if args.inspect:
        job = None
        if args.job:
            d = next((j for j in job_dicts if j.get("job") == args.job), None)
            if d is None:
                raise SystemExit(f"column_map.yaml 中没有名为 {args.job} 的 job")
            job = Job(d, money_unit)
        sheet = args.sheet if args.sheet is not None else (job.sheet if job else 0)
        if isinstance(sheet, str) and sheet.isdigit():
            sheet = int(sheet)
        inspect(Path(args.inspect).expanduser().resolve(), job, sheet,
                args.header_row or (job.header_row if job else 1), args.header_rows or (job.header_rows if job else 1))
        return

    wanted = {x.strip() for x in args.jobs.split(",")} if args.jobs else None
    jobs = []
    for d in job_dicts:
        nm = d.get("job")
        if (wanted and nm not in wanted) or (not wanted and not d.get("enabled", False)):
            continue
        try:
            jobs.append(Job(d, money_unit))
        except (ValueError, KeyError) as e:
            raise SystemExit(f"column_map.yaml 中 job {nm} 写法有误：{e}")
    if wanted and wanted - {j.name for j in jobs}:
        raise SystemExit(f"column_map.yaml 中没有这些 job：{sorted(wanted - {j.name for j in jobs})}")
    if not jobs:
        raise SystemExit("没有要运行的 job。请在 column_map.yaml 中把要用的 job 的 enabled 改为 true，或用 --jobs 指定。")

    settings = cmap.get("settings") or {}
    state_path = resolve(settings.get("state_file", "数据/中间/convert/convert_state.json"))
    cache_dir = resolve(settings.get("cache_dir", "数据/中间/convert/cache"))
    conv_dir = state_path.parent
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    state.setdefault("files", {})

    tasks = []
    for job in jobs:
        fs = job.files()
        if not fs:
            LOG.warning(f"job {job.name}：没有找到输入文件 {job.inputs}")
        tasks += [(job, f) for f in fs]
    prog = ChunkProgress(max(len(tasks), 1), LOG, label="文件")
    by_output: dict = {}
    unmatched_by_job: dict = {}
    failed = []
    for i, (job, f) in enumerate(tasks):
        rel = str(f.relative_to(VERSION_DIR)) if f.is_relative_to(VERSION_DIR) else str(f)
        key = f"{job.name}::{rel}"        # 用相对路径记录，整个迭代文件夹搬到别处后记录仍然有效
        sig = {"sha256": sha256_of(f), "map": job.signature}
        cache = cache_dir / job.name / (re.sub(r"[^\w.-]", "_", f.stem) + "_"
                                        + hashlib.sha256(rel.encode("utf-8")).hexdigest()[:8] + ".csv")
        um_cache = cache.with_name(cache.stem + "_unmatched.csv")
        rec = state["files"].get(key, {})
        by_output.setdefault(job.output, {"jobs": [], "parts": []})
        if job not in by_output[job.output]["jobs"]:
            by_output[job.output]["jobs"].append(job)
        if not args.force and rec.get("sha256") == sig["sha256"] and rec.get("map") == sig["map"] and cache.exists():
            prog.skip(i, f"{f.name} 未变化，沿用上次结果（断点续跑）")
            by_output[job.output]["parts"].append(cache)
            if um_cache.exists():
                unmatched_by_job.setdefault(job.name, []).append(um_cache)
            continue
        prog.start(i, f"{job.name}：{f.name}")
        try:
            wide, unmatched, conflicts, notes, st = convert_file(job, f)
        except Exception as e:  # noqa: BLE001  一个文件出错不影响其他文件，最后汇总
            LOG.error(f"{f.name} 转换失败：{e}")
            failed.append(f.name)
            continue
        atomic_write_csv(wide, cache)
        atomic_write_csv(unmatched, um_cache)
        atomic_write_csv(conflicts, cache.with_name(cache.stem + "_conflicts.csv"))
        for n in notes:
            LOG.info(f"    {n}")
        if len(conflicts):
            LOG.warning(f"    {len(conflicts)} 个代码年份在本文件的多列或多行中取值不一致，保留先读到的值")
        LOG.info(f"    读入 {st['rows_in']} 行，写出 {st['rows_out']} 个代码年份，映射 {st['n_cols']} 个模板列，"
                 f"未匹配代码 {st['unmatched']} 行")
        state["files"][key] = {**sig, "rows_out": st["rows_out"], "unmatched": st["unmatched"],
                               "time": time.strftime("%Y-%m-%d %H:%M:%S")}
        atomic_write_json(state, state_path)
        by_output[job.output]["parts"].append(cache)
        unmatched_by_job.setdefault(job.name, []).append(um_cache)
        prog.finish(i)
    prog.summary()

    for name, paths in unmatched_by_job.items():
        um = [read_table(p) for p in paths if p.exists()]
        um = pd.concat(um, ignore_index=True) if um else pd.DataFrame()
        out = conv_dir / f"{name}_未匹配代码.csv"
        if len(um):
            atomic_write_csv(um, out)
            LOG.warning(f"job {name}：{len(um)} 行没有得到有效代码，清单见 {out}")
        elif out.exists():
            out.unlink()
    for output, d in by_output.items():
        tpls = {j.template for j in d["jobs"]}
        if len(tpls) > 1:
            LOG.error(f"{output.name} 由使用不同模板 {sorted(tpls)} 的 job 写出，无法合并，已跳过。请给它们不同的 output。")
            failed.append(output.name)
            continue
        if d["parts"]:
            assemble(output, d["parts"], d["jobs"], state, conv_dir)
    atomic_write_json(state, state_path)
    if failed:
        LOG.error(f"{len(failed)} 个文件转换失败：{failed}。请用 --inspect 查看表头后修改 column_map.yaml。")
        sys.exit(1)
    LOG.info("完成。下一步运行 python tools/validate_raw_data.py 体检转换结果。")


if __name__ == "__main__":
    main()
