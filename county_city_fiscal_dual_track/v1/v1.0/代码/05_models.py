# -*- coding: utf-8 -*-
"""
05_models.py  基准回归：财政净流入、人口变化与公共空间、住房和社会基础设施

在哪里运行：Mac “终端 Terminal”
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python 05_models.py

输入：数据/结果/unit_indicators.csv（03 输出）。
输出：
    数据/结果/models_coef.csv       全部模型的系数、聚类稳健标准误、p 值、样本量、R²，以及每个模型检验的假设与预期符号
    数据/结果/models_summary.md     便于阅读的结果摘要：先列模型总表（假设、预期符号、是否运行），再逐个模型给出关键系数
    数据/结果/图表/图6_回归系数图.png   人均净流入 net_inflow_pc_k 在各结果变量上的系数（写到 analysis.fig_out_dir）
说明：本脚本给出的是截面与长差分的条件相关 (conditional association)，不是因果效应。
      核心财政变量是人均净流入（千元，缩尾后线性进入）与人均本级收入（取对数），分母都是预先确定的 2010 年人口；
      主要结果变量的模型含 人均净流入 × 人口变化 交互项。
      因果识别设计（省直管县、撤县设区、连片特困地区等准实验）见研究设计报告 §9.5，计划在 v1.1 实现。
"""
from __future__ import annotations

import re
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
MIN_N = 50
FE_TERMS = ("prov_code", "pref_code")


# ===========================================================================
# 代码块 1：样本与变量准备
# 目的：剔除 excluded 单元（兵团城市）、财政口径不一致的单元（fiscal_scope_mismatch）与外围市辖区；
#       主分析期有收支数据的年份少于 analysis.min_fiscal_years（默认 2）时，财政变量记为缺失；
#       对取对数的变量先缩尾 (winsorize) 再取对数，对线性变量直接缩尾，减少极端值影响；生成长差分结果变量。
# 结果：返回建模用 DataFrame。
# ===========================================================================
LOG_VARS = ["tree_pc_core", "green_pc_core", "greenpatch_pc_core", "riparian_green_pc", "u_access_min", "builtup_pc_core",
            "floor_res_pc_unit", "ntl_per_built", "park_pc_core", "exp_pc_res", "gap_pc_res", "core_pop", "core_pop_ghs",
            "own_rev_pc", "own_rev_pc_rob", "tree_new_pc_core", "tree_area_m2_core", "tree_pc_core_ghs",
            "park_area_pc_mohurd", "muni_invest_green_pc", "land_conv_pc", "lgfv_debt_pc", "special_bond_pc",
            "housing_slack_ratio"]
LINEAR_VARS = ["net_inflow_pc_k", "net_inflow_pc_k_rob", "gap_ratio", "pop_chg_1020", "pop_chg_0010", "green_share_core",
               "expo_tree_core", "tree_share_core", "park_access_share", "ndvi_gap", "core_growth_1020", "fss_2010",
               "greenpatch_access_share", "transfer_pc_2000_k", "imp_growth_0010_core", "imp_growth_1018_core",
               "dlnS_builtup_1020", "dlnP_core_1020", "share_rent_market", "housing_area_pc", "collective_share",
               "beds_res_hukou_ratio", "beds_per_1k_res", "students_per_child", "exp_personnel_share", "exp_genpub_share",
               "fund_fiscal_share", "fund_debt_share"]
FISCAL_COLS = ["net_inflow_pc_k", "own_rev_pc", "gap_ratio", "fss", "exp_personnel_share", "exp_genpub_share"]


def winsor(s: pd.Series, p: float) -> pd.Series:
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def as_bool(s: pd.Series) -> pd.Series:
    return s.astype("string").str.lower().isin(["true", "1"]).fillna(False).astype(bool)


def prepare(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    a = cfg["analysis"]
    p = float(a["winsor_pct"])
    d = df.copy()
    if "excluded" in d:
        ex = as_bool(d["excluded"])
        LOG.info(f"剔除 excluded 单元 {int(ex.sum())} 个")
        d = d[~ex]
    if "fiscal_scope_mismatch" in d:
        d = d[~as_bool(d["fiscal_scope_mismatch"])]
    d = d[d["group5"] != "外围市辖区"]
    min_years = int(a.get("min_fiscal_years", 2))
    if "n_years_main" in d:
        few = pd.to_numeric(d["n_years_main"], errors="coerce").fillna(0) < min_years
        if few.any():
            LOG.info(f"{int(few.sum())} 个单元主分析期收支都有数的年份少于 {min_years} 年，财政变量记为缺失")
            d.loc[few, [c for c in FISCAL_COLS if c in d]] = np.nan
    for v in LOG_VARS:
        if v in d:
            x = pd.to_numeric(d[v], errors="coerce")
            d["ln_" + v] = np.log(winsor(x.where(x > 0), p))
    for v in LINEAR_VARS:
        if v in d:
            d[v] = winsor(pd.to_numeric(d[v], errors="coerce"), p)
    if "fss_2010" in d:
        d["gap_ratio_2010"] = 1 - d["fss_2010"]
    if {"core_growth_1020", "pop_chg_1020"} <= set(d.columns):
        d["excess_land_growth"] = d["core_growth_1020"] - d["pop_chg_1020"]
    if {"imp_growth_0010_core", "pop_chg_0010"} <= set(d.columns):
        d["excess_imp_0010"] = d["imp_growth_0010_core"] - d["pop_chg_0010"]
    if {"imp_growth_1018_core", "pop_chg_1020"} <= set(d.columns):
        d["excess_imp_1018"] = d["imp_growth_1018_core"] - d["pop_chg_1020"]
    # 以“县”为参照组；不在五类中的单元（如“市辖区（规模未知）”）先设为缺失，再转为分类变量
    #（直接把类别外的值放进 Categorical 在 pandas 3 中已不推荐、pandas 4 将报错）
    cats = ["县", "县级市", "中小城市市辖区", "大城市市辖区", "超大特大城市市辖区"]
    d["group5"] = pd.Categorical(d["group5"].where(d["group5"].isin(cats)), categories=cats)
    return d


# ===========================================================================
# 代码块 2：模型设定
# 目的：每个模型是一条记录，写明名称、公式、检验的假设与预期符号。核心财政变量为人均净流入 net_inflow_pc_k
#       与人均本级收入 ln_own_rev_pc；主要结果变量的模型含 net_inflow_pc_k × pop_chg_1020 交互项。
#       控制中心建成区人口规模、自然植被本底（ndvi_ring）、地形、气候与区位，加入五类分组与省份固定效应；
#       标准误在 analysis.cluster_col（默认地级市）层面聚类。optional 中的变量有数据时才加入（土地与债务）；
#       min_group_n 为 True 的模型只保留样本中不少于 analysis.min_group_n 个单元的分组。
# 结果：MODELS 列表。
# ===========================================================================
BASE = "ndvi_ring + u_elev + u_slope + u_t2m_c_2020 + u_prcp_mm_2020 + ln_u_access_min"
CONTROLS = f"ln_core_pop + {BASE} + C(group5) + C(prov_code)"
CONTROLS_NOPOP = f"{BASE} + C(group5) + C(prov_code)"
BASE_TERMS = set(BASE.split(" + "))
FISCAL = "net_inflow_pc_k * pop_chg_1020 + ln_own_rev_pc"
FISCAL_ADD = "net_inflow_pc_k + ln_own_rev_pc + pop_chg_1020"
S_MAIN = "net_inflow_pc_k > 0；net_inflow_pc_k:pop_chg_1020 < 0（人口收缩单元中关联更强，H3）"


def M(name, formula, hypothesis, expected_sign, **kw):
    return {"name": name, "formula": formula, "hypothesis": hypothesis, "expected_sign": expected_sign, **kw}


MODELS = [
    # H2 人均供给（绿地）
    M("M1 人均树木覆盖", f"ln_tree_pc_core ~ {FISCAL} + {CONTROLS}", "H2、H3", S_MAIN),
    M("M2 人口加权树木暴露", f"expo_tree_core ~ {FISCAL} + {CONTROLS}", "H2", "net_inflow_pc_k > 0"),
    M("M2b 人均绿地（稳健性口径）", f"ln_green_pc_core ~ {FISCAL} + {CONTROLS}", "H2", S_MAIN),
    M("M3 城区相对本底绿度", f"ndvi_gap ~ {FISCAL} + {CONTROLS}", "H2（辅助）", "net_inflow_pc_k > 0"),
    M("M7 人均大型树木斑块", f"ln_greenpatch_pc_core ~ {FISCAL} + {CONTROLS}", "H2", S_MAIN),
    M("M7b 大型树木斑块 500 m 可达比例", f"greenpatch_access_share ~ {FISCAL} + {CONTROLS}", "H2", "net_inflow_pc_k > 0"),
    M("M7c 人均滨水线性绿地", f"ln_riparian_green_pc ~ {FISCAL} + {CONTROLS}", "H2", "net_inflow_pc_k > 0"),
    M("M7d 公园步行可达比例（需公园矢量）", f"park_access_share ~ {FISCAL} + {CONTROLS}", "H2", "net_inflow_pc_k > 0"),
    M("M7e 人均公园面积（需公园矢量）", f"ln_park_pc_core ~ {FISCAL} + {CONTROLS}", "H2", "net_inflow_pc_k > 0"),
    M("M7f 人均新增树木", f"ln_tree_new_pc_core ~ {FISCAL} + {CONTROLS}", "H2",
      "net_inflow_pc_k > 0（新增树木比存量更接近财政投入的结果）"),
    # 住建部城市与县城建设统计
    M("M10a 人均公园面积（住建部）", f"ln_park_area_pc_mohurd ~ {FISCAL} + {CONTROLS}", "H2", "net_inflow_pc_k > 0"),
    M("M10b 人均园林绿化投资（住建部）", f"ln_muni_invest_green_pc ~ {FISCAL} + {CONTROLS}", "H2（资金通道）",
      "net_inflow_pc_k > 0"),
    M("M10c 市政投资中财政拨款占比", f"fund_fiscal_share ~ {FISCAL} + {CONTROLS}", "项目化供给",
      "net_inflow_pc_k > 0"),
    M("M10d 市政投资中债券与贷款占比", f"fund_debt_share ~ {FISCAL} + {CONTROLS}", "项目化供给与市场工具",
      "net_inflow_pc_k < 0；ln_own_rev_pc > 0"),
    # H3 分子与分母
    M("M11 树木面积对中心人口的弹性", f"ln_tree_area_m2_core ~ ln_core_pop + {FISCAL_ADD} + {CONTROLS_NOPOP}", "H3",
      "ln_core_pop < 1（树木总量随人口的弹性小于 1，人少则人均高）"),
    M("M12 建成面积变化分解", f"dlnS_builtup_1020 ~ dlnP_core_1020 + net_inflow_pc_k + ln_own_rev_pc + {CONTROLS_NOPOP}", "H3",
      "dlnP_core_1020 < 1；net_inflow_pc_k > 0"),
    # H4 建设与使用强度
    M("M4 人均建成面积", f"ln_builtup_pc_core ~ {FISCAL} + {CONTROLS}", "H2、H4", S_MAIN),
    M("M5 人均住宅面积估算", f"ln_floor_res_pc_unit ~ {FISCAL} + {CONTROLS}", "H4", "net_inflow_pc_k > 0"),
    M("M6 单位建成面积灯光（辅助）", f"ln_ntl_per_built ~ {FISCAL} + {CONTROLS}", "H4", "net_inflow_pc_k < 0"),
    M("M4h 住房余量比", f"ln_housing_slack_ratio ~ {FISCAL} + {CONTROLS}", "H4",
      "net_inflow_pc_k > 0；net_inflow_pc_k:pop_chg_1020 < 0"),
    # H5 市场依赖与住房压力
    M("M13a 市场租赁户比例", f"share_rent_market ~ {FISCAL_ADD} + {CONTROLS_NOPOP}", "H5",
      "大城市、超大特大城市市辖区 > 县；ln_own_rev_pc > 0；net_inflow_pc_k < 0"),
    M("M13b 人均住房建筑面积", f"housing_area_pc ~ {FISCAL_ADD} + {CONTROLS_NOPOP}", "H5",
      "大城市、超大特大城市市辖区 < 县；net_inflow_pc_k > 0"),
    M("M13c 集体户人口比例", f"collective_share ~ {FISCAL_ADD} + {CONTROLS_NOPOP}", "H5",
      "大城市、超大特大城市市辖区 > 县；ln_own_rev_pc > 0"),
    # H7 社会基础设施
    M("M14a 床位常住与户籍口径之比", f"beds_res_hukou_ratio ~ {FISCAL} + {CONTROLS_NOPOP}", "H7",
      "net_inflow_pc_k > 0；pop_chg_1020 < 0（该比值等于 户籍 / 常住）"),
    M("M14b 每千常住人口床位", f"beds_per_1k_res ~ {FISCAL} + {CONTROLS_NOPOP}", "H7", S_MAIN),
    M("M14c 在校生与 0–14 岁人口之比", f"students_per_child ~ {FISCAL} + {CONTROLS_NOPOP}", "H7", S_MAIN),
    # R1 对立假说
    M("M15a 工资福利支出占比", f"exp_personnel_share ~ {FISCAL_ADD} + {CONTROLS_NOPOP}", "R1",
      "R1 成立时 net_inflow_pc_k > 0"),
    M("M15b 一般公共服务支出占比", f"exp_genpub_share ~ {FISCAL_ADD} + {CONTROLS_NOPOP}", "R1",
      "R1 成立时 net_inflow_pc_k > 0"),
    # 其他资金来源与链条
    M("M16 人均树木覆盖（加入土地与债务）", f"ln_tree_pc_core ~ {FISCAL} + {CONTROLS}", "H2 与市场工具对照",
      "net_inflow_pc_k > 0；土地与债务变量 > 0", optional=["ln_land_conv_pc", "ln_lgfv_debt_pc", "ln_special_bond_pc"]),
    M("M17 链条（描述）：园林投资与大型树木斑块",
      f"ln_greenpatch_pc_core ~ ln_muni_invest_green_pc + {FISCAL_ADD} + {CONTROLS}", "H2（资金通道，描述）",
      "ln_muni_invest_green_pc > 0；加入投资后 net_inflow_pc_k 变小"),
    # 稳健性
    M("R-a 比值口径（gap_ratio）", f"ln_tree_pc_core ~ gap_ratio * pop_chg_1020 + {CONTROLS}", "稳健性", "gap_ratio > 0"),
    M("R-b 稳健性财政年份", f"ln_tree_pc_core ~ net_inflow_pc_k_rob * pop_chg_1020 + ln_own_rev_pc_rob + {CONTROLS}",
      "稳健性", "net_inflow_pc_k_rob > 0"),
    M("R-c GHS-POP 分母", f"ln_tree_pc_core_ghs ~ {FISCAL} + ln_core_pop_ghs + {CONTROLS_NOPOP}", "稳健性",
      "net_inflow_pc_k > 0"),
    # 分组斜率与地级市固定效应
    M("M8 分组斜率：人均树木覆盖",
      f"ln_tree_pc_core ~ net_inflow_pc_k:C(group5) + ln_own_rev_pc + pop_chg_1020 + {CONTROLS}", "H2 异质性",
      "各组 net_inflow_pc_k > 0，县与县级市更大", min_group_n=True),
    M("M1p 人均树木覆盖（地级市固定效应，同一城市内比较市辖区与县）",
      f"ln_tree_pc_core ~ {FISCAL} + ln_core_pop + {BASE} + C(group5) + C(pref_code)", "H2", S_MAIN),
    # 长差分：预先确定的 1999–2001 年人均转移支付为处理变量
    M("M9a 长差分 2000–2010：超额不透水面增长（前期对照）",
      f"excess_imp_0010 ~ transfer_pc_2000_k + {BASE} + C(group5) + C(prov_code)", "长差分",
      "与 M9b 同号且相近时，2010 年后的关联不能归于此后的财政变化"),
    M("M9b 长差分 2010–2020：超额不透水面增长（GAIA，至 2018）",
      f"excess_imp_1018 ~ transfer_pc_2000_k + {BASE} + C(group5) + C(prov_code)", "长差分",
      "transfer_pc_2000_k > 0"),
    M("M9c 长差分 2010–2020：超额土地扩张（GHSL）",
      f"excess_land_growth ~ transfer_pc_2000_k + {BASE} + C(group5) + C(prov_code)", "长差分",
      "transfer_pc_2000_k > 0"),
]


# ===========================================================================
# 代码块 3：估计
# 目的：对每个模型先按公式所需变量删除缺失，再删除样本中只有 1 个单元的固定效应组（单例组对系数没有信息，
#       却会虚增样本量并影响聚类标准误），最后做 OLS 与聚类稳健标准误；
#       变量缺失（例如没有公园或住建部数据）或样本太少时跳过并记录原因，任何模型出错都不会中断其他模型。
# 结果：返回系数长表、模型总表与文字摘要。
# ===========================================================================
def _vars_in(formula: str) -> list:
    """从公式中取出原始变量名（去掉 C()、交互符号等）。"""
    rhs = formula.replace("~", "+").replace("*", "+").replace(":", "+")
    toks = [re.sub(r"^C\((.*)\)$", r"\1", t.strip()) for t in rhs.split("+")]
    return [t for t in toks if t and t != "1"]


def drop_singletons(dd: pd.DataFrame, formula: str) -> tuple[pd.DataFrame, str]:
    notes = []
    for fe in FE_TERMS:
        if f"C({fe})" in formula:
            cnt = dd[fe].map(dd[fe].value_counts())
            single = cnt < 2
            if single.any():
                notes.append(f"{fe} 单例组 {int(dd.loc[single, fe].nunique())} 个（{int(single.sum())} 个单元）已删除")
                dd = dd[~single]
    return dd, "；".join(notes)


def fit_one(spec: dict, d: pd.DataFrame, cluster: str, min_group: int):
    formula = spec["formula"]
    opt = [v for v in spec.get("optional", []) if v in d and d[v].notna().sum() >= MIN_N]
    if spec.get("optional"):
        if not opt:
            return None, f"跳过：{spec['optional']} 都没有数据（土地、城投债务或专项债文件未提供）", formula
        lhs, rhs = formula.split("~", 1)
        formula = f"{lhs}~ {' + '.join(opt)} + {rhs.strip()}"
    needed = sorted(set(_vars_in(formula)))
    missing = [v for v in needed if v not in d or d[v].notna().sum() == 0]
    if missing:
        return None, f"跳过：缺少变量 {missing}", formula
    dd = d.dropna(subset=needed + [cluster]).copy()
    notes = []
    if spec.get("min_group_n"):
        vc = dd["group5"].value_counts()
        small = vc[(vc > 0) & (vc < min_group)].index.tolist()
        if small:
            notes.append(f"单元数少于 {min_group} 的分组已剔除：{[str(x) for x in small]}")
            dd = dd[~dd["group5"].isin(small)]
    dd, sn = drop_singletons(dd, formula)
    if sn:
        notes.append(sn)
    if len(dd) < MIN_N:
        return None, f"跳过：有效样本 {len(dd)} < {MIN_N}" + (f"（{'；'.join(notes)}）" if notes else ""), formula
    # 删除本模型样本中没有单元的分组（例如试点省份没有超大特大城市），
    # 否则设计矩阵出现全 0 列，结果表里会出现系数 0、标准误 0 的无意义行
    if isinstance(dd["group5"].dtype, pd.CategoricalDtype):
        dd["group5"] = dd["group5"].cat.remove_unused_categories()
    res = smf.ols(formula, data=dd).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(dd[cluster])[0]})
    return res, "；".join(notes), formula


def fit_all(d: pd.DataFrame, cluster: str, min_group: int):
    rows, overview, notes = [], [], []
    for spec in MODELS:
        name = spec["name"]
        head = f"### {name}\n检验：{spec['hypothesis']}；预期符号：{spec['expected_sign']}\n"
        try:
            res, note, formula = fit_one(spec, d, cluster, min_group)
        except Exception as e:  # noqa: BLE001  单个模型失败不影响其他模型
            res, note, formula = None, f"失败：{str(e)[:300]}", spec["formula"]
        if res is None:
            overview.append({"模型": name, "假设": spec["hypothesis"], "预期符号": spec["expected_sign"], "状态": note})
            notes.append(f"{head}\n公式：`{formula}`\n\n{note}\n")
            continue
        for term in res.params.index:
            if term.startswith(tuple(f"C({fe})" for fe in FE_TERMS)) or term == "Intercept":
                continue
            rows.append({"model": name, "hypothesis": spec["hypothesis"], "expected_sign": spec["expected_sign"],
                         "formula": formula, "term": term, "coef": res.params[term], "se": res.bse[term],
                         "p": res.pvalues[term], "n": int(res.nobs), "r2": res.rsquared})
        # 摘要只列财政、人口、分组与土地债务等关键项；地形、气候、区位控制与固定效应只写进 models_coef.csv
        keys = [t for t in res.params.index if t != "Intercept" and t not in BASE_TERMS
                and not t.startswith(tuple(f"C({fe})" for fe in FE_TERMS))]
        txt = "\n".join(f"- {t} = {res.params[t]:.3f}（se {res.bse[t]:.3f}，p {res.pvalues[t]:.3f}）" for t in keys)
        overview.append({"模型": name, "假设": spec["hypothesis"], "预期符号": spec["expected_sign"],
                         "状态": f"已运行，N = {int(res.nobs)}" + (f"；{note}" if note else "")})
        notes.append(f"{head}\n公式：`{formula}`\n\nN = {int(res.nobs)}，R² = {res.rsquared:.3f}"
                     + (f"。{note}" if note else "") + f"\n\n{txt}\n")
    return pd.DataFrame(rows), pd.DataFrame(overview), "\n".join(notes)


def coef_plot(coef: pd.DataFrame, fig_dir: Path):
    from importlib import import_module
    import_module("04_describe_and_map").set_cjk_font()
    c = coef[coef["term"] == "net_inflow_pc_k"]
    if c.empty:
        LOG.warning("没有模型估计出 net_inflow_pc_k 的系数，跳过图6。")
        return
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(c) + 1.6))
    y = np.arange(len(c))
    ax.errorbar(c["coef"], y, xerr=1.96 * c["se"], fmt="o", color="#2166ac", capsize=3)
    ax.axvline(0, color="#888888", lw=0.8)
    ax.set_yticks(y, c["model"], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("人均净流入 net_inflow_pc_k 的系数（95% 置信区间；交互模型中为人口变化 = 0 处）")
    ax.set_title("人均净流入与各结果变量的条件相关")
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / "图6_回归系数图.png", dpi=300, bbox_inches="tight")
    fig.savefig(fig_dir / "图6_回归系数图.pdf", bbox_inches="tight")
    plt.close(fig)
    LOG.info("已保存 图6_回归系数图.png / .pdf")


def to_md(df: pd.DataFrame) -> str:
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.values) + " |")
    return "\n".join(lines) + "\n"


def main():
    cfg = load_config()
    a = cfg["analysis"]
    out_dir = resolve(a["out_dir"])
    df = read_table(out_dir / "unit_indicators.csv", code_cols=("unit_id", "prov_code", "pref_code"))
    d = prepare(df, cfg)
    coef, overview, notes = fit_all(d, a["cluster_col"], int(a.get("min_group_n", 10)))
    cols = ["model", "hypothesis", "expected_sign", "formula", "term", "coef", "se", "p", "n", "r2"]
    atomic_write_csv(coef if len(coef) else pd.DataFrame(columns=cols), out_dir / "models_coef.csv")
    head = ("# 基准回归结果摘要\n\n以下为条件相关，不是因果效应。标准误在地级市层面聚类。"
            "交互模型中 net_inflow_pc_k 的系数表示人口变化为 0 时的关联。"
            "准实验设计见研究设计报告 §9.5，计划在 v1.1 实现。\n\n## 模型总表\n\n")
    atomic_write_text(out_dir / "models_summary.md", head + to_md(overview) + "\n## 各模型结果\n\n" + notes)
    if len(coef):
        coef_plot(coef, resolve(a.get("fig_out_dir", "数据/结果/图表")))
    n_ok = coef["model"].nunique() if len(coef) else 0
    LOG.info(f"完成：{n_ok} / {len(MODELS)} 个模型已运行，其余见 models_summary.md 中的跳过原因 → models_coef.csv / models_summary.md")


if __name__ == "__main__":
    main()
