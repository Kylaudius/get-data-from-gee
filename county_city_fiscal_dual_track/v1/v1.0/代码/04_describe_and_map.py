# -*- coding: utf-8 -*-
"""
04_describe_and_map.py  分组描述统计、四象限交叉表与全国地图

在哪里运行：Mac “终端 Terminal”
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python 04_describe_and_map.py

输入：数据/结果/unit_indicators.csv（03 输出）；数据/中间/units/units_full.gpkg（00 输出，用于制图）。
输出：
    数据/结果/table1_group_summary.csv / .md     五类分组的描述统计（中位数与人口加权均值）
    数据/结果/table2_quadrant_by_group.csv / .md 财政—人口四象限 × 五类分组
    图表/fig1_bivariate_gap_popchange.png        人均财政缺口 × 人口变化 双变量地图
    图表/fig2_green_vs_fss.png                   人均树木覆盖 × 财政自给率 散点图
    图表/fig3_exp_pc_denominators.png            常住与户籍两种口径的人均支出对比
    图表/fig4_land_pop_diverge.png               建成区扩张—人口收缩背离的比例
注意：公开发表的中国地图须使用自然资源部标准地图服务的底图并取得审图号（见 附录B），本脚本的地图仅供研究内部使用。
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


# ===========================================================================
# 代码块 2：表 1 五类分组描述统计
# 目的：比较超大特大城市、大城市、中小城市市辖区与县级市、县在财政、人口和遥感指标上的差异。
#       每个指标给出中位数（不受极端值影响）与常住人口加权均值（反映“人”的平均处境）。
# 结果：table1_group_summary.csv 与 .md。
# ===========================================================================
TABLE1_VARS = [("fss", "财政自给率"), ("exp_pc_res", "人均支出(常住,元)"), ("gap_pc_res", "人均缺口(常住,元)"),
               ("res_hukou_ratio", "常住/户籍"), ("pop_chg_1020", "人口对数变化10–20"),
               ("tree_pc_core", "人均树木覆盖(m²)"), ("expo_tree_core", "人口加权树木暴露"),
               ("greenpatch_pc_core", "人均连片绿地(公园代理,m²)"), ("greenpatch_access_share", "连片绿地500m可达比例"),
               ("riparian_green_pc", "人均滨水绿带(绿道代理,m²)"), ("green_pc_core", "人均绿地(m²,稳健性)"),
               ("builtup_pc_core", "人均建成面积(m²)"), ("floor_res_pc_unit", "人均住宅面积估算(m²)"),
               ("ntl_per_built", "单位建成面积灯光"), ("park_access_share", "公园可达比例")]


def wmean(x, w):
    m = x.notna() & w.notna()
    return np.nan if w[m].sum() == 0 else float(np.average(x[m], weights=w[m]))


def table1(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total_pop = df["pop_resident_2020"].sum() if "pop_resident_2020" in df else np.nan
    for g in [x for x in GROUP_ORDER if x in set(df["group5"])]:
        d = df[df["group5"] == g]
        r = {"分组": g, "单元数": len(d)}
        if "pop_resident_2020" in d:
            r["常住人口(万人)"] = round(d["pop_resident_2020"].sum() / 1e4, 1)
            r["人口占比"] = round(d["pop_resident_2020"].sum() / total_pop, 3) if total_pop else np.nan
            # 只在人口变化非缺失的单元中计算比例（缺失单元不能算作“未收缩”）
            pc = d["pop_chg_1020"].dropna() if "pop_chg_1020" in d else pd.Series(dtype=float)
            r["人口收缩单元比例"] = round((pc < 0).mean(), 3) if len(pc) else np.nan
        for v, name in TABLE1_VARS:
            if v in d and d[v].notna().any():
                r[f"{name}·中位数"] = round(d[v].median(), 3)
                if "pop_resident_2020" in d:
                    r[f"{name}·人口加权均值"] = round(wmean(d[v], d["pop_resident_2020"]), 3)
        if "land_pop_diverge" in d:
            r["扩张—收缩背离比例"] = round(d["land_pop_diverge"].astype(float).mean(), 3)
        rows.append(r)
    return pd.DataFrame(rows)


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


# ===========================================================================
# 代码块 3：图 1 双变量地图（人均财政缺口 × 人口变化）
# 目的：用 3×3 配色同时显示“人均财政缺口的三分位”和“2010–2020 常住人口变化的三分位”，
#       直接呈现“高缺口—人口收缩”（转移支付支撑的收缩地区）与“低缺口—人口增长”（市场主导的增长地区）的空间分布。
# 结果：图表/fig1_bivariate_gap_popchange.png（及同名 .pdf）。
# ===========================================================================
BIVAR = {  # 行：缺口三分位（低→高）；列：人口变化三分位（收缩→增长）
    (0, 0): "#e8e8e8", (0, 1): "#ace4e4", (0, 2): "#5ac8c8",
    (1, 0): "#dfb0d6", (1, 1): "#a5add3", (1, 2): "#5698b9",
    (2, 0): "#be64ac", (2, 1): "#8c62aa", (2, 2): "#3b4994",
}


def fig1(df, gdf, fig_dir):
    d = gdf.merge(df[["unit_id", "gap_pc_res", "pop_chg_1020"]], on="unit_id", how="left")
    ok = d["gap_pc_res"].notna() & d["pop_chg_1020"].notna()
    if ok.sum() < 3:   # 财政或普查数据尚未准备好时，三分位无法计算，跳过本图而不是让整个脚本报错
        LOG.warning(f"人均财政缺口与人口变化同时非缺失的单元只有 {int(ok.sum())} 个，跳过图 1。")
        return
    d["gq"] = pd.qcut(d.loc[ok, "gap_pc_res"].rank(method="first"), 3, labels=False)
    d["pq"] = pd.qcut(d.loc[ok, "pop_chg_1020"].rank(method="first"), 3, labels=False)
    d["color"] = [BIVAR.get((int(a), int(b)), "#ffffff") if pd.notna(a) and pd.notna(b) else "#ffffff"
                  for a, b in zip(d["gq"], d["pq"])]
    fig, ax = plt.subplots(figsize=(10, 8))
    d.to_crs("+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84").plot(
        ax=ax, color=d["color"], edgecolor="#bbbbbb", linewidth=0.05)
    ax.set_axis_off()
    ax.set_title("人均财政缺口（常住口径）× 2010–2020 常住人口变化", fontsize=13)
    lg = fig.add_axes([0.12, 0.12, 0.16, 0.16])
    for (i, j), c in BIVAR.items():
        lg.add_patch(plt.Rectangle((j, i), 1, 1, color=c))
    lg.set_xlim(0, 3)
    lg.set_ylim(0, 3)
    lg.set_xticks([0.5, 2.5], ["收缩", "增长"], fontsize=8)
    lg.set_yticks([0.5, 2.5], ["低缺口", "高缺口"], fontsize=8)
    lg.set_xlabel("人口变化 →", fontsize=8)
    lg.set_ylabel("人均缺口 →", fontsize=8)
    for s in lg.spines.values():
        s.set_visible(False)
    save(fig, fig_dir / "fig1_bivariate_gap_popchange")


def fig2(df, fig_dir):
    if not {"tree_pc_core", "fss", "pop_resident_2020"} <= set(df.columns):
        LOG.warning("缺少人均树木覆盖、财政自给率或 2020 常住人口列，跳过图 2。")
        return
    d = df[df["tree_pc_core"].gt(0) & df["fss"].notna()]
    if d.empty:   # 遥感或财政数据尚未准备好
        LOG.warning("人均树木覆盖与财政自给率同时非缺失的单元为 0 个，跳过图 2。")
        return
    fig, ax = plt.subplots(figsize=(8, 6))
    for g in [x for x in GROUP_ORDER if x in set(d["group5"])]:
        s = d[d["group5"] == g]
        pmax = d["pop_resident_2020"].max()
        pmax = pmax if pd.notna(pmax) and pmax > 0 else 1.0   # 人口全缺失时点大小统一，而不是变成 NaN（不显示）
        size = 5 + 60 * np.sqrt(s["pop_resident_2020"].fillna(0) / pmax)
        ax.scatter(s["fss"], s["tree_pc_core"], s=size, alpha=0.6, color=GROUP_COLORS[g], label=g, linewidths=0)
    ax.set_yscale("log")
    ax.set_xlabel("财政自给率（一般公共预算收入 / 支出）")
    ax.set_ylabel("中心建成区人均树木覆盖面积（m²，对数轴）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("财政自给率与县城/中心城区人均树木覆盖")
    save(fig, fig_dir / "fig2_green_vs_fss")


def fig3(df, fig_dir):
    if not any(v in df and df[v].gt(0).any() for v in ("exp_pc_res", "exp_pc_hukou")):
        LOG.warning("人均财政支出全部缺失，跳过图 3。")
        return
    groups = [x for x in GROUP_ORDER if x in set(df["group5"])]
    fig, ax = plt.subplots(figsize=(9, 5))
    pos = np.arange(len(groups))
    for k, (v, lab, off, c) in enumerate([("exp_pc_res", "常住口径", -0.18, "#2166ac"),
                                           ("exp_pc_hukou", "户籍口径", 0.18, "#b2182b")]):
        if v not in df or df[v].notna().sum() == 0:
            continue
        data = [df.loc[df["group5"] == g, v].dropna() for g in groups]
        bp = ax.boxplot(data, positions=pos + off, widths=0.3, patch_artist=True, showfliers=False)
        for b in bp["boxes"]:
            b.set_facecolor(c)
            b.set_alpha(0.5)
        ax.plot([], [], color=c, lw=6, alpha=0.5, label=lab)
    ax.set_xticks(pos, groups, rotation=15)
    ax.set_yscale("log")
    ax.set_ylabel("人均一般公共预算支出（元，对数轴）")
    ax.legend(frameon=False)
    ax.set_title("分母口径对人均财政支出的影响")
    save(fig, fig_dir / "fig3_exp_pc_denominators")


def fig4(df, fig_dir):
    if "land_pop_diverge" not in df or df["land_pop_diverge"].notna().sum() == 0:
        return
    groups = [x for x in GROUP_ORDER if x in set(df["group5"])]
    share = [df.loc[df["group5"] == g, "land_pop_diverge"].astype(float).mean() for g in groups]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(groups, share, color=[GROUP_COLORS[g] for g in groups])
    ax.set_ylabel("比例")
    ax.set_title("2010–2020 中心建成区扩张而常住人口下降的单元比例")
    save(fig, fig_dir / "fig4_land_pop_diverge")


def save(fig, stem: Path):
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    LOG.info(f"已保存 {stem.name}.png / .pdf")


# ===========================================================================
# 代码块 4：主流程
# 目的：读取指标表 → 表 1、表 2 → 四张图。
# 结果：见文件开头“输出”。
# ===========================================================================
def main():
    cfg = load_config()
    out_dir = resolve(cfg["analysis"]["out_dir"])
    fig_dir = resolve(cfg["analysis"]["fig_dir"])
    set_cjk_font()
    df = read_table(out_dir / "unit_indicators.csv", code_cols=("unit_id", "prov_code", "pref_code"))

    t1 = table1(df)
    atomic_write_csv(t1, out_dir / "table1_group_summary.csv")
    # Markdown 版本转置（指标为行、分组为列），便于阅读
    atomic_write_text(out_dir / "table1_group_summary.md", to_md(t1.set_index("分组").T.reset_index().rename(columns={"index": "指标"})))

    d = df.dropna(subset=["quadrant"])
    if len(d):
        t2n = pd.crosstab(d["quadrant"], d["group5"]).reindex(columns=[g for g in GROUP_ORDER if g in set(d["group5"])])
        t2p = (d.pivot_table(index="quadrant", columns="group5", values="pop_resident_2020", aggfunc="sum") / 1e4).round(1)
        t2 = pd.concat({"单元数": t2n, "常住人口(万人)": t2p}, axis=1).reset_index()
        t2.columns = [" ".join(map(str, c)).strip() if isinstance(c, tuple) else c for c in t2.columns]
        atomic_write_csv(t2, out_dir / "table2_quadrant_by_group.csv")
        atomic_write_text(out_dir / "table2_quadrant_by_group.md", to_md(t2))

    gpkg = resolve(cfg["units"]["out_dir"]) / "units_full.gpkg"
    if gpkg.exists():
        import geopandas as gpd
        fig1(df, gpd.read_file(gpkg), fig_dir)
    fig2(df, fig_dir)
    fig3(df, fig_dir)
    fig4(df, fig_dir)
    LOG.info("完成。")


if __name__ == "__main__":
    main()
