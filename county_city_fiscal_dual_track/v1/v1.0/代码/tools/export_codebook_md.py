# -*- coding: utf-8 -*-
"""
tools/export_codebook_md.py  由 03_build_indicators.py 中的 CODEBOOK 生成 附录C

在哪里运行：Mac “终端 Terminal”，在 代码/ 文件夹下：
    python tools/export_codebook_md.py
能得到什么：覆盖写出 附录/附录C_指标定义与计算公式.md，使附录与代码中的指标口径保持一致。
            运行前请先用 tools/check_manual_edits.py --check 确认你没有手动改过附录C；
            如果改过，把修改先挪到 CODEBOOK 里，再运行本脚本。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))
from common import VERSION_DIR, atomic_write_text  # noqa: E402

# ---------------------------------------------------------------------------
# 代码块 1：读取 CODEBOOK
# 目的：直接导入 03 脚本中的指标说明表，而不是另抄一份。
# 结果：rows 为 (变量名, 中文名, 英文术语, 公式, 单位) 列表。
# ---------------------------------------------------------------------------
spec = importlib.util.spec_from_file_location("m03", CODE / "03_build_indicators.py")
m03 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m03)
rows = m03.CODEBOOK

# ---------------------------------------------------------------------------
# 代码块 2：写出 Markdown
# 目的：生成指标总表与原始遥感字段命名规则两部分。
# 结果：附录/附录C_指标定义与计算公式.md
# ---------------------------------------------------------------------------
RAW_FIELDS = [
    ("`core_method` / `core_closing_m` / `core_area_m2`", "中心建成区识别方法 / 闭运算半径（m）/ 面积（m²）",
     "JRC/GHSL/P2023A/GHS_BUILT_S"),
    ("`c_builtcell_m2_2020`", "闭运算与填洞前已达建成阈值、位于最终中心建成区内的栅格面积（m²）", "JRC/GHSL/P2023A/GHS_BUILT_S"),
    ("`*_bs_YYYY` / `*_bsn_YYYY`", "建成面积 / 非住宅建成面积（m²）", "JRC/GHSL/P2023A/GHS_BUILT_S"),
    ("`*_bv_YYYY` / `*_bvn_YYYY`", "建筑总体量 / 非住宅体量（m³）", "JRC/GHSL/P2023A/GHS_BUILT_V"),
    ("`*_pop_ghs_YYYY`", "人口", "JRC/GHSL/P2023A/GHS_POP"),
    ("`*_pop_wp_YYYY`", "人口（稳健性）", "WorldPop/GP/100m/pop"),
    ("`*_ntl_viirs_YYYY` / `*_ntl_ccnl_YYYY`", "夜间灯光辐亮度求和",
     "NOAA/VIIRS/DNB/ANNUAL_V21（2013 至 2021 年）、ANNUAL_V22（2022 年起），average_masked；BNU/FGS/CCNL/v1"),
    ("`c_wc_<类>_m2`", "各地类面积（m²），11 类；树木指标把树木 (10) 与红树林 (95) 合计", "ESA/WorldCover/v100"),
    ("`c_tree_stock_m2_2020` / `c_tree_new_m2_2020`", "2020 年树木中 2000 年树冠覆盖度达到 / 未达到 gee.baseline_tree_cover_pct 的面积",
     "ESA/WorldCover/v100 × UMD/hansen/global_forest_change_2025_v1_13（treecover2000）"),
    ("`c_tree_flat_m2_2020`", "坡度不超过 gee.slope_mask_deg 的树木面积", "ESA/WorldCover/v100 × NASA/NASADEM_HGT/001"),
    ("`c_pw_tree_YYYY` / `c_pw_green_YYYY` / `c_pop_expo_YYYY`", "人口 × 邻域树木（绿地）比例之和 / 人口之和", "WorldCover × GHS-POP"),
    ("`c_greenpatch_m2_YYYY` / `c_pop_greenpatch500_YYYY`", "大型树木斑块面积（先截断于中心建成区再做连通计数）/ 其 500 m 内人口",
     "WorldCover × GHS-POP"),
    ("`c_riparian_green_m2_YYYY`", "近永久水体外扩带内的绿地面积（滨水线性绿地）", "WorldCover × JRC/GSW1_4/GlobalSurfaceWater"),
    ("`c_roadside_green_m2_YYYY`", "道路面外扩带内的绿地面积（行道树代理）", "WorldCover × JRC/GHSL/P2023A/GHS_BUILT_C"),
    ("`c_openveg_m2_2018` / `c_road_m2_2018`", "聚落内植被开放空间 / 道路面面积", "JRC/GHSL/P2023A/GHS_BUILT_C"),
    ("`c_gaia_imp_m2_YYYY` / `u_gaia_imp_m2_YYYY`", "固定的 2020 年中心建成区 / 单元内的不透水面面积（2000、2010、2018 年）",
     "Tsinghua/FROM-GLC/GAIA/v10"),
    ("`u_smod_ucl_m2_2020` / `u_smod_uc_m2_2020` / `c_smod_ucl_m2_2020`", "城镇簇（代码 22、23、30）/ 城市中心（代码 30）面积",
     "JRC/GHSL/P2023A/GHS_SMOD_V2-0"),
    ("`c_clcdYYYY_<类>_m2` / `c_green_new_clcd_m2_2020`", "CLCD 各地类面积 / 基准年后新增的森林、灌木与草地面积（可选）",
     "CLCD 30 m 年度地类（gee.clcd_asset_template）"),
    ("`c_ndvi_s2_YYYY`", "生长季 NDVI 均值，剔除水面", "COPERNICUS/S2_SR_HARMONIZED"),
    ("`c_dw_trees_YYYY` / `c_dw_grass_YYYY`", "树木 / 草地概率均值", "GOOGLE/DYNAMICWORLD/V1"),
    ("`r_ndvi_modis_YYYY`", "环带非建成栅格 NDVI 均值，剔除水面", "MODIS/061/MOD13Q1"),
    ("`*_elev` / `*_slope`", "高程、坡度均值；坡度在 30 m 原生网格上计算", "NASA/NASADEM_HGT/001"),
    ("`u_t2m_c_YYYY` / `u_prcp_mm_YYYY`", "年均气温（°C）/ 年降水（mm）", "ECMWF/ERA5_LAND/MONTHLY_AGGR"),
    ("`u_access_min`", "到最近城市的出行时间均值（分钟，2015）",
     "projects/malariaatlasproject/assets/accessibility/accessibility_to_cities/2015_v1_0"),
    ("`c_park_m2_YYYY` / `c_pop_park500_YYYY`", "公园面积 / 公园 500 m 内人口（可选）", "用户上传的公园多边形"),
    ("`c_greenway_len_m` / `c_pop_greenway<距离>_2020`", "绿道长度（m）/ 绿道可达范围内人口（可选）", "用户上传的绿道线要素"),
    ("`c_n_poi_<类>` / `c_pop_poi_<类><距离>_2020`", "学校、医院、养老机构点位数 / 可达范围内人口（可选）", "用户上传的设施点位"),
]

out = ["# 附录C 指标定义与计算公式（v1.0）", "",
       "本附录由 `代码/tools/export_codebook_md.py` 根据 `代码/03_build_indicators.py` 中的 CODEBOOK 自动生成，与代码计算口径一致。",
       "", "财政金额统一换算为元。主分析期为 2017 至 2019 年三年均值，是营改增后第一个完整年度到疫情前的时段，"
       "只在收入与支出都有数的年份上平均。稳健性年份为 2018、2019、2021 年，2010 期为 2009 至 2011 年，2000 期为 1999 至 2001 年。"
       "财政水平量以 2010 年普查常住人口为分母，这一分母先于主分析期确定。人口来自第五、六、七次人口普查分县资料，统一到 2020 年行政区划边界。"
       "遥感指标除特别说明外为 2020 年，统计范围为 2020 年中心建成区。中心建成区退化为几何中心 1 km 缓冲的单元，全部中心建成区指标记为缺失。"
       "表中 P2020、P2010、P2000 为普查常住人口，core_pop 为中心建成区人口主口径。",
       "", "| 变量名 | 中文名 | 英文术语 | 公式 | 单位 |", "|---|---|---|---|---|"]
out += [f"| `{v}` | {zh} | {en} | {f} | {u} |" for v, zh, en, f, u in rows]
out += ["", "## 原始遥感字段命名规则", "",
        "`01_gee_extract_rs.py` 输出的原始字段以前缀区分统计范围。`u_` 为整个分析单元，`c_` 为中心建成区（2020 年边界），`r_` 为中心建成区外 5 km 环带，后缀为年份。例如 `c_bs_2010` 是 2020 年中心建成区范围内 2010 年的 GHSL 建成面积（m²），`core2010_area_m2` 是按 2010 年 GHSL 单独识别的中心建成区面积。",
        "", "`--annual` 模式另写 `数据/中间/gee/annual/annual_long.csv`，每个单元每年一行，字段为 c_gaia_imp_m2、u_gaia_imp_m2、c_ntl_viirs、u_ntl_viirs、c_dw_trees 与 c_dw_grass。`--units did` 模式对县级单元层（每个 2020 年县级行政区一个单元）做同样的提取，结果在 `数据/中间/gee/did/`。",
        "", "| 字段 | 含义 | 来源（GEE asset） |", "|---|---|---|"]
out += [f"| {a} | {b} | {c} |" for a, b, c in RAW_FIELDS]
atomic_write_text(VERSION_DIR / "附录" / "附录C_指标定义与计算公式.md", "\n".join(out) + "\n")
print(f"已写出 附录C（{len(rows)} 个指标）")
