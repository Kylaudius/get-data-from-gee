# -*- coding: utf-8 -*-
"""
05_models.py  基准回归：转移支付依赖、人口变化与遥感测度的公共空间供给

在哪里运行：Mac “终端 Terminal”
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python 05_models.py

输入：数据/结果/unit_indicators.csv（03 输出）。
输出（数据/结果/）：
    models_coef.csv       全部模型的系数、聚类稳健标准误、p 值、样本量、R²
    models_summary.md     便于阅读的结果摘要（每个模型一段）
    图表/fig5_coef_gap_ratio.png   转移支付依赖度在不同结果变量上的系数图
说明：本脚本给出的是截面与长差分的条件相关 (conditional association)，不是因果效应；
      因果识别设计（撤县设区、贫困县退出等准实验）见研究设计报告第 8 节，在 v1.1 实现。
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import atomic_write_csv, atomic_write_text, get_logger, load_config, read_table, resolve  # noqa: E402

LOG = get_logger("05_models")


# ===========================================================================
# 代码块 1：样本与变量准备
# 目的：剔除财政口径不一致的单元（fiscal_scope_mismatch）与外围市辖区；对取对数的变量先缩尾 (winsorize)
#       再取对数，减少极端值影响；生成控制变量。
# 结果：返回建模用 DataFrame。
# ===========================================================================
def winsor(s: pd.Series, p: float) -> pd.Series:
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def prepare(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    p = float(cfg["analysis"]["winsor_pct"])
    d = df.copy()
    if "fiscal_scope_mismatch" in d:
        d = d[~d["fiscal_scope_mismatch"].astype(str).str.lower().eq("true")]
    d = d[d["group5"] != "外围市辖区"]
    for v in ["tree_pc_core", "green_pc_core", "greenpatch_pc_core", "riparian_green_pc", "u_access_min", "builtup_pc_core", "floor_res_pc_unit", "ntl_per_built", "park_pc_core",
              "exp_pc_res", "gap_pc_res", "core_pop"]:
        if v in d:
            x = pd.to_numeric(d[v], errors="coerce")
            d["ln_" + v] = np.log(winsor(x.where(x > 0), p))
    for v in ["gap_ratio", "pop_chg_1020", "pop_chg_0010", "green_share_core", "expo_tree_core", "tree_share_core", "park_access_share",
              "ndvi_gap", "core_growth_1020", "fss_2010", "greenpatch_access_share"]:
        if v in d:
            d[v] = winsor(pd.to_numeric(d[v], errors="coerce"), p)
    if "fss_2010" in d:
        d["gap_ratio_2010"] = 1 - d["fss_2010"]
    if {"core_growth_1020", "pop_chg_1020"} <= set(d.columns):
        d["excess_land_growth"] = d["core_growth_1020"] - d["pop_chg_1020"]
    d["group5"] = pd.Categorical(d["group5"], categories=["县", "县级市", "中小城市市辖区", "大城市市辖区", "超大特大城市市辖区"])
    return d


# ===========================================================================
# 代码块 2：模型设定
# 目的：统一定义结果变量与控制变量。核心解释变量为转移支付依赖度 gap_ratio、人口对数变化及二者交互；
#       控制中心建成区人口规模、自然植被本底（ndvi_ring）、地形与气候，并加入省份固定效应；
#       标准误在地级市层面聚类。
# 结果：MODELS 列表（名称、公式）。
# ===========================================================================
CONTROLS = ("ln_core_pop + ndvi_ring + u_elev + u_slope + u_t2m_c_2020 + u_prcp_mm_2020 + ln_u_access_min"
            " + C(group5) + C(prov_code)")
MODELS = [
    ("M1 人均树木覆盖", f"ln_tree_pc_core ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M2 人口加权树木暴露", f"expo_tree_core ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M2b 人均绿地（稳健性口径）", f"ln_green_pc_core ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M3 城区相对本底绿度", f"ndvi_gap ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M4 人均建成面积", f"ln_builtup_pc_core ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M5 人均住宅面积估算", f"ln_floor_res_pc_unit ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M6 单位建成面积灯光", f"ln_ntl_per_built ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M7 公园代理：人均连片绿地", f"ln_greenpatch_pc_core ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M7b 公园代理：500 m 可达比例", f"greenpatch_access_share ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M7c 绿道代理：人均滨水绿带", f"ln_riparian_green_pc ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M7d 公园可达比例（需公园矢量）", f"park_access_share ~ gap_ratio * pop_chg_1020 + {CONTROLS}"),
    ("M8 分组斜率：人均树木覆盖", f"ln_tree_pc_core ~ gap_ratio:C(group5) + pop_chg_1020 + {CONTROLS}"),
    ("M1p 人均树木覆盖（地级市固定效应，同一城市内比较市辖区与县）",
     "ln_tree_pc_core ~ gap_ratio * pop_chg_1020 + ln_core_pop + ndvi_ring + u_elev + u_slope + u_t2m_c_2020"
     " + u_prcp_mm_2020 + ln_u_access_min + C(group5) + C(pref_code)"),
    ("M9 长差分：超额土地扩张", "excess_land_growth ~ gap_ratio_2010 + pop_chg_0010 + ndvi_ring + u_elev + u_slope"
                         " + u_t2m_c_2020 + u_prcp_mm_2020 + ln_u_access_min + C(group5) + C(prov_code)"),
]


# ===========================================================================
# 代码块 3：估计
# 目的：对每个模型先按公式所需变量删除缺失，再做 OLS 与地级市聚类稳健标准误；
#       变量缺失（例如没有公园数据）或样本太少时跳过并记录原因。
# 结果：返回系数长表与文字摘要。
# ===========================================================================
def fit_all(d: pd.DataFrame, cluster: str):
    rows, notes = [], []
    for name, formula in MODELS:
        try:
            needed = sorted(set(_vars_in(formula)))
            missing = [v for v in needed if v not in d]
            if missing:
                notes.append(f"### {name}\n跳过：缺少变量 {missing}\n")
                continue
            dd = d.dropna(subset=needed + [cluster])
            if len(dd) < 50:
                notes.append(f"### {name}\n跳过：有效样本 {len(dd)} < 50\n")
                continue
            res = smf.ols(formula, data=dd).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(dd[cluster])[0]})
            for term in res.params.index:
                if term.startswith(("C(prov_code)", "C(pref_code)")) or term == "Intercept":
                    continue
                rows.append({"model": name, "term": term, "coef": res.params[term], "se": res.bse[term],
                             "p": res.pvalues[term], "n": int(res.nobs), "r2": res.rsquared})
            key = [t for t in res.params.index if t.startswith("gap_ratio")]
            txt = "; ".join(f"{t} = {res.params[t]:.3f} (se {res.bse[t]:.3f}, p {res.pvalues[t]:.3f})" for t in key)
            notes.append(f"### {name}\n公式：`{formula}`\n\nN = {int(res.nobs)}，R² = {res.rsquared:.3f}\n\n{txt}\n")
        except Exception as e:  # noqa: BLE001
            notes.append(f"### {name}\n失败：{str(e)[:300]}\n")
    return pd.DataFrame(rows), "\n".join(notes)


def _vars_in(formula: str) -> list:
    """从公式中取出原始变量名（去掉 C()、交互符号等）。"""
    import re
    rhs = formula.replace("~", "+").replace("*", "+").replace(":", "+")
    toks = [re.sub(r"^C\((.*)\)$", r"\1", t.strip()) for t in rhs.split("+")]
    return [t for t in toks if t and t != "1"]


def coef_plot(coef: pd.DataFrame, fig_dir: Path):
    from importlib import import_module
    set_font = import_module("04_describe_and_map").set_cjk_font
    set_font()
    c = coef[coef["term"] == "gap_ratio"]
    if c.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 0.5 * len(c) + 1.5))
    y = np.arange(len(c))
    ax.errorbar(c["coef"], y, xerr=1.96 * c["se"], fmt="o", color="#2166ac", capsize=3)
    ax.axvline(0, color="#888888", lw=0.8)
    ax.set_yticks(y, c["model"])
    ax.set_xlabel("转移支付依赖度 gap_ratio 的系数（95% 置信区间，人口变化 = 0 处）")
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / "fig5_coef_gap_ratio.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    cfg = load_config()
    out_dir = resolve(cfg["analysis"]["out_dir"])
    df = read_table(out_dir / "unit_indicators.csv", code_cols=("unit_id", "prov_code", "pref_code"))
    d = prepare(df, cfg)
    coef, notes = fit_all(d, cfg["analysis"]["cluster_col"])
    atomic_write_csv(coef, out_dir / "models_coef.csv")
    head = ("# 基准回归结果摘要\n\n以下为条件相关，不是因果效应。标准误在地级市层面聚类。"
            "交互模型中 gap_ratio 的系数表示人口变化为 0 时的关联。\n\n")
    atomic_write_text(out_dir / "models_summary.md", head + notes)
    if len(coef):
        coef_plot(coef, resolve(cfg["analysis"]["fig_dir"]))
    LOG.info(f"完成：{coef['model'].nunique() if len(coef) else 0} 个模型 → models_coef.csv / models_summary.md")


if __name__ == "__main__":
    main()
