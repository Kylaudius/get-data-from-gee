# -*- coding: utf-8 -*-
"""
04_describe_and_map.py  分组描述统计、四象限交叉表、分母分解表与全国地图

在哪里运行：Mac “终端 Terminal”
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python 04_describe_and_map.py

输入：数据/结果/unit_indicators.csv（03 输出）；数据/中间/units/units_full.gpkg（00 输出，用于制图）。
输出（表格写到 数据/结果/，图写到 analysis.fig_out_dir，默认 数据/结果/图表/）：
    table1_group_summary.csv / .md              五类分组的描述统计（中位数与人口加权均值）
    table2_quadrant_by_group.csv / .md          财政与人口四象限 × 五类分组
    table3_denominator_decomposition.csv / .md  中心人口、人口变化、建成面积变化与反事实分母的分组比较
    table4_quadrant_town.csv / .md              单元与中心建成区人口变化四象限 × 五类分组
    图2_财政人口双变量地图.png / .pdf            人均净流入 × 人口变化 双变量地图
    图3_五类分组散点.png / .pdf                  人均净流入与中心建成区人均树木覆盖
    图4_五类分组绿地箱线图.png / .pdf            四项绿地指标的分组分布
    图5_人均建成面积与人口变化.png / .pdf        固定中心建成区内建成面积变化与人口变化
    图S1_中心建成区质控.png / .pdf               建成栅格比例、与住建部建成区之比、官方与遥感人口之比
说明：excluded 单元（默认兵团城市 6590xx）不进入表格与散点、箱线图，地图中以浅灰色显示。
      研究者从 数据/结果/图表/ 挑选满意的图，再手动复制到 图表/（报告引用的位置）。图1 概念框架不由脚本生成。
      公开发表的中国地图须使用自然资源部标准地图服务的底图并取得审图号（见 附录B），本脚本的地图仅供研究内部使用。
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import atomic_write_csv, atomic_write_text, get_logger, load_config, read_table, resolve  # noqa: E402

LOG = get_logger("04_describe_and_map")
GROUP_ORDER = ["超大特大城市市辖区", "大城市市辖区", "中小城市市辖区", "县级市", "县", "外围市辖区", "市辖区（规模未知）"]
GROUP_COLORS = {"超大特大城市市辖区": "#b2182b", "大城市市辖区": "#ef8a62", "中小城市市辖区": "#fddbc7",
                "县级市": "#67a9cf", "县": "#2166ac", "外围市辖区": "#999999", "市辖区（规模未知）": "#cccccc"}


# ===========================================================================
# 代码块 1：中文字体
# 目的：matplotlib 默认字体不含中文，依次尝试 Mac 自带的苹方、黑体等，避免图中中文显示为方块。
# 结果：设置全局字体；终端打印实际使用的字体名。
# ===========================================================================
def set_cjk_font():
    wanted = ["PingFang SC", "Heiti SC", "Songti SC", "Arial Unicode MS", "Noto Sans CJK SC",
              "Source Han Sans SC", "WenQuanYi Zen Hei", "SimHei", "Microsoft YaHei"]
    have = {f.name for f in font_manager.fontManager.ttflist}
    for w in wanted:
        if w in have:
            plt.rcParams["font.sans-serif"] = [w]
            plt.rcParams["axes.unicode_minus"] = False
            LOG.info(f"图表字体：{w}")
            return
    LOG.warning("没有找到中文字体，图中中文可能显示为方块。")


def groups_in(df):
    return [x for x in GROUP_ORDER if x in set(df["group5"])]


def drop_excluded(df: pd.DataFrame) -> pd.DataFrame:
    if "excluded" not in df:
        return df
    ex = df["excluded"].astype("string").str.lower().isin(["1", "true"]).fillna(False).astype(bool)
    if ex.any():
        LOG.info(f"表格与散点图剔除 excluded 单元 {int(ex.sum())} 个：{df.loc[ex, 'unit_id'].tolist()[:10]}")
    return df[~ex].copy()


# ===========================================================================
# 代码块 2：表 1 五类分组描述统计
# 目的：比较超大特大城市、大城市、中小城市市辖区与县级市、县在财政、人口、住房、土地债务、
#       绿地、建设强度、社会基础设施和住建部统计上的差异。
#       每个指标给出中位数（不受极端值影响）与常住人口加权均值（反映“人”的平均处境）。
# 结果：table1_group_summary.csv 与 .md。
# ===========================================================================
TABLE1_VARS = [
    # 财政
    ("net_inflow_pc", "人均净流入(元,2010人口)"), ("own_rev_pc", "人均本级收入(元,2010人口)"),
    ("fss", "财政自给率(描述)"), ("exp_pc_res", "人均支出(常住,元)"), ("exp_pc_hukou", "人均支出(户籍,元)"),
    ("specific_share", "专项转移支付占比"), ("exp_personnel_share", "工资福利支出占比"),
    # 人口
    ("res_hukou_ratio", "常住/户籍"), ("pop_chg_1020", "人口对数变化10–20"), ("core_pop_chg_1020", "中心人口对数变化10–20"),
    # 住房
    ("share_rent_market", "市场租赁户比例"), ("share_commodity", "商品房户比例"), ("share_self_built", "自建房户比例"),
    ("housing_area_pc", "人均住房建筑面积(m²)"), ("collective_share", "集体户人口比例"), ("housing_slack_ratio", "住房余量比"),
    # 土地、债务与国家中心性
    ("land_conv_pc", "人均土地出让价款(元)"), ("land_dep", "土地出让依赖度"), ("lgfv_debt_pc", "人均城投有息债务(元)"),
    ("special_bond_pc", "人均新增专项债(元)"), ("devzone_share", "开发区核准面积比"), ("admin_rank", "行政等级"),
    # 绿地
    ("tree_pc_core", "人均树木覆盖(m²)"), ("tree_share_core", "树木覆盖占比"), ("expo_tree_core", "人口加权树木暴露"),
    ("tree_new_share", "新增树木占比"), ("greenpatch_pc_core", "人均大型树木斑块(m²)"),
    ("greenpatch_access_share", "大型树木斑块500m可达比例"), ("riparian_green_pc", "人均滨水线性绿地(m²)"),
    ("green_pc_core", "人均绿地(m²,稳健性)"), ("park_access_share", "公园可达比例"),
    # 建设与使用强度
    ("builtup_pc_core", "人均建成面积(m²)"), ("floor_res_pc_unit", "人均住宅面积估算(m²)"), ("ntl_per_built", "单位建成面积灯光"),
    # 社会基础设施
    ("beds_per_1k_res", "每千常住人口床位"), ("beds_per_1k_hukou", "每千户籍人口床位"),
    ("students_per_child", "在校生/0–14岁人口"), ("welfare_beds_per_1k_65", "每千名65岁以上老人养老床位"),
    ("teachers_per_100_students", "每百名学生专任教师"),
    # 住建部城市与县城建设统计
    ("park_area_pc_mohurd", "人均公园面积(住建部,m²)"), ("road_area_pc_mohurd", "人均道路面积(住建部,m²)"),
    ("park_green_pc_m2", "人均公园绿地(住建部报告值,m²)"), ("muni_invest_pc", "人均市政设施投资(元)"),
    ("muni_invest_green_pc", "人均园林绿化投资(元)"), ("fund_fiscal_share", "财政拨款占比"), ("fund_debt_share", "债券与贷款占比"),
    ("maint_subsidy_share", "维护资金上级补助占比"),
]


def wmean(x, w):
    x = pd.to_numeric(x, errors="coerce")
    w = pd.to_numeric(w, errors="coerce")
    m = x.notna() & w.notna()
    return np.nan if w[m].sum() == 0 else float(np.average(x[m], weights=w[m]))


def group_stats(df: pd.DataFrame, variables: list) -> list:
    """每组每个变量的中位数与常住人口加权均值。"""
    rows = []
    for g in groups_in(df):
        d = df[df["group5"] == g]
        r = {"分组": g, "单元数": len(d)}
        for v, name in variables:
            if v in d and pd.to_numeric(d[v], errors="coerce").notna().any():
                x = pd.to_numeric(d[v], errors="coerce")
                r[f"{name}·中位数"] = round(x.median(), 3)
                if "pop_resident_2020" in d:
                    r[f"{name}·人口加权均值"] = round(wmean(x, d["pop_resident_2020"]), 3)
        rows.append(r)
    return rows


def table1(df: pd.DataFrame) -> pd.DataFrame:
    total_pop = df["pop_resident_2020"].sum() if "pop_resident_2020" in df else np.nan
    out = []
    for r in group_stats(df, TABLE1_VARS):
        d = df[df["group5"] == r["分组"]]
        extra = {}
        if "pop_resident_2020" in d:
            extra["常住人口(万人)"] = round(d["pop_resident_2020"].sum() / 1e4, 1)
            extra["人口占比"] = round(d["pop_resident_2020"].sum() / total_pop, 3) if total_pop else np.nan
            # 只在人口变化非缺失的单元中计算比例（缺失单元不能算作“未收缩”）
            pc = d["pop_chg_1020"].dropna() if "pop_chg_1020" in d else pd.Series(dtype=float)
            extra["人口收缩单元比例"] = round((pc < 0).mean(), 3) if len(pc) else np.nan
        if "land_pop_diverge" in d:
            extra["扩张与收缩背离比例"] = round(pd.to_numeric(d["land_pop_diverge"], errors="coerce").mean(), 3)
        if "core_fallback" in d:
            extra["中心建成区退化为几何中心缓冲的单元数"] = int(pd.to_numeric(d["core_fallback"], errors="coerce").fillna(0).sum())
        # 把规模与人口放在指标前面
        items = list(r.items())
        out.append(dict(items[:2] + list(extra.items()) + items[2:]))
    return pd.DataFrame(out)


def to_md(df: pd.DataFrame) -> str:
    """把 DataFrame 转成 Markdown 表格（不依赖 tabulate 包）。"""
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]

    def fmt(v):
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)) and float(v).is_integer():
            return str(int(v))
        return str(v)

    for _, r in df.iterrows():
        lines.append("| " + " | ".join(fmt(v) for v in r.values) + " |")
    return "\n".join(lines) + "\n"


def write_table(df: pd.DataFrame, out_dir: Path, stem: str, transpose: bool = False):
    atomic_write_csv(df, out_dir / f"{stem}.csv")
    md = df.set_index(df.columns[0]).T.reset_index().rename(columns={"index": "指标"}) if transpose else df
    atomic_write_text(out_dir / f"{stem}.md", to_md(md))


def crosstab_with_pop(df: pd.DataFrame, row: str) -> pd.DataFrame | None:
    """某分类变量 × 五类分组：单元数与常住人口（万人）。"""
    d = df.dropna(subset=[row])
    if not len(d):
        return None
    cols = groups_in(d)
    n = pd.crosstab(d[row], d["group5"]).reindex(columns=cols)
    p = (d.pivot_table(index=row, columns="group5", values="pop_resident_2020", aggfunc="sum") / 1e4).round(1) \
        .reindex(columns=cols)
    t = pd.concat({"单元数": n, "常住人口(万人)": p}, axis=1).reset_index()
    t.columns = [" ".join(map(str, c)).strip() if isinstance(c, tuple) else c for c in t.columns]
    return t


# ===========================================================================
# 代码块 3：表 3 分母分解
# 目的：检验 H3。比较各组的中心建成区人口、单元与中心的人口变化、固定中心建成区内的建成面积变化，
#       以及人均树木覆盖在实际分母与 2010 年反事实分母下的差别（分母效应）。
# 结果：table3_denominator_decomposition.csv 与 .md。
# ===========================================================================
TABLE3_VARS = [("core_pop", "中心建成区人口"), ("pop_chg_1020", "单元人口对数变化"),
               ("core_pop_chg_1020", "中心人口对数变化"), ("dlnS_builtup_1020", "建成面积对数变化(dlnS)"),
               ("dlnP_core_1020", "中心人口对数变化(dlnP)"), ("tree_pc_core", "人均树木覆盖(实际分母)"),
               ("tree_pc_core_cf2010", "人均树木覆盖(反事实分母)"), ("denom_effect_core", "分母效应")]


# ===========================================================================
# 代码块 4：图（双变量地图、散点、箱线图、质控）
# 目的：图2 用 3×3 配色同时显示人均净流入与 2010–2020 常住人口变化的三分位，呈现“高净流入与人口收缩”
#       和“低净流入与人口增长”的空间分布；图3 至图5 与图S1 分组比较绿地、建成强度与中心建成区质量。
#       数据不足时跳过该图并在终端说明原因，不影响其他图。
# 结果：analysis.fig_out_dir 下的 PNG 与 PDF。
# ===========================================================================
BIVAR = {  # 行：人均净流入三分位（低→高）；列：人口变化三分位（收缩→增长）
    (0, 0): "#e8e8e8", (0, 1): "#ace4e4", (0, 2): "#5ac8c8",
    (1, 0): "#dfb0d6", (1, 1): "#a5add3", (1, 2): "#5698b9",
    (2, 0): "#be64ac", (2, 1): "#8c62aa", (2, 2): "#3b4994",
}


def fig_map(df_all, gdf, fig_dir):
    keep = ["unit_id", "net_inflow_pc", "pop_chg_1020", "excluded"]
    d = gdf.merge(df_all[[c for c in keep if c in df_all]], on="unit_id", how="left")
    ex = d["excluded"].astype("string").str.lower().isin(["1", "true"]).fillna(False).astype(bool) \
        if "excluded" in d else pd.Series(False, index=d.index)
    if "net_inflow_pc" not in d or "pop_chg_1020" not in d:
        LOG.warning("缺少人均净流入或人口变化列，跳过图2。")
        return
    ok = d["net_inflow_pc"].notna() & d["pop_chg_1020"].notna() & ~ex
    if ok.sum() < 3:   # 财政或普查数据尚未准备好时，三分位无法计算，跳过本图而不是让整个脚本报错
        LOG.warning(f"人均净流入与人口变化同时非缺失的单元只有 {int(ok.sum())} 个，跳过图2。")
        return
    d["gq"] = pd.qcut(d.loc[ok, "net_inflow_pc"].rank(method="first"), 3, labels=False)
    d["pq"] = pd.qcut(d.loc[ok, "pop_chg_1020"].rank(method="first"), 3, labels=False)
    d["color"] = [BIVAR.get((int(a), int(b)), "#ffffff") if pd.notna(a) and pd.notna(b) else "#ffffff"
                  for a, b in zip(d["gq"], d["pq"])]
    d.loc[ex, "color"] = "#dddddd"
    fig, ax = plt.subplots(figsize=(10, 8))
    d.to_crs("+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84").plot(
        ax=ax, color=d["color"], edgecolor="#bbbbbb", linewidth=0.05)
    ax.set_axis_off()
    ax.set_title("人均净流入（2010 年人口为分母）× 2010–2020 常住人口变化", fontsize=13)
    if ex.any():
        ax.text(0.02, 0.02, "浅灰：不参与分析的单元（excluded）", transform=ax.transAxes, fontsize=8, color="#666666")
    lg = fig.add_axes([0.12, 0.12, 0.16, 0.16])
    for (i, j), c in BIVAR.items():
        lg.add_patch(plt.Rectangle((j, i), 1, 1, color=c))
    lg.set_xlim(0, 3)
    lg.set_ylim(0, 3)
    lg.set_xticks([0.5, 2.5], ["收缩", "增长"], fontsize=8)
    lg.set_yticks([0.5, 2.5], ["低净流入", "高净流入"], fontsize=8)
    lg.set_xlabel("人口变化 →", fontsize=8)
    lg.set_ylabel("人均净流入 →", fontsize=8)
    for s in lg.spines.values():
        s.set_visible(False)
    save(fig, fig_dir / "图2_财政人口双变量地图")


def fig_scatter(df, fig_dir):
    if not {"tree_pc_core", "net_inflow_pc_k", "pop_resident_2020"} <= set(df.columns):
        LOG.warning("缺少人均树木覆盖、人均净流入或 2020 常住人口列，跳过图3。")
        return
    d = df[df["tree_pc_core"].gt(0) & df["net_inflow_pc_k"].notna()]
    if d.empty:   # 遥感或财政数据尚未准备好
        LOG.warning("人均树木覆盖与人均净流入同时非缺失的单元为 0 个，跳过图3。")
        return
    fig, ax = plt.subplots(figsize=(8, 6))
    pmax = d["pop_resident_2020"].max()
    pmax = pmax if pd.notna(pmax) and pmax > 0 else 1.0   # 人口全缺失时点大小统一，而不是变成 NaN（不显示）
    for g in groups_in(d):
        s = d[d["group5"] == g]
        size = 5 + 60 * np.sqrt(s["pop_resident_2020"].fillna(0) / pmax)
        ax.scatter(s["net_inflow_pc_k"], s["tree_pc_core"], s=size, alpha=0.6, color=GROUP_COLORS[g], label=g, linewidths=0)
    ax.set_yscale("log")
    ax.set_xlabel("人均净流入（千元，2010 年常住人口为分母）")
    ax.set_ylabel("中心建成区人均树木覆盖面积（m²，对数轴）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("人均净流入与县城、中心城区人均树木覆盖")
    save(fig, fig_dir / "图3_五类分组散点")


def boxplot_panels(df, panels, title, stem, fig_dir, fig_label):
    groups = groups_in(df)
    have = [(v, lab, lg) for v, lab, lg in panels if v in df and pd.to_numeric(df[v], errors="coerce").notna().sum() >= 3]
    if not have or not groups:
        LOG.warning(f"{fig_label} 所需指标全部缺失或不足 3 个单元，跳过{fig_label}。")
        return
    n = len(have)
    ncol = 2 if n > 1 else 1
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(6 * ncol, 3.8 * nrow), squeeze=False)
    for ax, (v, lab, logy) in zip(axes.flat, have):
        data = [pd.to_numeric(df.loc[df["group5"] == g, v], errors="coerce").dropna() for g in groups]
        data = [x[x > 0] if logy else x for x in data]
        pos = [i for i, x in enumerate(data) if len(x)]
        if not pos:
            ax.set_visible(False)
            continue
        bp = ax.boxplot([data[i] for i in pos], positions=pos, widths=0.6, patch_artist=True, showfliers=False)
        for b, i in zip(bp["boxes"], pos):
            b.set_facecolor(GROUP_COLORS[groups[i]])
            b.set_alpha(0.8)
        ax.set_xticks(range(len(groups)), groups, rotation=20, fontsize=8)
        ax.set_title(lab, fontsize=10)
        if logy:
            ax.set_yscale("log")
    for ax in list(axes.flat)[n:]:
        ax.set_visible(False)
    fig.suptitle(title)
    fig.tight_layout()
    save(fig, fig_dir / stem)


def fig_green_box(df, fig_dir):
    panels = [("tree_share_core", "树木覆盖占比", False), ("expo_tree_core", "人口加权树木暴露", False),
              ("greenpatch_access_share", "大型树木斑块 500 m 可达人口比例", False),
              ("tree_pc_core", "人均树木覆盖（m²，对数轴）", True)]
    boxplot_panels(df, panels, "中心建成区绿地指标的分组分布", "图4_五类分组绿地箱线图", fig_dir, "图4")


def fig_builtup_pop(df, fig_dir):
    need = {"dlnP_core_1020", "dlnS_builtup_1020"}
    if not need <= set(df.columns):
        LOG.warning("缺少中心人口变化或建成面积变化列，跳过图5。")
        return
    d = df.dropna(subset=list(need))
    if len(d) < 3:
        LOG.warning(f"中心人口变化与建成面积变化同时非缺失的单元只有 {len(d)} 个，跳过图5。")
        return
    fig, ax = plt.subplots(figsize=(7.5, 6))
    for g in groups_in(d):
        s = d[d["group5"] == g]
        ax.scatter(s["dlnP_core_1020"], s["dlnS_builtup_1020"], s=12, alpha=0.6, color=GROUP_COLORS[g], label=g, linewidths=0)
    lo = float(np.nanmin([d["dlnP_core_1020"].min(), d["dlnS_builtup_1020"].min()]))
    hi = float(np.nanmax([d["dlnP_core_1020"].max(), d["dlnS_builtup_1020"].max()]))
    ax.plot([lo, hi], [lo, hi], color="#666666", lw=0.8, ls="--")
    ax.axhline(0, color="#aaaaaa", lw=0.5)
    ax.axvline(0, color="#aaaaaa", lw=0.5)
    ax.set_xlabel("中心建成区人口对数变化 dlnP（2010–2020）")
    ax.set_ylabel("固定中心建成区内建成面积对数变化 dlnS")
    ax.text(0.02, 0.97, "虚线上方：人均建成面积上升", transform=ax.transAxes, fontsize=8, va="top", color="#444444")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("人均建成面积与人口变化")
    save(fig, fig_dir / "图5_人均建成面积与人口变化")


def fig_core_qc(df, fig_dir):
    panels = [("core_builtcell_share", "建成栅格占中心建成区比例", False),
              ("core_mohurd_ratio", "中心建成区面积 / 住建部建成区面积（对数轴）", True),
              ("core_pop_ratio_official_ghs", "官方中心人口 / GHS-POP 中心人口（对数轴）", True)]
    boxplot_panels(df, panels, "中心建成区质控", "图S1_中心建成区质控", fig_dir, "图S1")


def save(fig, stem: Path):
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_name(stem.name + ".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_name(stem.name + ".pdf"), bbox_inches="tight")
    plt.close(fig)
    LOG.info(f"已保存 {stem.name}.png / .pdf")


# ===========================================================================
# 代码块 5：主流程
# 目的：读取指标表 → 剔除 excluded 单元 → 表1 至表4 → 各图。
# 结果：见文件开头“输出”。
# ===========================================================================
def main():
    cfg = load_config()
    out_dir = resolve(cfg["analysis"]["out_dir"])
    fig_dir = resolve(cfg["analysis"].get("fig_out_dir", "数据/结果/图表"))
    set_cjk_font()
    df_all = read_table(out_dir / "unit_indicators.csv", code_cols=("unit_id", "prov_code", "pref_code"))
    df = drop_excluded(df_all)

    write_table(table1(df), out_dir, "table1_group_summary", transpose=True)
    t2 = crosstab_with_pop(df, "quadrant")
    if t2 is not None:
        write_table(t2, out_dir, "table2_quadrant_by_group")
    else:
        LOG.warning("财政与人口四象限全部缺失，跳过表2。")
    t3 = pd.DataFrame(group_stats(df, TABLE3_VARS))
    if len(t3.columns) > 2:
        write_table(t3, out_dir, "table3_denominator_decomposition", transpose=True)
    else:
        LOG.warning("分母分解所需指标全部缺失，跳过表3。")
    t4 = crosstab_with_pop(df, "quadrant_town") if "quadrant_town" in df else None
    if t4 is not None:
        write_table(t4, out_dir, "table4_quadrant_town")
    else:
        LOG.warning("单元与中心人口变化四象限全部缺失，跳过表4。")

    gpkg = resolve(cfg["units"]["out_dir"]) / "units_full.gpkg"
    if gpkg.exists():
        import geopandas as gpd
        fig_map(df_all, gpd.read_file(gpkg), fig_dir)
    else:
        LOG.warning("找不到 units_full.gpkg，跳过图2。")
    fig_scatter(df, fig_dir)
    fig_green_box(df, fig_dir)
    fig_builtup_pop(df, fig_dir)
    fig_core_qc(df, fig_dir)
    LOG.info(f"完成。图已写到 {fig_dir}，挑选后再复制到 图表/。")


if __name__ == "__main__":
    main()
