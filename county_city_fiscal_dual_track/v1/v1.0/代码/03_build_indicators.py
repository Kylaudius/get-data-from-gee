# -*- coding: utf-8 -*-
"""
03_build_indicators.py  合并财政、普查与遥感数据，计算全部分析指标并划分城市/县城类型

在哪里运行：Mac “终端 Terminal”
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python 03_build_indicators.py
    python 03_build_indicators.py --codebook-only   # 只导出指标说明表（不需要任何数据）

输入：00 的 units_table.csv 与 county_to_unit.csv；01 的 gee_unit_metrics.csv；02 的 unit_fiscal_census.csv；
      外部参数 中的城市规模标准、超大特大城市名单与行政等级表；
      可选的城区人口表（city_urban_pop_file）与住建部城市、县城建设统计面板（mohurd_file）。
输出（数据/结果/）：
    unit_indicators.csv       一行一个分析单元，含全部指标、分组变量与 excluded 标记
    codebook_indicators.csv   指标说明（中文名、英文名、公式、单位），与 附录C 一致
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (atomic_write_csv, code_to_unit, get_logger, is_excluded, load_config,  # noqa: E402
                    norm_adcode, pref_code, read_table, resolve)

LOG = get_logger("03_build_indicators")
FALLBACK_CORE = "fallback_centroid_1km"
POI_KEYS = ("school", "hospital", "elderly")

# ===========================================================================
# 代码块 1：指标说明表 (codebook)
# 目的：集中写明每个指标的中文名、英文术语、计算公式与单位；脚本计算与 附录C 共用这一份定义。
#       P2020、P2010、P2000 为普查常住人口，统一到 2020 年边界；财政金额为主分析期（默认 2017–2019）年均值，单位元。
# 结果：CODEBOOK 列表；--codebook-only 时导出为 CSV。
# ===========================================================================
CODEBOOK = [
    # ---- 财政水平与结构 ----
    ("fss", "财政自给率（描述）", "fiscal self-sufficiency ratio",
     "一般公共预算收入 / 一般公共预算支出，主分析期均值；只作描述，不进入回归", "比值"),
    ("gap_ratio", "转移支付依赖度（描述）", "transfer dependence ratio", "= 1 − fss，仅作描述", "比值"),
    ("net_inflow_pc", "人均净流入", "net fiscal inflow per capita",
     "(一般公共预算支出 − 一般公共预算收入) / P2010。分母取 2010 年人口，不受此后人口变化影响；净缺口含转移支付、债务收入、调入资金与上年结转", "元/人"),
    ("net_inflow_pc_k", "人均净流入（千元）", "net fiscal inflow per capita, thousand yuan",
     "net_inflow_pc / 1000；回归的核心财政变量，缩尾后以线性形式进入模型", "千元/人"),
    ("own_rev_pc", "人均本级收入", "own-source revenue per capita", "一般公共预算收入 / P2010；回归中取对数", "元/人"),
    ("exp_pc_2010base", "人均支出（2010 年人口为分母）", "expenditure per capita, 2010 population base",
     "一般公共预算支出 / P2010", "元/人"),
    ("net_inflow_pc_rob", "人均净流入（稳健性年份）", "net fiscal inflow per capita, robustness years",
     "同 net_inflow_pc，财政取 fiscal_years_robust（默认 2018、2019、2021）均值", "元/人"),
    ("net_inflow_pc_k_rob", "人均净流入（稳健性年份，千元）", "net fiscal inflow per capita, robustness years, thousand yuan",
     "net_inflow_pc_rob / 1000", "千元/人"),
    ("own_rev_pc_rob", "人均本级收入（稳健性年份）", "own-source revenue per capita, robustness years",
     "稳健性年份一般公共预算收入 / P2010", "元/人"),
    ("exp_pc_2010base_rob", "人均支出（稳健性年份）", "expenditure per capita, robustness years",
     "稳健性年份一般公共预算支出 / P2010", "元/人"),
    ("exp_pc_res", "人均财政支出（常住口径）", "expenditure per resident", "一般公共预算支出 / P2020", "元/人"),
    ("exp_pc_hukou", "人均财政支出（户籍口径）", "expenditure per registered resident", "一般公共预算支出 / 户籍人口", "元/人"),
    ("gap_pc_res", "人均财政缺口（常住口径）", "fiscal gap per resident", "(支出 − 收入) / P2020", "元/人"),
    ("rev_pc_res", "人均本级收入（常住口径）", "own-source revenue per resident", "一般公共预算收入 / P2020", "元/人"),
    ("tax_share", "税收收入占比", "tax share of own revenue", "税收收入 / 一般公共预算收入", "比值"),
    ("transfer_obs_pc", "人均转移支付（观测值）", "observed transfers per capita",
     "转移支付合计 / P2010；只在录入了转移支付的单元计算（2009 年《全国地市县财政统计资料》或试点省决算）", "元/人"),
    ("specific_share", "专项转移支付占比", "specific-purpose share of transfers",
     "专项转移支付 / (一般性转移支付 + 专项转移支付)", "比值"),
    ("tax_rebate_share", "税收返还占比", "tax rebate share of transfers",
     "税收返还 / 转移支付合计；合计缺失时分母取 税收返还 + 一般性转移支付 + 专项转移支付", "比值"),
    ("fss_2010", "财政自给率（2010 期）", "fiscal self-sufficiency, 2009–2011", "2009–2011 年均收入 / 年均支出", "比值"),
    ("net_inflow_pc_2010", "人均净流入（2010 期）", "net fiscal inflow per capita, 2009–2011",
     "(2009–2011 年均支出 − 年均收入) / P2010；与 transfer_obs_pc_2010 对照，检验净缺口代理", "元/人"),
    ("transfer_obs_pc_2010", "人均转移支付（2010 期观测值）", "observed transfers per capita, 2009–2011",
     "2009–2011 年有数年份的转移支付合计均值 / P2010；通常只有 2009 年《全国地市县财政统计资料》一年", "元/人"),
    ("specific_share_2010", "专项转移支付占比（2010 期）", "specific-purpose share of transfers, 2009–2011",
     "专项转移支付 / (一般性转移支付 + 专项转移支付)，2010 期", "比值"),
    ("gap_ratio_2000", "转移支付依赖度（2000 期）", "transfer dependence ratio, 1999–2001",
     "(1999–2001 年均支出 − 年均收入) / 年均支出", "比值"),
    ("transfer_pc_2000_k", "人均转移支付（2000 期，预先确定）", "predetermined transfers per capita, 1999–2001",
     "有转移支付观测值时取 1999–2001 年均转移支付合计（合计缺失时为税收返还、一般性与专项转移支付之和）/ P2000，否则取年均净流入 / P2000，再除以 1000；来源见 transfer_2000_src；长差分的处理变量", "千元/人"),
    ("transfer_2000_src", "2000 期转移支付来源", "source of the 2000 transfer measure",
     "observed 为转移支付观测值，net_inflow 为净缺口代理", "类别"),
    ("exp_edu_share", "教育支出占比", "education share of expenditure", "教育支出 / 一般公共预算支出", "比值"),
    ("exp_health_share", "卫生健康支出占比", "health share of expenditure", "卫生健康支出 / 一般公共预算支出", "比值"),
    ("exp_community_share", "城乡社区支出占比", "urban and rural community affairs share of expenditure",
     "城乡社区支出 / 一般公共预算支出；公园与市政维护最直接的预算科目", "比值"),
    ("exp_personnel_share", "工资福利支出占比", "personnel share of expenditure",
     "工资福利支出（经济分类）/ 一般公共预算支出；检验对立假说 R1", "比值"),
    ("exp_genpub_share", "一般公共服务支出占比", "general public services share of expenditure",
     "一般公共服务支出 / 一般公共预算支出；检验对立假说 R1", "比值"),
    # ---- 土地、债务与国家中心性 ----
    ("land_conv_pc", "人均土地出让价款", "land conveyance revenue per capita",
     "中国土地市场网出让价款（主分析期年均）/ P2010", "元/人"),
    ("land_dep", "土地出让依赖度", "land-conveyance dependence",
     "土地出让价款 / 一般公共预算收入，主分析期均值；全部单元用土地市场网汇总，缺失时用财政表中的土地出让收入", "比值"),
    ("lgfv_debt_pc", "人均城投有息债务", "LGFV interest-bearing debt per capita",
     "城投平台有息债务（主分析期年末均值，按平台所属行政单位归并）/ P2010", "元/人"),
    ("special_bond_pc", "人均新增专项债", "new special-purpose bonds per capita", "文件所列各年新增专项债合计 / P2010", "元/人"),
    ("special_bond_green_pc", "人均市政与绿化类专项债", "municipal, greening and ecological special bonds per capita",
     "市政、园林绿化、生态环保三类新增专项债合计 / P2010", "元/人"),
    ("devzone_share", "开发区核准面积比", "development-zone approved area relative to core",
     "(国家级 + 省级开发区核准面积) / 中心建成区面积；开发区可位于中心建成区外，比值可大于 1", "比值"),
    ("admin_rank", "行政等级", "administrative rank",
     "4 直辖市，3 副省级城市，2 其他省会城市，1 其他地级市（市辖区单元；外围市辖区取所属城市），0 县级市与县；来自 外部参数/admin_rank.csv", "序数"),
    # ---- 人口 ----
    ("pop_chg_1020", "常住人口对数变化 2010–2020", "log change of resident population",
     "ln(P2020 / P2010)，普查常住人口；任一期人口为 0 或缺失时不计算", "对数差"),
    ("pop_chg_0010", "常住人口对数变化 2000–2010", "log change of resident population", "ln(P2010 / P2000)", "对数差"),
    ("res_hukou_ratio", "常住与户籍人口之比", "resident-to-registered ratio", "P2020 / 户籍人口；小于 1 表示人口净流出", "比值"),
    ("urb_rate_2020", "城镇化率 2020", "urbanization rate", "城镇人口 / 常住人口", "比值"),
    ("share_hukou_elsewhere", "人户分离人口比例 2020", "share of residents registered elsewhere",
     "七普表3“户口登记地在外乡镇街道的人口” / 常住人口；含县内跨乡镇迁移，只作流动强度的近似", "比值"),
    ("conv_pop_share_2020", "撤县设区人口占比", "population share of converted districts",
     "市辖区单元 2020 年常住人口中，2000 年后撤县（市）设区的区所占比例", "比值"),
    # ---- 住房 ----
    ("share_rent_market", "市场租赁户比例 2020", "share of households renting on the market",
     "租赁廉租住房、公租房以外住房的家庭户 / 家庭户（七普长表，按户数合并到单元）", "比值"),
    ("share_rent_public", "公租房租赁户比例 2020", "share of households renting public housing",
     "租赁廉租住房或公租房的家庭户 / 家庭户", "比值"),
    ("share_commodity", "商品房户比例 2020", "share of households in purchased commodity housing",
     "购买新建商品房与二手房的家庭户 / 家庭户", "比值"),
    ("share_self_built", "自建房户比例 2020", "share of households in self-built housing", "自建住房的家庭户 / 家庭户", "比值"),
    ("housing_area_pc", "人均住房建筑面积 2020", "housing floor area per household member",
     "家庭户住房建筑面积 / 家庭户人口（按家庭户人口合并到单元）", "m²/人"),
    ("collective_share", "集体户人口比例 2020", "share of population in collective households",
     "集体户人口 / P2020；刻画宿舍劳动体制 (dormitory labour regime)", "比值"),
    ("housing_slack_ratio", "住房余量比", "housing slack ratio",
     "单元 GHSL 住宅建筑面积 ((u_bv_2020 − u_bvn_2020) / 层高) / (人均住房建筑面积 × 家庭户人口 2020)；大于 1 表示空置或季节性居住，小于 1 表示拥挤", "比值"),
    # ---- 中心建成区人口与三种分母 ----
    ("core_pop", "中心建成区人口（主口径）", "core population, main source",
     "按 analysis.core_pop_source 取 core_pop_official 或 core_pop_ghs，缺失时改用另一种，来源见 core_pop_src；低于 analysis.min_core_pop 记为缺失", "人"),
    ("core_pop_src", "中心建成区人口来源", "source of core population", "official 或 ghs", "类别"),
    ("core_pop_ghs", "中心建成区人口（GHS-POP 重标定）", "core population, census-rescaled GHS-POP",
     "GHS-POP 2020 中心建成区求和 × (P2020 / GHS-POP 单元求和)；普查缺失时用未重标定值。GHS-POP 按建筑体量分配人口，隐含各处入住率相同", "人"),
    ("core_pop_official", "中心建成区人口（官方统计）", "core population, official statistics",
     "市辖区与县级市取七普城区常住人口（city_urban_pop_file）；县优先取 2020 年分乡镇街道普查中城关镇与县城街道的常住人口（township.census_township_files），"
     "缺失时取住建部《县城建设统计年鉴》mohurd_stock_year 年县城人口加暂住人口（户籍口径，不是普查常住人口）；来源见 core_pop_official_src", "人"),
    ("core_pop_official_src", "官方中心人口的来源", "source of official core population",
     "census_urban（七普城区人口）、census_town（乡镇街道普查）或 mohurd（住建部城区、县城人口加暂住人口）", "类别"),
    ("town_pop_chg_1020", "县城常住人口对数变化 2010–2020（乡镇街道普查）", "log change of county-town population from township census",
     "ln(城关镇与县城街道 2020 年常住人口 / 2010 年常住人口)；两期都需在 township.census_township_files 中提供，2010 年的 county_adcode 须为 2020 年代码", "对数差"),
    ("core_pop_ratio_official_ghs", "官方与遥感中心人口之比", "official-to-GHS core population ratio",
     "core_pop_official / core_pop_ghs；中心建成区识别的质控指标", "比值"),
    ("core_pop_2010_ghs", "中心建成区人口 2010（GHS-POP 重标定）", "core population 2010, census-rescaled",
     "c_pop_ghs_2010 × P2010 / u_pop_ghs_2010，范围固定为 2020 年中心建成区", "人"),
    ("core_pop_chg_1020", "中心建成区人口对数变化 2010–2020", "log change of core population",
     "ln(core_pop_ghs / core_pop_2010_ghs)；两期各按当年普查重标定", "对数差"),
    ("core_share_2020", "中心建成区人口占单元比例 2020", "core share of unit population",
     "core_pop_ghs / P2020，等于 c_pop_ghs_2020 / u_pop_ghs_2020", "比值"),
    ("core_share_chg_1020", "中心建成区人口占比变化 2010–2020", "change in core share of unit population",
     "core_share_2020 − core_pop_2010_ghs / P2010", "比值差"),
    ("quadrant_town", "单元与中心人口变化四象限", "unit versus core population-change quadrant",
     "按 pop_chg_1020 与 core_pop_chg_1020 的正负分为 县域收缩-县城增长、县域收缩-县城收缩、县域增长-县城增长、县域增长-县城收缩；市辖区单元的县域指单元，县城指中心城区", "类别"),
    ("core_pop_cf2010", "反事实中心建成区人口", "counterfactual core population",
     "core_pop × core_pop_2010_ghs / core_pop_ghs，即固定的 2020 年中心建成区人口停留在 2010 年水平时的主口径中心人口；"
     "变化率取 GHS-POP 重标定的两期，避免混用两种来源；core_pop 缺失时为缺失", "人"),
    ("denom_effect_core", "分母效应", "denominator effect",
     "ln(core_pop_cf2010 / core_pop) = −core_pop_chg_1020，即任一中心人均指标的 ln(实际值) − ln(反事实值)；树木、绿地、大型树木斑块与建成面积四项按构造相同。"
     "正值表示中心人口减少抬高了人均值", "对数差"),
    ("tree_pc_unit", "人均树木覆盖（单元常住口径）", "core tree cover per unit resident", "中心建成区树木面积 / P2020", "m²/人"),
    ("tree_pc_hukou", "人均树木覆盖（户籍口径）", "core tree cover per registered resident", "中心建成区树木面积 / 户籍人口", "m²/人"),
    ("tree_pc_core_cf2010", "人均树木覆盖（反事实分母）", "core tree cover per counterfactual core resident",
     "中心建成区树木面积 / core_pop_cf2010", "m²/人"),
    ("tree_pc_core_ghs", "人均树木覆盖（GHS-POP 分母，稳健性）", "tree cover per capita, GHS-POP denominator",
     "中心建成区树木面积 / core_pop_ghs；低于 min_core_pop 不计算", "m²/人"),
    ("green_pc_unit", "人均绿地（单元常住口径）", "core green space per unit resident", "中心建成区树木 + 灌木 + 草地面积 / P2020", "m²/人"),
    ("green_pc_hukou", "人均绿地（户籍口径）", "core green space per registered resident", "同上 / 户籍人口", "m²/人"),
    ("green_pc_core_cf2010", "人均绿地（反事实分母）", "core green space per counterfactual core resident", "同上 / core_pop_cf2010", "m²/人"),
    ("greenpatch_pc_unit", "人均大型树木斑块（单元常住口径）", "large tree patch area per unit resident", "c_greenpatch_m2_2020 / P2020", "m²/人"),
    ("greenpatch_pc_hukou", "人均大型树木斑块（户籍口径）", "large tree patch area per registered resident", "c_greenpatch_m2_2020 / 户籍人口", "m²/人"),
    ("greenpatch_pc_core_cf2010", "人均大型树木斑块（反事实分母）", "large tree patch area per counterfactual core resident",
     "c_greenpatch_m2_2020 / core_pop_cf2010", "m²/人"),
    ("builtup_pc_unit", "人均建成面积（单元常住口径）", "core built-up surface per unit resident", "c_bs_2020 / P2020", "m²/人"),
    ("builtup_pc_hukou", "人均建成面积（户籍口径）", "core built-up surface per registered resident", "c_bs_2020 / 户籍人口", "m²/人"),
    ("builtup_pc_core_cf2010", "人均建成面积（反事实分母）", "core built-up surface per counterfactual core resident",
     "c_bs_2020 / core_pop_cf2010", "m²/人"),
    # ---- 分子与分母分解（固定的 2020 年中心建成区） ----
    ("dlnS_builtup_1020", "建成面积对数变化 2010–2020", "log change of built-up surface in the fixed core",
     "ln(c_bs_2020 / c_bs_2010)", "对数差"),
    ("dlnS_volume_1020", "建筑体量对数变化 2010–2020", "log change of building volume in the fixed core",
     "ln(c_bv_2020 / c_bv_2010)", "对数差"),
    ("dlnS_imp_1018", "不透水面对数变化 2010–2018（分解表用）", "log change of impervious surface, 2010–2018",
     "ln(c_gaia_imp_m2_2018 / c_gaia_imp_m2_2010)，与 imp_growth_1018_core 相同", "对数差"),
    ("dlnS_imp_0010", "不透水面对数变化 2000–2010（分解表用）", "log change of impervious surface, 2000–2010",
     "ln(c_gaia_imp_m2_2010 / c_gaia_imp_m2_2000)，与 imp_growth_0010_core 相同", "对数差"),
    ("dlnP_core_1020", "中心人口对数变化（分解表用）", "log change of core population", "= core_pop_chg_1020", "对数差"),
    ("dln_builtup_pc_1020", "人均建成面积对数变化 2010–2020", "log change of built-up surface per core resident",
     "dlnS_builtup_1020 − dlnP_core_1020", "对数差"),
    # ---- 遥感：中心建成区 ----
    ("core_area_km2", "中心建成区面积", "core built-up area",
     "GHSL 2020 建成栅格经闭运算、填洞后含驻地点的斑块（无驻地点时取最大斑块）面积", "km²"),
    ("core_fallback", "中心建成区为几何中心缓冲", "core fell back to a centroid buffer",
     "core_method 为 fallback_centroid_1km 时为 1；这类单元的全部中心建成区指标记为缺失", "0/1"),
    ("core_builtcell_share", "中心建成区建成栅格比例", "share of core in built cells before closing",
     "c_builtcell_m2_2020 / core_area_m2；闭运算与填洞前已达建成阈值的 GHSL 栅格占比，越低表示并入的河流、山体与湖泊越多", "比值"),
    ("smod_share_core", "中心建成区中城镇簇比例", "share of core in GHS-SMOD urban clusters",
     "c_smod_ucl_m2_2020 / core_area_m2；SMOD 代码 22、23、30", "比值"),
    ("core_mohurd_ratio", "遥感与住建部建成区面积之比", "remote-sensing to MOHURD built-up area ratio",
     "core_area_km2 / 住建部建成区面积（mohurd_stock_year）", "比值"),
    ("builtup_pc_core", "人均建成面积（中心建成区）", "built-up surface per capita", "GHSL 建成面积 / core_pop", "m²/人"),
    ("tree_area_m2_core", "中心建成区树木面积", "tree cover area in core",
     "WorldCover 树木 (10) 与红树林 (95) 面积之和", "m²"),
    ("tree_share_core", "树木覆盖占比（中心建成区，主口径）", "tree cover share",
     "树木面积 / 各地类面积之和；WorldCover 草地类精度低，故以树木为主口径", "比值"),
    ("tree_pc_core", "人均树木覆盖面积（主口径）", "tree cover per capita", "树木面积 / core_pop", "m²/人"),
    ("tree_stock_pc_core", "人均存量树木", "pre-existing tree cover per capita",
     "c_tree_stock_m2_2020 / core_pop；存量指 Hansen 2000 年树冠覆盖度 ≥ gee.baseline_tree_cover_pct 的 2020 年树木像元", "m²/人"),
    ("tree_new_pc_core", "人均新增树木", "new tree cover per capita", "c_tree_new_m2_2020 / core_pop", "m²/人"),
    ("tree_new_share", "新增树木占比", "share of new tree cover", "c_tree_new_m2_2020 / (c_tree_stock_m2_2020 + c_tree_new_m2_2020)", "比值"),
    ("tree_flat_share", "平缓地树木占比", "share of tree cover on gentle slopes",
     "c_tree_flat_m2_2020 / 树木面积；坡度 ≤ gee.slope_mask_deg，用于排除山体残林的敏感性检验", "比值"),
    ("green_share_core", "绿地占比（稳健性口径）", "green share", "树木 + 灌木 + 草地面积 / 各地类面积之和", "比值"),
    ("green_pc_core", "人均绿地面积（稳健性口径）", "green space per capita", "树木 + 灌木 + 草地面积 / core_pop", "m²/人"),
    ("expo_tree_core", "人口加权树木暴露（主口径）", "population-weighted tree-cover exposure",
     "Σ(格网人口 × 格网周围 500 m 树木覆盖比例) / Σ格网人口（Chen et al. 2022）", "比值"),
    ("expo_green_core", "人口加权绿地暴露（稳健性口径）", "population-weighted greenspace exposure",
     "同上，绿地为树木、灌木与草地", "比值"),
    ("ndvi_core", "中心建成区 NDVI", "mean NDVI (Sentinel-2)", "2020 年 5–9 月 Sentinel-2 中值合成 NDVI 均值，剔除水面", "无量纲"),
    ("ndvi_ring", "自然植被本底", "background NDVI (MODIS, 5 km ring)", "中心建成区外 5 km 环带非建成栅格 MODIS NDVI 均值，剔除水面", "无量纲"),
    ("ndvi_gap", "城区相对本底的绿度差", "core-minus-background NDVI", "ndvi_core − ndvi_ring", "无量纲"),
    ("greenpatch_pc_core", "人均大型树木斑块", "large tree patch area per capita",
     "中心建成区内面积 ≥ gee.green_patch_min_m2 的连通树木斑块面积 / core_pop；地类由 gee.green_patch_class 设定（默认只用树木），连通计数前先截断于中心建成区。遥感代理不称公园，公园一词只用于矢量数据", "m²/人"),
    ("greenpatch_access_share", "大型树木斑块 500 m 可达人口比例", "share of population within 500 m of a large tree patch",
     "斑块 500 m 范围内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口", "比值"),
    ("riparian_green_pc", "人均滨水线性绿地", "riparian linear green space per capita",
     "近永久水体外扩 gee.riparian_buffer_m 内的绿地面积 / core_pop；水体为 JRC 出现频率 ≥ gee.riparian_water_occurrence 且连通水面 ≥ gee.riparian_min_water_m2，或 gee.river_asset；绿地地类同大型树木斑块", "m²/人"),
    ("roadside_green_pc", "人均道路绿带（行道树代理，辅助指标）", "roadside green per capita, street-tree proxy",
     "GHSL 2018 道路面外扩 gee.road_buffer_m 内的绿地面积 / core_pop", "m²/人"),
    ("greenway_len_per_10k", "每万人绿道长度", "greenway length per 10,000 core residents",
     "c_greenway_len_m / (core_pop / 10000)；需提供 gee.greenway_asset 矢量", "m/万人"),
    ("greenway_access_share", "绿道可达人口比例", "share of population near a greenway",
     "绿道 gee.greenway_access_distance_m 范围内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口", "比值"),
    ("openveg_share_2018", "聚落内植被开放空间占比（2018）", "vegetated open space share (GHS-BUILT-C)",
     "GHSL 2018 聚落特征 1–3 类面积 / 各地类面积之和", "比值"),
    ("road_share_2018", "道路面占比（2018）", "road surface share (GHS-BUILT-C)", "GHSL 2018 聚落特征 5 类面积 / 各地类面积之和", "比值"),
    ("park_pc_core", "人均公园面积（可选）", "park area per capita", "公园多边形面积 / core_pop（需提供公园矢量）", "m²/人"),
    ("park_access_share", "公园步行可达人口比例（可选）", "share of population within walking distance of a park",
     "公园 500 m 缓冲区内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口", "比值"),
    ("floor_res_pc_core", "人均住宅建筑面积（遥感估算）", "residential floor area per capita (GHSL volume)",
     "(总建筑体量 − 非住宅体量) / 层高 / core_pop", "m²/人"),
    ("floor_res_pc_unit", "人均住宅建筑面积（单元，遥感估算）", "residential floor area per resident",
     "单元内 (总体量 − 非住宅体量) / 层高 / P2020", "m²/人"),
    ("ntl_per_built", "单位建成面积夜间灯光", "night-light radiance per km² built-up",
     "VIIRS 2020 average_masked 求和 / 中心建成区建成面积（km²）；受路灯影响，只作辅助指标", "nW/cm²/sr per km²"),
    ("ntl_per_volume", "单位建筑体量夜间灯光", "night-light radiance per building volume",
     "中心建成区 VIIRS 2020 求和 / 建筑体量（百万 m³）", "nW/cm²/sr per 10⁶ m³"),
    ("ntl_pc", "人均夜间灯光", "night-light radiance per resident", "单元 VIIRS 2020 求和 / P2020", "nW/cm²/sr per 人"),
    ("core_growth_1020", "中心建成区面积对数变化", "log change of core area", "ln(2020 动态核心面积 / 2010 动态核心面积)", "对数差"),
    ("lcrpgr", "土地消耗率与人口增长率之比 (SDG 11.3.1)", "land consumption rate to population growth rate ratio",
     "ln(A2020/A2010) / ln(P2020/P2010)，P 为单元常住人口；人口变化接近 0 时不计算", "比值"),
    ("land_pop_diverge", "扩张与收缩背离", "built-up expansion under population decline",
     "中心建成区面积增长且常住人口下降 = 1", "0/1"),
    ("imp_growth_0010_core", "不透水面对数变化 2000–2010（中心建成区）", "log change of impervious surface in core, 2000–2010",
     "ln(c_gaia_imp_m2_2010 / c_gaia_imp_m2_2000)，范围固定为 2020 年中心建成区；GAIA", "对数差"),
    ("imp_growth_1018_core", "不透水面对数变化 2010–2018（中心建成区）", "log change of impervious surface in core, 2010–2018",
     "ln(c_gaia_imp_m2_2018 / c_gaia_imp_m2_2010)", "对数差"),
    ("imp_growth_0010_unit", "不透水面对数变化 2000–2010（单元）", "log change of impervious surface in unit, 2000–2010",
     "ln(u_gaia_imp_m2_2010 / u_gaia_imp_m2_2000)", "对数差"),
    ("imp_growth_1018_unit", "不透水面对数变化 2010–2018（单元）", "log change of impervious surface in unit, 2010–2018",
     "ln(u_gaia_imp_m2_2018 / u_gaia_imp_m2_2010)", "对数差"),
    ("forest_share_clcd_YYYY", "CLCD 森林占比（可选）", "CLCD forest share of core",
     "c_clcdYYYY_forest_m2 / 当年各 CLCD 地类面积之和，YYYY 取 gee.clcd_years；需配置 gee.clcd_asset_template", "比值"),
    ("green_new_clcd_share", "CLCD 新增绿地占比（可选）", "share of CLCD green that is new since the baseline year",
     "c_green_new_clcd_m2_2020 / 2020 年 CLCD 森林、灌木与草地面积；新增指 2020 年为这三类、而 gee.clcd_baseline_year 时为耕地、裸地或不透水面，两端都用 CLCD", "比值"),
    # ---- 社会基础设施 ----
    ("beds_per_1k_res", "每千常住人口床位", "hospital beds per 1,000 residents",
     "医疗卫生机构床位（主分析期均值）/ P2020 × 1000", "张/千人"),
    ("beds_per_1k_hukou", "每千户籍人口床位", "hospital beds per 1,000 registered residents", "床位 / 户籍人口 × 1000", "张/千人"),
    ("students_per_child", "在校生与 0–14 岁人口之比", "enrolled students per child aged 0–14",
     "(小学 + 普通中学在校生) / (share_0_14 × P2020)；学龄与 0–14 岁并不对应，只是近似", "比值"),
    ("welfare_beds_per_1k_65", "每千名 65 岁以上老人养老床位", "welfare beds per 1,000 residents aged 65+",
     "社会福利收养性单位床位 / (share_65plus × P2020) × 1000", "张/千人"),
    ("teachers_per_100_students", "每百名学生专任教师", "full-time teachers per 100 students",
     "专任教师 / (小学 + 普通中学在校生) × 100", "人/百人"),
] + [
    (f"{k}_access_share", f"{zh}可达人口比例（可选）", f"share of core population near a {en}",
     f"{zh}点位 gee.poi_access_distance_m.{k} 范围内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口；需提供 gee.poi_assets.{k}", "比值")
    for k, zh, en in (("school", "学校", "school"), ("hospital", "医院", "hospital"), ("elderly", "养老机构", "care home"))
] + [
    (f"{k}_per_10k", f"每万人{zh}数（可选）", f"{en}s per 10,000 core residents",
     f"中心建成区内{zh}点位数 / core_pop × 10000", "个/万人")
    for k, zh, en in (("school", "学校", "school"), ("hospital", "医院", "hospital"), ("elderly", "养老机构", "care home"))
] + [
    # ---- 住建部城市与县城建设统计 ----
    ("park_count", "公园个数（住建部）", "number of parks (MOHURD)", "mohurd_stock_year 年鉴报告值", "个"),
    ("park_area_pc_mohurd", "人均公园面积（住建部，中心人口分母）", "park area per core resident (MOHURD)",
     "公园面积（公顷）× 10000 / core_pop；县的 core_pop 主口径取自住建部县城人口加暂住人口，与年鉴分母同源，core_pop_source 设为 ghs 时改用普查重标定人口", "m²/人"),
    ("road_area_pc_mohurd", "人均道路面积（住建部，中心人口分母）", "road area per core resident (MOHURD)",
     "道路面积（万 m²）× 10000 / core_pop", "m²/人"),
    ("park_green_pc_m2", "人均公园绿地面积（住建部报告值）", "park green space per capita as reported",
     "年鉴报告值，分母为城区（县城）人口加暂住人口", "m²/人"),
    ("mohurd_builtup_area_km2", "建成区面积（住建部）", "built-up area (MOHURD)", "mohurd_stock_year 年鉴报告值", "km²"),
    ("muni_invest_pc", "人均市政公用设施投资", "municipal infrastructure investment per core resident",
     "mohurd_years_main 年均市政公用设施建设固定资产投资 / core_pop", "元/人"),
    ("muni_invest_green_pc", "人均园林绿化投资", "landscaping investment per core resident", "年均园林绿化投资 / core_pop", "元/人"),
    ("muni_invest_road_pc", "人均道路桥梁投资", "road and bridge investment per core resident", "年均道路桥梁投资 / core_pop", "元/人"),
    ("fund_fiscal_share", "财政拨款占资金来源比例", "fiscal appropriation share of funding",
     "(中央财政拨款 + 地方财政拨款) / 资金来源合计；各项先取 mohurd_years_main 的年均值（缺报年份不计入该项均值）再相除", "比值"),
    ("fund_debt_share", "债券与贷款占资金来源比例", "bond and loan share of funding", "(债券 + 国内贷款) / 资金来源合计", "比值"),
    ("fund_self_share", "自筹资金占资金来源比例", "self-raised share of funding", "自筹资金 / 资金来源合计", "比值"),
    ("maint_subsidy_share", "维护建设资金中上级补助比例", "upper-level subsidy share of maintenance funds",
     "上级补助 / 城市（县城）维护建设资金收入合计", "比值"),
    ("maint_land_share", "维护建设资金中土地出让转入比例", "land-revenue share of maintenance funds",
     "土地出让转入 / 维护建设资金收入合计", "比值"),
    ("green_official_ratio", "官方与遥感人均绿地之比（可选）", "official-to-remote-sensing green ratio",
     "住建部人均公园绿地面积 / 遥感人均绿地面积", "比值"),
    ("green_official_gap", "官方与遥感绿地对数差", "log gap between official and remote-sensing green",
     "ln(park_green_pc_m2) − ln(greenpatch_pc_core)", "对数差"),
    # ---- 分组 ----
    ("city_size_class", "城市规模等级（市辖区）", "city size class (State Council 2014)",
     "按城区常住人口（万人）套用国发〔2014〕51号标准；超大特大按七普名单", "类别"),
    ("size_class_all", "城市规模等级（全部单元）", "size class for all units",
     "同一标准推广到全部单元：市辖区取 city_size_class，县级市取七普城区人口，县取住建部县城人口加暂住人口", "类别"),
    ("admin_size_group", "行政类型与规模交叉分组", "administrative type by size class",
     "单元类型 × size_class_all，如 县级市｜Ⅱ型小城市；用于在同一规模档内比较不同行政类型", "类别"),
    ("large_county_city", "大县级市", "large county-level city", "县级市且城区人口达到Ⅱ型大城市标准（≥ 100 万）为 1", "0/1"),
    ("group5", "五类分组", "five-group typology",
     "超大特大城市市辖区 / 大城市市辖区 / 中小城市市辖区 / 县级市 / 县；另有 外围市辖区，以及城区人口缺失、无法分级的 市辖区（规模未知）", "类别"),
    ("quadrant", "财政与人口四象限", "fiscal–demographic quadrant", "财政自给率是否 ≥ 阈值 × 常住人口是否增长", "类别"),
    ("excluded", "排除单元", "excluded unit",
     "代码以 units.exclude_code_prefixes 或 analysis.exclude_code_prefixes 开头（默认兵团城市 6590xx）；保留在地图中，不进入表格与回归", "0/1"),
    ("fiscal_scope_mismatch", "财政口径与单元不一致", "fiscal scope mismatch",
     "units.city_proper_custom 中的城市（默认重庆）只把中心城区作为市辖区单元，财政却仍为《城市统计年鉴》全部市辖区合计时为 1；"
     "这类单元的全部财政指标记为缺失，也不进入回归。逐区录入财政并列入 fiscal_census.district_level_fiscal_prefs 后为 0", "0/1"),
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
    return pd.to_numeric(df[name], errors="coerce") if name in df else pd.Series(np.nan, index=df.index)


def pick_col(df, pattern: str, prefer: str | None = None):
    """按正则取第一个匹配的列名；prefer 为优先的距离后缀（如 500）。"""
    cands = [c for c in df.columns if re.fullmatch(pattern, c)]
    if prefer is not None:
        for c in cands:
            if re.fullmatch(pattern.replace(r"(\d+)", str(prefer)), c):
                return c
    return cands[0] if cands else None


# ===========================================================================
# 代码块 2：城市规模、五类分组与交叉分组
# 目的：市辖区单元按城区常住人口套用 2014 年标准分级；超大、特大城市以官方七普名单为准（外部参数/megacities_2020.csv）；
#       县级市、县各自成组；district_outer（如重庆主城区以外的市辖区）单列；
#       城区人口缺失、又不在七普名单中的市辖区单元无法分级，标为“市辖区（规模未知）”，不默认归入中小城市。
#       规模分级再推广到全部单元（县级市用七普城区人口，县用住建部县城人口），与单元类型交叉，
#       以便在同一规模档内比较县级市与市辖区，分离财政层级与规模的作用。
# 结果：新增 city_size_class、group5、size_class_all、admin_size_group、large_county_city。
# ===========================================================================
TYPE_ZH = {"city_proper": "市辖区", "county_city": "县级市", "county": "县", "district_outer": "外围市辖区"}


def assign_groups(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    df = df.copy()
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
        df = df.drop(columns="mega_class").copy()

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

    # 全部单元的规模分级：县级市用七普城区人口（缺失时用住建部城区人口），县用住建部县城人口 + 暂住人口
    upop = col(df, "urban_pop_total_10k")
    mohurd_pop = col(df, "mohurd_pop_total_10k")
    pop_all = pd.Series(np.nan, index=df.index)
    pop_all[cp] = upop[cp]
    cc = df["unit_type"] == "county_city"
    pop_all[cc] = upop[cc].fillna(mohurd_pop[cc])
    ct = df["unit_type"] == "county"
    pop_all[ct] = mohurd_pop[ct]
    df["urban_pop_all_10k"] = pop_all
    sc = pop_all.map(size_class)
    sc[cp] = df.loc[cp, "city_size_class"]
    df["size_class_all"] = sc
    tz = df["unit_type"].map(TYPE_ZH).fillna(df["unit_type"])
    df["admin_size_group"] = [f"{t}｜{s}" if isinstance(s, str) else f"{t}｜规模未知" for t, s in zip(tz, sc)]
    big = std.loc[std["class_zh"] == "Ⅱ型大城市", "min_urban_pop_10k"]
    cut = float(big.iloc[0]) if len(big) else 100.0
    lcc = pd.Series(0.0, index=df.index)
    lcc[cc] = (pop_all[cc] >= cut).astype(float).where(pop_all[cc].notna())
    df["large_county_city"] = lcc.astype("Int64")
    if int(df["large_county_city"].sum()):
        LOG.info(f"城区人口达到Ⅱ型大城市标准的县级市 {int(df['large_county_city'].sum())} 个："
                 f"{df.loc[df['large_county_city'] == 1, 'unit_id'].tolist()[:20]}")
    return df


# ===========================================================================
# 代码块 3：计算全部指标
# 目的：按 CODEBOOK 的公式逐项计算；分母为 0 或缺失时结果为缺失；中心建成区人口过小的单元不计算人均指标。
#       中心建成区退化为几何中心 1 km 缓冲（core_method = fallback_centroid_1km）的单元，
#       其 c_、r_ 字段与中心建成区面积全部置为缺失，所有基于中心建成区的指标随之缺失，并按分组记录数量。
#       财政口径与单元不一致（fiscal_scope_mismatch，如重庆只取主城九区而财政为全部市辖区合计）的单元，
#       财政表的全部字段置为缺失：分子覆盖全部市辖区、分母只含中心城区，人均值与比值都不对应这个单元。
# 结果：df 新增全部指标列。
# ===========================================================================
# 02 输出的财政表字段（与 02 的 FISCAL_VARS 一致），后缀为 main、rob、y2010、y2000
FISCAL_TABLE_VARS = ("gen_budget_revenue", "gen_budget_expenditure", "tax_revenue", "land_conveyance_revenue", "gdp",
                     "tax_rebate", "transfer_general", "transfer_specific", "transfer_total", "fund_budget_revenue",
                     "exp_education", "exp_health", "exp_community", "exp_personnel", "exp_general_public",
                     "students_primary", "students_secondary", "teachers_fulltime", "hospital_beds", "welfare_beds",
                     "pop_hukou_yearend")
FISCAL_SUFFIXES = ("main", "rob", "y2010", "y2000")


def blank_scope_mismatch(df: pd.DataFrame) -> pd.DataFrame:
    if "fiscal_scope_mismatch" not in df:
        return df
    mm = df["fiscal_scope_mismatch"].astype("string").str.lower().isin(["true", "1"]).fillna(False).astype(bool)
    df["fiscal_scope_mismatch"] = mm.astype(int)
    if mm.any():
        cols = [f"{v}_{s}" for v in FISCAL_TABLE_VARS for s in FISCAL_SUFFIXES if f"{v}_{s}" in df]
        df.loc[mm, cols] = np.nan
        LOG.warning(f"{int(mm.sum())} 个单元的财政为全部市辖区口径、单元只含中心城区，财政指标记为缺失："
                    f"{df.loc[mm, 'unit_id'].tolist()}。逐区录入财政并写入 district_level_fiscal_prefs 后即可使用。")
    return df


def blank_fallback_cores(df: pd.DataFrame) -> pd.DataFrame:
    method = df["core_method"].astype("string") if "core_method" in df else pd.Series(pd.NA, index=df.index, dtype="string")
    fb = method.eq(FALLBACK_CORE).fillna(False).astype(bool)
    df["core_fallback"] = fb.astype(int).where(method.notna())
    if fb.any():
        raw = [c for c in df.columns if c.startswith(("c_", "r_"))] + ["core_area_m2"]
        df.loc[fb, [c for c in raw if c in df]] = np.nan
        by = df.loc[fb, "group5"].value_counts() if "group5" in df else pd.Series(dtype=int)
        LOG.warning(f"{int(fb.sum())} 个单元的中心建成区为几何中心 1 km 缓冲，全部中心建成区指标记为缺失。按分组：\n"
                    + by.to_string())
    if "core2010_method" in df:
        fb10 = df["core2010_method"].astype("string").eq(FALLBACK_CORE).fillna(False).astype(bool)
        if fb10.any():
            df.loc[fb10, "core2010_area_m2"] = np.nan
            LOG.warning(f"{int(fb10.sum())} 个单元的 2010 年中心建成区为几何中心缓冲，core_growth_1020 记为缺失。")
    return df


def compute(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    df = df.copy()   # 合并后的表由许多小块组成，先整理成连续内存，避免逐列新增指标时出现 PerformanceWarning
    df = blank_fallback_cores(df)
    df = blank_scope_mismatch(df)
    a = cfg["analysis"]
    g = cfg.get("gee", {})
    storey = float(a["storey_height_m"])
    min_pop = float(a["min_core_pop"])
    new = {}   # 新指标先放进字典，最后一次性拼接

    rev, exp = col(df, "gen_budget_revenue_main"), col(df, "gen_budget_expenditure_main")
    p20, p10, p00 = col(df, "pop_resident_2020"), col(df, "pop_resident_2010"), col(df, "pop_resident_2000")
    hukou = col(df, "pop_hukou_yearend_main").fillna(col(df, "pop_hukou_2020"))

    # 3a 财政：比值只作描述；水平量以 2010 年人口为分母
    new["fss"] = safe_div(rev, exp)
    new["gap_ratio"] = safe_div(exp - rev, exp)
    new["net_inflow_pc"] = safe_div(exp - rev, p10)
    new["net_inflow_pc_k"] = new["net_inflow_pc"] / 1000
    new["own_rev_pc"] = safe_div(rev, p10)
    new["exp_pc_2010base"] = safe_div(exp, p10)
    rev_r, exp_r = col(df, "gen_budget_revenue_rob"), col(df, "gen_budget_expenditure_rob")
    new["net_inflow_pc_rob"] = safe_div(exp_r - rev_r, p10)
    new["net_inflow_pc_k_rob"] = new["net_inflow_pc_rob"] / 1000
    new["own_rev_pc_rob"] = safe_div(rev_r, p10)
    new["exp_pc_2010base_rob"] = safe_div(exp_r, p10)
    new["exp_pc_res"] = safe_div(exp, p20)
    new["exp_pc_hukou"] = safe_div(exp, hukou)
    new["gap_pc_res"] = safe_div(exp - rev, p20)
    new["rev_pc_res"] = safe_div(rev, p20)
    new["tax_share"] = safe_div(col(df, "tax_revenue_main"), rev)
    tr_g, tr_s, tr_r = col(df, "transfer_general_main"), col(df, "transfer_specific_main"), col(df, "tax_rebate_main")
    tr_tot = col(df, "transfer_total_main").fillna(tr_g + tr_s + tr_r)
    new["transfer_obs_pc"] = safe_div(tr_tot, p10)
    new["specific_share"] = safe_div(tr_s, tr_g + tr_s)
    new["tax_rebate_share"] = safe_div(tr_r, tr_tot)
    rev10, exp10 = col(df, "gen_budget_revenue_y2010"), col(df, "gen_budget_expenditure_y2010")
    new["fss_2010"] = safe_div(rev10, exp10)
    new["net_inflow_pc_2010"] = safe_div(exp10 - rev10, p10)
    g10, s10 = col(df, "transfer_general_y2010"), col(df, "transfer_specific_y2010")
    tot10 = col(df, "transfer_total_y2010").fillna(g10 + s10 + col(df, "tax_rebate_y2010"))
    new["transfer_obs_pc_2010"] = safe_div(tot10, p10)
    new["specific_share_2010"] = safe_div(s10, g10 + s10)
    rev00, exp00 = col(df, "gen_budget_revenue_y2000"), col(df, "gen_budget_expenditure_y2000")
    new["gap_ratio_2000"] = safe_div(exp00 - rev00, exp00)
    # 与主分析期、2010 期相同：合计缺失时用 税收返还 + 一般性转移支付 + 专项转移支付（《全国地市县财政统计资料》常只给分项）
    obs00 = col(df, "transfer_total_y2000").fillna(
        col(df, "transfer_general_y2000") + col(df, "transfer_specific_y2000") + col(df, "tax_rebate_y2000"))
    t00 = obs00.where(obs00.notna(), exp00 - rev00)
    new["transfer_pc_2000_k"] = safe_div(t00, p00) / 1000
    new["transfer_2000_src"] = pd.Series(np.where(obs00.notna(), "observed",
                                                  np.where((exp00 - rev00).notna(), "net_inflow", None)), index=df.index)
    for v, c in [("exp_edu_share", "exp_education"), ("exp_health_share", "exp_health"),
                 ("exp_community_share", "exp_community"), ("exp_personnel_share", "exp_personnel"),
                 ("exp_genpub_share", "exp_general_public")]:
        new[v] = safe_div(col(df, f"{c}_main"), exp)

    # 3b 土地、债务与国家中心性
    land = col(df, "land_conv_revenue_main").fillna(col(df, "land_conveyance_revenue_main"))
    new["land_conv_pc"] = safe_div(col(df, "land_conv_revenue_main"), p10)
    new["land_dep"] = safe_div(land, rev)
    new["lgfv_debt_pc"] = safe_div(col(df, "lgfv_debt_main"), p10)
    new["special_bond_pc"] = safe_div(col(df, "special_bond_total"), p10)
    new["special_bond_green_pc"] = safe_div(col(df, "special_bond_green_sub"), p10)
    core_km2 = col(df, "core_area_m2") / 1e6
    dz = col(df, "devzone_nat_km2").fillna(0) + col(df, "devzone_prov_km2").fillna(0)
    dz = dz.where(col(df, "devzone_nat_km2").notna() | col(df, "devzone_prov_km2").notna())
    # 开发区目录已提供时，没有开发区的单元记为 0，而不是缺失
    if "devzone_nat_km2" in df or "devzone_prov_km2" in df:
        dz = dz.fillna(0)
    new["devzone_share"] = safe_div(dz, core_km2)

    # 3c 人口
    pc = safe_log(safe_div(p20, p10))
    new["pop_chg_1020"] = pc
    new["pop_chg_0010"] = safe_log(safe_div(p10, p00))
    new["res_hukou_ratio"] = safe_div(p20, hukou)
    new["urb_rate_2020"] = safe_div(col(df, "pop_urban_2020"), p20)
    new["share_hukou_elsewhere"] = safe_div(col(df, "pop_hukou_elsewhere_2020"), p20)

    # 3d 住房
    new["share_rent_market"] = col(df, "share_rent_market_2020")
    new["share_rent_public"] = col(df, "share_rent_public_2020")
    new["share_commodity"] = col(df, "share_buy_new_2020") + col(df, "share_buy_second_2020")
    new["share_self_built"] = col(df, "share_self_built_2020")
    new["housing_area_pc"] = col(df, "housing_area_pc_2020")
    new["collective_share"] = safe_div(col(df, "collective_pop_2020"), p20)
    res_floor_unit = (col(df, "u_bv_2020") - col(df, "u_bvn_2020")) / storey
    new["housing_slack_ratio"] = safe_div(res_floor_unit, new["housing_area_pc"] * col(df, "hh_pop_2020"))

    # 3e 中心建成区人口：官方统计与 GHS-POP 重标定两种来源，按 core_pop_source 取主口径
    core_ghs = col(df, "c_pop_ghs_2020") * safe_div(p20, col(df, "u_pop_ghs_2020"))
    core_ghs = core_ghs.fillna(col(df, "c_pop_ghs_2020"))
    official = col(df, "core_pop_official")
    src = str(a.get("core_pop_source", "official")).strip().lower()
    first, second, other = (official, core_ghs, "ghs") if src == "official" else (core_ghs, official, "official")
    src = "official" if src == "official" else "ghs"
    core_raw = first.fillna(second)
    new["core_pop_src"] = pd.Series(np.where(first.notna(), src, np.where(second.notna(), other, None)), index=df.index)
    core_pop = core_raw.where(core_raw >= min_pop)
    new["core_pop"] = core_pop
    new["core_pop_ghs"] = core_ghs
    new["core_pop_official"] = official
    new["core_pop_ratio_official_ghs"] = safe_div(official, core_ghs)
    core10 = col(df, "c_pop_ghs_2010") * safe_div(p10, col(df, "u_pop_ghs_2010"))
    new["core_pop_2010_ghs"] = core10
    cpc = safe_log(safe_div(core_ghs, core10))
    new["core_pop_chg_1020"] = cpc
    new["core_share_2020"] = safe_div(core_ghs, p20)
    new["core_share_chg_1020"] = new["core_share_2020"] - safe_div(core10, p10)
    qt = pd.Series([f"{'县域增长' if x >= 0 else '县域收缩'}-{'县城增长' if y >= 0 else '县城收缩'}"
                    for x, y in zip(pc.fillna(0), cpc.fillna(0))], index=df.index)
    new["quadrant_town"] = qt.where(pc.notna() & cpc.notna())
    # 反事实分母：主口径中心人口按 GHS-POP 重标定的两期变化率折回 2010 年（固定的 2020 年中心建成区），
    # 变化率只取同一来源，避免“官方 2020 年人口 / 格网 2010 年人口”混用两种口径
    cf = core_pop * safe_div(core10, core_ghs)
    new["core_pop_cf2010"] = cf
    new["denom_effect_core"] = safe_log(safe_div(cf, core_pop))
    new["town_pop_chg_1020"] = safe_log(safe_div(col(df, "town_pop_census_2020"), col(df, "town_pop_census_2010")))
    core_ghs_ok = core_ghs.where(core_ghs >= min_pop)

    # 3f 遥感面积：树木含红树林；绿地 = 树木 + 灌木 + 草地
    wc_cols = [c for c in df.columns if c.startswith("c_wc_") and c.endswith("_m2")]
    wc_total = df[wc_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1) if wc_cols else pd.Series(np.nan, index=df.index)
    tree = (col(df, "c_wc_tree_m2").fillna(0) + col(df, "c_wc_mangrove_m2").fillna(0)).where(wc_total.notna())
    green = (tree + col(df, "c_wc_shrub_m2").fillna(0) + col(df, "c_wc_grass_m2").fillna(0)).where(wc_total.notna())
    patch = col(df, "c_greenpatch_m2_2020")
    bs20 = col(df, "c_bs_2020")
    new["tree_area_m2_core"] = tree
    for stem, num in (("tree", tree), ("green", green), ("greenpatch", patch), ("builtup", bs20)):
        new[f"{stem}_pc_core"] = safe_div(num, core_pop)
        new[f"{stem}_pc_unit"] = safe_div(num, p20)
        new[f"{stem}_pc_hukou"] = safe_div(num, hukou)
        new[f"{stem}_pc_core_cf2010"] = safe_div(num, cf)
    new["tree_pc_core_ghs"] = safe_div(tree, core_ghs_ok)

    # 3g 分子与分母分解（固定的 2020 年中心建成区）
    new["dlnS_builtup_1020"] = safe_log(safe_div(bs20, col(df, "c_bs_2010")))
    new["dlnS_volume_1020"] = safe_log(safe_div(col(df, "c_bv_2020"), col(df, "c_bv_2010")))
    # GAIA 年份固定为 2000、2010、2018（指标名中的年份），与 gee.gaia_years 的默认值一致
    y0, y1, y2 = 2000, 2010, 2018
    new["imp_growth_0010_core"] = safe_log(safe_div(col(df, f"c_gaia_imp_m2_{y1}"), col(df, f"c_gaia_imp_m2_{y0}")))
    new["imp_growth_1018_core"] = safe_log(safe_div(col(df, f"c_gaia_imp_m2_{y2}"), col(df, f"c_gaia_imp_m2_{y1}")))
    new["imp_growth_0010_unit"] = safe_log(safe_div(col(df, f"u_gaia_imp_m2_{y1}"), col(df, f"u_gaia_imp_m2_{y0}")))
    new["imp_growth_1018_unit"] = safe_log(safe_div(col(df, f"u_gaia_imp_m2_{y2}"), col(df, f"u_gaia_imp_m2_{y1}")))
    new["dlnS_imp_1018"] = new["imp_growth_1018_core"]
    new["dlnS_imp_0010"] = new["imp_growth_0010_core"]
    new["dlnP_core_1020"] = cpc
    new["dln_builtup_pc_1020"] = new["dlnS_builtup_1020"] - cpc

    # 3h 中心建成区质控
    new["core_area_km2"] = core_km2
    new["core_builtcell_share"] = safe_div(col(df, "c_builtcell_m2_2020"), col(df, "core_area_m2"))
    new["smod_share_core"] = safe_div(col(df, "c_smod_ucl_m2_2020"), col(df, "core_area_m2"))
    new["core_mohurd_ratio"] = safe_div(core_km2, col(df, "mohurd_builtup_area_km2"))

    # 3i 绿地与建成强度
    new["tree_share_core"] = safe_div(tree, wc_total)
    stock, newtree = col(df, "c_tree_stock_m2_2020"), col(df, "c_tree_new_m2_2020")
    new["tree_stock_pc_core"] = safe_div(stock, core_pop)
    new["tree_new_pc_core"] = safe_div(newtree, core_pop)
    new["tree_new_share"] = safe_div(newtree, stock + newtree)
    new["tree_flat_share"] = safe_div(col(df, "c_tree_flat_m2_2020"), tree)
    new["expo_tree_core"] = safe_div(col(df, "c_pw_tree_2020"), col(df, "c_pop_expo_2020"))
    new["expo_green_core"] = safe_div(col(df, "c_pw_green_2020"), col(df, "c_pop_expo_2020"))
    new["green_share_core"] = safe_div(green, wc_total)
    new["ndvi_core"] = col(df, "c_ndvi_s2_2020")
    new["ndvi_ring"] = col(df, "r_ndvi_modis_2020")
    new["ndvi_gap"] = new["ndvi_core"] - new["ndvi_ring"]
    gp_pop = pick_col(df, r"c_pop_greenpatch(\d+)_2020", 500)
    # 分子是未重标定的 GHS-POP，分母也必须用同一口径的 GHS-POP（c_pop_expo_2020），否则比例会偏离甚至大于 1
    new["greenpatch_access_share"] = safe_div(col(df, gp_pop), col(df, "c_pop_expo_2020")) if gp_pop else np.nan
    new["riparian_green_pc"] = safe_div(col(df, "c_riparian_green_m2_2020"), core_pop)
    new["roadside_green_pc"] = safe_div(col(df, "c_roadside_green_m2_2020"), core_pop)
    new["greenway_len_per_10k"] = safe_div(col(df, "c_greenway_len_m"), core_pop / 1e4)
    gw_pop = pick_col(df, r"c_pop_greenway(\d+)_2020", g.get("greenway_access_distance_m"))
    new["greenway_access_share"] = safe_div(col(df, gw_pop), col(df, "c_pop_expo_2020")) if gw_pop else np.nan
    new["openveg_share_2018"] = safe_div(col(df, "c_openveg_m2_2018"), wc_total)
    new["road_share_2018"] = safe_div(col(df, "c_road_m2_2018"), wc_total)
    new["park_pc_core"] = safe_div(col(df, "c_park_m2_2020"), core_pop)
    park_pop = pick_col(df, r"c_pop_park(\d+)_2020", g.get("park_access_distance_m"))
    new["park_access_share"] = safe_div(col(df, park_pop), col(df, "c_pop_expo_2020")) if park_pop else np.nan
    new["floor_res_pc_core"] = safe_div((col(df, "c_bv_2020") - col(df, "c_bvn_2020")) / storey, core_pop)
    new["floor_res_pc_unit"] = safe_div(res_floor_unit, p20)
    new["ntl_per_built"] = safe_div(col(df, "c_ntl_viirs_2020"), bs20 / 1e6)
    new["ntl_per_volume"] = safe_div(col(df, "c_ntl_viirs_2020"), col(df, "c_bv_2020") / 1e6)
    new["ntl_pc"] = safe_div(col(df, "u_ntl_viirs_2020"), p20)
    a20, a10 = col(df, "core_area_m2"), col(df, "core2010_area_m2")
    new["core_growth_1020"] = safe_log(safe_div(a20, a10))
    new["lcrpgr"] = safe_div(new["core_growth_1020"], pc.where(pc.abs() >= 0.01))
    new["land_pop_diverge"] = ((new["core_growth_1020"] > 0) & (pc < 0)).astype("Int64").where(
        new["core_growth_1020"].notna() & pc.notna())

    # 3j CLCD（可选）：各年森林占比与新增绿地占比
    clcd = {}
    for c in df.columns:
        m = re.fullmatch(r"c_clcd(\d{4})_(\w+?)_m2", c)
        if m:
            clcd.setdefault(int(m.group(1)), {})[m.group(2)] = c
    for y, cls in sorted(clcd.items()):
        tot = df[list(cls.values())].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)
        new[f"forest_share_clcd_{y}"] = safe_div(col(df, cls.get("forest", "_none_")), tot)
    if clcd:
        ylast = max(clcd)
        gsum = sum(col(df, clcd[ylast].get(k, "_none_")).fillna(0) for k in ("forest", "shrub", "grass"))
        new["green_new_clcd_share"] = safe_div(col(df, "c_green_new_clcd_m2_2020"), gsum.where(gsum > 0))

    # 3k 社会基础设施
    beds = col(df, "hospital_beds_main")
    new["beds_per_1k_res"] = safe_div(beds, p20) * 1000
    new["beds_per_1k_hukou"] = safe_div(beds, hukou) * 1000
    students = col(df, "students_primary_main") + col(df, "students_secondary_main")
    new["students_per_child"] = safe_div(students, col(df, "share_0_14_2020") * p20)
    new["welfare_beds_per_1k_65"] = safe_div(col(df, "welfare_beds_main"), col(df, "share_65plus_2020") * p20) * 1000
    new["teachers_per_100_students"] = safe_div(col(df, "teachers_fulltime_main"), students) * 100
    poi_d = g.get("poi_access_distance_m") or {}
    for k in sorted(set(POI_KEYS) | set((g.get("poi_assets") or {}).keys())):
        pcol = pick_col(df, rf"c_pop_poi_{k}(\d+)_2020", poi_d.get(k))
        if pcol:
            new[f"{k}_access_share"] = safe_div(col(df, pcol), col(df, "c_pop_expo_2020"))
        if f"c_n_poi_{k}" in df:
            new[f"{k}_per_10k"] = safe_div(col(df, f"c_n_poi_{k}"), core_pop) * 1e4

    # 3l 住建部城市与县城建设统计（人均一律用 core_pop 重算；县的主口径 core_pop 本身来自住建部县城人口）
    new["park_count"] = col(df, "mohurd_park_count")
    new["park_area_pc_mohurd"] = safe_div(col(df, "mohurd_park_area_ha") * 1e4, core_pop)
    new["road_area_pc_mohurd"] = safe_div(col(df, "mohurd_road_area_10k_m2") * 1e4, core_pop)
    new["park_green_pc_m2"] = col(df, "mohurd_park_green_pc_m2")
    new["mohurd_builtup_area_km2"] = col(df, "mohurd_builtup_area_km2")
    new["muni_invest_pc"] = safe_div(col(df, "muni_invest_total_mohurd"), core_pop)
    new["muni_invest_green_pc"] = safe_div(col(df, "muni_invest_green_mohurd"), core_pop)
    new["muni_invest_road_pc"] = safe_div(col(df, "muni_invest_road_mohurd"), core_pop)
    fund_cols = ["fund_central", "fund_local_fiscal", "fund_bond", "fund_loan", "fund_self", "fund_other"]
    f = {c: col(df, f"{c}_mohurd") for c in fund_cols}
    ftot = pd.concat(f.values(), axis=1).sum(axis=1, min_count=1)
    new["fund_fiscal_share"] = safe_div(f["fund_central"].fillna(0) + f["fund_local_fiscal"].fillna(0), ftot)
    new["fund_debt_share"] = safe_div(f["fund_bond"].fillna(0) + f["fund_loan"].fillna(0), ftot)
    new["fund_self_share"] = safe_div(f["fund_self"], ftot)
    mt = col(df, "maint_fund_total_mohurd")
    new["maint_subsidy_share"] = safe_div(col(df, "maint_fund_upper_subsidy_mohurd"), mt)
    new["maint_land_share"] = safe_div(col(df, "maint_fund_land_mohurd"), mt)
    new["green_official_ratio"] = safe_div(new["park_green_pc_m2"], new["green_pc_core"])
    new["green_official_gap"] = safe_log(new["park_green_pc_m2"]) - safe_log(new["greenpatch_pc_core"])

    # 3m 财政与人口四象限
    cut = float(a["self_sufficiency_cut"])
    fs = np.where(new["fss"] >= cut, "财政自给", "转移依赖")
    pg = np.where(pc >= 0, "人口增长", "人口收缩")
    q = pd.Series([f"{x}-{y}" for x, y in zip(fs, pg)], index=df.index)
    new["quadrant"] = q.where(new["fss"].notna() & pc.notna())

    new = {k: (v if isinstance(v, pd.Series) else pd.Series(v, index=df.index)) for k, v in new.items()}
    df = df.drop(columns=[c for c in new if c in df])
    return pd.concat([df, pd.DataFrame(new, index=df.index)], axis=1)


# ===========================================================================
# 代码块 4：读取与合并
# 目的：以分析单元表为底，依次左连接遥感、财政普查、城区人口、住建部面板与行政等级；缺失的可选数据自动跳过。
#       城区人口表的 code 列可填地级代码 xxxx00（市辖区单元）或县级市代码；旧模板的 pref_code 列仍可使用。
#       同一单元有多年记录时优先取 2020 年（住建部面板取 mohurd_stock_year），否则取最近一年。
# 结果：返回合并后的 DataFrame。
# ===========================================================================
def _prefer_year(d: pd.DataFrame, year: int) -> pd.DataFrame:
    if "year" not in d:
        return d.drop_duplicates("unit_id")
    d = d.assign(_y=pd.to_numeric(d["year"], errors="coerce"))
    d = d.assign(_k=(d["_y"] != year).astype(int), _neg=-d["_y"].fillna(-1))
    return d.sort_values(["unit_id", "_k", "_neg"]).drop_duplicates("unit_id").drop(columns=["_y", "_k", "_neg"])


MOHURD_STOCK = {"park_count": "mohurd_park_count", "park_area_ha": "mohurd_park_area_ha",
                "park_green_area_ha": "mohurd_park_green_area_ha", "park_green_pc_m2": "mohurd_park_green_pc_m2",
                "green_ratio_builtup_pct": "mohurd_green_ratio_pct", "green_cover_builtup_pct": "mohurd_green_cover_pct",
                "road_area_10k_m2": "mohurd_road_area_10k_m2", "road_area_pc_m2": "mohurd_road_area_pc_m2",
                "builtup_area_km2": "mohurd_builtup_area_km2", "pop_urban_10k": "mohurd_pop_urban_10k",
                "pop_temp_10k": "mohurd_pop_temp_10k"}
MOHURD_MONEY = ["maint_fund_total", "maint_fund_upper_subsidy", "maint_fund_land", "muni_invest_total", "muni_invest_green",
                "muni_invest_road", "fund_central", "fund_local_fiscal", "fund_bond", "fund_loan", "fund_self", "fund_other"]


def load_mohurd(cfg, c2u) -> pd.DataFrame | None:
    fc = cfg["fiscal_census"]
    mp = resolve(fc["mohurd_file"])
    if not mp.exists():
        LOG.info(f"未提供住建部面板（{mp.name}），住建部指标为缺失。")
        return None
    m = read_table(mp, code_cols=("code",))
    if "built_area_km2" in m and "builtup_area_km2" not in m:   # 旧模板列名
        m = m.rename(columns={"built_area_km2": "builtup_area_km2"})
    m["unit_id"] = code_to_unit(m["code"], c2u)
    un = m[m["unit_id"].isna()]
    if len(un):
        LOG.warning(f"住建部面板：{un['code'].nunique()} 个代码未匹配到分析单元：{un['code'].drop_duplicates().head(10).tolist()}")
    m = m.dropna(subset=["unit_id"])
    m["year"] = pd.to_numeric(m["year"], errors="coerce")
    for c in list(MOHURD_STOCK) + MOHURD_MONEY:
        if c in m:
            m[c] = pd.to_numeric(m[c], errors="coerce")
    # 同一单元同一年多行（例如同时录入了地级代码与区代码）时，优先保留地级代码 xxxx00 的行
    m["_pref"] = m["code"].astype("string").str[4:].eq("00").fillna(False).astype(int)
    m = m.sort_values(["unit_id", "year", "_pref"], ascending=[True, True, False])
    dup = m.duplicated(["unit_id", "year"])
    if dup.any():
        LOG.warning(f"住建部面板：{int(dup.sum())} 行与同单元同年份的其他行重复，只保留一行。")
    m = m[~dup]
    sy = int(fc.get("mohurd_stock_year", 2020))
    stock = m[m["year"] == sy]
    out = stock[["unit_id"] + [c for c in MOHURD_STOCK if c in stock]].rename(columns=MOHURD_STOCK).set_index("unit_id")
    if "mohurd_pop_urban_10k" in out:
        temp = out["mohurd_pop_temp_10k"].fillna(0) if "mohurd_pop_temp_10k" in out else 0
        out["mohurd_pop_total_10k"] = out["mohurd_pop_urban_10k"] + temp
    yrs = [int(y) for y in fc.get("mohurd_years_main", [])]
    flow = m[m["year"].isin(yrs)]
    money = [c for c in MOHURD_MONEY if c in flow]
    if money:
        fl = flow.groupby("unit_id")[money].mean() * 1e4     # 年鉴金额单位为万元
        out = out.join(fl.rename(columns={c: f"{c}_mohurd" for c in money}), how="outer")
    LOG.info(f"住建部面板：存量年 {sy} 有 {len(stock)} 个单元，流量年 {yrs} 有 {flow['unit_id'].nunique()} 个单元。")
    return out.reset_index()


def load_town_census(cfg, c2u):
    """乡镇街道普查（可选）：把城关镇与县城街道（is_seat_town = 1）的常住人口按县汇总。
    返回 unit_id、town_pop_census_2010、town_pop_census_2020；两年都没有文件时返回 None。
    county_adcode 须为 2020 年县级代码（2010 年资料中的旧代码请先按代码对照表改写）。"""
    files = ((cfg.get("township") or {}).get("census_township_files") or {})
    out = None
    for y, path in files.items():
        p = resolve(path)
        if not p.exists():
            continue
        tw = read_table(p, code_cols=("code12", "county_adcode"))
        if "is_seat_town" not in tw or "pop_resident" not in tw:
            LOG.warning(f"{p.name} 缺少 is_seat_town 或 pop_resident 列，跳过")
            continue
        seat = tw["is_seat_town"].astype("string").str.strip().str.lower().isin(["1", "1.0", "true", "是", "y", "yes"])
        tw = tw[seat.fillna(False).astype(bool)].copy()
        tw["adcode"] = tw["county_adcode"].map(norm_adcode)
        tw["pop"] = pd.to_numeric(tw["pop_resident"], errors="coerce")
        g = tw.dropna(subset=["adcode"]).groupby("adcode")["pop"].sum(min_count=1).reset_index()
        g["unit_id"] = g["adcode"].map(dict(zip(c2u["adcode"], c2u["unit_id"])))
        miss = g["unit_id"].isna()
        if miss.any():
            LOG.warning(f"{p.name}：{int(miss.sum())} 个县代码未匹配到分析单元，示例 {g.loc[miss, 'adcode'].head(10).tolist()}")
        g = g.dropna(subset=["unit_id"]).groupby("unit_id")["pop"].sum(min_count=1).rename(f"town_pop_census_{int(y)}").reset_index()
        out = g if out is None else out.merge(g, on="unit_id", how="outer")
    return out


def load_all(cfg) -> pd.DataFrame:
    ud = resolve(cfg["units"]["out_dir"])
    units = read_table(ud / "units_table.csv", code_cols=("unit_id", "prov_code", "pref_code"))
    c2u = read_table(ud / "county_to_unit.csv", code_cols=("adcode", "unit_id", "prov_code", "pref_code"))
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

    # 城区人口：市辖区单元与县级市
    up = resolve(cfg["fiscal_census"]["city_urban_pop_file"])
    if up.exists():
        u = read_table(up, code_cols=("code", "pref_code"))
        code = u["code"] if "code" in u else u["pref_code"]
        if "code" in u and "pref_code" in u:
            code = u["code"].where(u["code"].notna(), u["pref_code"])
        u["unit_id"] = code_to_unit(code, c2u)
        # 只填了地级代码的旧表：未匹配到 county_to_unit 时按地级代码映射。只对 xxxx00 形式的代码这样做，
        # 查不到的县级市代码（如边界中没有的新设县级市）不能归到所在地级市的市辖区单元，否则会顶替该市的城区人口
        miss = u["unit_id"].isna()
        u.loc[miss, "unit_id"] = code[miss].map(norm_adcode).map(
            lambda c: "CP" + pref_code(c) if c and c[4:] == "00" else None)
        if u["unit_id"].isna().any():
            LOG.warning(f"城区人口表中 {int(u['unit_id'].isna().sum())} 行代码未匹配到分析单元，已忽略："
                        f"{code[u['unit_id'].isna()].head(10).tolist()}")
        u["urban_pop_total_10k"] = pd.to_numeric(u["urban_pop_10k"], errors="coerce") + \
            pd.to_numeric(u["urban_temp_pop_10k"], errors="coerce").fillna(0) if "urban_temp_pop_10k" in u else \
            pd.to_numeric(u["urban_pop_10k"], errors="coerce")
        u = u.dropna(subset=["unit_id", "urban_pop_total_10k"])
        u = _prefer_year(u, 2020)
        ok_type = u["unit_id"].map(dict(zip(units["unit_id"], units["unit_type"]))).isin(["city_proper", "county_city"])
        if (~ok_type).any():
            LOG.warning(f"城区人口表中 {int((~ok_type).sum())} 行不是市辖区单元或县级市，已忽略：{u.loc[~ok_type, 'unit_id'].tolist()[:10]}")
        df = df.merge(u.loc[ok_type, ["unit_id", "urban_pop_total_10k"]], on="unit_id", how="left")

    mo = load_mohurd(cfg, c2u)
    if mo is not None:
        df = df.merge(mo, on="unit_id", how="left")
    town = load_town_census(cfg, c2u)
    if town is not None:
        df = df.merge(town, on="unit_id", how="left")
    df = df.copy()   # 多次合并后整理内存，避免逐列新增时的 PerformanceWarning

    # 官方中心人口：市辖区与县级市用七普城区人口（缺失时用住建部城区人口），县用住建部县城人口 + 暂住人口
    t = df["unit_type"]
    upop = col(df, "urban_pop_total_10k")
    mpop = col(df, "mohurd_pop_total_10k")
    tpop = col(df, "town_pop_census_2020") / 1e4
    off = pd.Series(np.nan, index=df.index)
    osrc = pd.Series(None, index=df.index, dtype="object")
    cityish = t.isin(["city_proper", "county_city"])
    cnty = t == "county"
    off[cityish] = upop[cityish].fillna(mpop[cityish])
    osrc[cityish & upop.notna()] = "census_urban"
    osrc[cityish & upop.isna() & mpop.notna()] = "mohurd"
    # 县：优先用乡镇街道普查的城关镇与县城街道常住人口（普查口径），缺失时才用住建部县城人口 + 暂住人口（户籍口径）
    off[cnty] = tpop[cnty].fillna(mpop[cnty])
    osrc[cnty & tpop.notna()] = "census_town"
    osrc[cnty & tpop.isna() & mpop.notna()] = "mohurd"
    df["core_pop_official"] = off * 1e4
    df["core_pop_official_src"] = osrc
    n_m = int((cnty & (osrc == "mohurd")).sum())
    if n_m:
        LOG.info(f"{n_m} 个县的官方中心人口取自住建部县城人口 + 暂住人口（户籍口径）；提供乡镇街道普查后会改用普查常住人口")

    # 行政等级
    ar_path = resolve(cfg["analysis"].get("admin_rank_file", "外部参数/admin_rank.csv"))
    rank = pd.Series(np.nan, index=df.index)
    ranks = {}
    if ar_path.exists():
        ar = read_table(ar_path, code_cols=("pref_code",))
        ranks = dict(zip(ar["pref_code"].map(norm_adcode).map(norm_pref), pd.to_numeric(ar["admin_rank"], errors="coerce")))
    pc_ = df["pref_code"].map(lambda c: norm_pref(norm_adcode(c)) if isinstance(c, str) else None)
    cityrank = pc_.map(ranks).fillna(1)
    rank[t.isin(["city_proper", "district_outer"])] = cityrank[t.isin(["city_proper", "district_outer"])]
    rank[t.isin(["county", "county_city"])] = 0
    df["admin_rank"] = rank

    # excluded：00 的标记，再加上 analysis.exclude_code_prefixes
    prefixes = [str(p) for p in (cfg["analysis"].get("exclude_code_prefixes") or [])]
    ex0 = df["excluded"].astype("string").str.lower().isin(["true", "1"]) if "excluded" in df else pd.Series(False, index=df.index)
    df["excluded"] = (ex0.fillna(False).astype(bool) | df["unit_id"].map(lambda c: is_excluded(c, prefixes))).astype(int)
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
    if df["excluded"].any():
        LOG.info(f"excluded：{int(df['excluded'].sum())} 个单元不进入表格与回归：{df.loc[df['excluded'] == 1, 'unit_id'].tolist()[:20]}")
    LOG.info(f"完成：{len(df)} 个单元 → {out_dir / 'unit_indicators.csv'}")


if __name__ == "__main__":
    main()
