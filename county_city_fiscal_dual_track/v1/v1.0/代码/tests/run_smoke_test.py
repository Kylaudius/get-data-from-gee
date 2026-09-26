# -*- coding: utf-8 -*-
"""
tests/run_smoke_test.py  用合成数据 (synthetic data) 端到端检查 00、01(合并部分)、02、03、04、05 能否跑通

在哪里运行：Mac “终端 Terminal”，在 代码/ 文件夹下：
    python tests/run_smoke_test.py
能得到什么：在系统临时文件夹中生成一套“假”的边界、财政、普查与 GEE 结果，依次运行各脚本，
            最后打印每一步是否成功及输出文件位置。合成数据只用于检查代码，任何数值都不是研究结果，
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
from shapely.geometry import box

CODE = Path(__file__).resolve().parents[1]
VERSION = CODE.parent
RNG = np.random.default_rng(20260926)


# ===========================================================================
# 代码块 1：合成县级边界
# 目的：构造覆盖各类特殊情况的县级单元：直辖市、重庆主城与外围区、普通地级市的区/县/县级市、
#       不设区地级市（441900）、省直辖县级市（429004）、一个曾为县级市后改设区的代码（440184 → 440106）。
# 结果：返回 GeoDataFrame（adcode、name、geometry）。
# ===========================================================================
def synthetic_counties() -> gpd.GeoDataFrame:
    specs = []
    specs += [(f"1101{i:02d}", f"测试{i}区") for i in range(1, 6)]
    specs += [(c, f"测试{c}区") for c in ["500103", "500104", "500105", "500106", "500107", "500108", "500110", "500114"]]
    specs += [("500229", "测试城口县"), ("500230", "测试丰都县")]
    specs += [(c, f"测试{c}区") for c in ["440103", "440104", "440105", "440106", "440303", "440304"]]
    specs += [("441900", "测试东莞市"), ("429004", "测试仙桃市")]
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


# ===========================================================================
# 代码块 2：合成财政、普查、城区人口与 GEE 结果
# 目的：按单元类型生成量级合理的随机数，覆盖缺失值、代码变更与重复记录等情形。
# 结果：写入临时文件夹 数据/原始/ 与 数据/中间/gee/ 下的各文件。
# ===========================================================================
def write_inputs(base: Path, gdf: gpd.GeoDataFrame):
    raw = base / "数据" / "原始"
    (raw / "boundary").mkdir(parents=True, exist_ok=True)
    gdf.to_file(raw / "boundary" / "county_2020.shp", encoding="utf-8")

    sys.path.insert(0, str(CODE))
    from common import classify_unit, pref_code
    gdf = gdf.copy()
    gdf["t"] = [classify_unit(c, n) for c, n in zip(gdf["adcode"], gdf["name"])]

    # 普查：2010 年用旧代码 440184（2014 年改设区为 440106）
    rows = []
    for yr in (2000, 2010, 2020):
        for c, t in zip(gdf["adcode"], gdf["t"]):
            base_pop = {"district": 6e5, "county": 3.5e5, "county_city": 6e5, "pref_city_no_district": 8e6}[t]
            growth = {"district": 0.015, "county": -0.008, "county_city": 0.002, "pref_city_no_district": 0.03}[t]
            pop = base_pop * np.exp(growth * (yr - 2020) * -1) * RNG.lognormal(0, 0.3)
            code = "440184" if (yr < 2014 and c == "440106") else c
            rows.append({"adcode": code, "name": "x", "census_year": yr, "pop_resident": round(pop),
                         "pop_urban": round(pop * RNG.uniform(0.3, 0.95)), "households": round(pop / 2.8),
                         "hh_pop": round(pop * 0.9), "pop_hukou": round(pop * RNG.uniform(0.7, 1.4)),
                         "housing_area_pc": RNG.uniform(25, 55) if yr == 2020 else np.nan,
                         "share_rent_market": RNG.uniform(0.02, 0.4) if yr == 2020 else np.nan})
    cen = pd.DataFrame(rows)
    (raw / "census").mkdir(exist_ok=True)
    for yr in (2000, 2010, 2020):
        d = cen[cen["census_year"] == yr]
        if yr == 2020:
            d = pd.concat([d, d.head(1)])  # 故意放一条重复记录
        d.to_csv(raw / "census" / f"census_{yr}_county.csv", index=False, encoding="utf-8-sig")

    (raw / "crosswalk").mkdir(exist_ok=True)
    pd.DataFrame([{"old_code": "440184", "old_name": "旧县级市", "new_code": "440106", "new_name": "新区",
                   "change_year": 2014, "change_type": "撤市设区", "weight": 1}]).to_csv(
        raw / "crosswalk" / "admin_crosswalk.csv", index=False, encoding="utf-8-sig")

    # 财政：县、县级市（万元）；440184 在 2009–2011 年仍为县级市
    frows = []
    for yr in (2009, 2010, 2011, 2018, 2019, 2020, 2021):
        for c, t in zip(gdf["adcode"], gdf["t"]):
            if t not in ("county", "county_city"):
                if not (c == "440106" and yr <= 2011):
                    continue
                c = "440184"
            exp = RNG.lognormal(np.log(3e5), 0.4)
            frows.append({"adcode": c, "name": "x", "year": yr, "gen_budget_revenue": exp * RNG.uniform(0.1, 0.5),
                          "gen_budget_expenditure": exp, "tax_revenue": exp * 0.2, "pop_hukou_yearend": 40})
    (raw / "fiscal").mkdir(exist_ok=True)
    pd.DataFrame(frows).to_csv(raw / "fiscal" / "fiscal_county.csv", index=False, encoding="utf-8-sig")

    prefs = sorted({pref_code(c) for c, t in zip(gdf["adcode"], gdf["t"]) if t == "district"} | {"441900"})
    crows = []
    for yr in (2009, 2010, 2011, 2018, 2019, 2021):
        for p in prefs:
            exp = RNG.lognormal(np.log(3e6), 0.5)
            crows.append({"pref_code": p, "name": "x", "year": yr, "scope": "市辖区",
                          "gen_budget_revenue": exp * RNG.uniform(0.5, 0.95), "gen_budget_expenditure": exp,
                          "tax_revenue": exp * 0.5, "land_conveyance_revenue": exp * 0.4})
    pd.DataFrame(crows).to_csv(raw / "fiscal" / "fiscal_city_proper.csv", index=False, encoding="utf-8-sig")

    (raw / "city").mkdir(exist_ok=True)
    pd.DataFrame({"pref_code": prefs, "city_name": "x", "year": 2020,
                  "urban_pop_10k": RNG.uniform(40, 1200, len(prefs)), "urban_temp_pop_10k": 0}).to_csv(
        raw / "city" / "city_urban_pop_2020.csv", index=False, encoding="utf-8-sig")


def write_mock_gee(base: Path, units: pd.DataFrame):
    """模拟 01 脚本的分批输出（两个 chunk），用于检查 --merge-only 与后续脚本。"""
    ch = base / "数据" / "中间" / "gee" / "chunks"
    ch.mkdir(parents=True, exist_ok=True)
    rows = []
    for uid in units["unit_id"]:
        a20 = RNG.uniform(5e6, 3e8)
        pop = RNG.uniform(3e4, 5e6)
        r = {"unit_id": uid, "core_method": "largest_patch", "core_area_m2": a20,
             "core2010_area_m2": a20 * RNG.uniform(0.6, 1.0)}
        for y in (2010, 2020):
            for pre in ("u_", "c_"):
                bs = a20 * RNG.uniform(0.3, 0.6)
                r.update({f"{pre}bs_{y}": bs, f"{pre}bsn_{y}": bs * 0.3, f"{pre}bv_{y}": bs * RNG.uniform(6, 30),
                          f"{pre}bvn_{y}": bs * 3, f"{pre}pop_ghs_{y}": pop, f"{pre}pop_wp_{y}": pop * 1.1})
        r.update({"u_ntl_viirs_2020": RNG.uniform(1e3, 1e6), "c_ntl_viirs_2020": RNG.uniform(1e3, 5e5),
                  "u_ntl_ccnl_2010": RNG.uniform(1e2, 1e5), "c_ntl_ccnl_2010": RNG.uniform(1e2, 5e4)})
        for k in ("tree", "shrub", "grass", "crop", "built", "bare", "water", "wetland"):
            r[f"c_wc_{k}_m2"] = a20 * RNG.uniform(0.01, 0.3)
        r.update({"c_pw_tree_2020": pop * RNG.uniform(0.05, 0.3), "c_pw_green_2020": pop * RNG.uniform(0.2, 0.5),
                  "c_pop_expo_2020": pop, "c_greenpatch_m2_2020": a20 * RNG.uniform(0.01, 0.1),
                  "c_riparian_green_m2_2020": a20 * RNG.uniform(0.001, 0.02),
                  "c_roadside_green_m2_2020": a20 * RNG.uniform(0.005, 0.03),
                  "c_openveg_m2_2018": a20 * RNG.uniform(0.05, 0.2), "c_road_m2_2018": a20 * RNG.uniform(0.05, 0.15),
                  "c_pop_greenpatch500_2020": pop * RNG.uniform(0.3, 0.95), "u_access_min": RNG.uniform(10, 600)})
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
# 结果：终端打印每一步的 OK/FAIL；全部 OK 时返回码为 0。
# ===========================================================================
def run(script: str, base: Path, *args) -> bool:
    env = dict(os.environ, FDT_BASE_DIR=str(base), PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(CODE / script), *args], env=env, cwd=CODE,
                       capture_output=True, text=True, encoding="utf-8")
    ok = r.returncode == 0
    print(f"{'OK  ' if ok else 'FAIL'} {script} {' '.join(args)}")
    if not ok:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
    return ok


def main():
    keep = "--keep" in sys.argv
    base = Path(tempfile.mkdtemp(prefix="fdt_smoke_"))
    # 本进程随后也会 import common 与 02 脚本，先设置 FDT_BASE_DIR，使其日志同样写进临时文件夹
    os.environ["FDT_BASE_DIR"] = str(base)
    shutil.copytree(VERSION / "外部参数", base / "外部参数")
    gdf = synthetic_counties()
    write_inputs(base, gdf)
    steps = [run("00_prepare_units.py", base)]
    units = pd.read_csv(base / "数据" / "中间" / "units" / "units_table.csv", dtype=str, encoding="utf-8-sig")
    write_mock_gee(base, units)
    steps += [run("01_gee_extract_rs.py", base, "--merge-only"),
              run("02_build_fiscal_census.py", base),
              run("03_build_indicators.py", base),
              run("04_describe_and_map.py", base),
              run("05_models.py", base)]

    # 关键断言：分组、代码变更、边界口径
    ind = pd.read_csv(base / "数据" / "结果" / "unit_indicators.csv", dtype={"unit_id": str}, encoding="utf-8-sig")
    checks = {
        "重庆外围区为 district_outer": set(ind.loc[ind["unit_id"].isin(["500110", "500114"]), "unit_type"]) == {"district_outer"},
        "东莞为市辖区单元 CP441900": "CP441900" in set(ind["unit_id"]),
        "仙桃为县级市": ind.loc[ind["unit_id"] == "429004", "unit_type"].eq("county_city").all(),
        "2010 普查旧代码并入 CP440100": ind.loc[ind["unit_id"] == "CP440100", "pop_resident_2010"].notna().all(),
        "财政自给率非空比例 > 0.8": ind["fss"].notna().mean() > 0.8,
        "五类分组齐全": {"县", "县级市"} <= set(ind["group5"]),
    }
    # 函数级检查：代码对照表中“部分划出、原代码保留”（A→A 0.8、A→B 0.2，2012 年）与
    # 同一旧代码的第二次变更（A→C，2018 年）同时存在时，2010 年数据应得到 B 200、C 800，总量守恒
    spec = importlib.util.spec_from_file_location("m02", CODE / "02_build_fiscal_census.py")
    m02 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m02)
    cw = pd.DataFrame({"old_code": ["430121"] * 3, "new_code": ["430121", "430102", "430103"],
                       "weight": [0.8, 0.2, 1.0], "change_year": [2012, 2012, 2018]})
    h = m02.harmonize(pd.DataFrame({"adcode": ["430121"], "pop_resident": [1000.0]}), "adcode",
                      m02.CENSUS_COUNTS, [], cw, 2010, "pop_resident")
    got = dict(zip(h["adcode"], h["pop_resident"]))
    checks["代码对照：拆分保留原代码 + 二次变更，人口守恒"] = (
        set(got) == {"430102", "430103"} and np.isclose(got["430102"], 200) and np.isclose(got["430103"], 800))
    from common import classify_unit
    checks["名称缺失时按代码判别（神农架林区 429021 → 县）"] = classify_unit("429021", float("nan")) == "county"
    for k, v in checks.items():
        print(f"{'OK  ' if v else 'FAIL'} 断言：{k}")
    all_ok = all(steps) and all(checks.values())
    print(f"\n临时文件夹：{base}")
    if not keep and all_ok:
        shutil.rmtree(base)
        print("全部通过，已删除临时文件夹（加 --keep 可保留以便查看图表）。")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
