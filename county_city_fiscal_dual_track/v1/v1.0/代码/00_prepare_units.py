# -*- coding: utf-8 -*-
"""
00_prepare_units.py  构建分析单元（analysis units）

在哪里运行：Mac “终端 Terminal”，先激活环境并进入 代码/ 文件夹：
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python 00_prepare_units.py

输入：外部参数/config.yaml 中 units.boundary_file 指向的县级行政区划边界（shp / gpkg / geojson），
      必须含 6 位行政区划代码字段和名称字段（字段名在 config 里设置）；
      units.seat_points_file 指向的县、市政府驻地点表（units.require_seats 为 true 时必需）；
      可选的撤县（市）设区名单 units.converted_districts_file，缺失时从代码对照表推断。
输出（写到 数据/中间/units/）：
    units_full.gpkg            全精度分析单元（本地分析、制图用）
    units_for_gee.geojson      简化后的分析单元（01 脚本直接读取并发送给 GEE）
    units_for_gee_shp.zip      同上，Shapefile 压缩包（若想上传为 GEE Asset 可用这个）
    units_table.csv            分析单元属性表（unit_id、类型、省/地级代码、面积、excluded、n_converted）
    county_to_unit.csv         县级行政区 → 分析单元 的对应表（含 excluded、converted_year），普查、财政数据按它汇总
    seats.geojson              每个分析单元的驻地点（01 用它挑选县城/中心城区斑块）
    准实验用的县级单元层（units.write_did_units 为 true 时）：
    units_did_full.gpkg        每个 2020 年县级行政区一个单元，市辖区不合并，unit_id = 6 位代码
    units_did_for_gee.geojson  同上的简化版，供 01 --units did 使用
    units_did_table.csv        属性表（含所属主分析单元 main_unit_id、converted_year、excluded）
    seats_did.geojson          县级单元层的驻地点（驻地代码即单元代码）

分析单元的定义（研究设计报告第 5 节）：
    A. 城市市辖区单元 city_proper：同一地级市的全部市辖区合并为一个单元（unit_id = "CP" + 地级代码），
       与《中国城市统计年鉴》“市辖区”口径和住建部“城区”口径对应；不设区的地级市（东莞、中山、儋州、嘉峪关）也归入此类。
       可在 config 的 city_proper_custom 中为重庆等“市辖区范围过大”的城市指定中心城区名单，
       名单外的市辖区单独成为 district_outer 单元。
    B. 县级市 county_city 与 县 county（含自治县、旗、自治旗、特区、林区）：每个行政区一个单元，unit_id = 6 位代码。
    excluded：代码以 units.exclude_code_prefixes 开头的单元（默认新疆生产建设兵团城市 6590xx）保留在地图中，
       但 03–05 不把它们放进表格与回归。
    converted_year：2000 年后由县或县级市改设的市辖区（撤县设区）记下设区年份，units_table 的 n_converted 为单元内这类区的个数。
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (VERSION_DIR, atomic_write_csv, classify_unit, get_logger, is_excluded,  # noqa: E402
                    load_config, load_overrides, norm_adcode, pref_code, read_table, resolve)

# 中国常用等积投影（Albers Equal Area，双标准纬线 25°N/47°N，中央经线 105°E），用于计算面积
CHINA_ALBERS = "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
# 代码对照表 change_type 中表示“县或县级市改设市辖区”的写法
CONVERT_PATTERN = r"撤县设区|撤市设区|县改区|市改区"

SEAT_HELP = (
    "01 用驻地点挑选县城和中心城区所在的建成区斑块。没有驻地点时只能取单元内最大的斑块，"
    "常把工业园区或与邻县连成一片的城区误认作县城。\n"
    "获取方法有两种：\n"
    "  1. 国家基础地理信息中心 1:100 万公众版基础地理信息数据（全国地理信息资源目录服务系统 www.webmap.cn 免费下载）"
    "的居民地图层，筛选县级及以上政府驻地，导出 adcode,name,lon,lat；\n"
    "  2. 按民政部行政区划网站 xzqh.mca.gov.cn 或《中华人民共和国行政区划简册》列出的政府驻地名称做地理编码。"
    "高德、百度返回的坐标是 GCJ-02 或 BD-09，须先转成 WGS-84。\n"
    "表格式见 数据/模板/seat_points_template.csv，地级市政府驻地填地级代码 xxxx00。\n"
    "暂时拿不到时，可把 config.yaml 中 units.require_seats 改为 false，01 会退回最大斑块规则（不推荐，结果须复核）。"
)


def valid_polygons(geoms: gpd.GeoSeries) -> gpd.GeoSeries:
    """修复无效几何，并只保留面状部分。
    边界数据常有“毛刺”（退化成线的尖角）或自相交，make_valid 后会得到 多边形 + 线/点 的 GeometryCollection，
    Shapefile 无法写入这种几何（报错 Attempt to write non-polygon geometry），面积与分区统计也用不到线和点。"""
    def fix(g):
        if g is None or g.is_empty or g.geom_type in ("Polygon", "MultiPolygon"):
            return g
        polys = [x for x in shapely.get_parts(g) if x.geom_type in ("Polygon", "MultiPolygon")]
        return shapely.union_all(polys) if polys else None
    return gpd.GeoSeries([fix(g) for g in geoms.make_valid()], index=geoms.index, crs=geoms.crs)


def load_converted_years(cfg: dict, district_codes: set, log) -> dict:
    """撤县（市）设区的年份：优先读 units.converted_districts_file（adcode,name,convert_year,from_type,source），
    没有该文件时从代码对照表中 change_type 为撤县设区、撤市设区、县改区、市改区的行推断（new_code 为 2020 年的区）。
    只保留 convert_year 晚于 units.converted_since_year 的区。返回 {区代码: 设区年份}。"""
    ucfg = cfg["units"]
    since = int(ucfg.get("converted_since_year", 2000))
    path = ucfg.get("converted_districts_file")
    out = {}
    if path and resolve(path).exists():
        d = read_table(resolve(path), code_cols=("adcode",))
        d["adcode"] = d["adcode"].map(norm_adcode)
        d["convert_year"] = pd.to_numeric(d["convert_year"], errors="coerce") if "convert_year" in d else np.nan
        d = d.dropna(subset=["adcode", "convert_year"])
        src = f"撤县设区名单 {resolve(path).name} "
        pairs = d[["adcode", "convert_year"]]
    else:
        cw_path = resolve(cfg["fiscal_census"]["crosswalk_file"])
        if not cw_path.exists():
            log.warning("既没有撤县设区名单，也没有代码对照表，converted_year 全部为空，n_converted 为 0。")
            return out
        cw = read_table(cw_path, code_cols=("old_code", "new_code"))
        if "change_type" not in cw or "change_year" not in cw:
            log.warning("代码对照表缺少 change_type 或 change_year 列，无法推断撤县设区年份。")
            return out
        cw["adcode"] = cw["new_code"].map(norm_adcode)
        cw["convert_year"] = pd.to_numeric(cw["change_year"], errors="coerce")
        hit = cw["change_type"].astype("string").str.contains(CONVERT_PATTERN, regex=True, na=False)
        pairs = cw.loc[hit, ["adcode", "convert_year"]].dropna()
        src = f"代码对照表 {cw_path.name} 的 change_type "
    n_all = len(pairs)
    pairs = pairs[pairs["convert_year"] > since]
    not_district = sorted(set(pairs["adcode"]) - district_codes)
    if not_district:
        log.warning(f"撤县设区记录中 {len(not_district)} 个代码在 2020 年边界中不是市辖区，已忽略：{not_district[:10]}")
    pairs = pairs[pairs["adcode"].isin(district_codes)]
    out = pairs.groupby("adcode")["convert_year"].min().astype(int).to_dict()
    log.info(f"撤县设区：从{src}得到 {len(out)} 个 {since} 年后设立的区（原始 {n_all} 行）。")
    return out


def read_seats(ucfg: dict, log) -> pd.DataFrame | None:
    """读取驻地点表（adcode, lon, lat；WGS-84），代码规范化并剔除坐标缺失的行。"""
    seat_file = ucfg.get("seat_points_file")
    if not seat_file or not resolve(seat_file).exists():
        return None
    # read_table 自动识别 UTF-8 / GBK 编码（Excel 另存的中文 CSV 常为 GBK）
    s = read_table(resolve(seat_file), code_cols=("adcode",))
    if not {"adcode", "lon", "lat"} <= set(s.columns):
        log.error(f"驻地点表 {resolve(seat_file).name} 须包含 adcode、lon、lat 三列，现有列为 {list(s.columns)}。")
        sys.exit(1)
    s["adcode"] = s["adcode"].map(norm_adcode)
    s["lon"] = pd.to_numeric(s["lon"], errors="coerce")
    s["lat"] = pd.to_numeric(s["lat"], errors="coerce")
    bad = s["adcode"].isna() | s["lon"].isna() | s["lat"].isna()
    if bad.any():
        log.warning(f"驻地点表中 {int(bad.sum())} 行代码或坐标缺失，已剔除。")
    s = s[~bad].copy()
    out_range = ~(s["lon"].between(73, 136) & s["lat"].between(3, 54))
    if out_range.any():
        log.warning(f"驻地点表中 {int(out_range.sum())} 行坐标不在中国范围内（经度 73–136、纬度 3–54），已剔除："
                    f"{s.loc[out_range, 'adcode'].head(10).tolist()}")
        s = s[~out_range]
    return s


def write_gee_layers(units: gpd.GeoDataFrame, out_dir: Path, stem: str, tol: float, shp: bool):
    """写出全精度 GPKG 与简化后的 GeoJSON（及可选的 Shapefile 压缩包）。"""
    units.to_file(out_dir / f"{stem}_full.gpkg", driver="GPKG")
    simp = units[["unit_id", "unit_type", "prov_code", "pref_code", "geometry"]].copy()
    simp["geometry"] = valid_polygons(simp.geometry.simplify(tol, preserve_topology=True))
    simp.to_file(out_dir / f"{stem}_for_gee.geojson", driver="GeoJSON")
    if shp:
        shp_dir = out_dir / f"{stem}_for_gee_shp"
        shp_dir.mkdir(exist_ok=True)
        simp.to_file(shp_dir / f"{stem}_for_gee.shp", encoding="utf-8")
        with zipfile.ZipFile(out_dir / f"{stem}_for_gee_shp.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in shp_dir.iterdir():
                z.write(f, f.name)


def main():
    cfg = load_config()
    ucfg = cfg["units"]
    log = get_logger("00_prepare_units")
    out_dir = resolve(ucfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # 代码块 1：检查驻地点表并读取县级边界
    # 目的：units.require_seats 为 true 而驻地点表不存在时，先停下并说明获取方法（避免跑完 GEE 才发现县城识别有误）。
    #       读入边界文件，统一到 WGS-84 经纬度 (EPSG:4326)。
    #       注意：来自高德/AMap、阿里云 DataV 的边界多为 GCJ-02 加密坐标，与遥感影像存在数百米偏移，
    #       本脚本无法自动识别 GCJ-02，请使用国家基础地理信息中心等 WGS-84/CGCS2000 来源的边界。
    # 结果：得到 GeoDataFrame gdf，含 adcode、name 两列；seats_raw 为驻地点表（可能为 None）。
    # -----------------------------------------------------------------------
    require_seats = bool(ucfg.get("require_seats", False))
    seats_raw = read_seats(ucfg, log)
    if seats_raw is None and require_seats:
        log.error(f"找不到县、市政府驻地点表：{resolve(ucfg.get('seat_points_file') or '（config 未设置 seat_points_file）')}\n"
                  + SEAT_HELP)
        sys.exit(1)
    if seats_raw is not None and seats_raw.empty and require_seats:
        # 表存在但没有一行可用（例如经纬度写反，全部落在中国范围外），不能当作已提供驻地点
        log.error(f"驻地点表 {resolve(ucfg['seat_points_file']).name} 中没有一行有效的代码与坐标，请检查 lon、lat 是否写反、"
                  "代码是否为 6 位。\n" + SEAT_HELP)
        sys.exit(1)

    src = resolve(ucfg["boundary_file"])
    if not src.exists():
        log.error(f"找不到县级边界文件：{src}。请按 数据/README.md 的说明下载并放到该位置，或修改 config.yaml。")
        sys.exit(1)
    gdf = gpd.read_file(src)
    log.info(f"读取边界 {src.name}：{len(gdf)} 个要素，坐标系 {gdf.crs}；边界年份按 units.boundary_year = "
             f"{ucfg.get('boundary_year', '未设置')} 处理")
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
    gdf["geometry"] = valid_polygons(gdf.geometry)

    # -----------------------------------------------------------------------
    # 代码块 2：判别单元类型、排除标记与撤县设区年份
    # 目的：把每个县级行政区判为 市辖区 / 县级市 / 县 / 不设区地级市，并允许人工覆盖（覆盖值填错会直接报错）；
    #       按 exclude_code_prefixes 标记兵团城市等不进入分析的单元；记下 2000 年后撤县（市）设区的年份。
    # 结果：gdf 新增 admin_type、prov_code、pref_code、excluded、converted_year 五列；日志打印各类型数量，便于与民政部统计核对。
    # -----------------------------------------------------------------------
    try:
        overrides = load_overrides(resolve(ucfg["unit_type_overrides"]))
    except ValueError as e:
        log.error(str(e))
        sys.exit(1)
    gdf["admin_type"] = [classify_unit(c, n, overrides) for c, n in zip(gdf["adcode"], gdf["name"])]
    gdf["prov_code"] = gdf["adcode"].str[:2] + "0000"
    gdf["pref_code"] = gdf["adcode"].map(pref_code)
    log.info("县级单元类型计数：\n" + gdf["admin_type"].value_counts().to_string())
    prefixes = [str(p) for p in (ucfg.get("exclude_code_prefixes") or [])]
    gdf["excluded"] = gdf["adcode"].map(lambda c: is_excluded(c, prefixes))
    if gdf["excluded"].any():
        log.info(f"excluded：{int(gdf['excluded'].sum())} 个县级行政区的代码以 {prefixes} 开头，保留在地图中，"
                 f"不进入表格与回归：{gdf.loc[gdf['excluded'], 'adcode'].tolist()[:20]}")
    districts = set(gdf.loc[gdf["admin_type"] == "district", "adcode"])
    conv = load_converted_years(cfg, districts, log)
    gdf["converted_year"] = gdf["adcode"].map(conv).astype("Int64")

    # -----------------------------------------------------------------------
    # 代码块 3：生成 county → unit 对应关系
    # 目的：市辖区按地级市合并为 city_proper；config 中指定了中心城区名单的城市，名单外的区成为 district_outer；
    #       县、县级市各自成为一个单元。
    # 结果：gdf 新增 unit_id、unit_type 两列；写出 county_to_unit.csv。
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
    c2u = gdf[["adcode", "name", "admin_type", "prov_code", "pref_code", "unit_id", "unit_type",
               "excluded", "converted_year"]]
    atomic_write_csv(c2u, out_dir / "county_to_unit.csv")

    # -----------------------------------------------------------------------
    # 代码块 4：合并几何、计算面积
    # 目的：把同一 unit_id 的多边形合并 (dissolve)，在等积投影下计算面积（km²）。
    #       单元的 excluded 取成员是否全部被排除；n_converted 为成员中 2000 年后撤县设区的区数。
    # 结果：units（GeoDataFrame），每行一个分析单元。
    # -----------------------------------------------------------------------
    units = gdf.dissolve(
        by="unit_id", as_index=False,
        aggfunc={"unit_type": "first", "prov_code": "first", "pref_code": "first",
                 # 名称缺失（None/NaN）的成员跳过，避免拼接成员名时报错
                 "name": lambda s: "、".join(str(x) for x in s if isinstance(x, str) and x)},
    )
    units = units.rename(columns={"name": "member_names"})
    units["n_members"] = units["unit_id"].map(c2u["unit_id"].value_counts())
    units["excluded"] = units["unit_id"].map(c2u.groupby("unit_id")["excluded"].all()).astype(bool)
    units["n_converted"] = units["unit_id"].map(c2u.groupby("unit_id")["converted_year"].count()).fillna(0).astype(int)
    units["area_km2"] = units.to_crs(CHINA_ALBERS).area / 1e6
    units = units.sort_values("unit_id").reset_index(drop=True)
    log.info("分析单元计数：\n" + units["unit_type"].value_counts().to_string())
    if units["n_converted"].sum():
        log.info(f"含撤县设区的市辖区单元 {int((units['n_converted'] > 0).sum())} 个，共 {int(units['n_converted'].sum())} 个区。")

    # -----------------------------------------------------------------------
    # 代码块 5：写出结果
    # 目的：全精度版本供本地分析；简化版本（默认容差约 100 m）供 GEE 使用，减少网络传输量。
    # 结果：数据/中间/units/ 下出现 units_full.gpkg、units_for_gee.geojson、units_for_gee_shp.zip、units_table.csv。
    # -----------------------------------------------------------------------
    tol = float(ucfg.get("simplify_tolerance_deg", 0.001))
    write_gee_layers(units, out_dir, "units", tol, shp=True)
    atomic_write_csv(units.drop(columns="geometry"), out_dir / "units_table.csv")

    # -----------------------------------------------------------------------
    # 代码块 6：驻地点（县政府/市政府所在地）
    # 目的：01 脚本优先选取“包含驻地点”的建成区斑块作为县城，而不是简单取最大斑块。
    #       市辖区单元使用地级市政府驻地（在表中以地级代码 xxxx00 填写）；只填了区政府驻地时用其中一个。
    #       列出没有驻地点的单元，便于补齐。
    # 结果：数据/中间/units/seats.geojson（没有驻地点表且 require_seats 为 false 时跳过）。
    # -----------------------------------------------------------------------
    if seats_raw is not None:
        s = seats_raw.copy()
        s["unit_id"] = s["adcode"].map(dict(zip(c2u["adcode"], c2u["unit_id"])))
        is_pref = s["adcode"].str[4:] == "00"
        s.loc[is_pref, "unit_id"] = "CP" + s.loc[is_pref, "adcode"].map(pref_code)
        # 同一市辖区单元若同时填了“地级市政府驻地（xxxx00）”和“某个区政府驻地”，优先用地级市政府驻地
        s = (s.assign(_is_pref=is_pref).sort_values("_is_pref", ascending=False, kind="stable")
             .dropna(subset=["unit_id"]))
        s = s[s["unit_id"].isin(set(units["unit_id"]))].drop_duplicates("unit_id")
        seats = gpd.GeoDataFrame(s[["unit_id", "adcode"]], geometry=gpd.points_from_xy(s["lon"], s["lat"]), crs=4326)
        seats.to_file(out_dir / "seats.geojson", driver="GeoJSON")
        # 驻地点应落在所属单元内；落在单元外多半是坐标系（GCJ-02）或代码填错
        inside = gpd.sjoin(seats, units[["unit_id", "geometry"]].rename(columns={"unit_id": "_uid"}),
                           how="left", predicate="within")
        outside = inside[inside["_uid"] != inside["unit_id"]]["unit_id"].drop_duplicates()
        if len(outside):
            log.warning(f"{len(outside)} 个驻地点不在所属单元的边界内，请核对坐标系（须为 WGS-84）与代码："
                        f"{outside.tolist()[:20]}")
        missing = sorted(set(units["unit_id"]) - set(seats["unit_id"]))
        log.info(f"驻地点：匹配到 {len(seats)} / {len(units)} 个分析单元。")
        if missing:
            log.warning(f"{len(missing)} 个分析单元没有驻地点，01 将对它们使用最大斑块规则。请在驻地点表中补齐："
                        f"{missing[:50]}{' …' if len(missing) > 50 else ''}")
    else:
        log.warning("未提供驻地点表且 units.require_seats 为 false，01 将以“单元内最大建成区斑块”作为县城/中心城区。")

    # -----------------------------------------------------------------------
    # 代码块 7：准实验用的县级单元层（不合并市辖区）
    # 目的：撤县设区、省直管县等准实验（研究设计报告 §9.5）需要每个 2020 年县级行政区单独成为一个单元，
    #       市辖区也不合并，这样撤县设区的区仍保留自己的县城斑块。unit_id 直接用 6 位代码。
    #       驻地点：代码与单元相同的驻地直接使用；没有自己驻地的单元，若地级市政府驻地（xxxx00）落在其中则用它。
    # 结果：units_did_full.gpkg、units_did_for_gee.geojson、units_did_table.csv、seats_did.geojson。
    # -----------------------------------------------------------------------
    if ucfg.get("write_did_units", False):
        did = gdf.rename(columns={"unit_id": "main_unit_id", "unit_type": "main_unit_type"}).copy()
        did["unit_id"] = did["adcode"]
        did["unit_type"] = did["admin_type"]
        did["area_km2"] = did.to_crs(CHINA_ALBERS).area / 1e6
        did = did[["unit_id", "adcode", "name", "unit_type", "admin_type", "main_unit_id", "main_unit_type",
                   "prov_code", "pref_code", "excluded", "converted_year", "area_km2", "geometry"]]
        did = did.sort_values("unit_id").reset_index(drop=True)
        write_gee_layers(did, out_dir, "units_did", tol, shp=False)
        atomic_write_csv(did.drop(columns="geometry"), out_dir / "units_did_table.csv")
        if seats_raw is not None:
            own = seats_raw[seats_raw["adcode"].isin(set(did["unit_id"]))].drop_duplicates("adcode")
            own = gpd.GeoDataFrame({"unit_id": own["adcode"], "adcode": own["adcode"]},
                                   geometry=gpd.points_from_xy(own["lon"], own["lat"]), crs=4326)
            pref = seats_raw[(seats_raw["adcode"].str[4:] == "00") & ~seats_raw["adcode"].isin(set(did["unit_id"]))]
            if len(pref):
                pref = gpd.GeoDataFrame({"adcode": pref["adcode"].to_numpy()},
                                        geometry=gpd.points_from_xy(pref["lon"], pref["lat"]), crs=4326)
                j = gpd.sjoin(pref, did[["unit_id", "geometry"]], how="inner", predicate="within")
                j = j[~j["unit_id"].isin(set(own["unit_id"]))].drop_duplicates("unit_id")
                own = pd.concat([own, gpd.GeoDataFrame(j[["unit_id", "adcode"]], geometry=j.geometry, crs=4326)],
                                ignore_index=True)
            seats_did = gpd.GeoDataFrame(own[["unit_id", "adcode"]], geometry=own.geometry, crs=4326)
            seats_did.to_file(out_dir / "seats_did.geojson", driver="GeoJSON")
            miss_did = sorted(set(did["unit_id"]) - set(seats_did["unit_id"]))
            log.info(f"县级单元层：{len(did)} 个单元，驻地点匹配 {len(seats_did)} 个。")
            if miss_did:
                log.warning(f"县级单元层中 {len(miss_did)} 个单元没有驻地点（多为市辖区，驻地点表只填了地级市政府驻地）："
                            f"{miss_did[:30]}{' …' if len(miss_did) > 30 else ''}")
        else:
            log.info(f"县级单元层：{len(did)} 个单元（没有驻地点表）。")

    log.info(f"完成。输出目录：{out_dir.relative_to(VERSION_DIR)}")


if __name__ == "__main__":
    main()
