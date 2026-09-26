# -*- coding: utf-8 -*-
"""
tests/run_smoke_test.py  用合成数据 (synthetic data) 端到端检查 00、01(合并部分)、02、03、04、05 能否跑通

在哪里运行：Mac “终端 Terminal”，在 代码/ 文件夹下：
    python tests/run_smoke_test.py
    python tests/run_smoke_test.py --keep     # 保留临时文件夹，便于查看生成的表和图
能得到什么：在系统临时文件夹中生成一套“假”的边界、驻地点、财政、普查、住建部面板、土地债务与 GEE 结果，依次运行各脚本，
            最后打印每一步与每条断言是否通过。合成数据只用于检查代码，任何数值都不是研究结果，
            临时文件夹不在本迭代目录内，不会污染 数据/ 与 图表/。
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from shapely.geometry import box

CODE = Path(__file__).resolve().parents[1]
VERSION = CODE.parent
RNG = np.random.default_rng(20260926)
FALLBACK_UNIT = "320121"        # 模拟 01 中心建成区退化为几何中心缓冲的单元
EXCLUDED_UNIT = "659001"        # 兵团城市，应被 excluded
LARGE_CITY = "320181"           # 城区人口表中的县级市，城区人口达到Ⅱ型大城市
NO_SEAT = "429004"              # 故意不给驻地点的单元
LATE_OLD, LATE_NEW = "130127", "130103"   # 普查年 12 月撤县设区：2020 年普查仍用旧代码
Y2000_SUBITEMS = "320122"       # 1999–2001 年只录了转移支付分项、没有合计的县


def load_module(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, CODE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ===========================================================================
# 代码块 1：合成县级边界
# 目的：构造覆盖各类特殊情况的县级单元：直辖市、重庆主城与外围区、普通地级市的区/县/县级市、
#       不设区地级市（441900）、省直辖县级市（429004）、兵团城市（659001）、
#       一个曾为县级市后改设区的代码（440184 → 440106，2014 年）、一个普查年 12 月撤县设区的代码（130127 → 130103）。
# 结果：返回 GeoDataFrame（adcode、name、geometry）。
# ===========================================================================
def synthetic_counties() -> gpd.GeoDataFrame:
    specs = []
    specs += [(f"1101{i:02d}", f"测试{i}区") for i in range(1, 6)]
    specs += [(c, f"测试{c}区") for c in ["500103", "500104", "500105", "500106", "500107", "500108", "500110", "500114"]]
    specs += [("500229", "测试城口县"), ("500230", "测试丰都县")]
    specs += [(c, f"测试{c}区") for c in ["440103", "440104", "440105", "440106", "440303", "440304"]]
    specs += [("441900", "测试东莞市"), ("429004", "测试仙桃市"), (EXCLUDED_UNIT, "测试石河子市")]
    for prov in ["32", "41", "51", "52", "62", "65", "23", "43", "36", "13"]:
        for pref in ["01", "02", "03"]:
            specs += [(f"{prov}{pref}{i:02d}", f"测试{prov}{pref}{i:02d}区") for i in (2, 3)]
            specs += [(f"{prov}{pref}{i:02d}", f"测试{prov}{pref}{i:02d}县") for i in range(21, 27)]
            specs += [(f"{prov}{pref}{i:02d}", f"测试{prov}{pref}{i:02d}市") for i in (81, 82)]
    geoms = []
    for k, _ in enumerate(specs):
        x0 = 80 + (k % 40) * 1.0
        y0 = 22 + (k // 40) * 1.0
        geoms.append(box(x0, y0, x0 + 0.95, y0 + 0.95))
    return gpd.GeoDataFrame({"adcode": [s[0] for s in specs], "name": [s[1] for s in specs]},
                            geometry=geoms, crs=4326)


def old_code(c: str, yr: int, month: int = 12) -> str:
    """数据年份对应的旧代码：440106 在 2014 年前为 440184；130103 在 2020 年 12 月前为 130127。"""
    if c == "440106" and yr < 2014:
        return "440184"
    if c == LATE_NEW and (yr < 2020 or (yr == 2020 and month < 12)):
        return LATE_OLD
    return c


# ===========================================================================
# 代码块 2：合成财政、普查、城区人口、住建部面板、土地债务与驻地点
# 目的：按单元类型生成量级合理的随机数，覆盖缺失值、代码变更、重复记录、区级财政（重庆）等情形。
# 结果：写入临时文件夹 数据/原始/ 下的各文件。
# ===========================================================================
def write_inputs(base: Path, gdf: gpd.GeoDataFrame):
    raw = base / "数据" / "原始"
    (raw / "boundary").mkdir(parents=True, exist_ok=True)
    gdf.to_file(raw / "boundary" / "county_2020.shp", encoding="utf-8")

    sys.path.insert(0, str(CODE))
    from common import classify_unit, pref_code
    gdf = gdf.copy()
    gdf["t"] = [classify_unit(c, n) for c, n in zip(gdf["adcode"], gdf["name"])]
    types = dict(zip(gdf["adcode"], gdf["t"]))

    # 普查：2010、2000 年用旧代码；2020 年普查标准时点（11 月 1 日）时 130103 仍为 130127
    rows = []
    for yr in (1990, 2000, 2010, 2020):
        for c, t in zip(gdf["adcode"], gdf["t"]):
            base_pop = {"district": 6e5, "county": 3.5e5, "county_city": 6e5, "pref_city_no_district": 8e6}[t]
            growth = {"district": 0.015, "county": -0.008, "county_city": 0.002, "pref_city_no_district": 0.03}[t]
            pop = base_pop * np.exp(growth * (yr - 2020) * -1) * RNG.lognormal(0, 0.3)
            hh = pop / 2.8
            r = {"adcode": old_code(c, yr, month=11), "name": "x", "census_year": yr, "pop_resident": round(pop),
                 "pop_urban": round(pop * RNG.uniform(0.3, 0.95)), "households": round(hh),
                 "hh_pop": round(pop * 0.9), "pop_hukou": round(pop * RNG.uniform(0.7, 1.4)),
                 "collective_pop": round(pop * RNG.uniform(0.01, 0.12)),
                 "share_0_14": RNG.uniform(0.12, 0.25), "share_65plus": RNG.uniform(0.08, 0.2)}
            if yr == 2020:
                rm, rp = RNG.uniform(0.02, 0.4), RNG.uniform(0, 0.05)
                bn, bs = RNG.uniform(0.05, 0.4), RNG.uniform(0.02, 0.15)
                r.update({"pop_hukou_elsewhere": round(pop * RNG.uniform(0.05, 0.4)),
                          "housing_area_pc": RNG.uniform(25, 55), "share_rent_market": rm, "share_rent_public": rp,
                          "share_buy_new": bn, "share_buy_second": bs, "share_self_built": max(0.0, 1 - rm - rp - bn - bs - 0.1)})
            rows.append(r)
    cen = pd.DataFrame(rows)
    (raw / "census").mkdir(exist_ok=True)
    for yr in (1990, 2000, 2010, 2020):
        d = cen[cen["census_year"] == yr]
        if yr == 2020:
            d = pd.concat([d, d.head(1)])  # 故意放一条重复记录
        d.to_csv(raw / "census" / f"census_{yr}_county.csv", index=False, encoding="utf-8-sig")

    (raw / "crosswalk").mkdir(exist_ok=True)
    pd.DataFrame([
        {"old_code": "440184", "old_name": "旧县级市", "new_code": "440106", "new_name": "新区",
         "change_year": 2014, "change_date": "2014-02-12", "change_type": "撤市设区", "weight": 1},
        {"old_code": LATE_OLD, "old_name": "旧县", "new_code": LATE_NEW, "new_name": "新区",
         "change_year": 2020, "change_date": "2020-12-01", "change_type": "撤县设区", "weight": 1},
    ]).to_csv(raw / "crosswalk" / "admin_crosswalk.csv", index=False, encoding="utf-8-sig")

    # 财政：县、县级市（万元）。重庆各区逐区录入（district_level_fiscal_prefs = 500000）；
    # 440184 在 2014 年前、130127 在 2020 年前仍为县级单位
    years = (1999, 2000, 2001, 2009, 2010, 2011, 2017, 2018, 2019, 2020, 2021)
    frows = []
    for yr in years:
        for c, t in zip(gdf["adcode"], gdf["t"]):
            code = old_code(c, yr)
            if t not in ("county", "county_city") and not c.startswith("50") and code == c:
                continue
            exp = RNG.lognormal(np.log(3e5), 0.4)
            r = {"adcode": code, "name": "x", "year": yr, "gen_budget_revenue": exp * RNG.uniform(0.1, 0.5),
                 "gen_budget_expenditure": exp, "tax_revenue": exp * 0.2, "pop_hukou_yearend": 40,
                 "exp_education": exp * RNG.uniform(0.12, 0.25), "exp_health": exp * RNG.uniform(0.06, 0.12),
                 "exp_community": exp * RNG.uniform(0.03, 0.15), "exp_personnel": exp * RNG.uniform(0.2, 0.4),
                 "exp_general_public": exp * RNG.uniform(0.06, 0.14), "fund_budget_revenue": exp * RNG.uniform(0.05, 0.6),
                 "students_primary": RNG.uniform(1e4, 6e4), "students_secondary": RNG.uniform(8e3, 5e4),
                 "teachers_fulltime": RNG.uniform(1e3, 6e3), "hospital_beds": RNG.uniform(800, 5000),
                 "welfare_beds": RNG.uniform(100, 1500)}
            if yr in (1999, 2000, 2001, 2009):
                tg, ts, tr = exp * 0.3, exp * 0.2, exp * 0.05
                r.update({"transfer_general": tg, "transfer_specific": ts, "tax_rebate": tr, "transfer_total": tg + ts + tr})
                if c == Y2000_SUBITEMS and yr < 2009:
                    r.pop("transfer_total")
            frows.append(r)
    (raw / "fiscal").mkdir(exist_ok=True)
    pd.DataFrame(frows).to_csv(raw / "fiscal" / "fiscal_county.csv", index=False, encoding="utf-8-sig")

    prefs = sorted({pref_code(c) for c, t in zip(gdf["adcode"], gdf["t"]) if t == "district"} | {"441900"})
    crows = []
    for yr in years:
        for p in prefs:
            exp = RNG.lognormal(np.log(3e6), 0.5)
            crows.append({"pref_code": p, "name": "x", "year": yr, "scope": "市辖区",
                          "gen_budget_revenue": exp * RNG.uniform(0.5, 0.95), "gen_budget_expenditure": exp,
                          "tax_revenue": exp * 0.5, "land_conveyance_revenue": exp * 0.4,
                          "exp_education": exp * 0.15, "exp_health": exp * 0.07, "exp_community": exp * 0.2,
                          "exp_general_public": exp * 0.08, "hospital_beds": RNG.uniform(5e3, 8e4),
                          "students_primary": RNG.uniform(5e4, 8e5), "students_secondary": RNG.uniform(4e4, 6e5),
                          "teachers_fulltime": RNG.uniform(5e3, 8e4), "welfare_beds": RNG.uniform(1e3, 3e4)})
    pd.DataFrame(crows).to_csv(raw / "fiscal" / "fiscal_city_proper.csv", index=False, encoding="utf-8-sig")

    # 城区人口：地级代码 + 一个县级市（城区人口 120 万，达到Ⅱ型大城市）
    (raw / "city").mkdir(exist_ok=True)
    up = pd.DataFrame({"code": prefs, "name": "x", "level": "地级及以上城市", "year": 2020,
                       "urban_pop_10k": RNG.uniform(40, 1200, len(prefs)), "urban_temp_pop_10k": 0})
    ccity = [c for c, t in types.items() if t == "county_city" and c not in (LARGE_CITY, EXCLUDED_UNIT)][:10]
    up = pd.concat([up, pd.DataFrame({"code": [LARGE_CITY] + ccity, "name": "x", "level": "县级市", "year": 2020,
                                      "urban_pop_10k": [120.0] + list(RNG.uniform(10, 60, len(ccity))),
                                      "urban_temp_pop_10k": 0})], ignore_index=True)
    up.to_csv(raw / "city" / "city_urban_pop_2020.csv", index=False, encoding="utf-8-sig")

    # 住建部面板：城市（地级代码与县级市代码）与县城，2017–2020 四年
    mrows = []
    for yr in (2017, 2018, 2019, 2020):
        for code, lvl in [(p, "城市") for p in prefs] + [(c, "城市" if t == "county_city" else "县城")
                                                          for c, t in types.items() if t in ("county", "county_city")]:
            big = lvl == "城市"
            inv = RNG.lognormal(np.log(3e5 if big else 3e4), 0.5)
            funds = RNG.dirichlet(np.ones(6)) * inv
            mrows.append({"code": code, "name": "x", "level": lvl, "year": yr,
                          "builtup_area_km2": RNG.uniform(60, 900) if big else RNG.uniform(8, 40),
                          "park_count": int(RNG.integers(3, 200)), "park_area_ha": RNG.uniform(30, 5000),
                          "park_green_area_ha": RNG.uniform(20, 4000), "park_green_pc_m2": RNG.uniform(8, 20),
                          "green_ratio_builtup_pct": RNG.uniform(25, 42), "green_cover_builtup_pct": RNG.uniform(30, 46),
                          "road_area_10k_m2": RNG.uniform(50, 8000), "road_area_pc_m2": RNG.uniform(10, 25),
                          "pop_urban_10k": RNG.uniform(50, 800) if big else RNG.uniform(3, 30),
                          "pop_temp_10k": RNG.uniform(0, 50) if big else RNG.uniform(0, 3),
                          "maint_fund_total": inv * 0.6, "maint_fund_upper_subsidy": inv * RNG.uniform(0.05, 0.3),
                          "maint_fund_land": inv * RNG.uniform(0.05, 0.3), "muni_invest_total": inv,
                          "muni_invest_green": inv * RNG.uniform(0.05, 0.2), "muni_invest_road": inv * RNG.uniform(0.2, 0.5),
                          "fund_central": funds[0], "fund_local_fiscal": funds[1], "fund_bond": funds[2],
                          "fund_loan": funds[3], "fund_self": funds[4], "fund_other": funds[5], "source": "合成"})
    (raw / "mohurd").mkdir(exist_ok=True)
    pd.DataFrame(mrows).to_csv(raw / "mohurd" / "mohurd_panel.csv", index=False, encoding="utf-8-sig")

    # 乡镇街道普查（县 320122）：城关镇与县城街道 is_seat_town = 1，另一乡镇为 0；03 应改用普查常住人口作县城人口
    (raw / "township").mkdir(exist_ok=True)
    for yr, pops in ((2010, (52000, 18000, 30000)), (2020, (61000, 21000, 26000))):
        pd.DataFrame([{"code12": f"320122{k:03d}000", "name": n, "county_adcode": "320122", "census_year": yr,
                       "is_seat_town": seat, "pop_resident": pop, "source": "合成"}
                      for k, (n, seat, pop) in enumerate(zip(("城关镇", "县城街道", "某乡"), (1, "是", 0), pops), 1)]).to_csv(
            raw / "township" / f"census_{yr}_township.csv", index=False, encoding="utf-8-sig")

    # 土地出让、城投债务、专项债、开发区（万元）
    (raw / "land").mkdir(exist_ok=True)
    codes = list(gdf["adcode"])
    pd.DataFrame([{"adcode": c, "year": yr, "land_conv_revenue": RNG.uniform(1e4, 5e5), "land_conv_area_ha": RNG.uniform(10, 800),
                   "n_parcels": int(RNG.integers(5, 300))} for c in codes for yr in (2017, 2018, 2019)]).to_csv(
        raw / "land" / "land_conveyance.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"adcode": c, "year": yr, "lgfv_debt": RNG.uniform(1e4, 3e6)}
                  for c in codes[::2] + prefs[:5] for yr in (2017, 2018, 2019)]).to_csv(
        raw / "land" / "lgfv_debt.csv", index=False, encoding="utf-8-sig")
    cats = ["市政", "园林绿化", "生态环保", "棚户区改造", "其他", "产业园区"]
    pd.DataFrame([{"adcode": c, "year": yr, "category": cats[int(RNG.integers(0, len(cats)))], "amount": RNG.uniform(1e3, 2e5)}
                  for c in codes for yr in (2019, 2020)]).to_csv(raw / "land" / "special_bonds.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"adcode": c, "zone_name": "测试开发区", "level": "国家级" if k % 3 == 0 else "省级",
                   "approved_area_km2": RNG.uniform(1, 30), "approval_year": 2006} for k, c in enumerate(codes[::4])]).to_csv(
        raw / "land" / "devzones_2018.csv", index=False, encoding="utf-8-sig")


def write_seats(base: Path, gdf: gpd.GeoDataFrame):
    """驻地点：每个县级行政区一个（取多边形中心），另加几个地级市政府驻地；故意漏掉一个单元。"""
    pts = gdf.to_crs(3857).representative_point().to_crs(4326)
    s = pd.DataFrame({"adcode": gdf["adcode"], "name": "x", "lon": pts.x, "lat": pts.y})
    s = s[s["adcode"] != NO_SEAT]
    pref = s[s["adcode"].isin(["440103", "320102"])].assign(adcode=lambda x: x["adcode"].str[:4] + "00")
    pd.concat([s, pref]).to_csv(base / "数据" / "原始" / "boundary" / "seat_points.csv", index=False, encoding="utf-8-sig")


def write_mock_gee(base: Path, units: pd.DataFrame):
    """模拟 01 脚本的分批输出（两个 chunk），用于检查 --merge-only 与后续脚本；列名按 01 与 03 的接口约定。"""
    ch = base / "数据" / "中间" / "gee" / "chunks"
    ch.mkdir(parents=True, exist_ok=True)
    rows = []
    for uid in units["unit_id"]:
        a20 = RNG.uniform(5e6, 3e8)
        pop = RNG.uniform(3e4, 5e6)
        r = {"unit_id": uid, "core_method": "fallback_centroid_1km" if uid == FALLBACK_UNIT else "seat_patch",
             "core_area_m2": a20, "core_closing_m": 200, "core2010_method": "seat_patch",
             "core2010_area_m2": a20 * RNG.uniform(0.6, 1.0), "c_builtcell_m2_2020": a20 * RNG.uniform(0.5, 0.95)}
        for y in (2010, 2020):
            for pre in ("u_", "c_"):
                bs = a20 * RNG.uniform(0.3, 0.6) * (1 if y == 2020 else RNG.uniform(0.6, 1.0))
                r.update({f"{pre}bs_{y}": bs, f"{pre}bsn_{y}": bs * 0.3, f"{pre}bv_{y}": bs * RNG.uniform(6, 30),
                          f"{pre}bvn_{y}": bs * 3, f"{pre}pop_ghs_{y}": pop * (1 if pre == "c_" else 1.6) * (1 if y == 2020 else RNG.uniform(0.7, 1.2)),
                          f"{pre}pop_wp_{y}": pop * 1.1})
        r.update({"u_ntl_viirs_2020": RNG.uniform(1e3, 1e6), "c_ntl_viirs_2020": RNG.uniform(1e3, 5e5),
                  "u_ntl_ccnl_2010": RNG.uniform(1e2, 1e5), "c_ntl_ccnl_2010": RNG.uniform(1e2, 5e4)})
        for k in ("tree", "shrub", "grass", "crop", "built", "bare", "snow", "water", "wetland", "mangrove", "moss"):
            r[f"c_wc_{k}_m2"] = a20 * RNG.uniform(0.01, 0.3) if k not in ("snow", "mangrove", "moss") else a20 * RNG.uniform(0, 0.002)
        tree = r["c_wc_tree_m2"] + r["c_wc_mangrove_m2"]
        sh = RNG.uniform(0.3, 0.9)
        r.update({"c_tree_stock_m2_2020": tree * sh, "c_tree_new_m2_2020": tree * (1 - sh),
                  "c_tree_flat_m2_2020": tree * RNG.uniform(0.4, 1.0)})
        r.update({"c_pw_tree_2020": pop * RNG.uniform(0.05, 0.3), "c_pw_green_2020": pop * RNG.uniform(0.2, 0.5),
                  "c_pop_expo_2020": pop, "c_greenpatch_m2_2020": a20 * RNG.uniform(0.01, 0.1),
                  "c_riparian_green_m2_2020": a20 * RNG.uniform(0.001, 0.02),
                  "c_roadside_green_m2_2020": a20 * RNG.uniform(0.005, 0.03),
                  "c_openveg_m2_2018": a20 * RNG.uniform(0.05, 0.2), "c_road_m2_2018": a20 * RNG.uniform(0.05, 0.15),
                  "c_pop_greenpatch500_2020": pop * RNG.uniform(0.3, 0.95), "u_access_min": RNG.uniform(10, 600),
                  "c_park_m2_2020": a20 * RNG.uniform(0.005, 0.05), "c_pop_park500_2020": pop * RNG.uniform(0.2, 0.9),
                  "c_greenway_len_m": RNG.uniform(0, 5e4), "c_pop_greenway500_2020": pop * RNG.uniform(0, 0.5)})
        for k, dist in (("school", 500), ("hospital", 1000), ("elderly", 500)):
            r[f"c_n_poi_{k}"] = int(RNG.integers(1, 300))
            r[f"c_pop_poi_{k}{dist}_2020"] = pop * RNG.uniform(0.3, 0.99)
        imp = a20 * RNG.uniform(0.2, 0.4)
        for y, f in ((1990, 0.3), (2000, 0.5), (2010, 0.8), (2018, 1.0)):
            r[f"c_gaia_imp_m2_{y}"] = imp * f * RNG.uniform(0.9, 1.1)
            r[f"u_gaia_imp_m2_{y}"] = imp * 2 * f * RNG.uniform(0.9, 1.1)
        r.update({"u_smod_ucl_m2_2020": a20 * 1.2, "u_smod_uc_m2_2020": a20 * 0.6, "c_smod_ucl_m2_2020": a20 * RNG.uniform(0.5, 1.0)})
        for y in (2000, 2010, 2020):
            for k in ("crop", "forest", "shrub", "grass", "water", "imp"):
                r[f"c_clcd{y}_{k}_m2"] = a20 * RNG.uniform(0.01, 0.3)
        r["c_green_new_clcd_m2_2020"] = r["c_clcd2020_forest_m2"] * RNG.uniform(0, 0.5)
        r.update({"c_ndvi_s2_2020": RNG.uniform(0.1, 0.5), "c_dw_trees_2020": RNG.uniform(0, 0.4),
                  "c_dw_grass_2020": RNG.uniform(0, 0.2), "r_ndvi_modis_2020": RNG.uniform(0.1, 0.8),
                  "u_elev": RNG.uniform(0, 3000), "u_slope": RNG.uniform(0, 25), "c_elev": RNG.uniform(0, 2000),
                  "c_slope": RNG.uniform(0, 10), "u_t2m_c_2020": RNG.uniform(-2, 24), "u_prcp_mm_2020": RNG.uniform(50, 2200)})
        rows.append(r)
    df = pd.DataFrame(rows)
    half = len(df) // 2
    for i, part in enumerate((df.iloc[:half], df.iloc[half:])):
        part.to_csv(ch / f"chunk_{i:04d}_unit.csv", index=False, encoding="utf-8-sig")
        feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [100, 30]},
                  "properties": {"unit_id": u}} for u in part["unit_id"]]
        (ch / f"chunk_{i:04d}_core.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}),
                                                        encoding="utf-8")


# ===========================================================================
# 代码块 3：依次运行各脚本
# 目的：用环境变量 FDT_BASE_DIR 把全部读写重定向到临时文件夹，逐个运行脚本并检查返回码与输出文件。
#       先在没有驻地点表时运行一次 00，确认 require_seats 会停止并给出说明；再补上驻地点表正式运行。
#       测试用的 config 副本把重庆设为区级财政（district_level_fiscal_prefs），不改动真实的 config.yaml。
# 结果：终端打印每一步的 OK/FAIL；全部 OK 时返回码为 0。
# ===========================================================================
def run(script: str, base: Path, *args, expect_fail: bool = False, must_contain: str | None = None) -> bool:
    env = dict(os.environ, FDT_BASE_DIR=str(base), PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(CODE / script), *args], env=env, cwd=CODE,
                       capture_output=True, text=True, encoding="utf-8")
    ok = (r.returncode != 0) if expect_fail else (r.returncode == 0)
    if ok and must_contain:
        ok = must_contain in (r.stdout + r.stderr)
    label = "（预期停止）" if expect_fail else ""
    print(f"{'OK  ' if ok else 'FAIL'} {script} {' '.join(args)}{label}")
    if not ok:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
    return ok


def patch_config(base: Path):
    p = base / "外部参数" / "config.yaml"
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    cfg["fiscal_census"]["district_level_fiscal_prefs"] = ["500000"]
    cfg["units"]["require_seats"] = True
    cfg["units"]["write_did_units"] = True
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return cfg


def main():
    keep = "--keep" in sys.argv
    base = Path(tempfile.mkdtemp(prefix="fdt_smoke_"))
    # 本进程随后也会 import common 与各脚本，先设置 FDT_BASE_DIR，使其日志同样写进临时文件夹
    os.environ["FDT_BASE_DIR"] = str(base)
    shutil.copytree(VERSION / "外部参数", base / "外部参数")
    cfg = patch_config(base)
    gdf = synthetic_counties()
    write_inputs(base, gdf)
    steps = [run("00_prepare_units.py", base, expect_fail=True, must_contain="units.require_seats")]
    write_seats(base, gdf)
    steps += [run("00_prepare_units.py", base)]
    ud = base / "数据" / "中间" / "units"
    units = pd.read_csv(ud / "units_table.csv", dtype=str, encoding="utf-8-sig")
    write_mock_gee(base, units)
    steps += [run("01_gee_extract_rs.py", base, "--merge-only"),
              run("02_build_fiscal_census.py", base),
              run("03_build_indicators.py", base),
              run("04_describe_and_map.py", base),
              run("05_models.py", base),
              run("tools/export_codebook_md.py", base)]

    # 关键断言：分组、代码变更、边界口径、新指标（前面某一步失败时，断言也会失败，但不会抛出长串报错）
    try:
        checks = assertions(base, ud, units, cfg)
    except Exception as e:  # noqa: BLE001
        checks = {f"断言无法完成（多半是前面的步骤失败）：{type(e).__name__}: {str(e)[:200]}": False}
    for k, v in checks.items():
        print(f"{'OK  ' if v else 'FAIL'} 断言：{k}")
    all_ok = all(steps) and all(bool(v) for v in checks.values())
    print(f"\n临时文件夹：{base}")
    if not keep and all_ok:
        shutil.rmtree(base)
        print("全部通过，已删除临时文件夹（加 --keep 可保留以便查看图表）。")
    sys.exit(0 if all_ok else 1)


def assertions(base: Path, ud: Path, units: pd.DataFrame, cfg: dict) -> dict:
    res = base / "数据" / "结果"
    ind = pd.read_csv(res / "unit_indicators.csv", dtype={"unit_id": str, "pref_code": str, "prov_code": str},
                      encoding="utf-8-sig")
    by = ind.set_index("unit_id")
    did = pd.read_csv(ud / "units_did_table.csv", dtype=str, encoding="utf-8-sig")
    c2u = pd.read_csv(ud / "county_to_unit.csv", dtype=str, encoding="utf-8-sig")
    summary = (res / "models_summary.md").read_text(encoding="utf-8")
    overview = [ln for ln in summary.split("## 各模型结果")[0].splitlines() if ln.startswith("| M") or ln.startswith("| R-")]
    cb = pd.read_csv(res / "codebook_indicators.csv", encoding="utf-8-sig")
    cb_vars = [v for v in cb["var"] if "YYYY" not in v]
    m05 = load_module("m05", "05_models.py")
    sample = m05.prepare(ind, cfg)
    qa_text = (base / "数据" / "中间" / "panel" / "qa_report.md").read_text(encoding="utf-8")
    checks = {
        "重庆外围区为 district_outer": set(ind.loc[ind["unit_id"].isin(["500110", "500114"]), "unit_type"]) == {"district_outer"},
        "东莞为市辖区单元 CP441900": "CP441900" in set(ind["unit_id"]),
        "仙桃为县级市": ind.loc[ind["unit_id"] == "429004", "unit_type"].eq("county_city").all(),
        "2010 普查旧代码并入 CP440100": ind.loc[ind["unit_id"] == "CP440100", "pop_resident_2010"].notna().all(),
        "财政自给率非空比例 > 0.8": ind["fss"].notna().mean() > 0.8,
        "五类分组齐全": {"县", "县级市"} <= set(ind["group5"]),
        "人均净流入非空比例 > 0.8": ind["net_inflow_pc"].notna().mean() > 0.8,
        "住房余量比已计算": ind["housing_slack_ratio"].notna().mean() > 0.5,
        "几何中心缓冲单元的 tree_pc_core 为缺失": pd.isna(by.loc[FALLBACK_UNIT, "tree_pc_core"])
        and by.loc[FALLBACK_UNIT, "core_fallback"] == 1,
        "兵团单元 excluded 且不在回归样本中": by.loc[EXCLUDED_UNIT, "excluded"] == 1 and EXCLUDED_UNIT not in set(sample["unit_id"]),
        "区级财政：重庆外围区有财政数据": by.loc[["500110", "500114"], "net_inflow_pc"].notna().all(),
        "区级财政：CP500000 不再标记口径不一致": not str(by.loc["CP500000", "fiscal_scope_mismatch"]).lower() in ("true", "1"),
        "县级单元层的单元多于主分析单元": len(did) > len(units),
        "驻地点文件已写出（主单元与县级单元层）": (ud / "seats.geojson").exists() and (ud / "seats_did.geojson").exists(),
        "每个模型都已运行或写明跳过原因": len(overview) == len(m05.MODELS)
        and all(("已运行" in ln) or ("跳过" in ln) for ln in overview),
        "至少 20 个模型已运行": sum("已运行" in ln for ln in overview) >= 20,
        "前趋势检验 M9p（1990–2000）已运行": any(ln.startswith("| M9p") and "已运行" in ln for ln in overview),
        "指标说明表中的指标都在结果表中": not [v for v in cb_vars if v not in ind.columns],
        "附录C 已导出": (base / "附录" / "附录C_指标定义与计算公式.md").exists(),
        "撤县设区：CP440100 含设区的区且人口占比 > 0": int(by.loc["CP440100", "n_converted"]) >= 1
        and by.loc["CP440100", "conv_pop_share_2020"] > 0,
        "撤县设区年份写入 county_to_unit": c2u.loc[c2u["adcode"] == "440106", "converted_year"].astype(float).eq(2014).all(),
        "普查年 12 月的变更（change_date）映射到 2020 年代码": by.loc["CP130100", "census_cov_2020"] == 1
        and f"'{LATE_OLD}'" not in qa_text,
        "县级市城区人口：大县级市标记": by.loc[LARGE_CITY, "large_county_city"] == 1
        and by.loc[LARGE_CITY, "size_class_all"] == "Ⅱ型大城市",
        "住建部面板：县的官方中心人口与人均公园面积": by.loc["320122", "core_pop_src"] == "official"
        and pd.notna(by.loc["320122", "park_area_pc_mohurd"]),
        "乡镇街道普查：县城人口取普查常住人口并计算县城人口变化": by.loc["320122", "core_pop_official_src"] == "census_town"
        and np.isclose(by.loc["320122", "core_pop_official"], 82000)
        and np.isclose(by.loc["320122", "town_pop_chg_1020"], np.log(82000 / 70000)),
        "分母效应 = −中心人口变化": np.allclose(
            ind["denom_effect_core"].dropna(), -ind.loc[ind["denom_effect_core"].notna(), "core_pop_chg_1020"]),
        "行政等级：北京 4，县 0": by.loc["CP110000", "admin_rank"] == 4 and by.loc["320122", "admin_rank"] == 0,
        "图与表已写出": all((res / f).exists() for f in ("table3_denominator_decomposition.csv", "table4_quadrant_town.csv",
                                                         "图表/图2_财政人口双变量地图.png", "图表/图S1_中心建成区质控.png",
                                                         "图表/图6_回归系数图.png")),
    }
    # 可选数据缺失时模型应跳过并写明原因：去掉公园矢量与土地债务变量后重新估计
    thin = sample.drop(columns=[c for c in sample.columns if c.startswith(("park_", "ln_park_pc", "ln_land", "ln_lgfv", "ln_special"))])
    _, ov, _ = m05.fit_all(thin, cfg["analysis"]["cluster_col"], 10)
    st = dict(zip(ov["模型"], ov["状态"]))
    checks["可选数据缺失时模型跳过并写明原因"] = all(
        st[k].startswith("跳过") for k in st if k.startswith(("M7d", "M7e", "M16"))) and len(st) == len(m05.MODELS)
    # 函数级检查：代码对照表中“部分划出、原代码保留”（A→A 0.8、A→B 0.2，2012 年）与
    # 同一旧代码的第二次变更（A→C，2018 年）同时存在时，2010 年数据应得到 B 200、C 800，总量守恒
    m02 = load_module("m02", "02_build_fiscal_census.py")
    cw = pd.DataFrame({"old_code": ["430121"] * 3, "new_code": ["430121", "430102", "430103"],
                       "weight": [0.8, 0.2, 1.0], "change_year": [2012, 2012, 2018]})
    h = m02.harmonize(pd.DataFrame({"adcode": ["430121"], "pop_resident": [1000.0]}), "adcode",
                      m02.CENSUS_COUNTS, [], cw, 2010, "pop_resident")
    got = dict(zip(h["adcode"], h["pop_resident"]))
    checks["代码对照：拆分保留原代码 + 二次变更，人口守恒"] = (
        set(got) == {"430102", "430103"} and np.isclose(got["430102"], 200) and np.isclose(got["430103"], 800))
    # 普查标准时点：同年 6 月的变更不映射（普查时已是新代码），12 月的变更映射；财政（不传 ref_date）都不映射
    one = pd.DataFrame({"adcode": ["430121"], "pop_resident": [10.0]})
    cw2 = pd.DataFrame({"old_code": ["430121"], "new_code": ["430102"], "weight": [1.0], "change_year": [2020.0],
                        "change_date": pd.to_datetime(["2020-06-01"])})
    cw3 = cw2.assign(change_date=pd.to_datetime(["2020-12-01"]))
    checks["代码对照：普查标准时点前后的同年变更"] = (
        m02.harmonize(one, "adcode", ["pop_resident"], [], cw2, 2020, ref_date="11-01")["adcode"].tolist() == ["430121"]
        and m02.harmonize(one, "adcode", ["pop_resident"], [], cw3, 2020, ref_date="11-01")["adcode"].tolist() == ["430102"]
        and m02.harmonize(one, "adcode", ["pop_resident"], [], cw3, 2020)["adcode"].tolist() == ["430121"])
    # 户比例按户数加权：两县户数 100 与 300、比例 0.1 与 0.5，合并后应为 0.4
    two = pd.DataFrame({"k": ["u", "u"], "households": [100.0, 300.0], "pop_resident": [900.0, 100.0],
                        "share_rent_market": [0.1, 0.5]})
    checks["住房来源比例按户数加权"] = np.isclose(
        m02.collapse(two, ["k"], ["households", "pop_resident"], ["share_rent_market"], m02.SHARE_WEIGHTS)["share_rent_market"].iloc[0], 0.4)
    # 2000 期转移支付只有分项时，按分项之和作为观测值（与主分析期、2010 期一致）
    checks["2000 期转移支付：只有分项时按观测值计算"] = by.loc[Y2000_SUBITEMS, "transfer_2000_src"] == "observed"
    # 双变量地图：excluded 单元显示为浅灰（边界文件自带 excluded 列，合并时不能出现 excluded_x、excluded_y）
    m04 = load_module("m04", "04_describe_and_map.py")
    colors = m04.map_colors(ind, gpd.read_file(ud / "units_full.gpkg")).set_index("unit_id")["color"]
    checks["双变量地图：兵团单元为浅灰"] = colors.get(EXCLUDED_UNIT) == "#dddddd"
    # 稳健性年份收支都有数的年份少于 min_fiscal_years 时，稳健性财政变量记为缺失
    one = ind.copy()
    uid = one.loc[one["net_inflow_pc_k_rob"].notna() & one["group5"].eq("县"), "unit_id"].iloc[0]
    one.loc[one["unit_id"] == uid, "n_years_rob"] = 1
    checks["稳健性年份不足时 net_inflow_pc_k_rob 为缺失"] = pd.isna(
        m05.prepare(one, cfg).set_index("unit_id").loc[uid, "net_inflow_pc_k_rob"])
    # 财政口径与单元不一致的单元，财政表字段全部置为缺失
    m03 = load_module("m03", "03_build_indicators.py")
    mm = m03.blank_scope_mismatch(pd.DataFrame({"unit_id": ["CP500000", "CP440100"], "fiscal_scope_mismatch": [True, False],
                                                "gen_budget_revenue_main": [1.0, 2.0], "hospital_beds_y2010": [3.0, 4.0]}))
    checks["财政口径不一致的单元财政字段为缺失"] = (mm["gen_budget_revenue_main"].isna().tolist() == [True, False]
                                                  and mm["hospital_beds_y2010"].isna().tolist() == [True, False])
    from common import classify_unit, load_overrides
    checks["名称缺失时按代码判别（神农架林区 429021 → 县）"] = classify_unit("429021", float("nan")) == "county"
    bad = base / "bad_overrides.csv"
    bad.write_text("adcode,unit_type\n110101,distrct\n", encoding="utf-8-sig")
    try:
        load_overrides(bad)
        checks["人工覆盖表填错类型时报错"] = False
    except ValueError as e:
        checks["人工覆盖表填错类型时报错"] = "distrct" in str(e)
    return checks


if __name__ == "__main__":
    main()
