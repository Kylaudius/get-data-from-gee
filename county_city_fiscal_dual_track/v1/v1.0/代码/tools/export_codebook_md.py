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
    ("`*_bs_YYYY` / `*_bsn_YYYY`", "建成面积 / 非住宅建成面积（m²）", "JRC/GHSL/P2023A/GHS_BUILT_S"),
    ("`*_bv_YYYY` / `*_bvn_YYYY`", "建筑总体量 / 非住宅体量（m³）", "JRC/GHSL/P2023A/GHS_BUILT_V"),
    ("`*_pop_ghs_YYYY`", "人口", "JRC/GHSL/P2023A/GHS_POP"),
    ("`*_pop_wp_YYYY`", "人口（稳健性）", "WorldPop/GP/100m/pop"),
    ("`*_ntl_viirs_YYYY` / `*_ntl_ccnl_YYYY`", "夜间灯光辐亮度求和",
     "NOAA/VIIRS/DNB/ANNUAL_V21（2013 至 2021 年）、ANNUAL_V22（2022 年起），average_masked；BNU/FGS/CCNL/v1"),
    ("`c_wc_<类>_m2`", "各地类面积（m²）", "ESA/WorldCover/v100"),
    ("`c_pw_tree_YYYY` / `c_pw_green_YYYY` / `c_pop_expo_YYYY`", "人口 × 邻域树木（绿地）比例之和 / 人口之和", "WorldCover × GHS-POP"),
    ("`c_greenpatch_m2_YYYY` / `c_pop_greenpatch500_YYYY`", "≥1 公顷连片绿地面积 / 其 500 m 内人口", "WorldCover × GHS-POP"),
    ("`c_riparian_green_m2_YYYY` / `c_roadside_green_m2_YYYY`", "滨水绿带 / 道路两侧绿带面积", "WorldCover × JRC/GSW1_4 / GHS_BUILT_C"),
    ("`c_openveg_m2_2018` / `c_road_m2_2018`", "聚落内植被开放空间 / 道路面面积", "JRC/GHSL/P2023A/GHS_BUILT_C"),
    ("`c_ndvi_s2_YYYY`", "生长季 NDVI 均值", "COPERNICUS/S2_SR_HARMONIZED"),
    ("`c_dw_trees_YYYY` / `c_dw_grass_YYYY`", "树木 / 草地概率均值", "GOOGLE/DYNAMICWORLD/V1"),
    ("`r_ndvi_modis_YYYY`", "环带非建成栅格 NDVI 均值", "MODIS/061/MOD13Q1"),
    ("`*_elev` / `*_slope`", "高程、坡度均值", "NASA/NASADEM_HGT/001"),
    ("`u_t2m_c_YYYY` / `u_prcp_mm_YYYY`", "年均气温（°C）/ 年降水（mm）", "ECMWF/ERA5_LAND/MONTHLY_AGGR"),
    ("`u_access_min`", "到最近城市的出行时间均值（分钟，2015）",
     "projects/malariaatlasproject/assets/accessibility/accessibility_to_cities/2015_v1_0"),
    ("`c_park_m2_YYYY` / `c_pop_park500_YYYY`", "公园面积 / 公园 500 m 内人口（可选）", "用户上传的公园多边形"),
]

out = ["# 附录C 指标定义与计算公式（v1.0）", "",
       "本附录由 `代码/tools/export_codebook_md.py` 根据 `代码/03_build_indicators.py` 中的 CODEBOOK 自动生成，与代码计算口径一致。",
       "", "财政金额统一换算为元。主分析期为 2018、2019、2021 三年均值，避开 2020 年抗疫特别国债与新增赤字经特殊转移支付直达市县造成的异常；2010 期为 2009 至 2011 年三年均值。人口来自第五、六、七次人口普查分县资料，统一到 2020 年行政区划边界。遥感指标除特别说明外为 2020 年，统计范围为 2020 年中心建成区。",
       "", "| 变量名 | 中文名 | 英文术语 | 公式 | 单位 |", "|---|---|---|---|---|"]
out += [f"| `{v}` | {zh} | {en} | {f} | {u} |" for v, zh, en, f, u in rows]
out += ["", "## 原始遥感字段命名规则", "",
        "`01_gee_extract_rs.py` 输出的原始字段以前缀区分统计范围。`u_` 为整个分析单元，`c_` 为中心建成区（2020 年边界），`r_` 为中心建成区外 5 km 环带，后缀为年份。例如 `c_bs_2010` 是 2020 年中心建成区范围内 2010 年的 GHSL 建成面积（m²），`core2010_area_m2` 是按 2010 年 GHSL 单独识别的中心建成区面积。",
        "", "| 字段 | 含义 | 来源（GEE asset） |", "|---|---|---|"]
out += [f"| {a} | {b} | {c} |" for a, b, c in RAW_FIELDS]
atomic_write_text(VERSION_DIR / "附录" / "附录C_指标定义与计算公式.md", "\n".join(out) + "\n")
print(f"已写出 附录C（{len(rows)} 个指标）")
