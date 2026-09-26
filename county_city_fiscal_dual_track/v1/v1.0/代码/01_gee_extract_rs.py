# -*- coding: utf-8 -*-
"""
01_gee_extract_rs.py  用 Google Earth Engine 批量提取每个分析单元的遥感指标（断点续跑 + 按 chunk 汇报进度）

在哪里运行：Mac “终端 Terminal”
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python 01_gee_extract_rs.py --preflight            # 第一步：只检查 GEE 登录与数据集是否可用（约 1 分钟）
    python 01_gee_extract_rs.py --province 44 --limit 20  # 第二步：试跑广东前 20 个单元，检查结果是否合理
    python 01_gee_extract_rs.py                        # 第三步：全国正式运行（可随时 Ctrl+C 中断，重新运行会自动续跑）
    python 01_gee_extract_rs.py --merge-only           # 可选：只把已完成的各批结果合并成总表

前置条件：已完成 00_prepare_units.py；已按 代码/README.md 完成 GEE 注册、Cloud 项目创建和 ee.Authenticate()。

每个分析单元提取三组指标（研究设计报告第 6 节、附录C 有完整定义）：
  u_*  整个单元（县域 / 市辖区合计）：GHSL 建成面积、建筑体量、GHS-POP 与 WorldPop 人口、夜间灯光、地形、气候
  c_*  中心建成区（县城 / 中心城区，按 GHSL 建成栅格的最大连通斑块或含驻地点的斑块识别，固定为 2020 年边界）：
       同上各项 + ESA WorldCover 2020 各地类面积、Sentinel-2 NDVI、Dynamic World 树木/草地概率、公园（可选）
  r_*  中心建成区外 5 km 环带：MODIS NDVI，作为“自然植被本底”控制变量（干旱区县城绿地少不等于财政投入少）

输出（数据/中间/gee/）：
  chunks/chunk_XXXX_unit.csv、chunk_XXXX_core.geojson   每批结果（存在即视为完成，续跑时跳过）
  chunks_manifest.json                                  分批方案（首次运行生成，保证续跑时分批不变）
  failures.csv                                          多次重试和拆分后仍失败的单元
  gee_unit_metrics.csv                                  全部批次合并后的总表（一行一个分析单元）
  core_polygons_2020.geojson                            全部中心建成区多边形（本地制图、矢量指标计算用）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (ChunkProgress, atomic_write_csv, atomic_write_json,  # noqa: E402
                    atomic_write_text, get_logger, load_config, resolve, retry)

try:
    import ee
except ImportError:  # 给不懂编程的使用者一个明确提示
    print("没有安装 earthengine-api。请先运行：pip install -r requirements.txt")
    raise

LOG = get_logger("01_gee_extract_rs")


# ===========================================================================
# 代码块 1：初始化 GEE
# 目的：用 config.yaml 中的 Cloud 项目 ID 连接 Earth Engine。
# 结果：成功则打印“GEE 初始化成功”；失败会提示先运行 ee.Authenticate()。
# ===========================================================================
def init_ee(project: str):
    try:
        ee.Initialize(project=project)
    except Exception as e:  # noqa: BLE001
        LOG.error("GEE 初始化失败。请先在终端运行：python -c \"import ee; ee.Authenticate(auth_mode='localhost')\" 完成浏览器登录，"
                  "并确认 config.yaml 中 gee.project 是你自己的 Cloud 项目 ID。原始错误：" + str(e)[:300])
        sys.exit(1)
    LOG.info(f"GEE 初始化成功（project = {project}）")


# ===========================================================================
# 代码块 2：数据集读取函数
# 目的：集中定义各数据集的读取方式（asset ID 与波段名已按 GEE 官方 STAC 目录核验，见 附录D）。
#       年份不在数据集覆盖范围内时返回 None，由调用处跳过该指标。
# 结果：返回 ee.Image 或 None。
# ===========================================================================
def year_image(coll_id: str, year: int) -> "ee.Image":
    return ee.Image(ee.ImageCollection(coll_id).filterDate(f"{year}-01-01", f"{year + 1}-01-01").first())


class DS:
    def __init__(self, cfg):
        self.c = cfg["gee"]["datasets"]

    def ghsl_s(self, y):  # 建成面积 m²/100 m 栅格，波段 built_surface、built_surface_nres
        return year_image(self.c["ghsl_built_s"], y)

    def ghsl_v(self, y):  # 建筑体量 m³/栅格，波段 built_volume_total、built_volume_nres
        return year_image(self.c["ghsl_built_v"], y)

    def ghsl_pop(self, y):  # 人口数/栅格，波段 population_count
        return year_image(self.c["ghsl_pop"], y).select("population_count")

    def worldpop(self, y):  # WorldPop 2000–2020，波段 population
        if y > 2020:
            return None
        col = ee.ImageCollection(self.c["worldpop"]).filter(ee.Filter.eq("country", "CHN"))
        return ee.Image(col.filter(ee.Filter.eq("year", y)).first()).select("population")

    def ntl(self, y):
        """夜间灯光：2013–2021 年用 VIIRS 年度 V21，2022 年起用 V22（均取 average_masked）；2012 年及以前用 CCNL（DMSP 校正，b1）。
        V22 在 STAC 中的说明年份与时间范围不一致，因此 2020 年固定用 V21。两种传感器不可直接比较。"""
        if 2013 <= y <= 2021:
            return year_image(self.c["viirs_annual_v21"], y).select("average_masked"), "viirs"
        if y >= 2022:
            return year_image(self.c["viirs_annual_v22"], y).select("average_masked"), "viirs"
        if y <= 2013:
            return year_image(self.c["ccnl"], y).select("b1"), "ccnl"
        return None, None

    def ghs_built_c(self):  # GHSL 2018 年 10 m 聚落内部特征：1–3 植被开放空间，4 水面，5 道路面，11–25 建筑
        return ee.ImageCollection(self.c["ghsl_built_c"]).first().select("built_characteristics").unmask(0)

    def water(self):  # JRC 全球地表水出现频率（%），未出现水体的像元为掩膜，置 0
        return ee.Image(self.c["surface_water"]).select("occurrence").unmask(0)

    def access(self):  # 到最近城市的出行时间（分钟，2015），作为区位控制
        return ee.Image(self.c["access_cities"]).select("accessibility")

    def worldcover(self):  # ESA WorldCover 2020 v100，波段 Map
        return ee.ImageCollection(self.c["worldcover"]).first().select("Map")

    def s2_ndvi(self, geom, year, months):
        def mask(img):
            scl = img.select("SCL")
            ok = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
            return img.updateMask(ok)
        col = (ee.ImageCollection(self.c["s2_sr"]).filterBounds(geom)
               .filter(ee.Filter.calendarRange(year, year, "year"))
               .filter(ee.Filter.calendarRange(months[0], months[1], "month"))
               .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 60))
               .map(mask))
        return col.median().normalizedDifference(["B8", "B4"]).rename("ndvi_s2")

    def dw_green(self, geom, year, months):
        col = (ee.ImageCollection(self.c["dynamic_world"]).filterBounds(geom)
               .filter(ee.Filter.calendarRange(year, year, "year"))
               .filter(ee.Filter.calendarRange(months[0], months[1], "month")))
        return col.select(["trees", "grass"]).mean().rename(["dw_trees", "dw_grass"])

    def modis_ndvi(self, year, months):
        col = (ee.ImageCollection(self.c["modis_ndvi"])
               .filter(ee.Filter.calendarRange(year, year, "year"))
               .filter(ee.Filter.calendarRange(months[0], months[1], "month")))
        return col.select("NDVI").mean().multiply(0.0001).rename("ndvi_modis")

    def terrain(self):
        dem = ee.Image(self.c["dem"]).select("elevation")
        return dem.rename("elev").addBands(ee.Terrain.slope(dem).rename("slope"))

    def climate(self, year):
        col = ee.ImageCollection(self.c["era5_land_monthly"]).filterDate(f"{year}-01-01", f"{year + 1}-01-01")
        t = col.select("temperature_2m").mean().subtract(273.15).rename("t2m_c")
        p = col.select("total_precipitation_sum").sum().multiply(1000).rename("prcp_mm")
        return t.addBands(p)


# ===========================================================================
# 代码块 3：数据集预检 (--preflight)
# 目的：正式运行前确认每个数据集在所选年份都能取到影像、波段名正确，避免跑了几小时才发现取不到数据。
# 结果：逐项打印 OK / 缺失；全部 OK 才建议继续。
# ===========================================================================
def preflight(cfg):
    ds = DS(cfg)
    years = cfg["gee"]["years"]
    checks = []
    for y in years:
        checks += [(f"GHSL BUILT_S {y}", ds.ghsl_s(y)), (f"GHSL BUILT_V {y}", ds.ghsl_v(y)),
                   (f"GHSL POP {y}", ds.ghsl_pop(y))]
        wp = ds.worldpop(y)
        if wp is not None:
            checks.append((f"WorldPop {y}", wp))
        img, src = ds.ntl(y)
        if img is not None:
            checks.append((f"夜间灯光 {src} {y}", img))
    checks += [("WorldCover 2020", ds.worldcover()), ("GHSL BUILT_C 2018", ds.ghs_built_c()),
               ("JRC 地表水", ds.water()), ("到城市出行时间", ds.access()), ("地形 DEM", ds.terrain()),
               (f"ERA5-Land {cfg['gee']['green_year']}", ds.climate(cfg["gee"]["green_year"]))]
    all_ok = True
    for name, img in checks:
        try:
            bands = img.bandNames().getInfo()
            LOG.info(f"OK   {name}: 波段 {bands}")
        except Exception as e:  # noqa: BLE001
            all_ok = False
            LOG.error(f"缺失 {name}: {str(e)[:200]}")
    LOG.info("预检全部通过，可以试跑。" if all_ok else "预检有缺失项，请把日志发给合作者或检查 config.yaml 的 datasets。")


# ===========================================================================
# 代码块 4：服务器端的中心建成区识别
# 目的：在每个分析单元内，把 GHSL 建成面积 ≥ 阈值的 100 m 栅格矢量化为连通斑块；
#       若提供驻地点，选“驻地点缓冲区内面积最大的斑块”，否则选最大斑块，作为县城/中心城区。
#       选中的斑块默认“填补内部孔洞”（config 中 core.fill_holes）：城区内部的公园、湖泊、广场、
#       大型运动场等建成比例低于阈值的栅格，矢量化后会成为多边形内部的“洞”；不填补的话，
#       这些公园绿地会被排除在中心建成区之外（公园代理、绿地指标系统性偏低），并被算进 5 km 环带本底。
#       单元内没有达到最小面积的斑块时，退化为单元几何中心 1 km 缓冲区并标记 core_method。
#       ee.Algorithms.If 在服务器端只计算被选中的分支，所以空集合时不会去取“空斑块”的几何。
# 结果：返回带 core 几何的 ee.Feature，属性 unit_id、core_method、core_area_m2。
# ===========================================================================
def fill_holes(geom):
    """只保留多边形（或多部件多边形每个部件）的外环，去掉内部孔洞；各部件合并为一个几何。"""
    parts = ee.Geometry(geom).geometries()
    shells = parts.map(lambda p: ee.Geometry.Polygon(ee.List(ee.Geometry(p).coordinates()).slice(0, 1)))
    return ee.Geometry.MultiPolygon(shells).dissolve(10)


def core_feature(unit: "ee.Feature", built_img: "ee.Image", ccfg: dict, seats: "ee.FeatureCollection | None"):
    geom = unit.geometry()
    bs = built_img.select("built_surface")      # 只取单个波段再取投影，避免多波段投影不一致时报错
    mask = bs.gte(ccfg["ghsl_threshold_m2"]).selfMask().rename("b").toInt()
    vec = mask.reduceToVectors(geometry=geom, scale=100, crs=bs.projection(),
                               geometryType="polygon", eightConnected=True,
                               labelProperty="b", maxPixels=int(1e10), bestEffort=False)
    vec = vec.map(lambda f: f.set("a", f.geometry().area(100)))
    cands = vec.filter(ee.Filter.gte("a", ccfg["min_patch_km2"] * 1e6))
    has = cands.size().gt(0)
    largest = ee.Feature(cands.sort("a", False).first())
    chosen = largest
    method = ee.String("largest_patch")
    if seats is not None:
        seat = seats.filter(ee.Filter.eq("unit_id", unit.get("unit_id")))
        near = cands.filterBounds(seat.geometry().buffer(ccfg["seat_buffer_m"]))
        # 没有驻地点的单元不去缓冲“空几何”：用 If 保证只有存在驻地点时才计算 near（And 会同时计算两侧）
        use_seat = ee.Number(ee.Algorithms.If(seat.size().gt(0), near.size(), 0)).gt(0)
        chosen = ee.Feature(ee.Algorithms.If(use_seat, near.sort("a", False).first(), largest))
        method = ee.String(ee.Algorithms.If(use_seat, "seat_patch", "largest_patch"))
    fallback = geom.centroid(100).buffer(1000)
    patch_geom = fill_holes(chosen.geometry()) if ccfg.get("fill_holes", True) else chosen.geometry()
    g = ee.Geometry(ee.Algorithms.If(has, patch_geom, fallback))
    return ee.Feature(g, {
        "unit_id": unit.get("unit_id"),
        "core_method": ee.Algorithms.If(has, method, "fallback_centroid_1km"),
        "core_area_m2": g.area(100),
    })


# ===========================================================================
# 代码块 5：分区统计的小工具
# 目的：reduceRegions 的输出字段名在单波段时是 'sum'/'mean'，多波段时是波段名；
#       这里统一给波段加前缀，并在单波段时强制命名，保证字段名稳定。
#       计数型栅格（人口、面积、体量、灯光）必须在“原生网格”上求和，否则重采样会改变总量，
#       所以 crs 取影像自身投影（ee.Projection，含原生像元大小与网格起点），scale 传 None：
#       GEE 规定 crs 与 scale 同时给出时会把网格“重缩放”到 scale，哪怕只差一点也会错位重采样
#       （例如 CCNL 原生约 927.7 m，若写 scale=1000 求和会少约 14%）。
# 结果：返回带新属性的 ee.FeatureCollection。
# ===========================================================================
def reduce_add(fc, img, names: list, kind: str, scale, prefix: str, crs=None, tile_scale=4):
    """names 为影像波段名（客户端已知），输出字段名 = prefix + 波段名；scale=None 且给出 crs 时按原生网格计算。"""
    out = [prefix + n for n in names]
    img = img.select(list(range(len(names))), out)
    red = ee.Reducer.sum() if kind == "sum" else ee.Reducer.mean()
    if len(names) == 1:
        red = red.setOutputs(out)
    kw = dict(collection=fc, reducer=red, tileScale=tile_scale)
    if scale is not None:
        kw["scale"] = scale
    if crs is not None:
        kw["crs"] = crs
    return img.reduceRegions(**kw)


def area_by_class(wc: "ee.Image", classes: dict) -> tuple:
    """把 WorldCover 转成“各地类面积（m²）”多波段影像，波段名 wc_<英文简称>_m2。"""
    pa = ee.Image.pixelArea()
    names = [f"wc_{k}_m2" for k in classes]
    bands = [pa.updateMask(wc.eq(int(v))).rename(n) for n, v in zip(names, classes.values())]
    return ee.Image.cat(*bands), names


# ===========================================================================
# 代码块 6：单个 chunk 的全部计算
# 目的：对一批分析单元，依次计算中心建成区、单元级指标、中心建成区指标和环带指标，
#       一次 getInfo 取回（减少请求次数）。
# 结果：返回 (unit_rows: list[dict], core_geojson: dict)。
# ===========================================================================
def run_chunk(units: "ee.FeatureCollection", cfg: dict, seats) -> tuple[list, dict]:
    g = cfg["gee"]
    ds = DS(cfg)
    years = g["years"]
    gy = g["green_year"]
    months = g["green_months"]
    ts = g.get("tile_scale", 4)

    # 5a. 中心建成区：以 green_year（2020）的 GHSL 建成面积识别，并固定这一边界比较各年份
    built_ref = ds.ghsl_s(gy)
    cores = units.map(lambda u: core_feature(u, built_ref, g["core"], seats))
    # 其他普查年份的“动态”中心建成区面积（同一规则、当年 GHSL），用于衡量建成区蔓延
    for y in years:
        if y == gy:
            continue
        by = ds.ghsl_s(y)
        dyn = units.map(lambda u, by=by: core_feature(u, by, g["core"], seats))
        d = ee.Dictionary.fromLists(dyn.aggregate_array("unit_id"), dyn.aggregate_array("core_area_m2"))
        cores = cores.map(lambda f, y=y, d=d: f.set(f"core{y}_area_m2", d.get(f.get("unit_id"))))

    # 5b. 单元级与中心建成区级：GHSL 面积、体量、人口（原生 100 m 网格求和），WorldPop，夜间灯光
    u_fc, c_fc = units, cores
    for y in years:
        stack = (ds.ghsl_s(y).select(["built_surface", "built_surface_nres"])
                 .addBands(ds.ghsl_v(y).select(["built_volume_total", "built_volume_nres"]))
                 .addBands(ds.ghsl_pop(y)))
        names = [f"bs_{y}", f"bsn_{y}", f"bv_{y}", f"bvn_{y}", f"pop_ghs_{y}"]
        proj = ds.ghsl_s(y).select("built_surface").projection()
        u_fc = reduce_add(u_fc, stack, names, "sum", 100, "u_", crs=proj, tile_scale=ts)
        c_fc = reduce_add(c_fc, stack, names, "sum", 100, "c_", crs=proj, tile_scale=ts)
        wp = ds.worldpop(y)
        if wp is not None:
            wproj = wp.projection()
            u_fc = reduce_add(u_fc, wp, [f"pop_wp_{y}"], "sum", 92.77, "u_", crs=wproj, tile_scale=ts)
            c_fc = reduce_add(c_fc, wp, [f"pop_wp_{y}"], "sum", 92.77, "c_", crs=wproj, tile_scale=ts)
        nimg, src = ds.ntl(y)
        if nimg is not None:
            sc = 463.83 if src == "viirs" else 1000
            nproj = nimg.projection()
            u_fc = reduce_add(u_fc, nimg, [f"ntl_{src}_{y}"], "sum", sc, "u_", crs=nproj, tile_scale=ts)
            c_fc = reduce_add(c_fc, nimg, [f"ntl_{src}_{y}"], "sum", sc, "c_", crs=nproj, tile_scale=ts)

    # 5c. 中心建成区内的绿地（10 m WorldCover 各地类面积；Sentinel-2 NDVI；Dynamic World 树木/草地概率）
    wc_img, wc_names = area_by_class(ds.worldcover(), g["worldcover_classes"])
    c_fc = reduce_add(c_fc, wc_img, wc_names, "sum", 10, "c_", tile_scale=ts)
    bounds = units.geometry().bounds()

    # 5c'. 人口加权绿地暴露（population-weighted greenspace exposure，Chen et al. 2022 Nature Communications）：
    #      先把 10 m 的树木、绿地（树木+灌木+草地）二值图聚合为 100 m 覆盖比例，再取半径 r 的圆形邻域均值，
    #      得到“每个 100 m 人口格网周围 r 米内的绿地比例”，乘以格网人口后在中心建成区内求和；
    #      03 脚本中除以人口总和即为暴露度。邻域可越出中心建成区边界，符合居民实际可达范围。
    gproj = ds.ghsl_s(gy).select("built_surface").projection()
    wc = ds.worldcover()
    frac = (ee.Image.cat(wc.eq(10), wc.eq(10).Or(wc.eq(20)).Or(wc.eq(30)))
            .rename(["tree", "green"])
            .reduceResolution(ee.Reducer.mean(), maxPixels=1024).reproject(gproj))
    rad = g["exposure_radius_m"]
    expo = frac.focalMean(radius=rad, kernelType="circle", units="meters").reproject(gproj)
    pop_g = ds.ghsl_pop(gy)
    pw = expo.multiply(pop_g).addBands(pop_g)
    c_fc = reduce_add(c_fc, pw, [f"pw_tree_{gy}", f"pw_green_{gy}", f"pop_expo_{gy}"], "sum", 100, "c_",
                      crs=gproj, tile_scale=ts)

    # 5c''. 公园与绿道的遥感代理（均为代理，报告中需注明；附录D 说明依据）
    #      公园代理：中心建成区内面积 ≥ green_patch_min_m2（默认 1 公顷）的连片绿地斑块；
    #      公园可达：斑块 park_access_distance_m 范围内的人口；
    #      绿道代理：水体（JRC 出现频率 ≥ 50%）外扩 riparian_buffer_m 内的绿地（滨水绿带），
    #               GHSL 2018 道路面外扩 road_buffer_m 内的绿地（道路两侧绿带）；
    #      另记 GHSL 2018 聚落内植被开放空间（1–3 类）与道路面（5 类）面积。
    if g.get("use_green_proxies", True):
        green10 = wc.eq(10).Or(wc.eq(20)).Or(wc.eq(30))
        minpix = max(int(g["green_patch_min_m2"] / 100), 2)          # 10 m 像元面积约 100 m²
        cnt = green10.selfMask().connectedPixelCount(maxSize=min(minpix, 1024), eightConnected=True)
        patch = cnt.gte(minpix).unmask(0).And(green10)
        water = ds.water().gte(50)
        riparian = green10.And(water.focalMax(radius=g["riparian_buffer_m"], units="meters")).And(water.Not())
        bc = ds.ghs_built_c()
        road = bc.eq(5)
        roadside = green10.And(road.focalMax(radius=g["road_buffer_m"], units="meters"))
        openveg = bc.gte(1).And(bc.lte(3))
        pa = ee.Image.pixelArea()
        prox = ee.Image.cat(pa.updateMask(patch), pa.updateMask(riparian), pa.updateMask(roadside),
                            pa.updateMask(openveg), pa.updateMask(road))
        c_fc = reduce_add(c_fc, prox, [f"greenpatch_m2_{gy}", f"riparian_green_m2_{gy}", f"roadside_green_m2_{gy}",
                                       "openveg_m2_2018", "road_m2_2018"], "sum", 10, "c_", tile_scale=ts)
        dist = g["park_access_distance_m"]
        patch100 = patch.reduceResolution(ee.Reducer.max(), maxPixels=1024).reproject(gproj)
        near = patch100.focalMax(radius=dist, units="meters").reproject(gproj)
        c_fc = reduce_add(c_fc, pop_g.updateMask(near), [f"pop_greenpatch{dist}_{gy}"], "sum", 100, "c_",
                          crs=gproj, tile_scale=ts)

    if g.get("use_s2_ndvi", True):
        c_fc = reduce_add(c_fc, ds.s2_ndvi(bounds, gy, months), [f"ndvi_s2_{gy}"],
                          "mean", g.get("s2_scale", 20), "c_", tile_scale=ts)
    if g.get("use_dynamic_world", True):
        c_fc = reduce_add(c_fc, ds.dw_green(bounds, gy, months), [f"dw_trees_{gy}", f"dw_grass_{gy}"],
                          "mean", g.get("dw_scale", 20), "c_", tile_scale=ts)

    # 5d. 可选：公园面积与公园步行可达人口（需要在 config 中提供公园多边形 asset）
    if g.get("park_asset"):
        parks = ee.FeatureCollection(g["park_asset"]).filterBounds(bounds)
        park_img = ee.Image.pixelArea().updateMask(ee.Image(0).byte().paint(parks, 1))
        c_fc = reduce_add(c_fc, park_img, [f"park_m2_{gy}"], "sum", 10, "c_", tile_scale=ts)
        dist = g["park_access_distance_m"]
        near = ee.Image(0).byte().paint(parks.map(lambda f: f.buffer(dist)), 1)
        pop_near = ds.ghsl_pop(gy).updateMask(near)
        c_fc = reduce_add(c_fc, pop_near, [f"pop_park{dist}_{gy}"], "sum", 100, "c_",
                          crs=ds.ghsl_s(gy).select("built_surface").projection(), tile_scale=ts)

    # 5e. 地形（单元与中心建成区）与气候（单元）
    u_fc = reduce_add(u_fc, ds.terrain(), ["elev", "slope"], "mean", 500, "u_", tile_scale=ts)
    c_fc = reduce_add(c_fc, ds.terrain(), ["elev", "slope"], "mean", 90, "c_", tile_scale=ts)
    u_fc = reduce_add(u_fc, ds.climate(gy), [f"t2m_c_{gy}", f"prcp_mm_{gy}"], "mean", 11132, "u_", tile_scale=ts)
    u_fc = reduce_add(u_fc, ds.access(), ["access_min"], "mean", 1000, "u_", tile_scale=ts)

    # 5f. 自然植被本底：中心建成区外 5 km 环带（剔除建成栅格）的 MODIS NDVI 均值
    rb = g["ring_buffer_m"]
    rings = cores.map(lambda f: ee.Feature(
        f.geometry().buffer(rb, 100).difference(f.geometry(), 100), {"unit_id": f.get("unit_id")}))
    nonbuilt = ds.ghsl_s(gy).select("built_surface").lt(g["core"]["ghsl_threshold_m2"] / 4)
    ndvi_bg = ds.modis_ndvi(gy, months).updateMask(nonbuilt)
    r_fc = reduce_add(rings, ndvi_bg, [f"ndvi_modis_{gy}"], "mean", 250, "r_", tile_scale=ts)

    # 5g. 一次性取回结果（单元级、环带级不取几何；中心建成区取简化几何以便本地制图）
    u_tab = u_fc.select([".*"], None, False)
    r_tab = r_fc.select([".*"], None, False)
    c_geo = c_fc.map(lambda f: f.setGeometry(f.geometry().transform("EPSG:4326", 10).simplify(30)))
    res = ee.Dictionary({"u": u_tab, "c": c_geo, "r": r_tab}).getInfo()
    return merge_rows(res), res["c"]


def merge_rows(res: dict) -> list:
    """把 u、c、r 三组结果按 unit_id 合并成一行一个单元的字典列表。"""
    rows = {}
    for key in ("u", "c", "r"):
        for feat in res[key]["features"]:
            p = feat["properties"]
            uid = p["unit_id"]
            row = rows.setdefault(uid, {"unit_id": uid})
            for k, v in p.items():
                if k in ("unit_id", "unit_type", "prov_code", "pref_code") and k in row:
                    continue
                if key == "c" and not k.startswith("c_") and k not in ("unit_id", "core_method", "core_area_m2") \
                        and not k.startswith("core"):
                    continue
                row[k] = v
    return list(rows.values())


# ===========================================================================
# 代码块 7：断点续跑 + 自动拆分
# 目的：某批失败时先重试（指数退避）；仍失败就拆成两半分别计算，直到单个单元；
#       单个单元仍失败则记入 failures.csv 并继续下一批，不让一个“坏单元”卡住全国任务。
# 结果：成功的部分写入 chunks/；失败单元写入 failures.csv。
# ===========================================================================
def run_with_split(ids, make_fc, cfg, seats, tag, out_dir, failures):
    unit_csv = out_dir / f"{tag}_unit.csv"
    core_geo = out_dir / f"{tag}_core.geojson"
    if unit_csv.exists() and core_geo.exists():
        return len(ids)
    g = cfg["gee"]
    tries = g["max_retries"] if len(ids) > 1 else g["max_retries"] + 1
    try:
        rows, core = retry(lambda: run_chunk(make_fc(ids), cfg, seats), tries=tries,
                           base_delay=g["retry_base_delay_s"], logger=LOG, what=tag)
        atomic_write_text(core_geo, json.dumps(core, ensure_ascii=False))
        atomic_write_csv(pd.DataFrame(rows), unit_csv)
        return len(ids)
    except KeyboardInterrupt:
        raise
    except Exception as e:  # noqa: BLE001
        if len(ids) == 1:
            LOG.error(f"单元 {ids[0]} 多次失败，记入 failures.csv：{str(e)[:200]}")
            failures.append({"unit_id": ids[0], "error": str(e)[:500]})
            return 0
        mid = len(ids) // 2
        LOG.warning(f"{tag} 失败，拆分为 {mid} + {len(ids) - mid} 个单元重试")
        a = run_with_split(ids[:mid], make_fc, cfg, seats, tag + "a", out_dir, failures)
        b = run_with_split(ids[mid:], make_fc, cfg, seats, tag + "b", out_dir, failures)
        return a + b


# ===========================================================================
# 代码块 8：合并全部批次
# 目的：把 chunks/ 下所有 *_unit.csv 与 *_core.geojson 合并为总表与总图层。
# 结果：gee_unit_metrics.csv、core_polygons_2020.geojson。
# ===========================================================================
def merge_all(out_dir: Path):
    ch = out_dir / "chunks"
    csvs = sorted(ch.glob("*_unit.csv"))
    if not csvs:
        LOG.warning("还没有任何已完成的批次。")
        return
    df = pd.concat([pd.read_csv(p, dtype={"unit_id": str}, encoding="utf-8-sig") for p in csvs], ignore_index=True)
    df = df.drop_duplicates("unit_id", keep="last").sort_values("unit_id")
    atomic_write_csv(df, out_dir / "gee_unit_metrics.csv")
    feats = []
    for p in sorted(ch.glob("*_core.geojson")):
        feats += json.loads(p.read_text(encoding="utf-8"))["features"]
    atomic_write_text(out_dir / "core_polygons_2020.geojson",
                      json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
    LOG.info(f"已合并 {len(csvs)} 个批次文件，共 {len(df)} 个单元 → gee_unit_metrics.csv")


# ===========================================================================
# 代码块 9：主流程
# 目的：读取分析单元 → 生成或读取分批方案 → 逐批计算（跳过已完成）→ 汇报进度 → 合并。
# 结果：见文件开头“输出”说明。
# ===========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true", help="只检查 GEE 登录与数据集")
    ap.add_argument("--province", default=None, help="只跑某省（两位代码，如 44）")
    ap.add_argument("--limit", type=int, default=None, help="只跑前 N 个单元（试跑用）")
    ap.add_argument("--merge-only", action="store_true", help="只合并已有批次")
    args = ap.parse_args()

    cfg = load_config()
    g = cfg["gee"]
    out_dir = resolve(g["out_dir"])
    (out_dir / "chunks").mkdir(parents=True, exist_ok=True)
    if args.merge_only:
        merge_all(out_dir)
        return
    init_ee(g["project"])
    if args.preflight:
        preflight(cfg)
        return

    units_path = resolve(cfg["units"]["out_dir"]) / "units_for_gee.geojson"
    if not units_path.exists():
        LOG.error("找不到 units_for_gee.geojson，请先运行 00_prepare_units.py")
        sys.exit(1)
    gj = json.loads(units_path.read_text(encoding="utf-8"))
    feats = sorted(gj["features"], key=lambda f: f["properties"]["unit_id"])
    if args.province:
        feats = [f for f in feats if f["properties"]["prov_code"].startswith(args.province)]
    if args.limit:
        feats = feats[: args.limit]

    # 分批方案：全国正式运行时写入 manifest，续跑时沿用同一分批，保证“已完成批次”的判断有效
    tag_prefix = "chunk" if not (args.province or args.limit) else f"test_{args.province or 'all'}_{args.limit or 'all'}"
    manifest_path = out_dir / f"{tag_prefix}_manifest.json"
    size = int(g["chunk_size"])
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        ids = [f["properties"]["unit_id"] for f in feats]
        manifest = {"chunk_size": size, "chunks": [ids[i:i + size] for i in range(0, len(ids), size)]}
        atomic_write_json(manifest, manifest_path)
    by_id = {f["properties"]["unit_id"]: f for f in feats}

    # 单元几何来源：local = 每批从本地 GeoJSON 发送（默认，免上传）；asset = 读取已上传的 GEE 表格资产（更稳，推荐全国运行）
    if g.get("units_source", "local") == "asset":
        units_asset = ee.FeatureCollection(g["units_asset"])

        def make_fc(ids):
            return units_asset.filter(ee.Filter.inList("unit_id", ids))
    else:
        def make_fc(ids):
            return ee.FeatureCollection([ee.Feature(by_id[u]) for u in ids if u in by_id])

    seats = None
    seat_path = resolve(cfg["units"]["out_dir"]) / "seats.geojson"
    if seat_path.exists():
        seats = ee.FeatureCollection(json.loads(seat_path.read_text(encoding="utf-8")))

    chunks = manifest["chunks"]
    prog = ChunkProgress(len(chunks), LOG)
    failures = []
    for i, ids in enumerate(chunks):
        tag = f"{tag_prefix}_{i:04d}"
        if (out_dir / "chunks" / f"{tag}_unit.csv").exists():
            prog.skip(i)
            continue
        ids = [u for u in ids if u in by_id]
        prog.start(i, f"{len(ids)} 个单元（{ids[0]} … {ids[-1]}）")
        n = run_with_split(ids, make_fc, cfg, seats, tag, out_dir / "chunks", failures)
        prog.finish(i, n)
    prog.summary()
    if failures:
        fpath = out_dir / "failures.csv"
        old = pd.read_csv(fpath, dtype=str, encoding="utf-8-sig") if fpath.exists() else pd.DataFrame()
        atomic_write_csv(pd.concat([old, pd.DataFrame(failures)]).drop_duplicates("unit_id", keep="last"), fpath)
        LOG.warning(f"{len(failures)} 个单元失败，见 failures.csv。可在 config 中调小 chunk_size 或增大 tile_scale 后重跑。")
    merge_all(out_dir)


if __name__ == "__main__":
    main()
