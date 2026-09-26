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
    代码对照表              历年行政区划代码 → 2020 年代码 → admin_crosswalk.csv
    00 脚本输出的 county_to_unit.csv
输出（数据/中间/panel/）：
    unit_fiscal_census.csv   一行一个分析单元：财政多年均值（主分析期、2010 期）与三次普查变量
    qa_report.md             数据质量报告：缺失、重复、未匹配代码清单
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (atomic_write_csv, atomic_write_text, get_logger, load_config, norm_adcode,  # noqa: E402
                    pref_code, read_table, resolve)

LOG = get_logger("02_build_fiscal_census")
QA: list[str] = []

MONEY_TO_YUAN = {"元": 1.0, "万元": 1e4, "亿元": 1e8}
FISCAL_MONEY = ["gen_budget_revenue", "gen_budget_expenditure", "tax_revenue", "land_conveyance_revenue", "gdp"]
CENSUS_COUNTS = ["pop_resident", "pop_urban", "households", "hh_pop", "pop_hukou", "pop_hukou_elsewhere"]
CENSUS_SHARES = ["housing_area_pc", "share_rent_public", "share_rent_market", "share_buy_new",
                 "share_buy_second", "share_self_built", "share_65plus"]


def qa(msg: str):
    QA.append(msg)
    LOG.info(msg)


# ===========================================================================
# 代码块 1：代码对照（行政区划调整的统一）
# 目的：2000–2020 年间大量“撤县设区”“合并”“更名”，旧代码必须映射到 2020 年代码才能与 2020 年边界对齐。
#       对照表每行给出 old_code → new_code 与权重 weight（拆分时按面积或人口比例填写，普通更名/合并填 1）。
#       计数型变量（人口、财政金额）按权重分配后加总；比例型变量按常住人口加权平均。
#       本函数按时间顺序应用对照表，处理“旧代码 → 中间代码 → 2020 代码”的多次变更：
#       每行数据记住自己“当前所处的年份”，每次只应用该代码的下一次变更（change_year 最早的一批），
#       应用后把年份推进到 change_year。这样：
#         · 拆分后保留原代码的情形（A→A 0.6、A→B 0.4）不会被重复拆分；
#         · 同一旧代码先后发生两次变更（2012 年部分划出、2018 年整体撤县设区）不会重复计数。
#       未填 change_year 的行视为适用；其中 old_code = new_code 的行视为终点。
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
    # weight、change_year 两列可选：缺 weight 视为 1（整体变更），缺 change_year 视为任何年份的数据都适用
    cw["weight"] = pd.to_numeric(cw["weight"], errors="coerce").fillna(1.0) if "weight" in cw else 1.0
    cw["change_year"] = pd.to_numeric(cw["change_year"], errors="coerce") if "change_year" in cw else np.nan
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


def applicable(cw: pd.DataFrame | None, data_year: int) -> pd.DataFrame | None:
    """对照表中适用于 data_year 年数据的行：change_year 晚于数据年份，或未填 change_year。"""
    if cw is None:
        return None
    return cw[cw["change_year"].isna() | (cw["change_year"] > data_year)]


def harmonize(df: pd.DataFrame, code_col: str, counts: list, shares: list, cw: pd.DataFrame | None,
              data_year: int, weight_col: str | None = None, max_iter: int = 10) -> pd.DataFrame:
    df = df.copy()
    cw = applicable(cw, data_year)
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


def collapse(df, keys, counts, shares, weight_col):
    """按 keys 汇总：计数型求和（全缺失保持缺失），比例型按 weight_col 加权平均。"""
    counts = [c for c in counts if c in df]
    shares = [c for c in shares if c in df]
    g = df.groupby(keys, dropna=False)
    out = g[counts].sum(min_count=1) if counts else g.size().to_frame("n").drop(columns="n")
    if shares:
        w = df[weight_col] if weight_col and weight_col in df else pd.Series(1.0, index=df.index)
        tmp = df[keys].copy()
        for c in shares:
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
# 结果：返回一行一个分析单元的普查宽表，例如 pop_resident_2020、pop_urban_2010。
# ===========================================================================
def build_census(cfg, c2u: pd.DataFrame, cw) -> pd.DataFrame:
    outs = []
    for year, path in cfg["fiscal_census"]["census_files"].items():
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
        df = collapse(df, ["adcode"], CENSUS_COUNTS, CENSUS_SHARES, "pop_resident")
        df = harmonize(df, "adcode", CENSUS_COUNTS, CENSUS_SHARES, cw, year, "pop_resident")
        m = df.merge(c2u[["adcode", "unit_id"]], on="adcode", how="left")
        un = m[m["unit_id"].isna()]
        if len(un):
            qa(f"{year} 普查：{len(un)} 个代码未匹配到 2020 年分析单元，示例 {un['adcode'].head(10).tolist()}"
               "（请在代码对照表中补充）")
        m = m.dropna(subset=["unit_id"])
        u = collapse(m, ["unit_id"], CENSUS_COUNTS, CENSUS_SHARES, "pop_resident")
        u = u.rename(columns={c: f"{c}_{year}" for c in u.columns if c != "unit_id"})
        outs.append(u.set_index("unit_id"))
        qa(f"{year} 普查：汇总得到 {len(u)} 个分析单元")
    if not outs:
        return pd.DataFrame(columns=["unit_id"])
    return pd.concat(outs, axis=1).reset_index()


# ===========================================================================
# 代码块 3：财政（县、县级市 + 市辖区合计）
# 目的：读取财政收支，统一货币单位到“元”，统一代码，按配置的年份求均值
#       （主分析期默认 2018、2019、2021 三年均值，避开 2020 年抗疫特殊转移支付的干扰；
#        2010 期默认 2009–2011 三年均值），并标注缺失年份数。
#       边界一致性：某县在 y 年仍是县、之后才撤县设区并入某市市辖区时，y 年《城市统计年鉴》的“市辖区”
#       不含该县，而本研究按 2020 年边界定义市辖区单元。因此把这类县在 y 年的财政数加到该市 y 年的
#       市辖区合计上，使各年份都对应 2020 年边界。
# 结果：返回一行一个分析单元的财政宽表，例如 gen_budget_expenditure_main、gen_budget_revenue_y2010。
# ===========================================================================
FISCAL_VARS = FISCAL_MONEY + ["pop_hukou_yearend"]


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


def fiscal_average(long, years, suffix):
    d = long[long["year"].isin(years)]
    cols = [c for c in FISCAL_VARS if c in d]
    g = d.groupby("unit_id")
    out = g[cols].mean()
    # n_years：参与平均的年份数（以一般公共预算支出非缺失的年份计）
    out["n_years_" + suffix] = g["gen_budget_expenditure"].count() if "gen_budget_expenditure" in d else 0
    return out.rename(columns={c: f"{c}_{suffix}" for c in cols}).reset_index()


def build_fiscal(cfg, c2u, cw) -> pd.DataFrame:
    fc = cfg["fiscal_census"]
    mult = MONEY_TO_YUAN[fc["money_unit_in_raw"]]
    longs = []
    to_cp = None

    # 3a. 县、县级市（逐年统一代码，再映射到 2020 年分析单元）
    p = resolve(fc["fiscal_county_file"])
    if p.exists():
        df = read_fiscal(p, "adcode", mult, "县域财政")
        # 防止重复计算：县域表若混入“2020 年属市辖区或不设区地级市”的代码（且该年不在对照表中、即当年已是区），
        # 这些记录与《城市统计年鉴》市辖区合计重复，不能再加到市辖区单元上，予以剔除。
        # （若某县撤县设区后仍沿用原代码，请在对照表中写一行 A→A、change_year=设区年份，以保留设区前的县级数据。）
        city_codes = set(c2u.loc[c2u["admin_type"].isin(["district", "pref_city_no_district"]), "adcode"])
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
        m = df.merge(c2u[["adcode", "unit_id", "unit_type"]], on="adcode", how="left")
        un = m[m["unit_id"].isna()]
        if len(un):
            qa(f"县域财政：{un['adcode'].nunique()} 个代码未匹配到 2020 年分析单元，示例 "
               f"{un['adcode'].drop_duplicates().head(10).tolist()}（请补充代码对照表）")
        to_cp = m[m["unit_type"] == "city_proper"]
        if len(to_cp):
            qa(f"县域财政：{to_cp['adcode'].nunique()} 个县在部分年份为县、2020 年已属市辖区，"
               "其财政数将加到对应城市的市辖区合计（2020 年边界口径）")
        cty = m[m["unit_type"].isin(["county", "county_city"])]
        cols = [c for c in FISCAL_VARS if c in cty]
        longs.append(cty.groupby(["unit_id", "year"])[cols].sum(min_count=1).reset_index())
    else:
        qa(f"缺少县域财政表：{p.name}")

    # 3b. 市辖区合计（地级及以上城市），并加上 3a 中“当年仍为县”的部分
    p = resolve(fc["fiscal_city_file"])
    if p.exists():
        df = read_fiscal(p, "pref_code", mult, "市辖区财政", city_scope=True)
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
        longs.append(cp.reset_index())
    else:
        qa(f"缺少市辖区财政表：{p.name}")

    if not longs:
        return pd.DataFrame(columns=["unit_id"])
    long = pd.concat(longs, ignore_index=True)
    main = fiscal_average(long, fc["fiscal_years_main"], "main")
    y10 = fiscal_average(long, fc["fiscal_years_2010"], "y2010")
    qa(f"财政：主分析期 {len(main)} 个单元，2010 期 {len(y10)} 个单元")
    return main.merge(y10, on="unit_id", how="outer")


# ===========================================================================
# 代码块 4：主流程
# 目的：读入 county_to_unit 对应表 → 普查 → 财政 → 合并 → 标注口径风险 → 写出结果与质量报告。
# 结果：数据/中间/panel/unit_fiscal_census.csv 与 qa_report.md。
# ===========================================================================
def main():
    cfg = load_config()
    fc = cfg["fiscal_census"]
    out_dir = resolve(fc["out_dir"])
    c2u_path = resolve(cfg["units"]["out_dir"]) / "county_to_unit.csv"
    if not c2u_path.exists():
        LOG.error("找不到 county_to_unit.csv，请先运行 00_prepare_units.py")
        sys.exit(1)
    c2u = read_table(c2u_path, code_cols=("adcode", "unit_id", "prov_code", "pref_code"))
    cw = load_crosswalk(cfg)
    if cw is not None:
        # new_code 应是 2020 年边界中的代码，或是后续另一次变更的 old_code（多步变更的中间代码）；
        # 两者都不是时（2020 年以后的新代码、录入错误），相关数据会在后面“未匹配”而丢失
        lost = sorted(set(cw["new_code"]) - set(c2u["adcode"]) - set(cw["old_code"]))
        if lost:
            qa(f"代码对照表：{len(lost)} 个 new_code 不在 2020 年边界中，相关数据将无法匹配（对照表应只写到 2020 年代码），"
               f"示例 {lost[:10]}")

    census = build_census(cfg, c2u, cw)
    fiscal = build_fiscal(cfg, c2u, cw)
    units = c2u.drop_duplicates("unit_id")[["unit_id", "unit_type", "prov_code", "pref_code"]]
    out = units.merge(census, on="unit_id", how="left").merge(fiscal, on="unit_id", how="left")

    # 口径风险标记：city_proper_custom 中的城市，财政为“全部市辖区”口径，而单元只含中心城区
    custom = {str(k) for k in (cfg["units"].get("city_proper_custom") or {})}
    out["fiscal_scope_mismatch"] = out["unit_id"].isin({"CP" + c for c in custom})
    if out["fiscal_scope_mismatch"].any():
        qa(f"口径提示：{sorted(out.loc[out['fiscal_scope_mismatch'], 'unit_id'])} 的财政为全部市辖区口径，"
           "单元只含中心城区，主回归中默认剔除。")

    for c in ["pop_resident_2020", "gen_budget_expenditure_main"]:
        if c in out:
            qa(f"{c} 缺失 {int(out[c].isna().sum())} / {len(out)} 个单元")
    atomic_write_csv(out, out_dir / "unit_fiscal_census.csv")
    atomic_write_text(out_dir / "qa_report.md", "# 财政与普查数据质量报告\n\n" + "\n".join(f"- {m}" for m in QA) + "\n")
    LOG.info(f"完成：{len(out)} 个分析单元 → {out_dir / 'unit_fiscal_census.csv'}")


if __name__ == "__main__":
    main()
