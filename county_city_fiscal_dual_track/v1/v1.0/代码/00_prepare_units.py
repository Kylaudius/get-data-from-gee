# -*- coding: utf-8 -*-
"""
00_prepare_units.py  构建分析单元（analysis units）

在哪里运行：Mac “终端 Terminal”，先激活环境并进入 代码/ 文件夹：
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python 00_prepare_units.py

输入：外部参数/config.yaml 中 units.boundary_file 指向的县级行政区划边界（shp / gpkg / geojson），
      必须含 6 位行政区划代码字段和名称字段（字段名在 config 里设置）。
输出（写到 数据/中间/units/）：
    units_full.gpkg          全精度分析单元（本地分析、制图用）
    units_for_gee.geojson    简化后的分析单元（01 脚本直接读取并发送给 GEE）
    units_for_gee_shp.zip    同上，Shapefile 压缩包（若想上传为 GEE Asset 可用这个）
    units_table.csv          分析单元属性表（unit_id、类型、省/地级代码、面积）
    county_to_unit.csv       县级行政区 → 分析单元 的对应表（普查、财政数据按它汇总）

分析单元的定义（研究设计报告第 4 节）：
    A. 城市市辖区单元 city_proper：同一地级市的全部市辖区合并为一个单元（unit_id = "CP" + 地级代码），
       与《中国城市统计年鉴》“市辖区”口径和住建部“城区”口径对应；不设区的地级市（东莞、中山、儋州、嘉峪关）也归入此类。
       可在 config 的 city_proper_custom 中为重庆等“市辖区范围过大”的城市指定中心城区名单，
       名单外的市辖区单独成为 district_outer 单元。
    B. 县级市 county_city 与 县 county（含自治县、旗、自治旗、特区、林区）：每个行政区一个单元，unit_id = 6 位代码。
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (VERSION_DIR, atomic_write_csv, classify_unit, get_logger,  # noqa: E402
                    load_config, load_overrides, norm_adcode, pref_code, resolve)

# 中国常用等积投影（Albers Equal Area，双标准纬线 25°N/47°N，中央经线 105°E），用于计算面积
CHINA_ALBERS = "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"


def main():
    cfg = load_config()
    ucfg = cfg["units"]
    log = get_logger("00_prepare_units")
    out_dir = resolve(ucfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # 代码块 1：读取县级边界并检查坐标系
    # 目的：读入边界文件，统一到 WGS-84 经纬度 (EPSG:4326)。
    #       注意：来自高德/AMap、阿里云 DataV 的边界多为 GCJ-02 加密坐标，与遥感影像存在数百米偏移，
    #       本脚本无法自动识别 GCJ-02，请使用国家基础地理信息中心等 WGS-84/CGCS2000 来源的边界。
    # 结果：得到 GeoDataFrame gdf，含 adcode、name 两列。
    # -----------------------------------------------------------------------
    src = resolve(ucfg["boundary_file"])
    if not src.exists():
        log.error(f"找不到县级边界文件：{src}。请按 数据/README.md 的说明下载并放到该位置，或修改 config.yaml。")
        sys.exit(1)
    gdf = gpd.read_file(src)
    log.info(f"读取边界 {src.name}：{len(gdf)} 个要素，坐标系 {gdf.crs}")
    if gdf.crs is None:
        log.warning("边界文件没有坐标系信息，按 EPSG:4326 处理。请确认它不是 GCJ-02 或投影坐标。")
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    gdf = gdf.rename(columns={ucfg["code_field"]: "adcode", ucfg["name_field"]: "name"})
    gdf["adcode"] = gdf["adcode"].map(norm_adcode)
    bad = gdf["adcode"].isna().sum()
    if bad:
        log.warning(f"{bad} 个要素的行政区划代码无法识别，已剔除。")
    gdf = gdf[gdf["adcode"].notna()].copy()
    # 只保留内地 31 个省级单位（剔除台湾 71、香港 81、澳门 82）
    gdf = gdf[~gdf["adcode"].str[:2].isin(["71", "81", "82"])].copy()
    # 同一代码存在多个多边形（飞地）时先合并
    gdf = gdf.dissolve(by="adcode", as_index=False, aggfunc={"name": "first"})
    gdf["geometry"] = gdf.geometry.make_valid()

    # -----------------------------------------------------------------------
    # 代码块 2：判别单元类型
    # 目的：把每个县级行政区判为 市辖区 / 县级市 / 县 / 不设区地级市，并允许人工覆盖。
    # 结果：gdf 新增 admin_type、prov_code、pref_code 三列；在日志中打印各类型数量，便于与民政部统计核对。
    # -----------------------------------------------------------------------
    overrides = load_overrides(resolve(ucfg["unit_type_overrides"]))
    gdf["admin_type"] = [classify_unit(c, n, overrides) for c, n in zip(gdf["adcode"], gdf["name"])]
    gdf["prov_code"] = gdf["adcode"].str[:2] + "0000"
    gdf["pref_code"] = gdf["adcode"].map(pref_code)
    log.info("县级单元类型计数：\n" + gdf["admin_type"].value_counts().to_string())

    # -----------------------------------------------------------------------
    # 代码块 3：生成 county → unit 对应关系
    # 目的：市辖区按地级市合并为 city_proper；config 中指定了中心城区名单的城市，名单外的区成为 district_outer；
    #       县、县级市各自成为一个单元。
    # 结果：gdf 新增 unit_id、unit_type 两列。
    # -----------------------------------------------------------------------
    custom = {str(k): set(map(str, v)) for k, v in (ucfg.get("city_proper_custom") or {}).items()}

    def to_unit(row):
        t = row["admin_type"]
        if t == "pref_city_no_district":
            return "CP" + row["adcode"], "city_proper"
        if t == "district":
            pc = row["pref_code"]
            if pc in custom and row["adcode"] not in custom[pc]:
                return row["adcode"], "district_outer"
            return "CP" + pc, "city_proper"
        return row["adcode"], t

    gdf[["unit_id", "unit_type"]] = gdf.apply(lambda r: pd.Series(to_unit(r)), axis=1)
    c2u = gdf[["adcode", "name", "admin_type", "prov_code", "pref_code", "unit_id", "unit_type"]]
    atomic_write_csv(c2u, out_dir / "county_to_unit.csv")

    # -----------------------------------------------------------------------
    # 代码块 4：合并几何、计算面积
    # 目的：把同一 unit_id 的多边形合并 (dissolve)，在等积投影下计算面积（km²）。
    # 结果：units（GeoDataFrame），每行一个分析单元。
    # -----------------------------------------------------------------------
    units = gdf.dissolve(
        by="unit_id", as_index=False,
        aggfunc={"unit_type": "first", "prov_code": "first", "pref_code": "first", "name": lambda s: "、".join(s)},
    )
    units = units.rename(columns={"name": "member_names"})
    units["n_members"] = units["unit_id"].map(c2u["unit_id"].value_counts())
    units["area_km2"] = units.to_crs(CHINA_ALBERS).area / 1e6
    units = units.sort_values("unit_id").reset_index(drop=True)
    log.info("分析单元计数：\n" + units["unit_type"].value_counts().to_string())

    # -----------------------------------------------------------------------
    # 代码块 5：写出结果
    # 目的：全精度版本供本地分析；简化版本（默认容差约 100 m）供 GEE 使用，减少网络传输量。
    # 结果：数据/中间/units/ 下出现 units_full.gpkg、units_for_gee.geojson、units_for_gee_shp.zip、units_table.csv。
    # -----------------------------------------------------------------------
    units.to_file(out_dir / "units_full.gpkg", driver="GPKG")
    tol = float(ucfg.get("simplify_tolerance_deg", 0.001))
    simp = units[["unit_id", "unit_type", "prov_code", "pref_code", "geometry"]].copy()
    simp["geometry"] = simp.geometry.simplify(tol, preserve_topology=True).make_valid()
    simp.to_file(out_dir / "units_for_gee.geojson", driver="GeoJSON")
    shp_dir = out_dir / "units_for_gee_shp"
    shp_dir.mkdir(exist_ok=True)
    simp.to_file(shp_dir / "units_for_gee.shp", encoding="utf-8")
    with zipfile.ZipFile(out_dir / "units_for_gee_shp.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in shp_dir.iterdir():
            z.write(f, f.name)
    atomic_write_csv(units.drop(columns="geometry"), out_dir / "units_table.csv")

    # -----------------------------------------------------------------------
    # 代码块 6：可选的驻地点（县政府/市政府所在地）
    # 目的：若提供了驻地点表（adcode, lon, lat；WGS-84），01 脚本会优先选取“包含驻地点”的建成区斑块作为县城，
    #       而不是简单取最大斑块。市辖区单元使用地级市政府驻地（在表中以地级代码 xxxx00 填写）。
    # 结果：数据/中间/units/seats.geojson（没有驻地点表时跳过）。
    # -----------------------------------------------------------------------
    seat_file = ucfg.get("seat_points_file")
    if seat_file and resolve(seat_file).exists():
        s = pd.read_csv(resolve(seat_file), dtype={"adcode": str}, encoding="utf-8-sig")
        s["adcode"] = s["adcode"].map(norm_adcode)
        s["unit_id"] = s["adcode"].map(dict(zip(c2u["adcode"], c2u["unit_id"])))
        is_pref = s["adcode"].str[4:] == "00"
        s.loc[is_pref, "unit_id"] = "CP" + s.loc[is_pref, "adcode"].map(
            lambda c: c[:2] + "0000" if c[:2] in ("11", "12", "31", "50") else c)
        s = s.dropna(subset=["unit_id"]).drop_duplicates("unit_id")
        seats = gpd.GeoDataFrame(s[["unit_id", "adcode"]], geometry=gpd.points_from_xy(s["lon"], s["lat"]), crs=4326)
        seats.to_file(out_dir / "seats.geojson", driver="GeoJSON")
        log.info(f"驻地点：匹配到 {len(seats)} 个分析单元。")
    else:
        log.info("未提供驻地点表，01 脚本将以“单元内最大建成区斑块”作为县城/中心城区。")

    log.info(f"完成。输出目录：{out_dir.relative_to(VERSION_DIR)}")


if __name__ == "__main__":
    main()
