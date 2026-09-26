# -*- coding: utf-8 -*-
"""
02_build_fiscal_census.py  整理财政与人口普查数据，并汇总到分析单元

在哪里运行：Mac “终端 Terminal”
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python 02_build_fiscal_census.py

输入（按 数据/模板 的列名整理后放到 config.yaml 指定的位置）：
    财政（县、县级市）      《中国县域统计年鉴（县市卷）》→ fiscal_county.csv
    财政（市辖区合计）      《中国城市统计年鉴》市辖区口径 → fiscal_city_proper.csv
    普查（2000/2010/2020）   《中国人口普查分县资料》→ census_XXXX_county.csv
    代码对照表              历年行政区划代码 → 2020 年代码 → admin_crosswalk.csv（可选列 change_date）
    可选：土地出让 land_conveyance.csv、城投有息债务 lgfv_debt.csv、新增专项债 special_bonds.csv、
          开发区 devzones_2018.csv（路径见 config.yaml fiscal_census）
    00 脚本输出的 county_to_unit.csv
输出（数据/中间/panel/）：
    unit_fiscal_census.csv   一行一个分析单元：财政多年均值（主分析期 main、稳健性 rob、2010 期 y2010、2000 期 y2000）、
                             三次普查变量、成员覆盖率、土地债务与开发区变量
    qa_report.md             数据质量报告：缺失、重复、未匹配代码、成员覆盖率与口径提示
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (atomic_write_csv, atomic_write_text, code_to_unit, get_logger, load_config,  # noqa: E402
                    norm_adcode, pref_code, read_table, resolve)

LOG = get_logger("02_build_fiscal_census")
QA: list[str] = []

MONEY_TO_YUAN = {"元": 1.0, "万元": 1e4, "亿元": 1e8}
# 财政金额（按 money_unit_in_raw 换算为元）
FISCAL_MONEY = ["gen_budget_revenue", "gen_budget_expenditure", "tax_revenue", "land_conveyance_revenue", "gdp",
                "tax_rebate", "transfer_general", "transfer_specific", "transfer_total", "fund_budget_revenue",
                "exp_education", "exp_health", "exp_community", "exp_personnel", "exp_general_public"]
# 财政表中的非金额计数（学生、教师、床位），成员之间直接求和，不乘货币单位
FISCAL_COUNTS = ["students_primary", "students_secondary", "teachers_fulltime", "hospital_beds", "welfare_beds"]
CENSUS_COUNTS = ["pop_resident", "pop_urban", "households", "hh_pop", "pop_hukou", "pop_hukou_elsewhere", "collective_pop"]
CENSUS_HH_SHARES = ["share_rent_public", "share_rent_market", "share_buy_new", "share_buy_second", "share_self_built"]
CENSUS_POP_SHARES = ["share_65plus", "share_0_14"]
CENSUS_SHARES = CENSUS_HH_SHARES + ["housing_area_pc"] + CENSUS_POP_SHARES
# 比例型变量合并时的权重（依次尝试，取表中第一个有数值的列）：
# 住房来源比例是“户”的比例，按家庭户户数加权；人均住房面积按家庭户人口加权（等于总面积 / 总人口）；
# 年龄结构是“人”的比例，按常住人口加权
SHARE_WEIGHTS = {**{c: ("households", "pop_resident") for c in CENSUS_HH_SHARES},
                 "housing_area_pc": ("hh_pop", "households", "pop_resident"),
                 **{c: ("pop_resident",) for c in CENSUS_POP_SHARES}}
FISCAL_PERIODS = [("fiscal_years_main", "main"), ("fiscal_years_robust", "rob"),
                  ("fiscal_years_2010", "y2010"), ("fiscal_years_2000", "y2000")]
BOND_CATEGORIES = {"市政": "muni", "园林绿化": "greening", "生态环保": "eco", "棚户区改造": "shanty", "其他": "other"}


def qa(msg: str):
    QA.append(msg)
    LOG.info(msg)


def norm_pref(x):
    c = norm_adcode(x)
    return pref_code(c) if c else None


# ===========================================================================
# 代码块 1：代码对照（行政区划调整的统一）
# 目的：2000–2020 年间大量“撤县设区”“合并”“更名”，旧代码必须映射到 2020 年代码才能与 2020 年边界对齐。
#       对照表每行给出 old_code → new_code 与权重 weight（拆分时按面积或人口比例填写，普通更名/合并填 1）。
#       计数型变量（人口、财政金额）按权重分配后加总；比例型变量按各自的权重（户数、人口）加权平均。
#       本函数按时间顺序应用对照表，处理“旧代码 → 中间代码 → 2020 代码”的多次变更：
#       每行数据记住自己“当前所处的年份”，每次只应用该代码的下一次变更（change_year 最早的一批），
#       应用后把年份推进到 change_year。这样：
#         · 拆分后保留原代码的情形（A→A 0.6、A→B 0.4）不会被重复拆分；
#         · 同一旧代码先后发生两次变更（2012 年部分划出、2018 年整体撤县设区）不会重复计数。
#       未填 change_year 的行视为适用；其中 old_code = new_code 的行视为终点。
#       普查的标准时点是 11 月 1 日：对照表填了 change_date 时，普查年当年、标准时点之后的变更也要映射
#       （普查数据仍是旧代码）；财政为年末数，只映射晚于数据年份的变更，规则不变。
# 结果：返回代码已统一到 2020 年的 DataFrame。
# ===========================================================================
def load_crosswalk(cfg) -> pd.DataFrame | None:
    p = resolve(cfg["fiscal_census"]["crosswalk_file"])
    if not p.exists():
        qa(f"未提供代码对照表（{p.name}），历年数据按原代码匹配，未匹配部分见本报告。")
        return None
    cw = read_table(p, code_cols=("old_code", "new_code"))
    cw["old_code"] = cw["old_code"].map(norm_adcode)
    cw["new_code"] = cw["new_code"].map(norm_adcode)
    # weight、change_year、change_date 三列可选：缺 weight 视为 1（整体变更），缺 change_year 视为任何年份的数据都适用
    cw["weight"] = pd.to_numeric(cw["weight"], errors="coerce").fillna(1.0) if "weight" in cw else 1.0
    cw["change_year"] = pd.to_numeric(cw["change_year"], errors="coerce") if "change_year" in cw else np.nan
    if "change_date" in cw:
        cw["change_date"] = pd.to_datetime(cw["change_date"], errors="coerce", format="%Y-%m-%d")
        # 只填了日期、没填年份时，用日期的年份
        cw["change_year"] = cw["change_year"].fillna(cw["change_date"].dt.year)
        bad = cw["change_date"].notna() & cw["change_year"].notna() & (cw["change_date"].dt.year != cw["change_year"])
        if bad.any():
            qa(f"代码对照表：{int(bad.sum())} 行 change_date 的年份与 change_year 不一致，请核对，示例 "
               f"{cw.loc[bad, 'old_code'].head(10).tolist()}")
    cw = cw.dropna(subset=["old_code", "new_code"])
    n0 = len(cw)
    cw = cw.drop_duplicates(["old_code", "new_code", "change_year"]).reset_index(drop=True)
    if len(cw) < n0:
        qa(f"代码对照表：{n0 - len(cw)} 行重复（old_code、new_code、change_year 都相同），已去重")
    # 同一旧代码在同一次变更中的权重之和应为 1，否则计数型变量（人口、财政）会被放大或缩小
    ws = cw.groupby([cw["old_code"], cw["change_year"].fillna(-1)])["weight"].sum()
    bad = ws[(ws - 1).abs() > 0.01]
    if len(bad):
        qa(f"代码对照表：{len(bad)} 个旧代码的拆分权重之和不等于 1，请核对，示例 "
           f"{[(k[0], round(v, 3)) for k, v in bad.head(10).items()]}")
    return cw


def applicable(cw: pd.DataFrame | None, data_year: int, ref_date: str | None = None) -> pd.DataFrame | None:
    """对照表中适用于 data_year 年数据的行：change_year 晚于数据年份，或未填 change_year。
    ref_date（月-日，如 "11-01"）只用于普查：change_year 等于普查年、且 change_date 晚于当年标准时点的变更同样适用，
    这类变更的年份记为 data_year + 0.5，使它排在次年变更之前。"""
    if cw is None:
        return None
    cw = cw.copy()
    cw["change_year"] = pd.to_numeric(cw["change_year"], errors="coerce").astype(float)
    if ref_date and "change_date" in cw:
        cut = pd.Timestamp(f"{int(data_year)}-{ref_date}")
        late = cw["change_year"].eq(data_year) & cw["change_date"].notna() & (cw["change_date"] > cut)
        cw.loc[late, "change_year"] = data_year + 0.5
    return cw[cw["change_year"].isna() | (cw["change_year"] > data_year)]


def harmonize(df: pd.DataFrame, code_col: str, counts: list, shares: list, cw: pd.DataFrame | None,
              data_year: int, weight_col=None, max_iter: int = 10, ref_date: str | None = None) -> pd.DataFrame:
    df = df.copy()
    cw = applicable(cw, data_year, ref_date)
    if cw is None or cw.empty or not df[code_col].isin(cw["old_code"]).any():
        return df
    m = cw[["old_code", "new_code", "weight", "change_year"]]
    df = df.reset_index(drop=True)
    df["_t"] = float(data_year)   # 该行数据当前所处的年份
    df["_done"] = False           # 已到达终点（未填年份且 old_code = new_code）
    for _ in range(max_iter):
        cand = (df[[code_col, "_t", "_done"]].rename_axis("_row").reset_index()
                .merge(m, left_on=code_col, right_on="old_code"))
        # 有年份的变更：只取晚于当前年份的最早一次
        dated = cand[cand["change_year"] > cand["_t"]]
        dated = dated[dated["change_year"] == dated.groupby("_row")["change_year"].transform("min")]
        # 未填年份的变更：该行没有待应用的有年份变更、且尚未到达终点时才应用
        undated = cand[cand["change_year"].isna() & ~cand["_done"] & ~cand["_row"].isin(dated["_row"])]
        step = pd.concat([dated, undated], ignore_index=True)
        if step.empty:
            break
        moved = df.loc[step["_row"]].reset_index(drop=True)
        w = step["weight"].to_numpy(dtype=float)
        for c in counts:
            if c in moved:
                moved[c] = moved[c] * w
        cy = step["change_year"].to_numpy(dtype=float)
        moved[code_col] = step["new_code"].to_numpy()
        moved["_t"] = np.where(np.isnan(cy), moved["_t"].to_numpy(dtype=float), cy)
        moved["_done"] = np.isnan(cy) & (step["new_code"] == step["old_code"]).to_numpy()
        df = pd.concat([df.drop(index=step["_row"].unique()), moved], ignore_index=True)
    else:
        qa(f"代码对照表可能存在循环（如 A→B 且 B→A），{data_year} 年数据迭代 {max_iter} 次仍未收敛，请检查对照表")
    df = df.drop(columns=["_t", "_done"])
    return collapse(df, [code_col] + [c for c in ("year", "census_year") if c in df], counts, shares, weight_col)


def _share_weight(df: pd.DataFrame, share: str, weight_col) -> pd.Series:
    """比例型变量的权重列：weight_col 为字符串时所有比例共用；为字典时按 SHARE_WEIGHTS 依次尝试候选列。"""
    cands = weight_col.get(share, ("pop_resident",)) if isinstance(weight_col, dict) else (weight_col,)
    for c in cands:
        if c and c in df and df[c].notna().any():
            return pd.to_numeric(df[c], errors="coerce")
    return pd.Series(1.0, index=df.index)


def collapse(df, keys, counts, shares, weight_col):
    """按 keys 汇总：计数型求和（全缺失保持缺失），比例型按权重加权平均。"""
    counts = [c for c in counts if c in df]
    shares = [c for c in shares if c in df]
    g = df.groupby(keys, dropna=False)
    out = g[counts].sum(min_count=1) if counts else g.size().to_frame("n").drop(columns="n")
    if shares:
        tmp = df[keys].copy()
        for c in shares:
            w = _share_weight(df, c, weight_col)
            valid = df[c].notna() & w.notna()
            tmp[c + "__num"] = (df[c] * w).where(valid)
            tmp[c + "__den"] = w.where(valid)
        agg = tmp.groupby(keys, dropna=False).sum(min_count=1)
        for c in shares:
            out[c] = agg[c + "__num"] / agg[c + "__den"]
    return out.reset_index()


# ===========================================================================
# 代码块 2：人口普查（2000/2010/2020）
# 目的：读取分县普查表，统一代码，汇总到分析单元（市辖区按地级市合并），变量名加年份后缀。
#       同时计算成员覆盖率 census_cov_YYYY（有普查数的成员数 / 单元成员数），覆盖不全的市辖区单元人口会被低估。
# 结果：返回 (一行一个分析单元的普查宽表, 2020 年县级人口表)。宽表例如 pop_resident_2020、share_rent_market_2020。
# ===========================================================================
def build_census(cfg, c2u: pd.DataFrame, cw) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    fc = cfg["fiscal_census"]
    ref_date = fc.get("census_ref_date")
    members = c2u.groupby("unit_id")["adcode"].nunique()
    outs, county2020 = [], None
    for year, path in fc["census_files"].items():
        year = int(year)
        p = resolve(path)
        if not p.exists():
            qa(f"缺少 {year} 年普查表：{p.name}（跳过）")
            continue
        df = read_table(p)
        df["adcode"] = df["adcode"].map(norm_adcode)
        miss = df["adcode"].isna().sum()
        if miss:
            qa(f"{year} 普查：{miss} 行代码无法识别，已剔除")
        df = df.dropna(subset=["adcode"])
        for c in CENSUS_COUNTS + CENSUS_SHARES:
            if c in df:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        # 各列完全相同的行是重复录入，只保留一行（否则人口会被加倍）
        n_exact = int(df.duplicated().sum())
        if n_exact:
            df = df.drop_duplicates()
            qa(f"{year} 普查：{n_exact} 行与其他行完全相同（重复录入），已删除")
        dup = df["adcode"].duplicated().sum()
        if dup:
            qa(f"{year} 普查：{dup} 个代码出现多行且内容不同，已按求和/加权合并（如为乡镇级 12 位代码属正常，否则请核对）")
        df = collapse(df, ["adcode"], CENSUS_COUNTS, CENSUS_SHARES, SHARE_WEIGHTS)
        df = harmonize(df, "adcode", CENSUS_COUNTS, CENSUS_SHARES, cw, year, SHARE_WEIGHTS, ref_date=ref_date)
        m = df.merge(c2u[["adcode", "unit_id"]], on="adcode", how="left")
        un = m[m["unit_id"].isna()]
        if len(un):
            qa(f"{year} 普查：{len(un)} 个代码未匹配到 2020 年分析单元，示例 {un['adcode'].head(10).tolist()}"
               "（请在代码对照表中补充）")
        m = m.dropna(subset=["unit_id"])
        if year == 2020:
            county2020 = m[["adcode", "unit_id", "pop_resident"]].copy() if "pop_resident" in m else None
        u = collapse(m, ["unit_id"], CENSUS_COUNTS, CENSUS_SHARES, SHARE_WEIGHTS)
        u = u.rename(columns={c: f"{c}_{year}" for c in u.columns if c != "unit_id"})
        if "pop_resident" in m:
            cov = m[m["pop_resident"].notna()].groupby("unit_id")["adcode"].nunique() / members
            u[f"census_cov_{year}"] = u["unit_id"].map(cov).clip(upper=1.0)
            part = u[u[f"census_cov_{year}"] < 1]
            if len(part):
                qa(f"{year} 普查：{len(part)} 个单元的成员不全（census_cov_{year} < 1），单元人口会被低估，示例 "
                   f"{part['unit_id'].head(10).tolist()}")
        hh = [c for c in CENSUS_HH_SHARES if c in m and m[c].notna().any()]
        if hh:
            wcol = "households" if "households" in m and m["households"].notna().any() else "pop_resident"
            qa(f"{year} 普查：住房来源比例 {hh} 按 {wcol} 加权合并到单元")
        outs.append(u.set_index("unit_id"))
        qa(f"{year} 普查：汇总得到 {len(u)} 个分析单元")
    if not outs:
        return pd.DataFrame(columns=["unit_id"]), None
    return pd.concat(outs, axis=1).reset_index(), county2020


# ===========================================================================
# 代码块 3：财政（县、县级市 + 市辖区合计）
# 目的：读取财政收支、转移支付分项、支出结构与社会事业计数，统一货币单位到“元”，统一代码，
#       按配置的年份求均值：主分析期 main（默认 2017–2019，营改增后第一个完整年度至疫情前）、
#       稳健性 rob（默认 2018、2019、2021）、2010 期 y2010（2009–2011）、2000 期 y2000（1999–2001）。
#       金额只在“收入与支出都有数”的年份上平均，避免收入与支出取自不同年份；n_years_<期> 为这样的年份数。
#       边界一致性：某县在 y 年仍是县、之后才撤县设区并入某市市辖区时，y 年《城市统计年鉴》的“市辖区”
#       不含该县，而本研究按 2020 年边界定义市辖区单元。因此把这类县在 y 年的财政数加到该市 y 年的
#       市辖区合计上，使各年份都对应 2020 年边界。
#       district_level_fiscal_prefs 中的城市（如重庆）已在县域财政表中逐区录入：保留这些区的记录并归入各自单元
#       （中心城区或外围市辖区），不再使用《城市统计年鉴》的市辖区合计。
# 结果：返回 (一行一个分析单元的财政宽表, 主分析期成员覆盖率 Series)。宽表例如 gen_budget_expenditure_main、
#       transfer_total_y2000、hospital_beds_main。
# ===========================================================================
FISCAL_VARS = FISCAL_MONEY + FISCAL_COUNTS + ["pop_hukou_yearend"]


def read_fiscal(path, code_col, mult, label: str, city_scope: bool = False):
    df = read_table(path, code_cols=(code_col,))
    df[code_col] = df[code_col].map(norm_adcode)
    df = df.dropna(subset=[code_col])
    if city_scope:
        # 直辖市在年鉴中常写作 110100（“北京市市辖区”），统一为分析单元使用的 110000；其他城市不变
        df[code_col] = df[code_col].map(pref_code)
        # 《城市统计年鉴》同时给出“全市”和“市辖区”两种口径；若填了 scope 列，只保留市辖区口径（空白视为市辖区）
        if "scope" in df:
            sc = df["scope"].astype("string").str.strip()
            ok = sc.isna() | sc.eq("") | sc.str.contains("市辖区", regex=False)
            if (~ok).any():
                qa(f"{label}：{int((~ok).sum())} 行 scope 不是“市辖区”（如“全市”），已剔除")
            df = df[ok.fillna(True).astype(bool)]
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["year"])
    for c in FISCAL_MONEY:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce") * mult
    for c in FISCAL_COUNTS:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "pop_hukou_yearend" in df:
        df["pop_hukou_yearend"] = pd.to_numeric(df["pop_hukou_yearend"], errors="coerce") * 1e4
    # 完全相同的行是重复录入，删除；同一代码同一年仍有多行（内容不同）时会被加总，提示核对
    n_exact = int(df.duplicated().sum())
    if n_exact:
        df = df.drop_duplicates()
        qa(f"{label}：{n_exact} 行与其他行完全相同（重复录入），已删除")
    dup = df.duplicated([code_col, "year"])
    if dup.any():
        qa(f"{label}：{int(dup.sum())} 个“代码—年份”出现多行且内容不同，将被加总，请核对是否重复录入，示例 "
           f"{df.loc[dup, [code_col, 'year']].astype(str).agg('-'.join, axis=1).head(10).tolist()}")
    return df


def valid_years(d: pd.DataFrame) -> pd.Series:
    """收入与支出都有数的行。"""
    if {"gen_budget_revenue", "gen_budget_expenditure"} <= set(d.columns):
        return d["gen_budget_revenue"].notna() & d["gen_budget_expenditure"].notna()
    return pd.Series(False, index=d.index)


def fiscal_average(long, years, suffix):
    d = long[long["year"].isin([int(y) for y in years])]
    ok = valid_years(d)
    money = [c for c in FISCAL_MONEY if c in d]
    other = [c for c in FISCAL_COUNTS + ["pop_hukou_yearend"] if c in d]
    # 金额只在收入、支出都有数的年份平均；学生、床位、户籍人口等计数在各自有数的年份平均
    out = d[ok].groupby("unit_id")[money].mean()
    if other:
        out = out.join(d.groupby("unit_id")[other].mean(), how="outer")
    out["n_years_" + suffix] = d[ok].groupby("unit_id").size()
    out["n_years_" + suffix] = out["n_years_" + suffix].fillna(0).astype(int)
    return out.rename(columns={c: f"{c}_{suffix}" for c in money + other}).reset_index()


def build_fiscal(cfg, c2u, cw) -> tuple[pd.DataFrame, pd.Series | None]:
    fc = cfg["fiscal_census"]
    mult = MONEY_TO_YUAN[fc["money_unit_in_raw"]]
    main_years = [int(y) for y in fc["fiscal_years_main"]]
    dl_prefs = {p for p in (norm_pref(x) for x in (fc.get("district_level_fiscal_prefs") or [])) if p}
    longs = []
    to_cp = None
    covered = set()     # 主分析期收入、支出都有数的县级代码（2020 年代码）

    # 3a. 县、县级市（逐年统一代码，再映射到 2020 年分析单元）
    p = resolve(fc["fiscal_county_file"])
    if p.exists():
        df = read_fiscal(p, "adcode", mult, "县域财政")
        # 防止重复计算：县域表若混入“2020 年属市辖区或不设区地级市”的代码（且该年不在对照表中、即当年已是区），
        # 这些记录与《城市统计年鉴》市辖区合计重复，不能再加到市辖区单元上，予以剔除。
        # district_level_fiscal_prefs 中的城市例外：它们的区级记录就是该市唯一的财政来源。
        # （若某县撤县设区后仍沿用原代码，请在对照表中写一行 A→A、change_year=设区年份，以保留设区前的县级数据。）
        is_dist = c2u["admin_type"].isin(["district", "pref_city_no_district"])
        city_codes = set(c2u.loc[is_dist & ~c2u["pref_code"].isin(dl_prefs), "adcode"])
        blocks, n_city = [], 0
        for y in sorted(df["year"].unique()):
            b = df[df["year"] == y]
            cwy = applicable(cw, int(y))
            old = set(cwy["old_code"]) if cwy is not None else set()
            is_city = b["adcode"].isin(city_codes) & ~b["adcode"].isin(old)
            n_city += int(is_city.sum())
            blocks.append(harmonize(b[~is_city], "adcode", FISCAL_VARS, [], cw, int(y)))
        if n_city:
            qa(f"县域财政：{n_city} 条记录的代码当年已是市辖区或不设区地级市，与市辖区合计重复，已剔除")
        df = pd.concat(blocks, ignore_index=True)
        m = df.merge(c2u[["adcode", "unit_id", "unit_type", "pref_code"]], on="adcode", how="left")
        un = m[m["unit_id"].isna()]
        if len(un):
            qa(f"县域财政：{un['adcode'].nunique()} 个代码未匹配到 2020 年分析单元，示例 "
               f"{un['adcode'].drop_duplicates().head(10).tolist()}（请补充代码对照表）")
        m = m.dropna(subset=["unit_id"])
        mm = m[m["year"].isin(main_years)]
        covered = set(mm.loc[valid_years(mm), "adcode"])
        cols = [c for c in FISCAL_VARS if c in m]
        is_dl = m["pref_code"].isin(dl_prefs) & m["unit_type"].isin(["city_proper", "district_outer"])
        if is_dl.any():
            dl = m[is_dl]
            qa(f"区级财政：{sorted(dl_prefs)} 的 {dl['adcode'].nunique()} 个区按区级记录归入各自单元"
               f"（{sorted(dl['unit_id'].unique())[:20]}），不再使用这些城市的市辖区合计")
            longs.append(dl.groupby(["unit_id", "year"])[cols].sum(min_count=1).reset_index())
        to_cp = m[(m["unit_type"] == "city_proper") & ~is_dl]
        if len(to_cp):
            qa(f"县域财政：{to_cp['adcode'].nunique()} 个县在部分年份为县、2020 年已属市辖区，"
               "其财政数将加到对应城市的市辖区合计（2020 年边界口径）")
        cty = m[m["unit_type"].isin(["county", "county_city"])]
        longs.append(cty.groupby(["unit_id", "year"])[cols].sum(min_count=1).reset_index())
    else:
        qa(f"缺少县域财政表：{p.name}")

    # 3b. 市辖区合计（地级及以上城市），并加上 3a 中“当年仍为县”的部分
    cp_covered_units = set()
    p = resolve(fc["fiscal_city_file"])
    if p.exists():
        df = read_fiscal(p, "pref_code", mult, "市辖区财政", city_scope=True)
        drop = df["pref_code"].isin(dl_prefs)
        if drop.any():
            qa(f"市辖区财政：{sorted(dl_prefs)} 已使用区级财政，剔除其市辖区合计 {int(drop.sum())} 行")
            df = df[~drop]
        df["unit_id"] = "CP" + df["pref_code"]
        un = sorted(set(df["unit_id"]) - set(c2u["unit_id"]))
        if un:
            qa(f"市辖区财政：{len(un)} 个地级代码未匹配到分析单元，示例 {un[:10]}")
        cols = [c for c in FISCAL_VARS if c in df]
        cp = df.groupby(["unit_id", "year"])[cols].sum(min_count=1)
        if to_cp is not None and len(to_cp):
            add = to_cp.groupby(["unit_id", "year"])[[c for c in cols if c in to_cp]].sum(min_count=1)
            add = add.reindex(cp.index)
            cp = cp.add(add, fill_value=0).where(cp.notna())
        cp = cp.reset_index()
        cm = cp[cp["year"].isin(main_years)]
        cp_covered_units = set(cm.loc[valid_years(cm), "unit_id"])
        longs.append(cp)
    else:
        qa(f"缺少市辖区财政表：{p.name}")

    if not longs:
        return pd.DataFrame(columns=["unit_id"]), None
    long = pd.concat(longs, ignore_index=True)
    out = None
    for key, suffix in FISCAL_PERIODS:
        years = fc.get(key)
        if not years:
            continue
        a = fiscal_average(long, years, suffix)
        qa(f"财政 {suffix}（{list(years)}）：{int((a['n_years_' + suffix] > 0).sum())} 个单元有收入与支出")
        out = a if out is None else out.merge(a, on="unit_id", how="outer")

    # 成员覆盖率：成员在主分析期有收入与支出记录的比例。市辖区合计来自《城市统计年鉴》时，
    # 主分析期开始前已是区的成员视为已覆盖；主分析期内才撤县设区的成员，须在县域财政表中有设区前的记录。
    first = min(main_years)
    cy = pd.to_numeric(c2u["converted_year"], errors="coerce") if "converted_year" in c2u else pd.Series(np.nan, index=c2u.index)
    by_city = c2u["unit_id"].isin(cp_covered_units) & c2u["admin_type"].isin(["district", "pref_city_no_district"]) \
        & (cy.isna() | (cy <= first))
    ok = by_city | c2u["adcode"].isin(covered)
    cov = ok.groupby(c2u["unit_id"]).mean()
    return out, cov


# ===========================================================================
# 代码块 4：可选的土地、债务、专项债与开发区数据
# 目的：把与转移支付并列的资金来源和国家中心性变量汇总到分析单元。金额单位与财政表相同（money_unit_in_raw），换算为元。
#       代码可以是县级代码，也可以是地级代码 xxxx00（市本级的出让或平台债务），后者归入该市的市辖区单元。
#       土地出让与城投债务取主分析期均值；专项债把文件中所有年份加总，并给出 市政+园林绿化+生态环保 小计；
#       开发区按国家级、省级分别加总核准面积与个数。
# 结果：返回一行一个分析单元的宽表（文件缺失时为空表）。
# ===========================================================================
def _read_optional(cfg, key, label, required_cols, code_col="adcode"):
    path = cfg["fiscal_census"].get(key)
    if not path or not resolve(path).exists():
        qa(f"未提供{label}（{key}），相关指标为缺失")
        return None
    df = read_table(resolve(path), code_cols=(code_col,))
    miss = [c for c in [code_col] + list(required_cols) if c not in df]
    if miss:
        qa(f"{label}：{resolve(path).name} 缺少列 {miss}（列名见 数据/模板），未使用该文件")
        return None
    df[code_col] = df[code_col].map(norm_adcode)
    bad = df[code_col].isna()
    if bad.any():
        qa(f"{label}：{int(bad.sum())} 行代码无法识别，已剔除")
    return df[~bad].copy()


def _to_units(df, c2u, cw, counts, label, year_col="year", fixed_year=None):
    """逐年统一代码后映射到分析单元，返回含 unit_id 的长表。"""
    blocks = []
    if df.empty:
        return df.assign(unit_id=pd.Series(dtype=object))
    years = [fixed_year] if fixed_year else sorted(df[year_col].dropna().unique())
    for y in years:
        b = df if fixed_year else df[df[year_col] == y]
        blocks.append(harmonize(b, "adcode", counts, [], cw, int(y)))
    d = pd.concat(blocks, ignore_index=True)
    d["unit_id"] = code_to_unit(d["adcode"], c2u)
    un = d[d["unit_id"].isna()]
    if len(un):
        qa(f"{label}：{un['adcode'].nunique()} 个代码未匹配到分析单元，示例 {un['adcode'].drop_duplicates().head(10).tolist()}")
    return d.dropna(subset=["unit_id"])


def build_optional(cfg, c2u, cw) -> pd.DataFrame:
    fc = cfg["fiscal_census"]
    mult = MONEY_TO_YUAN[fc["money_unit_in_raw"]]
    main_years = [int(y) for y in fc["fiscal_years_main"]]
    outs = []

    for key, label, money, cnts in [
        ("land_conveyance_file", "土地出让", ["land_conv_revenue"], ["land_conv_area_ha", "n_parcels"]),
        ("lgfv_debt_file", "城投有息债务", ["lgfv_debt"], []),
    ]:
        df = _read_optional(cfg, key, label, ["year"] + money)
        if df is None:
            continue
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        for c in money + cnts:
            df[c] = pd.to_numeric(df[c], errors="coerce") * (mult if c in money else 1.0) if c in df else np.nan
        d = _to_units(df[df["year"].isin(main_years)], c2u, cw, money + cnts, label)
        g = d.groupby(["unit_id", "year"])[money + cnts].sum(min_count=1).groupby("unit_id").mean()
        g = g.rename(columns={c: f"{c}_main" for c in g.columns})
        qa(f"{label}：主分析期 {main_years} 汇总得到 {len(g)} 个单元")
        outs.append(g)

    df = _read_optional(cfg, "special_bond_file", "新增专项债", ["year", "category", "amount"])
    if df is not None:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce") * mult
        cat = df["category"].astype("string").str.strip()
        df["cat"] = cat.map(BOND_CATEGORIES)
        unknown = df["cat"].isna()
        if unknown.any():
            qa(f"新增专项债：{int(unknown.sum())} 行 category 不在 {list(BOND_CATEGORIES)} 中，计入“其他”，示例 "
               f"{cat[unknown].dropna().unique().tolist()[:10]}")
            df.loc[unknown, "cat"] = "other"
        wide = df.pivot_table(index=["adcode", "year"], columns="cat", values="amount", aggfunc="sum").reset_index()
        wide.columns.name = None
        bcols = [f"special_bond_{v}" for v in BOND_CATEGORIES.values()]
        wide = wide.rename(columns={v: f"special_bond_{v}" for v in BOND_CATEGORIES.values()})
        for c in bcols:
            if c not in wide:
                wide[c] = np.nan
        d = _to_units(wide, c2u, cw, bcols, "新增专项债")
        g = d.groupby("unit_id")[bcols].sum(min_count=1)
        g["special_bond_total"] = g[bcols].sum(axis=1, min_count=1)
        g["special_bond_green_sub"] = g[["special_bond_muni", "special_bond_greening", "special_bond_eco"]].sum(axis=1, min_count=1)
        qa(f"新增专项债：{sorted(df['year'].dropna().astype(int).unique().tolist())} 年合计，{len(g)} 个单元")
        outs.append(g)

    df = _read_optional(cfg, "devzone_file", "开发区目录", ["level", "approved_area_km2"])
    if df is not None:
        lvl = df["level"].astype("string").str.strip()
        area = pd.to_numeric(df["approved_area_km2"], errors="coerce")
        df["devzone_nat_km2"] = area.where(lvl.eq("国家级"))
        df["devzone_prov_km2"] = area.where(lvl.eq("省级"))
        df["n_devzone_nat"] = lvl.eq("国家级").astype(float)
        df["n_devzone_prov"] = lvl.eq("省级").astype(float)
        other = ~lvl.isin(["国家级", "省级"]).fillna(False).astype(bool)
        if other.any():
            qa(f"开发区目录：{int(other.sum())} 行 level 不是“国家级”或“省级”，未计入")
        cols = ["devzone_nat_km2", "devzone_prov_km2", "n_devzone_nat", "n_devzone_prov"]
        d = _to_units(df[["adcode"] + cols], c2u, cw, cols, "开发区目录", fixed_year=2018)
        g = d.groupby("unit_id")[cols].sum(min_count=1)
        qa(f"开发区目录：{len(g)} 个单元有国家级或省级开发区")
        outs.append(g)

    if not outs:
        return pd.DataFrame(columns=["unit_id"])
    return pd.concat(outs, axis=1).reset_index().rename(columns={"index": "unit_id"})


# ===========================================================================
# 代码块 5：主流程
# 目的：读入 county_to_unit 对应表 → 普查 → 财政 → 可选资金来源 → 合并 → 标注口径风险 → 写出结果与质量报告。
# 结果：数据/中间/panel/unit_fiscal_census.csv 与 qa_report.md。
# ===========================================================================
def check_years(cfg):
    """数据年份晚于边界年份时提示：之后新设的区在县域年鉴中消失，而市辖区合计已包含它们，这些年份的数据不在边界口径上。"""
    by = cfg["units"].get("boundary_year")
    if not by:
        return
    fc = cfg["fiscal_census"]
    for key, suffix in FISCAL_PERIODS:
        late = [int(y) for y in (fc.get(key) or []) if int(y) > int(by)]
        if late:
            qa(f"口径提示：财政年份 {suffix} 中的 {late} 晚于边界年份 {by}（units.boundary_year）。"
               f"{by} 年后撤县设区的县在这些年份已从县域年鉴中消失，市辖区合计却已包含它们，"
               "相关单元的这几年数据不在同一边界上。")
    late = [int(y) for y in fc["census_files"] if int(y) > int(by)]
    if late:
        qa(f"口径提示：普查年份 {late} 晚于边界年份 {by}，请确认代码对照表已映射到 {by} 年代码。")


def main():
    cfg = load_config()
    fc = cfg["fiscal_census"]
    out_dir = resolve(fc["out_dir"])
    c2u_path = resolve(cfg["units"]["out_dir"]) / "county_to_unit.csv"
    if not c2u_path.exists():
        LOG.error("找不到 county_to_unit.csv，请先运行 00_prepare_units.py")
        sys.exit(1)
    c2u = read_table(c2u_path, code_cols=("adcode", "unit_id", "prov_code", "pref_code"))
    check_years(cfg)
    cw = load_crosswalk(cfg)
    if cw is not None:
        # new_code 应是 2020 年边界中的代码，或是后续另一次变更的 old_code（多步变更的中间代码）；
        # 两者都不是时（2020 年以后的新代码、录入错误），相关数据会在后面“未匹配”而丢失
        lost = sorted(set(cw["new_code"]) - set(c2u["adcode"]) - set(cw["old_code"]))
        if lost:
            qa(f"代码对照表：{len(lost)} 个 new_code 不在 2020 年边界中，相关数据将无法匹配（对照表应只写到 2020 年代码），"
               f"示例 {lost[:10]}")

    census, county2020 = build_census(cfg, c2u, cw)
    fiscal, fcov = build_fiscal(cfg, c2u, cw)
    opt = build_optional(cfg, c2u, cw)
    units = c2u.drop_duplicates("unit_id")[["unit_id", "unit_type", "prov_code", "pref_code"]]
    out = (units.merge(census, on="unit_id", how="left").merge(fiscal, on="unit_id", how="left")
           .merge(opt, on="unit_id", how="left"))
    if fcov is not None:
        out["fiscal_cov_main"] = out["unit_id"].map(fcov)
        part = out[out["fiscal_cov_main"] < 1]
        if len(part):
            qa(f"财政覆盖：{len(part)} 个单元的成员在主分析期不全（fiscal_cov_main < 1），示例 "
               f"{part['unit_id'].head(10).tolist()}")

    # 口径风险标记：city_proper_custom 中的城市，若财政仍为《城市统计年鉴》全部市辖区口径，而单元只含中心城区，
    # 则标记为不一致；已在 district_level_fiscal_prefs 中逐区录入财政的城市不再标记
    custom = {norm_pref(k) for k in (cfg["units"].get("city_proper_custom") or {})}
    dl = {norm_pref(k) for k in (fc.get("district_level_fiscal_prefs") or [])}
    out["fiscal_scope_mismatch"] = out["unit_id"].isin({"CP" + c for c in custom - dl if c})
    if out["fiscal_scope_mismatch"].any():
        qa(f"口径提示：{sorted(out.loc[out['fiscal_scope_mismatch'], 'unit_id'])} 的财政为全部市辖区口径，"
           "单元只含中心城区，主回归中默认剔除。改为逐区录入并在 district_level_fiscal_prefs 中列出后即可纳入。")

    # 撤县设区人口占比：市辖区单元 2020 年常住人口中，2000 年后撤县（市）设区的区所占比例
    if county2020 is not None and "converted_year" in c2u:
        conv = set(c2u.loc[pd.to_numeric(c2u["converted_year"], errors="coerce").notna(), "adcode"])
        cp = county2020[county2020["unit_id"].str.startswith("CP")]
        num = cp[cp["adcode"].isin(conv)].groupby("unit_id")["pop_resident"].sum()
        den = cp.groupby("unit_id")["pop_resident"].sum()
        share = (num.reindex(den.index).fillna(0) / den.where(den > 0))
        out["conv_pop_share_2020"] = out["unit_id"].map(share)
        out.loc[out["unit_type"] != "city_proper", "conv_pop_share_2020"] = np.nan
        qa(f"撤县设区：{int((out['conv_pop_share_2020'] > 0).sum())} 个市辖区单元含 2000 年后设立的区")

    for c in ["pop_resident_2020", "gen_budget_expenditure_main", "gen_budget_revenue_main"]:
        if c in out:
            qa(f"{c} 缺失 {int(out[c].isna().sum())} / {len(out)} 个单元")
    atomic_write_csv(out, out_dir / "unit_fiscal_census.csv")
    atomic_write_text(out_dir / "qa_report.md", "# 财政与普查数据质量报告\n\n" + "\n".join(f"- {m}" for m in QA) + "\n")
    LOG.info(f"完成：{len(out)} 个分析单元 → {out_dir / 'unit_fiscal_census.csv'}")


if __name__ == "__main__":
    main()
