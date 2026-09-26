# -*- coding: utf-8 -*-
"""
03_build_indicators.py  合并财政、普查与遥感数据，计算全部分析指标并划分城市/县城类型

在哪里运行：Mac “终端 Terminal”
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python 03_build_indicators.py
    python 03_build_indicators.py --codebook-only   # 只导出指标说明表（不需要任何数据）

输入：00 的 units_table.csv；01 的 gee_unit_metrics.csv；02 的 unit_fiscal_census.csv；
      外部参数 中的城市规模标准与超大特大城市名单；可选的城区人口表与住建部绿地统计表。
输出（数据/结果/）：
    unit_indicators.csv       一行一个分析单元，含全部指标与分组变量
    codebook_indicators.csv   指标说明（中文名、英文名、公式、单位），与 附录C 一致
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import atomic_write_csv, get_logger, load_config, norm_adcode, pref_code, read_table, resolve  # noqa: E402

LOG = get_logger("03_build_indicators")

# ===========================================================================
# 代码块 1：指标说明表 (codebook)
# 目的：集中写明每个指标的中文名、英文术语、计算公式与单位；脚本计算与 附录C 共用这一份定义。
# 结果：CODEBOOK 列表；--codebook-only 时导出为 CSV。
# ===========================================================================
CODEBOOK = [
    # 财政
    ("fss", "财政自给率", "fiscal self-sufficiency ratio", "一般公共预算收入 / 一般公共预算支出（主分析期三年均值）", "比值"),
    ("gap_ratio", "转移支付依赖度", "transfer dependence (fiscal gap ratio)", "(支出 − 收入) / 支出", "比值"),
    ("exp_pc_res", "人均财政支出（常住口径）", "expenditure per resident", "一般公共预算支出 / 2020 年常住人口", "元/人"),
    ("exp_pc_hukou", "人均财政支出（户籍口径）", "expenditure per registered resident", "一般公共预算支出 / 户籍人口", "元/人"),
    ("gap_pc_res", "人均财政缺口（常住口径）", "fiscal gap per resident", "(支出 − 收入) / 2020 年常住人口", "元/人"),
    ("rev_pc_res", "人均本级收入（常住口径）", "own-source revenue per resident", "一般公共预算收入 / 2020 年常住人口", "元/人"),
    ("tax_share", "税收收入占比", "tax share of own revenue", "税收收入 / 一般公共预算收入", "比值"),
    ("land_dep", "土地出让依赖度", "land-conveyance dependence", "国有土地使用权出让收入 / 一般公共预算收入（仅市辖区单元，可选）", "比值"),
    ("fss_2010", "财政自给率（2010 期）", "fiscal self-sufficiency, 2009–2011", "2009–2011 年均收入 / 年均支出", "比值"),
    # 人口
    ("pop_chg_1020", "常住人口对数变化 2010–2020", "log change of resident population",
     "ln(P2020 / P2010)，普查常住人口；任一期人口为 0 或缺失时不计算", "对数差"),
    ("pop_chg_0010", "常住人口对数变化 2000–2010", "log change of resident population", "ln(P2010 / P2000)", "对数差"),
    ("res_hukou_ratio", "常住/户籍人口比", "resident-to-registered ratio", "2020 常住人口 / 户籍人口；<1 表示人口净流出", "比值"),
    ("urb_rate_2020", "城镇化率 2020", "urbanization rate", "城镇人口 / 常住人口", "比值"),
    ("share_hukou_elsewhere", "人户分离人口比例 2020", "share of residents registered elsewhere",
     "七普表3“户口登记地在外乡镇街道的人口” / 常住人口；含县内跨乡镇迁移，只作流动强度的近似", "比值"),
    # 遥感：中心建成区（县城 / 中心城区，2020 年边界）
    ("core_area_km2", "中心建成区面积", "core built-up area", "GHSL 2020 建成栅格最大连通斑块（或含驻地斑块）面积", "km²"),
    ("core_pop", "中心建成区人口（普查重标定）", "core population, census-rescaled",
     "GHS-POP 2020 中心建成区求和 × (2020 普查常住人口 / GHS-POP 单元求和)；普查缺失时用未重标定值", "人"),
    ("builtup_pc_core", "人均建成面积（中心建成区）", "built-up surface per capita", "GHSL 建成面积 / 中心建成区人口", "m²/人"),
    ("tree_share_core", "树木覆盖占比（中心建成区，主口径）", "tree cover share",
     "WorldCover 树木面积 / 各地类面积之和；WorldCover 草地类精度低，故以树木为主口径", "比值"),
    ("tree_pc_core", "人均树木覆盖面积（主口径）", "tree cover per capita", "WorldCover 树木面积 / 中心建成区人口", "m²/人"),
    ("green_share_core", "绿地占比（树木+灌木+草地，稳健性口径）", "green share", "WorldCover 树木+灌木+草地面积 / 各地类面积之和", "比值"),
    ("green_pc_core", "人均绿地面积（稳健性口径）", "green space per capita", "WorldCover 树木+灌木+草地面积 / 中心建成区人口", "m²/人"),
    ("expo_tree_core", "人口加权树木暴露（主口径）", "population-weighted tree-cover exposure",
     "Σ(格网人口 × 格网周围 500 m 树木覆盖比例) / Σ格网人口（Chen et al. 2022）", "比值"),
    ("expo_green_core", "人口加权绿地暴露（稳健性口径）", "population-weighted greenspace exposure",
     "同上，绿地 = 树木+灌木+草地", "比值"),
    ("ndvi_core", "中心建成区 NDVI", "mean NDVI (Sentinel-2)", "2020 年 5–9 月 Sentinel-2 中值合成 NDVI 均值", "无量纲"),
    ("ndvi_ring", "自然植被本底", "background NDVI (MODIS, 5 km ring)", "中心建成区外 5 km 环带非建成栅格 MODIS NDVI 均值", "无量纲"),
    ("ndvi_gap", "城区相对本底的绿度差", "core-minus-background NDVI", "ndvi_core − ndvi_ring", "无量纲"),
    ("greenpatch_pc_core", "人均连片绿地（公园代理）", "park proxy per capita",
     "中心建成区内面积 ≥ 1 公顷的连片绿地（WorldCover 树木+灌木+草地）面积 / 中心建成区人口", "m²/人"),
    ("greenpatch_access_share", "连片绿地 500 m 可达人口比例（公园可达代理）", "share of population within 500 m of a ≥1 ha green patch",
     "斑块 500 m 范围内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口", "比值"),
    ("riparian_green_pc", "人均滨水绿带（绿道代理）", "riparian green per capita",
     "水体（JRC 出现频率 ≥ 50%）外扩 50 m 内的绿地面积 / 中心建成区人口", "m²/人"),
    ("roadside_green_pc", "人均道路两侧绿带（绿道代理）", "roadside green per capita",
     "GHSL 2018 道路面外扩 20 m 内的绿地面积 / 中心建成区人口", "m²/人"),
    ("openveg_share_2018", "聚落内植被开放空间占比（2018）", "vegetated open space share (GHS-BUILT-C)",
     "GHSL 2018 聚落特征 1–3 类面积 / 各地类面积之和", "比值"),
    ("road_share_2018", "道路面占比（2018）", "road surface share (GHS-BUILT-C)", "GHSL 2018 聚落特征 5 类面积 / 各地类面积之和", "比值"),
    ("park_pc_core", "人均公园面积（可选）", "park area per capita", "公园多边形面积 / 中心建成区人口（需提供公园数据）", "m²/人"),
    ("park_access_share", "公园步行可达人口比例（可选）", "share of population within walking distance of a park",
     "公园 500 m 缓冲区内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口", "比值"),
    ("floor_res_pc_core", "人均住宅建筑面积（遥感估算）", "residential floor area per capita (GHSL volume)",
     "(总建筑体量 − 非住宅体量) / 层高 / 中心建成区人口", "m²/人"),
    ("floor_res_pc_unit", "人均住宅建筑面积（单元，遥感估算）", "residential floor area per resident",
     "单元内 (总体量 − 非住宅体量) / 层高 / 2020 常住人口", "m²/人"),
    ("ntl_per_built", "单位建成面积夜间灯光", "night-light radiance per km² built-up",
     "VIIRS 2020 average_masked 求和 / 中心建成区建成面积（km²）；越低表示建成空间利用强度越低", "nW/cm²/sr per km²"),
    ("ntl_per_volume", "单位建筑体量夜间灯光", "night-light radiance per building volume",
     "中心建成区 VIIRS 2020 求和 / 建筑体量（百万 m³）；识别“高供给、低活力”", "nW/cm²/sr per 10⁶ m³"),
    ("ntl_pc", "人均夜间灯光", "night-light radiance per resident", "单元 VIIRS 2020 求和 / 2020 常住人口", "nW/cm²/sr per 人"),
    ("core_growth_1020", "中心建成区面积对数变化", "log change of core area", "ln(2020 动态核心面积 / 2010 动态核心面积)", "对数差"),
    ("lcrpgr", "土地消耗率/人口增长率之比 (SDG 11.3.1)", "land consumption rate to population growth rate ratio",
     "ln(A2020/A2010) / ln(P2020/P2010)，P 为单元常住人口；人口变化接近 0 时不计算", "比值"),
    ("land_pop_diverge", "扩张—收缩背离", "built-up expansion under population decline",
     "中心建成区面积增长且常住人口下降 = 1", "0/1"),
    ("green_official_ratio", "官方/遥感人均绿地比（可选）", "official-to-remote-sensing green ratio",
     "住建部人均公园绿地面积 / 遥感人均绿地面积", "比值"),
    # 分组
    ("city_size_class", "城市规模等级", "city size class (State Council 2014)", "按城区常住人口（万人）套用国发〔2014〕51号标准；超大特大按七普名单", "类别"),
    ("group5", "五类分组", "five-group typology",
     "超大特大城市市辖区 / 大城市市辖区 / 中小城市市辖区 / 县级市 / 县；另有 外围市辖区，以及城区人口缺失、无法分级的 市辖区（规模未知）", "类别"),
    ("quadrant", "财政—人口四象限", "fiscal–demographic quadrant", "财政自给率是否 ≥ 阈值 × 常住人口是否增长", "类别"),
]


def export_codebook(path: Path):
    cb = pd.DataFrame(CODEBOOK, columns=["var", "name_zh", "name_en", "formula", "unit"])
    atomic_write_csv(cb, path)
    return cb


def norm_pref(c):
    """地级代码规范化：直辖市常写作 110100（“北京市市辖区”）或 110000，统一为分析单元使用的 110000。"""
    return pref_code(c) if isinstance(c, str) else None


def safe_div(a, b):
    a = pd.to_numeric(a, errors="coerce")
    b = pd.to_numeric(b, errors="coerce")
    return a / b.where(b != 0)


def safe_log(x):
    """取自然对数；0、负数与缺失返回缺失（避免 ln(0) = -inf 进入后续统计与回归）。"""
    x = pd.to_numeric(x, errors="coerce")
    return np.log(x.where(x > 0))


def col(df, name):
    """取列；不存在时返回全缺失序列（可选数据未提供时不报错）。"""
    return df[name] if name in df else pd.Series(np.nan, index=df.index)


# ===========================================================================
# 代码块 2：城市规模与五类分组
# 目的：市辖区单元按城区常住人口套用 2014 年标准分级；超大、特大城市以官方七普名单为准（外部参数/megacities_2020.csv）；
#       县级市、县各自成组；district_outer（如重庆主城区以外的市辖区）单列；
#       城区人口缺失、又不在七普名单中的市辖区单元无法分级，标为“市辖区（规模未知）”，不默认归入中小城市。
# 结果：新增 city_size_class、group5 两列。
# ===========================================================================
def assign_groups(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    a = cfg["analysis"]
    std = read_table(resolve(a["city_size_file"]))
    std["min_urban_pop_10k"] = pd.to_numeric(std["min_urban_pop_10k"])
    std = std.sort_values("min_urban_pop_10k", ascending=False)

    def size_class(pop10k):
        if pd.isna(pop10k):
            return np.nan
        for _, r in std.iterrows():
            if pop10k >= r["min_urban_pop_10k"]:
                return r["class_zh"]
        return np.nan

    df["city_size_class"] = np.where(df["unit_type"] == "city_proper",
                                     col(df, "urban_pop_total_10k").map(size_class), np.nan)
    mc_path = resolve(a["megacity_file"])
    if mc_path.exists():
        mc = read_table(mc_path, code_cols=("pref_code",))
        mc["unit_id"] = "CP" + mc["pref_code"].map(norm_adcode).map(norm_pref)
        mc = mc.dropna(subset=["unit_id"]).drop_duplicates("unit_id")   # 名单中重复的城市只取一行，避免合并后行数增加
        df = df.merge(mc[["unit_id", "class_zh"]].rename(columns={"class_zh": "mega_class"}), on="unit_id", how="left")
        df["city_size_class"] = df["mega_class"].fillna(df["city_size_class"])
        # 名单外但城区人口达到特大标准的城市（与名单口径不一致），降为 Ⅰ型大城市并记录
        wrong = df["unit_type"].eq("city_proper") & df["mega_class"].isna() & df["city_size_class"].isin(["超大城市", "特大城市"])
        if wrong.any():
            LOG.warning(f"{int(wrong.sum())} 个城市的城区人口达到特大标准但不在七普名单中，按 Ⅰ型大城市处理：{df.loc[wrong, 'unit_id'].tolist()}")
            df.loc[wrong, "city_size_class"] = "Ⅰ型大城市"
        df = df.drop(columns="mega_class")

    g = pd.Series("县", index=df.index)
    g[df["unit_type"] == "county_city"] = "县级市"
    g[df["unit_type"] == "district_outer"] = "外围市辖区"
    cp = df["unit_type"] == "city_proper"
    g[cp] = "中小城市市辖区"
    unknown = cp & df["city_size_class"].isna()
    if unknown.any():
        LOG.warning(f"{int(unknown.sum())} 个市辖区单元缺少城区人口、无法分级，group5 标为“市辖区（规模未知）”，"
                    f"不进入五类比较与回归：{df.loc[unknown, 'unit_id'].tolist()[:20]}")
    g[unknown] = "市辖区（规模未知）"
    g[cp & df["city_size_class"].isin(["Ⅰ型大城市", "Ⅱ型大城市"])] = "大城市市辖区"
    g[cp & df["city_size_class"].isin(["超大城市", "特大城市"])] = "超大特大城市市辖区"
    df["group5"] = g
    return df


# ===========================================================================
# 代码块 3：计算全部指标
# 目的：按 CODEBOOK 的公式逐项计算；分母为 0 或缺失时结果为缺失；中心建成区人口过小的单元不计算人均指标。
# 结果：df 新增全部指标列。
# ===========================================================================
def compute(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    df = df.copy()   # 合并后的表由许多小块组成，先整理成连续内存，避免逐列新增指标时出现 PerformanceWarning
    a = cfg["analysis"]
    storey = float(a["storey_height_m"])
    rev, exp = col(df, "gen_budget_revenue_main"), col(df, "gen_budget_expenditure_main")
    p20, p10, p00 = col(df, "pop_resident_2020"), col(df, "pop_resident_2010"), col(df, "pop_resident_2000")
    hukou = col(df, "pop_hukou_yearend_main").fillna(col(df, "pop_hukou_2020"))

    df["fss"] = safe_div(rev, exp)
    df["gap_ratio"] = safe_div(exp - rev, exp)
    df["exp_pc_res"] = safe_div(exp, p20)
    df["exp_pc_hukou"] = safe_div(exp, hukou)
    df["gap_pc_res"] = safe_div(exp - rev, p20)
    df["rev_pc_res"] = safe_div(rev, p20)
    df["tax_share"] = safe_div(col(df, "tax_revenue_main"), rev)
    df["land_dep"] = safe_div(col(df, "land_conveyance_revenue_main"), rev)
    df["fss_2010"] = safe_div(col(df, "gen_budget_revenue_y2010"), col(df, "gen_budget_expenditure_y2010"))

    df["pop_chg_1020"] = safe_log(safe_div(p20, p10))
    df["pop_chg_0010"] = safe_log(safe_div(p10, p00))
    df["res_hukou_ratio"] = safe_div(p20, hukou)
    df["urb_rate_2020"] = safe_div(col(df, "pop_urban_2020"), p20)
    df["share_hukou_elsewhere"] = safe_div(col(df, "pop_hukou_elsewhere_2020"), p20)

    df["core_area_km2"] = col(df, "core_area_m2") / 1e6
    # 自上而下重标定：按普查常住人口 / GHS-POP 单元总量的比值调整中心建成区人口
    raw_core = col(df, "c_pop_ghs_2020")
    scale = safe_div(p20, col(df, "u_pop_ghs_2020"))
    core_pop = (raw_core * scale).fillna(raw_core)
    core_pop = core_pop.where(core_pop >= float(a["min_core_pop"]))
    df["core_pop"] = core_pop
    df["builtup_pc_core"] = safe_div(col(df, "c_bs_2020"), core_pop)
    green = col(df, "c_wc_tree_m2").fillna(0) + col(df, "c_wc_shrub_m2").fillna(0) + col(df, "c_wc_grass_m2").fillna(0)
    wc_cols = [c for c in df.columns if c.startswith("c_wc_") and c.endswith("_m2")]
    wc_total = df[wc_cols].sum(axis=1, min_count=1) if wc_cols else pd.Series(np.nan, index=df.index)
    green = green.where(wc_total.notna())
    tree = col(df, "c_wc_tree_m2").where(wc_total.notna())
    df["tree_share_core"] = safe_div(tree, wc_total)
    df["tree_pc_core"] = safe_div(tree, core_pop)
    df["expo_tree_core"] = safe_div(col(df, "c_pw_tree_2020"), col(df, "c_pop_expo_2020"))
    df["expo_green_core"] = safe_div(col(df, "c_pw_green_2020"), col(df, "c_pop_expo_2020"))
    df["green_share_core"] = safe_div(green, wc_total)
    df["green_pc_core"] = safe_div(green, core_pop)
    df["ndvi_core"] = col(df, "c_ndvi_s2_2020")
    df["ndvi_ring"] = col(df, "r_ndvi_modis_2020")
    df["ndvi_gap"] = df["ndvi_core"] - df["ndvi_ring"]
    df["greenpatch_pc_core"] = safe_div(col(df, "c_greenpatch_m2_2020"), core_pop)
    gp_pop = [c for c in df.columns if c.startswith("c_pop_greenpatch")]
    df["greenpatch_access_share"] = safe_div(df[gp_pop[0]], col(df, "c_pop_expo_2020")) if gp_pop else np.nan
    df["riparian_green_pc"] = safe_div(col(df, "c_riparian_green_m2_2020"), core_pop)
    df["roadside_green_pc"] = safe_div(col(df, "c_roadside_green_m2_2020"), core_pop)
    df["openveg_share_2018"] = safe_div(col(df, "c_openveg_m2_2018"), wc_total)
    df["road_share_2018"] = safe_div(col(df, "c_road_m2_2018"), wc_total)
    df["park_pc_core"] = safe_div(col(df, "c_park_m2_2020"), core_pop)
    park_pop = [c for c in df.columns if c.startswith("c_pop_park")]
    # 分子是未重标定的 GHS-POP，分母也必须用同一口径的 GHS-POP（与 greenpatch_access_share 一致），
    # 若用普查重标定后的 core_pop，比例会随重标定系数偏离，甚至大于 1
    df["park_access_share"] = safe_div(df[park_pop[0]], col(df, "c_pop_expo_2020")) if park_pop else np.nan
    df["floor_res_pc_core"] = safe_div((col(df, "c_bv_2020") - col(df, "c_bvn_2020")) / storey, core_pop)
    df["floor_res_pc_unit"] = safe_div((col(df, "u_bv_2020") - col(df, "u_bvn_2020")) / storey, p20)
    df["ntl_per_built"] = safe_div(col(df, "c_ntl_viirs_2020"), col(df, "c_bs_2020") / 1e6)
    df["ntl_per_volume"] = safe_div(col(df, "c_ntl_viirs_2020"), col(df, "c_bv_2020") / 1e6)
    df["ntl_pc"] = safe_div(col(df, "u_ntl_viirs_2020"), p20)

    a20, a10 = col(df, "core_area_m2"), col(df, "core2010_area_m2")
    df["core_growth_1020"] = safe_log(safe_div(a20, a10))
    pc = df["pop_chg_1020"]
    df["lcrpgr"] = safe_div(df["core_growth_1020"], pc.where(pc.abs() >= 0.01))
    df["land_pop_diverge"] = ((df["core_growth_1020"] > 0) & (pc < 0)).astype("Int64").where(
        df["core_growth_1020"].notna() & pc.notna())
    df["green_official_ratio"] = safe_div(col(df, "park_green_pc_m2"), df["green_pc_core"])

    cut = float(a["self_sufficiency_cut"])
    fs = np.where(df["fss"] >= cut, "财政自给", "转移依赖")
    pg = np.where(pc >= 0, "人口增长", "人口收缩")
    q = pd.Series([f"{x}-{y}" for x, y in zip(fs, pg)], index=df.index)
    df["quadrant"] = q.where(df["fss"].notna() & pc.notna())
    return df


# ===========================================================================
# 代码块 4：读取与合并
# 目的：以分析单元表为底，依次左连接遥感、财政普查、城区人口、住建部绿地数据；缺失的可选数据自动跳过。
# 结果：返回合并后的 DataFrame。
# ===========================================================================
def load_all(cfg) -> pd.DataFrame:
    ud = resolve(cfg["units"]["out_dir"])
    units = read_table(ud / "units_table.csv", code_cols=("unit_id", "prov_code", "pref_code"))
    df = units.copy()
    gee_path = resolve(cfg["gee"]["out_dir"]) / "gee_unit_metrics.csv"
    if gee_path.exists():
        gee = read_table(gee_path, code_cols=("unit_id",))
        gee = gee.drop(columns=[c for c in ("unit_type", "prov_code", "pref_code") if c in gee])
        df = df.merge(gee, on="unit_id", how="left")
    else:
        LOG.warning("未找到 gee_unit_metrics.csv，遥感指标将为缺失。")
    fc_path = resolve(cfg["fiscal_census"]["out_dir"]) / "unit_fiscal_census.csv"
    if fc_path.exists():
        fc = read_table(fc_path, code_cols=("unit_id", "prov_code", "pref_code"))
        fc = fc.drop(columns=[c for c in ("unit_type", "prov_code", "pref_code") if c in fc])
        df = df.merge(fc, on="unit_id", how="left")
    else:
        LOG.warning("未找到 unit_fiscal_census.csv，财政与普查指标将为缺失。")

    up = resolve(cfg["fiscal_census"]["city_urban_pop_file"])
    if up.exists():
        u = read_table(up, code_cols=("pref_code",))
        u["unit_id"] = "CP" + u["pref_code"].map(norm_adcode).map(norm_pref)
        u["urban_pop_total_10k"] = pd.to_numeric(u["urban_pop_10k"], errors="coerce") + \
            pd.to_numeric(col(u, "urban_temp_pop_10k"), errors="coerce").fillna(0)
        df = df.merge(u[["unit_id", "urban_pop_total_10k"]].drop_duplicates("unit_id"), on="unit_id", how="left")
    mp = resolve(cfg["fiscal_census"]["mohurd_file"])
    if mp.exists():
        m = read_table(mp, code_cols=("code",))
        m["code"] = m["code"].map(norm_adcode)
        is_cp = m["level"].astype(str).str.contains("城市") & m["code"].str[4:].eq("00").fillna(False).astype(bool)
        m["unit_id"] = np.where(is_cp, "CP" + m["code"].map(norm_pref), m["code"])
        keep = ["unit_id", "park_green_pc_m2", "green_ratio_builtup_pct", "green_cover_builtup_pct", "built_area_km2"]
        m = m[[c for c in keep if c in m]].drop_duplicates("unit_id")
        for c in m.columns[1:]:
            m[c] = pd.to_numeric(m[c], errors="coerce")
        df = df.merge(m.rename(columns={"built_area_km2": "mohurd_built_area_km2"}), on="unit_id", how="left")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codebook-only", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    out_dir = resolve(cfg["analysis"]["out_dir"])
    export_codebook(out_dir / "codebook_indicators.csv")
    if args.codebook_only:
        LOG.info("已导出指标说明表。")
        return
    df = load_all(cfg)
    df = assign_groups(df, cfg)
    df = compute(df, cfg)
    atomic_write_csv(df, out_dir / "unit_indicators.csv")
    LOG.info("分组计数：\n" + df["group5"].value_counts().to_string())
    LOG.info(f"完成：{len(df)} 个单元 → {out_dir / 'unit_indicators.csv'}")


if __name__ == "__main__":
    main()
