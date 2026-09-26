# -*- coding: utf-8 -*-
"""
01_gee_extract_rs.py  用 Google Earth Engine 批量提取每个分析单元的遥感指标（断点续跑 + 按 chunk 汇报进度）

在哪里运行：Mac “终端 Terminal”
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
  主流程：
    python 01_gee_extract_rs.py --preflight               # 第一步：只检查 GEE 登录与数据集是否可用（约 1 至 2 分钟），逐项打印 OK / 缺失
    python 01_gee_extract_rs.py --province 44 --limit 20  # 第二步：试跑广东前 20 个单元，结果在 chunks/test_*，检查是否合理
    python 01_gee_extract_rs.py                           # 第三步：全国正式运行（可随时 Ctrl+C 中断，重新运行会自动续跑），得到 gee_unit_metrics.csv
    python 01_gee_extract_rs.py --merge-only              # 可选：只把已完成的各批结果合并成总表，不连接 GEE
  超时单元改用批处理导出（交互请求约 5 分钟超时，特大单元拆到单个仍可能失败）：
    python 01_gee_extract_rs.py --export-failed           # 把 failures.csv 中的单元逐个提交为 GEE 批处理任务，导出到 Google Drive，
                                                          # 终端打印任务 ID 并定时汇报状态；中断后重新运行只继续查询，不重复提交
    python 01_gee_extract_rs.py --merge-exports ~/Downloads/fdt_gee_exports
                                                          # 从 Drive 下载全部 GeoJSON 到该文件夹后运行：转成 chunks/export_* 并重新合并总表
  年度结果变量（准实验用，须先完成第三步，沿用其 2020 年中心建成区）：
    python 01_gee_extract_rs.py --annual                  # 逐年提取 GAIA 不透水面、VIIRS 夜光、Dynamic World 绿度，得到 annual/annual_long.csv
    python 01_gee_extract_rs.py --annual --merge-only     # 只合并年度模式已完成的批次
  准实验单元层（每个 2020 年县级行政区一个单元，须 00 已输出 units_did_*）：
    python 01_gee_extract_rs.py --units did               # 对不合并市辖区的县级单元重复第三步，结果写到 数据/中间/gee/did/
    python 01_gee_extract_rs.py --units did --annual      # 同上，年度模式，结果写到 数据/中间/gee/did/annual/
  --units did 可与以上任一模式组合；--province、--limit 可与第三步或 --annual 组合试跑。

前置条件：已完成 00_prepare_units.py；已按 代码/README.md 完成 GEE 注册、Cloud 项目创建和 ee.Authenticate()。

每个分析单元提取三组指标（指标定义见研究设计报告第 7 节与附录C，遥感方法见第 8 节）：
  u_*  整个单元（县域 / 市辖区合计）：GHSL 建成面积、建筑体量、GHS-POP 与 WorldPop 人口、夜间灯光、
       GAIA 不透水面、GHS-SMOD 城市中心与城镇簇面积、地形、气候、到城市出行时间
  c_*  中心建成区（县城 / 中心城区）：GHSL 建成栅格先做形态学闭运算（连接被河流、道路隔开的斑块），
       再取最大连通斑块或含驻地点的斑块，默认填补内部孔洞（城区内的公园、湖泊等），固定为 2020 年边界。
       指标同上各项，另有 ESA WorldCover 2020 各地类面积、存量与新增树木、人口加权绿地暴露、
       大型绿斑与线性绿地、Sentinel-2 NDVI、Dynamic World 树木/草地概率；
       可选：CLCD 历年地类、公园、绿道、学校/医院/养老机构点位（须在 config 中提供资产）
  r_*  中心建成区外 5 km 环带：MODIS NDVI，作为自然植被本底控制变量（干旱区县城绿地少不等于财政投入少）

输出（数据/中间/gee/；--units did 时为 数据/中间/gee/did/）：
  chunks/chunk_XXXX_unit.csv、chunk_XXXX_core.geojson   每批结果（存在即视为完成，续跑时跳过）
  chunks/export_<单元>_unit.csv、_core.geojson          批处理导出的结果（--merge-exports 生成）
  chunk_manifest.json                                   分批方案（首次运行生成，保证续跑时分批不变）
  failures.csv                                          多次重试和拆分后仍失败的单元
  export_tasks.json                                     已提交的导出任务（任务 ID 与状态）
  gee_unit_metrics.csv                                  全部批次合并后的总表（一行一个分析单元）
  core_polygons_2020.geojson                            全部中心建成区多边形（本地制图、矢量指标计算用）
  annual/chunks/…、annual/failures.csv                  年度模式的分批结果与失败清单
  annual/annual_long.csv                                年度模式总表（一行一个单元年份）
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (ChunkProgress, atomic_write_csv, atomic_write_json,  # noqa: E402
                    atomic_write_text, get_logger, load_config, read_table, resolve, retry)

try:
    import ee
except ImportError:  # 给不懂编程的使用者一个明确提示
    print("没有安装 earthengine-api。请先运行：pip install -r requirements.txt")
    raise

LOG = get_logger("01_gee_extract_rs")

TREE_CODES = (10, 95)            # WorldCover 树木（10）与红树林（95）都记为树木
GREEN_CODES = (10, 95, 20, 30)   # 绿地 = 树木 + 红树林 + 灌木 + 草地
EXPORT_POLL_S = 60               # --export-failed 查询任务状态的间隔（秒）


# ===========================================================================
# 代码块 1：初始化 GEE
# 目的：用 config.yaml 中的 Cloud 项目 ID 连接 Earth Engine；并给每个请求设等待上限
#       （earthengine-api 默认不限时：网络/VPN 断开时 getInfo 可能一直卡住，既不报错也不重试）。
#       GEE 交互计算本身约 5 分钟超时，默认上限 600 秒不会误伤正常计算；超时后按失败处理，自动重试或拆分。
# 结果：成功则打印“GEE 初始化成功”；失败会提示先运行 ee.Authenticate()。
# ===========================================================================
def init_ee(project: str, timeout_s: float = 600):
    try:
        ee.Initialize(project=project)
        ee.data.setDeadline(int(timeout_s * 1000))
    except Exception as e:  # noqa: BLE001
        LOG.error("GEE 初始化失败。请先在终端运行：python -c \"import ee; ee.Authenticate(auth_mode='localhost')\" 完成浏览器登录，"
                  "并确认 config.yaml 中 gee.project 是你自己的 Cloud 项目 ID。原始错误：" + str(e)[:300])
        sys.exit(1)
    LOG.info(f"GEE 初始化成功（project = {project}；单次请求最长等待 {timeout_s:.0f} 秒）")


# ===========================================================================
# 代码块 2：数据集读取函数
# 目的：集中定义各数据集的读取方式（asset ID 与波段名已按 GEE 官方 STAC 目录核验，见 附录D）。
#       年份不在数据集覆盖范围内时返回 None，由调用处跳过该指标。
# 结果：返回 ee.Image 或 None。
# ===========================================================================
def year_image(coll_id: str, year: int) -> "ee.Image":
    return ee.Image(ee.ImageCollection(coll_id).filterDate(f"{year}-01-01", f"{year + 1}-01-01").first())


def wc_mask(wc: "ee.Image", codes) -> "ee.Image":
    """WorldCover 中属于 codes 任一代码的像元为 1。"""
    m = wc.eq(codes[0])
    for v in codes[1:]:
        m = m.Or(wc.eq(v))
    return m


class DS:
    def __init__(self, cfg):
        self.g = cfg["gee"]
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

    def water_proj(self):  # JRC 地表水原生网格（约 30 m 经纬度网格）
        return ee.Image(self.c["surface_water"]).select("occurrence").projection()

    def ndvi_water(self):
        """NDVI 均值要剔除的水面：JRC 出现频率 ≥ 50% 或 WorldCover 水体（80）。
        WorldCover 无数据处（外海）结果为掩膜，同样被剔除。"""
        return self.water().gte(50).Or(self.worldcover().eq(80))

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

    def slope(self):
        """坡度（度）：在 NASADEM 原生 30 m 网格上计算（reproject 固定计算网格）。
        不固定网格时，坡度按请求尺度计算，500 m 尺度下山区坡度被严重低估。"""
        dem = ee.Image(self.c["dem"]).select("elevation")
        return ee.Terrain.slope(dem).reproject(dem.projection()).rename("slope")

    def terrain(self):  # 高程 + 原生网格坡度；调用处再按统计尺度取均值
        dem = ee.Image(self.c["dem"]).select("elevation")
        return dem.rename("elev").addBands(self.slope())

    def climate(self, year):
        col = ee.ImageCollection(self.c["era5_land_monthly"]).filterDate(f"{year}-01-01", f"{year + 1}-01-01")
        t = col.select("temperature_2m").mean().subtract(273.15).rename("t2m_c")
        p = col.select("total_precipitation_sum").sum().multiply(1000).rename("prcp_mm")
        return t.addBands(p)

    def gaia_imp(self, y):
        """GAIA 不透水面（30 m，单幅影像）。波段 change_year_index 的值 v 表示像元在 2019 − v 年转为不透水面
        （34 = 1985 年，1 = 2018 年）。到 Y 年为止已是不透水面 ⇔ v ≥ 2019 − Y。
        STAC 说明写“1990 年的不透水面为值大于 29”，会漏掉 1990 年当年转化的像元（值 29），这里按查找表本身取 ≥。
        从未转为不透水面的像元先置 0。只覆盖 1985–2018 年，其余年份返回 None。"""
        if not 1985 <= int(y) <= 2018:
            return None
        return ee.Image(self.c["gaia"]).select("change_year_index").unmask(0).gte(2019 - int(y))

    def gaia_proj(self):
        return ee.Image(self.c["gaia"]).select("change_year_index").projection()

    def treecover2000(self):  # Hansen GFC v1.13：2000 年树冠覆盖度（%，0–100），无数据置 0
        return ee.Image(self.c["hansen_gfc"]).select("treecover2000").unmask(0)

    def smod(self, y):  # GHS-SMOD 城镇化程度（1 km Mollweide，5 年一期），波段 smod_code；按年份取当期影像
        return year_image(self.c["ghsl_smod"], y).select("smod_code")

    def clcd(self, y):
        """CLCD 30 m 年度地类（可选）。模板含 {year} 时按单幅影像读取；不含时视为 ImageCollection，按年份取当年影像。"""
        tpl = self.g.get("clcd_asset_template")
        if not tpl:
            return None
        band = self.g.get("clcd_band", "b1")
        if "{year}" in tpl:
            return ee.Image(tpl.format(year=y)).select(band)
        return year_image(tpl, y).select(band)


# ===========================================================================
# 代码块 3：数据集预检 (--preflight)
# 目的：正式运行前确认每个数据集在所选年份都能取到影像、波段名正确，避免跑了几小时才发现取不到数据。
#       覆盖全部用到的数据：逐年数据集、单期数据集（含 GAIA、Hansen、GHS-SMOD 2020 年一期、可选的 CLCD）、
#       逐景数据集（Sentinel-2、Dynamic World、MODIS，以广州一点检查生长季是否有影像）、
#       年度模式用到的 VIIRS 与 Dynamic World 各年份、按“集合第一幅”读取的单期集合是否真的只有一幅，
#       以及 config 中启用的 GEE 资产（units_asset、park_asset、river_asset、greenway_asset、poi_assets）。
# 结果：逐项打印 OK / 缺失；全部 OK 才建议继续。
# ===========================================================================
def annual_years(g: dict, key: str, lo: int, hi: int) -> list:
    """年度模式某类数据的年份（config 给起止年，含两端），只保留数据集覆盖的年份。"""
    v = (g.get("annual") or {}).get(key)
    if not v:
        return []
    y0, y1 = int(v[0]), int(v[-1])
    ys = [y for y in range(y0, y1 + 1) if lo <= y <= hi]
    out = [y for y in range(y0, y1 + 1) if y not in ys]
    if out:
        LOG.warning(f"annual.{key} 中 {out} 超出数据集覆盖范围（{lo}–{hi}），已跳过")
    return ys


def preflight(cfg):
    ds = DS(cfg)
    g = cfg["gee"]
    c = g["datasets"]
    years = g["years"]
    gy, months = g["green_year"], g["green_months"]
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
               (f"ERA5-Land {gy}", ds.climate(gy))]
    if c.get("gaia"):
        checks.append(("GAIA 不透水面", ee.Image(c["gaia"]).select("change_year_index")))
    if c.get("hansen_gfc"):
        checks.append(("Hansen GFC treecover2000", ee.Image(c["hansen_gfc"]).select("treecover2000")))
    if g.get("use_smod", True) and c.get("ghsl_smod"):
        checks.append((f"GHS-SMOD {gy}", ds.smod(gy)))
    if g.get("clcd_asset_template"):
        for y in sorted(set(g.get("clcd_years", [])) | {g.get("clcd_baseline_year", 2000)}):
            checks.append((f"CLCD {y}", ds.clcd(y)))
    # 年度模式用到的逐年夜光
    for y in annual_years(g, "viirs_years", 2013, 2100):
        checks.append((f"年度模式 VIIRS {y}", ds.ntl(y)[0]))
    pt = ee.Geometry.Point([113.26, 23.13])   # 广州：检查逐景数据集在指定年份的生长季是否有影像

    def first_scene(cid, bands, year):
        col = (ee.ImageCollection(cid).filterBounds(pt).filter(ee.Filter.calendarRange(year, year, "year"))
               .filter(ee.Filter.calendarRange(months[0], months[1], "month")))
        return ee.Image(col.first()).select(bands)
    if g.get("use_s2_ndvi", True):
        checks.append((f"Sentinel-2 SR {gy}", first_scene(c["s2_sr"], ["B4", "B8", "SCL"], gy)))
    if g.get("use_dynamic_world", True):
        checks.append((f"Dynamic World {gy}", first_scene(c["dynamic_world"], ["trees", "grass"], gy)))
    checks.append((f"MODIS NDVI {gy}", first_scene(c["modis_ndvi"], ["NDVI"], gy)))
    for y in annual_years(g, "dw_years", 2015, 2100):
        checks.append((f"年度模式 Dynamic World {y}", first_scene(c["dynamic_world"], ["trees", "grass"], y)))
    all_ok = True
    for name, img in checks:
        try:
            bands = img.bandNames().getInfo()
            if not bands:
                raise ValueError("影像没有任何波段（该年份/月份可能没有影像）")
            LOG.info(f"OK   {name}: 波段 {bands}")
        except Exception as e:  # noqa: BLE001
            all_ok = False
            LOG.error(f"缺失 {name}: {str(e)[:200]}")
    # 代码以“集合第一幅影像”读取 WorldCover 与 GHSL BUILT_C，集合若被拆成多幅分块，只会取到其中一块
    for name, cid in (("WorldCover 集合影像数", c["worldcover"]), ("GHSL BUILT_C 集合影像数", c["ghsl_built_c"])):
        try:
            n = ee.ImageCollection(cid).size().getInfo()
            if n != 1:
                all_ok = False
                LOG.error(f"异常 {name} = {n}（应为 1 幅全球影像）：请把 DS 中对应的 .first() 改为 .mosaic()")
            else:
                LOG.info(f"OK   {name} = 1")
        except Exception as e:  # noqa: BLE001
            all_ok = False
            LOG.error(f"缺失 {name}: {str(e)[:200]}")
    # GHS-SMOD 按年份取当期影像：该年份应恰好有 1 幅全球影像
    if g.get("use_smod", True) and c.get("ghsl_smod"):
        try:
            col = ee.ImageCollection(c["ghsl_smod"]).filterDate(f"{gy}-01-01", f"{gy + 1}-01-01")
            info = ee.Dictionary({"n": col.size(), "ids": col.aggregate_array("system:index")}).getInfo()
            if info["n"] != 1:
                all_ok = False
                LOG.error(f"异常 GHS-SMOD {gy} 年影像数 = {info['n']}（应为 1）：system:index {info['ids']}")
            else:
                LOG.info(f"OK   GHS-SMOD {gy} 年影像数 = 1（system:index {info['ids'][0]}）")
        except Exception as e:  # noqa: BLE001
            all_ok = False
            LOG.error(f"缺失 GHS-SMOD {gy}: {str(e)[:200]}")
    # config 中启用的 GEE 资产
    assets = []
    if g.get("units_source", "local") == "asset":
        assets.append(("分析单元资产 units_asset", g["units_asset"], True))
        if g.get("units_did_asset"):
            assets.append(("准实验单元资产 units_did_asset", g["units_did_asset"], True))
    if g.get("park_asset"):
        assets.append(("公园多边形资产 park_asset", g["park_asset"], False))
    if g.get("river_asset"):
        assets.append(("河道资产 river_asset", g["river_asset"], False))
    if g.get("greenway_asset"):
        assets.append(("绿道线资产 greenway_asset", g["greenway_asset"], False))
    for key, aid in (g.get("poi_assets") or {}).items():
        if aid:
            assets.append((f"设施点位资产 poi_assets.{key}", aid, False))
    for name, aid, need_uid in assets:
        try:
            fc = ee.FeatureCollection(aid)
            first = ee.Feature(fc.first())
            info = ee.Dictionary({"n": fc.size(), "props": first.propertyNames(),
                                  "geom": first.geometry().type()}).getInfo()
            if need_uid and "unit_id" not in info["props"]:
                raise ValueError(f"资产中没有 unit_id 字段（现有字段：{info['props']}）")
            LOG.info(f"OK   {name}: {info['n']} 个要素，几何类型 {info['geom']}")
        except Exception as e:  # noqa: BLE001
            all_ok = False
            LOG.error(f"缺失 {name}（{aid}）: {str(e)[:200]}")
    LOG.info("预检全部通过，可以试跑。" if all_ok else "预检有缺失项，请把日志发给合作者或检查 config.yaml 的 datasets。")


# ===========================================================================
# 代码块 4：服务器端的中心建成区识别
# 目的：在每个分析单元内，把 GHSL 建成面积 ≥ 阈值的 100 m 栅格矢量化为连通斑块；
#       矢量化之前先做形态学闭运算（morphological closing，先膨胀后腐蚀，config 中 core.closing_radius_m，
#       半径换算为 round(r/100) 个像元，0 = 不做）：宽度不超过约 2 倍半径的河流、道路、铁路走廊被连通，
#       跨河县城不再只剩驻地一侧；闭运算在 GHSL 原生 100 m 网格上进行（reproject 固定网格）。
#       若提供驻地点，选“驻地点缓冲区内面积最大的斑块”，否则选最大斑块，作为县城/中心城区。
#       选中的斑块默认“填补内部孔洞”（config 中 core.fill_holes）：城区内部的公园、湖泊、广场、
#       大型运动场等建成比例低于阈值的栅格，矢量化后会成为多边形内部的“洞”；不填补的话，
#       这些公园绿地会被排除在中心建成区之外（公园代理、绿地指标系统性偏低），并被算进 5 km 环带本底。
#       单元内没有达到最小面积的斑块时，退化为单元几何中心 1 km 缓冲区并标记 core_method。
#       ee.Algorithms.If 在服务器端只计算被选中的分支，所以空集合时不会去取“空斑块”的几何。
# 结果：返回带 core 几何的 ee.Feature，属性 unit_id、core_method、core_area_m2、core_closing_m。
# ===========================================================================
def closing_pixels(ccfg: dict) -> int:
    """闭运算半径（米）换算为 GHSL 100 m 像元数（四舍五入）；0 表示不做闭运算。"""
    r = float(ccfg.get("closing_radius_m") or 0)
    return max(int(r / 100.0 + 0.5), 0)


def built_mask(built_img: "ee.Image", ccfg: dict):
    """返回 (闭运算后的建成掩膜 b, 原始建成掩膜 0/1, built_surface 波段)。"""
    bs = built_img.select("built_surface")      # 只取单个波段再取投影，避免多波段投影不一致时报错
    raw = bs.gte(ccfg["ghsl_threshold_m2"])
    k = closing_pixels(ccfg)
    if k > 0:
        closed = (raw.unmask(0).focalMax(k, "square", "pixels").focalMin(k, "square", "pixels")
                  .reproject(bs.projection()))
    else:
        closed = raw
    return closed.selfMask().rename("b").toInt(), raw, bs


def fill_holes(geom):
    """只保留多边形（或多部件多边形每个部件）的外环，去掉内部孔洞；各部件合并为一个几何。"""
    parts = ee.Geometry(geom).geometries()
    shells = parts.map(lambda p: ee.Geometry.Polygon(ee.List(ee.Geometry(p).coordinates()).slice(0, 1)))
    return ee.Geometry.MultiPolygon(shells).dissolve(10)


def core_feature(unit: "ee.Feature", built_img: "ee.Image", ccfg: dict, seats: "ee.FeatureCollection | None"):
    geom = unit.geometry()
    mask, _, bs = built_mask(built_img, ccfg)
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
    # 填洞后再与单元边界求交：若斑块包围了别的行政单元的飞地，飞地不会被算进本单元
    patch_geom = (fill_holes(chosen.geometry()).intersection(geom, 10) if ccfg.get("fill_holes", True)
                  else chosen.geometry())
    g = ee.Geometry(ee.Algorithms.If(has, patch_geom, fallback))
    return ee.Feature(g, {
        "unit_id": unit.get("unit_id"),
        "core_method": ee.Algorithms.If(has, method, "fallback_centroid_1km"),
        "core_area_m2": g.area(100),
        "core_closing_m": closing_pixels(ccfg) * 100,
    })


# ===========================================================================
# 代码块 5：分区统计的小工具
# 目的：reduceRegions 的输出字段名在单波段时是 'sum'/'mean'，多波段时是波段名；
#       这里统一给波段加前缀，并在单波段时强制命名，保证字段名稳定。
#       计数型栅格（人口、面积、体量、灯光）必须在“原生网格”上求和，否则重采样会改变总量，
#       所以 crs 取影像自身投影（ee.Projection，含原生像元大小与网格起点），scale 传 None：
#       GEE 规定 crs 与 scale 同时给出时会把网格“重缩放”到 scale，哪怕只差一点也会错位重采样
#       （例如 DMSP/CCNL 的 30″ 经纬度网格名义约 927.7 m，若写 scale=1000，求和会少约 14%）。
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


def masked_areas(masks: list, names: list) -> "ee.Image":
    """把若干 0/1 掩膜转成面积（m²）多波段影像，波段依次命名，便于 reduce_add 按序号改名。"""
    pa = ee.Image.pixelArea()
    return ee.Image.cat(*[pa.updateMask(m).rename(n) for m, n in zip(masks, names)])


def riparian_water(ds: DS, g: dict, bounds) -> "ee.Image":
    """滨水线性绿地所依附的水体（0/1 影像）。
    提供 river_asset 时用河道要素（同时填充面要素并描 1 像元宽的线，面、线两种资产都能用）；
    否则用 JRC 近永久水体：出现频率 ≥ riparian_water_occurrence，且所在连通水面 ≥ riparian_min_water_m2（排除零散鱼塘）。
    连通面积在 JRC 原生网格上计数：连通像元数 × 该处像元面积（经纬度网格像元面积随纬度变化，逐像元换算）。"""
    if g.get("river_asset"):
        rivers = ee.FeatureCollection(g["river_asset"]).filterBounds(bounds)
        return ee.Image(0).byte().paint(rivers, 1).paint(rivers, 1, 1)
    w = ds.water().gte(g.get("riparian_water_occurrence", 90))
    min_m2 = float(g.get("riparian_min_water_m2") or 0)
    if min_m2 <= 0:
        return w
    # JRC 原生像元约 0.00025°：中国境内（北至约 53.5°N）单个像元面积不小于约 450 m²，按 400 m² 估计计数上限
    maxpix = int(math.ceil(min_m2 / 400.0))
    cnt = w.selfMask().connectedPixelCount(maxSize=min(maxpix, 1024), eightConnected=True)
    if maxpix > 1024:                                             # GEE 连通计数上限 1024 像元
        LOG.warning("riparian_min_water_m2 过大，connectedPixelCount 最多计到 1024 像元，连通水面门槛按 1024 像元处理")
        big = cnt.reproject(ds.water_proj()).gte(1024)
    else:
        big = cnt.multiply(ee.Image.pixelArea()).reproject(ds.water_proj()).gte(min_m2)
    return w.And(big.unmask(0))


# ===========================================================================
# 代码块 6：单个 chunk 的全部计算
# 目的：对一批分析单元，依次构建中心建成区、单元级指标、中心建成区指标和环带指标的计算图（build_chunk），
#       再一次 getInfo 取回（fetch_chunk，减少请求次数）。两步分开，--export-failed 可以把同一张计算图
#       交给批处理导出（export_collection），不受交互请求约 5 分钟的超时限制。
# 结果：run_chunk 返回 (unit_rows: list[dict], core_geojson: dict)；build_chunk 返回 {"u","c","r"} 三个 FeatureCollection。
# ===========================================================================
def build_chunk(units: "ee.FeatureCollection", cfg: dict, seats) -> dict:
    g = cfg["gee"]
    ds = DS(cfg)
    years = g["years"]
    gy = g["green_year"]
    months = g["green_months"]
    ts = g.get("tile_scale", 4)
    ccfg = g["core"]
    mask_water = g.get("mask_water_in_ndvi", True)

    # 6a. 中心建成区：以 green_year（2020）的 GHSL 建成面积识别，并固定这一边界比较各年份
    built_ref = ds.ghsl_s(gy)
    cores2020 = units.map(lambda u: core_feature(u, built_ref, ccfg, seats))
    cores = cores2020
    # 其他普查年份的“动态”中心建成区面积（同一规则、当年 GHSL，同样先做闭运算），用于衡量建成区蔓延。
    # 该年没有合格斑块（退化为 1 km 圆）时面积记为缺失、不写入 core{y}_area_m2，并记下 core{y}_method，
    # 否则 03 会用“1 km 圆面积 3.14 km²”去算 ln(A2020/A2010)，得到虚假的扩张/收缩（05 的 M9 直接使用）。
    for y in years:
        if y == gy:
            continue
        by = ds.ghsl_s(y)
        dyn = units.map(lambda u, by=by: core_feature(u, by, ccfg, seats))
        ok = dyn.filter(ee.Filter.neq("core_method", "fallback_centroid_1km"))
        d = ee.Dictionary.fromLists(ok.aggregate_array("unit_id"), ok.aggregate_array("core_area_m2"))
        dm = ee.Dictionary.fromLists(dyn.aggregate_array("unit_id"), dyn.aggregate_array("core_method"))

        def _set_dyn(f, y=y, d=d, dm=dm):
            uid = f.get("unit_id")
            f = f.set(f"core{y}_method", dm.get(uid))
            return ee.Feature(ee.Algorithms.If(d.contains(uid), f.set(f"core{y}_area_m2", d.get(uid)), f))
        cores = cores.map(_set_dyn)

    # 6b. 单元级与中心建成区级：GHSL 面积、体量、人口（原生 100 m 网格求和），WorldPop，夜间灯光
    u_fc, c_fc = units, cores
    for y in years:
        stack = (ds.ghsl_s(y).select(["built_surface", "built_surface_nres"])
                 .addBands(ds.ghsl_v(y).select(["built_volume_total", "built_volume_nres"]))
                 .addBands(ds.ghsl_pop(y)))
        names = [f"bs_{y}", f"bsn_{y}", f"bv_{y}", f"bvn_{y}", f"pop_ghs_{y}"]
        proj = ds.ghsl_s(y).select("built_surface").projection()
        u_fc = reduce_add(u_fc, stack, names, "sum", None, "u_", crs=proj, tile_scale=ts)
        c_fc = reduce_add(c_fc, stack, names, "sum", None, "c_", crs=proj, tile_scale=ts)
        # WorldPop（3″ ≈ 92.77 m）与夜光（VIIRS 15″ ≈ 463.8 m；CCNL 沿用 DMSP 的 30″ 网格，STAC 标 1 km）都是经纬度网格：
        # scale 传 None，直接在影像自身投影与像元大小上求和（给 scale 会把网格重缩放、错位重采样）
        wp = ds.worldpop(y)
        if wp is not None:
            wproj = wp.projection()
            u_fc = reduce_add(u_fc, wp, [f"pop_wp_{y}"], "sum", None, "u_", crs=wproj, tile_scale=ts)
            c_fc = reduce_add(c_fc, wp, [f"pop_wp_{y}"], "sum", None, "c_", crs=wproj, tile_scale=ts)
        nimg, src = ds.ntl(y)
        if nimg is not None:
            nproj = nimg.projection()
            u_fc = reduce_add(u_fc, nimg, [f"ntl_{src}_{y}"], "sum", None, "u_", crs=nproj, tile_scale=ts)
            c_fc = reduce_add(c_fc, nimg, [f"ntl_{src}_{y}"], "sum", None, "c_", crs=nproj, tile_scale=ts)

    # 6b'. 闭运算质控：最终中心建成区内“原始（未闭运算）达到阈值的 100 m 栅格”面积，原生网格求和。
    #      与 core_area_m2 之比越低，说明闭运算与填洞并入的非建成面积越多。
    gproj = ds.ghsl_s(gy).select("built_surface").projection()
    _, raw_ref, _ = built_mask(built_ref, ccfg)
    c_fc = reduce_add(c_fc, masked_areas([raw_ref], ["bc"]), [f"builtcell_m2_{gy}"], "sum", None, "c_",
                      crs=gproj, tile_scale=ts)

    # 6b''. GAIA 不透水面（30 m，至 2018 年）：固定的 2020 年中心建成区与整个单元内各年份面积，原生网格求和
    gaia_years = [y for y in g.get("gaia_years", []) if 1985 <= int(y) <= 2018]
    if gaia_years and ds.c.get("gaia"):
        names = [f"gaia_imp_m2_{y}" for y in gaia_years]
        img = masked_areas([ds.gaia_imp(y) for y in gaia_years], names)
        u_fc = reduce_add(u_fc, img, names, "sum", None, "u_", crs=ds.gaia_proj(), tile_scale=ts)
        c_fc = reduce_add(c_fc, img, names, "sum", None, "c_", crs=ds.gaia_proj(), tile_scale=ts)

    # 6b'''. GHS-SMOD（1 km，green_year 当期）：城市中心（30）与城镇簇（22、23、30）面积，作为中心建成区识别的外部对照
    if g.get("use_smod", True) and ds.c.get("ghsl_smod"):
        smod = ds.smod(gy)
        ucl = smod.eq(22).Or(smod.eq(23)).Or(smod.eq(30))
        img = masked_areas([ucl, smod.eq(30)], ["ucl", "uc"])
        sproj = smod.projection()
        u_fc = reduce_add(u_fc, img, [f"smod_ucl_m2_{gy}", f"smod_uc_m2_{gy}"], "sum", None, "u_",
                          crs=sproj, tile_scale=ts)
        c_fc = reduce_add(c_fc, img.select(["ucl"]), [f"smod_ucl_m2_{gy}"], "sum", None, "c_",
                          crs=sproj, tile_scale=ts)

    # 6c. 中心建成区内的绿地（10 m WorldCover 各地类面积；Sentinel-2 NDVI；Dynamic World 树木/草地概率）
    wc = ds.worldcover()
    tree10 = wc_mask(wc, TREE_CODES)
    green10 = wc_mask(wc, GREEN_CODES)
    wc_img, wc_names = area_by_class(wc, g["worldcover_classes"])
    c_fc = reduce_add(c_fc, wc_img, wc_names, "sum", 10, "c_", tile_scale=ts)
    bounds = units.bounds(100)   # 本批单元的外包矩形（只用于筛选逐景影像和矢量资产；不必先合并各县多边形）

    # 6c'. 存量树木与新增树木：2020 年树木像元中，Hansen 2000 年树冠覆盖度 ≥ baseline_tree_cover_pct 的记为存量，其余记为新增；
    #      另记坡度 ≤ slope_mask_deg 的树木（敏感性检验，排除山体残林；坡度在 NASADEM 原生 30 m 网格上计算）
    if ds.c.get("hansen_gfc"):
        tc = ds.treecover2000()
        pct = g.get("baseline_tree_cover_pct", 30)
        img = masked_areas([tree10.And(tc.gte(pct)), tree10.And(tc.lt(pct)),
                            tree10.And(ds.slope().lte(g.get("slope_mask_deg", 15)))], ["s", "n", "f"])
        c_fc = reduce_add(c_fc, img, [f"tree_stock_m2_{gy}", f"tree_new_m2_{gy}", f"tree_flat_m2_{gy}"],
                          "sum", 10, "c_", tile_scale=ts)

    # 6c''. 人口加权绿地暴露（population-weighted greenspace exposure，Chen et al. 2022 Nature Communications）：
    #      先把 10 m 的树木、绿地（树木+灌木+草地）二值图聚合为 100 m 覆盖比例，再取半径 r 的圆形邻域均值，
    #      得到“每个 100 m 人口格网周围 r 米内的绿地比例”，乘以格网人口后在中心建成区内求和；
    #      03 脚本中除以人口总和即为暴露度。邻域可越出中心建成区边界，符合居民实际可达范围。
    frac = (ee.Image.cat(tree10, green10)
            .rename(["tree", "green"])
            .reduceResolution(ee.Reducer.mean(), maxPixels=1024).reproject(gproj))
    rad = g["exposure_radius_m"]
    expo = frac.focalMean(radius=rad, kernelType="circle", units="meters").reproject(gproj)
    pop_g = ds.ghsl_pop(gy)
    pw = expo.multiply(pop_g).addBands(pop_g)
    c_fc = reduce_add(c_fc, pw, [f"pw_tree_{gy}", f"pw_green_{gy}", f"pop_expo_{gy}"], "sum", None, "c_",
                      crs=gproj, tile_scale=ts)

    # 6c'''. 大型绿斑与线性绿地（遥感代理；“公园”“绿道”两个词只用于矢量数据，附录D 说明依据）
    #      大型绿斑：中心建成区内面积 ≥ green_patch_min_m2（默认 1 公顷）的连片斑块，地类由 green_patch_class 指定
    #               （tree = 只用树木，主口径；green = 树木+灌木+草地）；clip_patch_to_core 时先乘中心建成区掩膜，
    #               截断斑块与区外山林的连通，再做连通计数；绿斑可达：斑块 park_access_distance_m 范围内的人口；
    #      滨水线性绿地：近永久水体（或 river_asset 河道）外扩 riparian_buffer_m 内的同类绿地；
    #      道路绿带（行道树代理）：GHSL 2018 道路面外扩 road_buffer_m 内的同类绿地；
    #      另记 GHSL 2018 聚落内植被开放空间（1–3 类）与道路面（5 类）面积。
    #      连片斑块在 GHSL 的 Mollweide 等积投影 10 m 网格上计数（p10）：每个像元恰好 100 m²，与纬度无关；
    #      若在经纬度网格上计数，像元面积约 100×cos(纬度) m²，“1 公顷”门槛在哈尔滨只相当于约 0.7 公顷，
    #      且面积与可达两处用到的网格不一致。p10 与 GHSL 100 m 网格对齐，每个 100 m 格恰含 10×10 个像元。
    if g.get("use_green_proxies", True):
        pclass = str(g.get("green_patch_class", "tree")).lower()
        if pclass not in ("tree", "green"):
            LOG.warning(f"green_patch_class = {pclass} 无法识别，按 tree（只用树木）处理")
            pclass = "tree"
        cls10 = tree10 if pclass == "tree" else green10
        p10 = gproj.atScale(10)
        src = cls10
        if g.get("clip_patch_to_core", True):
            src = cls10.And(ee.Image(0).byte().paint(cores2020, 1))
        g10 = src.reproject(p10)
        minpix = max(int(g["green_patch_min_m2"] / 100), 2)          # p10 像元面积 = 100 m²
        if minpix > 1024:                                             # GEE 连通计数上限 1024 像元（约 10 公顷）
            LOG.warning("green_patch_min_m2 超过 102400 m²，connectedPixelCount 最多计到 1024 像元，门槛按 1024 像元处理")
            minpix = 1024
        cnt = g10.selfMask().connectedPixelCount(maxSize=minpix, eightConnected=True).reproject(p10)
        patch = cnt.gte(minpix).unmask(0).And(g10)
        water = riparian_water(ds, g, bounds)
        riparian = cls10.And(water.focalMax(radius=g["riparian_buffer_m"], units="meters")).And(water.Not())
        bc = ds.ghs_built_c()
        road = bc.eq(5)
        roadside = cls10.And(road.focalMax(radius=g["road_buffer_m"], units="meters"))
        openveg = bc.gte(1).And(bc.lte(3))
        prox = masked_areas([patch, riparian, roadside, openveg, road], ["p", "rp", "rs", "ov", "rd"])
        c_fc = reduce_add(c_fc, prox, [f"greenpatch_m2_{gy}", f"riparian_green_m2_{gy}", f"roadside_green_m2_{gy}",
                                       "openveg_m2_2018", "road_m2_2018"], "sum", 10, "c_", tile_scale=ts)
        dist = g["park_access_distance_m"]
        patch100 = patch.reduceResolution(ee.Reducer.max(), maxPixels=1024).reproject(gproj)
        near = patch100.focalMax(radius=dist, units="meters").reproject(gproj)
        c_fc = reduce_add(c_fc, pop_g.updateMask(near), [f"pop_greenpatch{dist}_{gy}"], "sum", None, "c_",
                          crs=gproj, tile_scale=ts)

    # 6c''''. 可选：CLCD 30 m 年度地类（Yang & Huang 2021，社区目录，路径须先核验）
    #      各年份各地类面积（原生网格求和），以及“新增管理绿地”：CLCD 最后一年（clcd_years 最大值，
    #      与 03 中 green_new_clcd_share 的分母同一年）为林地、灌木或草地，且基期（clcd_baseline_year）
    #      为耕地、裸地或不透水面的面积。两端都用 CLCD：WorldCover 10 m 与 CLCD 30 m 的分类体系不同，
    #      跨产品相减会把分类差异（如老城区 30 m 像元被 CLCD 判为不透水面、却被 WorldCover 判为树木）当成新增
    if g.get("clcd_asset_template"):
        cls = g.get("clcd_classes") or {}
        for y in g.get("clcd_years", []):
            img = ds.clcd(y)
            names = [f"clcd{y}_{k}_m2" for k in cls]
            c_fc = reduce_add(c_fc, masked_areas([img.eq(int(v)) for v in cls.values()], names), names,
                              "sum", None, "c_", crs=img.projection(), tile_scale=ts)
        codes = [int(cls[k]) for k in ("crop", "bare", "imp") if k in cls]
        gcodes = [int(cls[k]) for k in ("forest", "shrub", "grass") if k in cls]
        cys = [int(y) for y in g.get("clcd_years", [])]
        if codes and gcodes and cys:
            last = ds.clcd(max(cys))
            base = ds.clcd(g.get("clcd_baseline_year", 2000))
            gn = wc_mask(last, gcodes).And(wc_mask(base, codes))
            c_fc = reduce_add(c_fc, masked_areas([gn], ["gn"]), [f"green_new_clcd_m2_{gy}"],
                              "sum", None, "c_", crs=last.projection(), tile_scale=ts)
        else:
            LOG.warning("clcd_classes 缺少 crop、bare、imp 或 forest、shrub、grass（或 clcd_years 为空），"
                        "无法计算 c_green_new_clcd_m2")

    if g.get("use_s2_ndvi", True):
        ndvi = ds.s2_ndvi(bounds, gy, months)
        if mask_water:
            ndvi = ndvi.updateMask(ds.ndvi_water().Not())
        c_fc = reduce_add(c_fc, ndvi, [f"ndvi_s2_{gy}"], "mean", g.get("s2_scale", 20), "c_", tile_scale=ts)
    if g.get("use_dynamic_world", True):
        c_fc = reduce_add(c_fc, ds.dw_green(bounds, gy, months), [f"dw_trees_{gy}", f"dw_grass_{gy}"],
                          "mean", g.get("dw_scale", 20), "c_", tile_scale=ts)

    # 6d. 可选：公园面积与公园步行可达人口（需要在 config 中提供公园多边形 asset）
    if g.get("park_asset"):
        parks = ee.FeatureCollection(g["park_asset"]).filterBounds(bounds)
        park_img = ee.Image.pixelArea().updateMask(ee.Image(0).byte().paint(parks, 1))
        c_fc = reduce_add(c_fc, park_img, [f"park_m2_{gy}"], "sum", 10, "c_", tile_scale=ts)
        dist = g["park_access_distance_m"]
        near = ee.Image(0).byte().paint(parks.map(lambda f: f.buffer(dist)), 1)
        pop_near = ds.ghsl_pop(gy).updateMask(near)
        c_fc = reduce_add(c_fc, pop_near, [f"pop_park{dist}_{gy}"], "sum", None, "c_",
                          crs=ds.ghsl_s(gy).select("built_surface").projection(), tile_scale=ts)

    # 6d'. 可选：学校、医院、养老机构点位（poi_assets）。中心建成区内的设施个数（逐个中心建成区 filterBounds 计数），
    #      以及设施 d 米内的人口：点位按地面距离缓冲成圆，画到 GHSL 100 m 网格上，再对网格人口求和
    #      （缓冲在地面距离上计算，不受投影变形影响）
    pdist = g.get("poi_access_distance_m") or {}
    for key, aid in (g.get("poi_assets") or {}).items():
        if not aid:
            continue
        dist = int(pdist.get(key, 500))
        pts = ee.FeatureCollection(aid).filterBounds(bounds.buffer(dist, 100))
        c_fc = c_fc.map(lambda f, pts=pts, key=key: f.set(f"c_n_poi_{key}", pts.filterBounds(f.geometry()).size()))
        near = ee.Image(0).byte().paint(pts.map(lambda p, dist=dist: p.buffer(dist, 10)), 1)
        c_fc = reduce_add(c_fc, pop_g.updateMask(near), [f"pop_poi_{key}{dist}_{gy}"], "sum", None, "c_",
                          crs=gproj, tile_scale=ts)

    # 6d''. 可选：绿道线要素（greenway_asset）。中心建成区内的绿道长度（线段与中心建成区求交后求长度），
    #       以及绿道 d 米内的人口（做法同设施点位）
    if g.get("greenway_asset"):
        gdist = int(g.get("greenway_access_distance_m", 500))
        lines = ee.FeatureCollection(g["greenway_asset"]).filterBounds(bounds.buffer(gdist, 100))

        def _gw_len(f):
            geom = f.geometry()
            segs = lines.filterBounds(geom).map(
                lambda ln: ee.Feature(None, {"len": ln.geometry().intersection(geom, 1).length(1)}))
            return f.set("c_greenway_len_m", segs.aggregate_sum("len"))
        c_fc = c_fc.map(_gw_len)
        near = ee.Image(0).byte().paint(lines.map(lambda ln: ln.buffer(gdist, 10)), 1)
        c_fc = reduce_add(c_fc, pop_g.updateMask(near), [f"pop_greenway{gdist}_{gy}"], "sum", None, "c_",
                          crs=gproj, tile_scale=ts)

    # 6e. 地形（单元与中心建成区）与气候（单元）：坡度在 NASADEM 原生 30 m 网格上计算，
    #     单元均值按 terrain_unit_scale_m 抽样统计，中心建成区按 30 m 统计
    terr = ds.terrain()
    u_fc = reduce_add(u_fc, terr, ["elev", "slope"], "mean", g.get("terrain_unit_scale_m", 90), "u_", tile_scale=ts)
    c_fc = reduce_add(c_fc, terr, ["elev", "slope"], "mean", 30, "c_", tile_scale=ts)
    u_fc = reduce_add(u_fc, ds.climate(gy), [f"t2m_c_{gy}", f"prcp_mm_{gy}"], "mean", 11132, "u_", tile_scale=ts)
    u_fc = reduce_add(u_fc, ds.access(), ["access_min"], "mean", 1000, "u_", tile_scale=ts)

    # 6f. 自然植被本底：中心建成区外 5 km 环带（剔除建成栅格与水面）的 MODIS NDVI 均值
    rb = g["ring_buffer_m"]
    rings = cores2020.map(lambda f: ee.Feature(
        f.geometry().buffer(rb, 100).difference(f.geometry(), 100), {"unit_id": f.get("unit_id")}))
    nonbuilt = ds.ghsl_s(gy).select("built_surface").lt(ccfg["ghsl_threshold_m2"] / 4)
    ndvi_bg = ds.modis_ndvi(gy, months).updateMask(nonbuilt)
    if mask_water:
        ndvi_bg = ndvi_bg.updateMask(ds.ndvi_water().Not())
    r_fc = reduce_add(rings, ndvi_bg, [f"ndvi_modis_{gy}"], "mean", 250, "r_", tile_scale=ts)
    return {"u": u_fc, "c": c_fc, "r": r_fc}


def chunk_tables(fcs: dict) -> dict:
    """取回前的整理：单元级、环带级不取几何；中心建成区转为经纬度并简化几何（约 30 m）以便本地制图。"""
    return {"u": fcs["u"].select([".*"], None, False),
            "c": fcs["c"].map(lambda f: f.setGeometry(f.geometry().transform("EPSG:4326", 10).simplify(30))),
            "r": fcs["r"].select([".*"], None, False)}


def fetch_chunk(fcs: dict) -> tuple[list, dict]:
    res = ee.Dictionary(chunk_tables(fcs)).getInfo()
    return merge_rows(res), res["c"]


def run_chunk(units: "ee.FeatureCollection", cfg: dict, seats) -> tuple[list, dict]:
    return fetch_chunk(build_chunk(units, cfg, seats))


def export_collection(fcs: dict) -> "ee.FeatureCollection":
    """批处理导出用（每次一个单元）：把 u_、r_ 属性并到中心建成区要素上，几何为中心建成区。"""
    t = chunk_tables(fcs)
    c = ee.Feature(t["c"].first())
    merged = ee.Feature(ee.Feature(c.copyProperties(ee.Feature(t["u"].first())))
                        .copyProperties(ee.Feature(t["r"].first())))
    return ee.FeatureCollection([merged])


def merge_rows(res: dict) -> list:
    """把 u、c、r 各组结果按 unit_id 合并成一行一个单元的字典列表（年度模式只有 u、c 或只有 c）。"""
    rows = {}
    for key in ("u", "c", "r"):
        for feat in (res.get(key) or {}).get("features", []):
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
# 代码块 7：年度模式的计算图（--annual）
# 目的：在固定的 2020 年中心建成区（读主运行合并的 core_polygons_2020.geojson）与整个单元内，逐年提取：
#       GAIA 不透水面面积（gaia_years，含两端，至 2018 年）、VIIRS 年度夜光总量（viirs_years）、
#       Dynamic World 生长季树木与草地平均概率（dw_years，只算中心建成区）。
#       每类数据单独成组，每组每批一次请求；Dynamic World 最费算力，按 dw_years_per_request 年一组（默认 3 年）。
# 结果：每批返回宽表行（如 c_gaia_imp_m2_2005），合并时转为长表 annual_long.csv（一行一个单元年份）。
# ===========================================================================
ANNUAL_VARS = ["c_gaia_imp_m2", "u_gaia_imp_m2", "c_ntl_viirs", "u_ntl_viirs", "c_dw_trees", "c_dw_grass"]
ANNUAL_RE = r"^(" + "|".join(ANNUAL_VARS) + r")_(\d{4})$"


def annual_groups(g: dict) -> list:
    """返回 [(组名, 数据类型, 年份列表)]；组名不含下划线，用于批次文件名。"""
    groups = []
    gys = annual_years(g, "gaia_years", 1985, 2018)
    if gys and g["datasets"].get("gaia"):
        groups.append(("gaia", "gaia", gys))
    vys = annual_years(g, "viirs_years", 2013, 2100)
    if vys:
        groups.append(("viirs", "viirs", vys))
    dys = annual_years(g, "dw_years", 2015, 2100)
    step = max(int((g.get("annual") or {}).get("dw_years_per_request", 3)), 1)
    for i in range(0, len(dys), step):
        part = dys[i:i + step]
        groups.append((f"dw{part[0]}-{part[-1]}", "dw", part))
    return groups


def build_annual(units, cores, cfg: dict, kind: str, years: list) -> dict:
    g = cfg["gee"]
    ds = DS(cfg)
    ts = g.get("tile_scale", 4)
    if kind == "gaia":
        names = [f"gaia_imp_m2_{y}" for y in years]
        img = masked_areas([ds.gaia_imp(y) for y in years], names)
        proj = ds.gaia_proj()
        return {"u": reduce_add(units, img, names, "sum", None, "u_", crs=proj, tile_scale=ts),
                "c": reduce_add(cores, img, names, "sum", None, "c_", crs=proj, tile_scale=ts)}
    if kind == "viirs":
        imgs = [ds.ntl(y)[0].rename(f"v{y}") for y in years]
        names = [f"ntl_viirs_{y}" for y in years]
        img, proj = ee.Image.cat(*imgs), imgs[0].projection()   # 同一 15″ 网格，原生网格求和
        return {"u": reduce_add(units, img, names, "sum", None, "u_", crs=proj, tile_scale=ts),
                "c": reduce_add(cores, img, names, "sum", None, "c_", crs=proj, tile_scale=ts)}
    if kind == "dw":
        bounds = cores.bounds(100)
        img = ee.Image.cat(*[ds.dw_green(bounds, y, g["green_months"]).rename([f"t{y}", f"g{y}"]) for y in years])
        names = [n for y in years for n in (f"dw_trees_{y}", f"dw_grass_{y}")]
        return {"c": reduce_add(cores, img, names, "mean", g.get("dw_scale", 20), "c_", tile_scale=ts)}
    raise ValueError(f"未知的年度数据类型：{kind}")


def fetch_annual(fcs: dict) -> tuple[list, None]:
    res = ee.Dictionary({k: v.select([".*"], None, False) for k, v in fcs.items()}).getInfo()
    return merge_rows(res), None


# ===========================================================================
# 代码块 8：断点续跑 + 自动拆分 + 逐批运行
# 目的：某批失败时先重试（指数退避）；仍失败就拆成两半分别计算，直到单个单元；
#       单个单元仍失败则记入 failures.csv 并继续下一批，不让一个“坏单元”卡住全国任务。
#       续跑时，若某批上次已被拆分（chunks/ 下已有 <批次名>a… 或 <批次名>b… 的结果），
#       直接沿用同样的拆分，只补算缺的部分，不再把整批（已知会失败）重新提交、白等重试。
#       注意：完成与否按文件判断。若中途重新运行 00 使某批的单元减少，旧的 a/b 拆分文件与新的两半可能对不上，
#       个别单元会被当作已完成而漏算；遇到这种情况（终端会警告），删除 chunks/ 与分批方案后重跑最稳妥。
#       连续 3 批全部失败时停止，多半是系统性问题。
# 结果：成功的部分写入 chunks/；失败单元写入 failures.csv（年度模式另记所属数据组）。
# ===========================================================================
def run_with_split(ids, compute, cfg, tag, out_dir, failures, with_core=True):
    """compute(ids) 返回 (rows, core_geojson)；with_core=False 时（年度模式）只写 _unit.csv。"""
    unit_csv = out_dir / f"{tag}_unit.csv"
    core_geo = out_dir / f"{tag}_core.geojson"
    if unit_csv.exists() and (core_geo.exists() or not with_core):
        return len(ids)
    if len(ids) == 1 and with_core and (out_dir / f"export_{ids[0]}_unit.csv").exists():
        LOG.info(f"单元 {ids[0]} 已有批处理导出结果（export_{ids[0]}_unit.csv），不再交互计算")
        return 1
    mid = len(ids) // 2

    def split():
        a = run_with_split(ids[:mid], compute, cfg, tag + "a", out_dir, failures, with_core)
        b = run_with_split(ids[mid:], compute, cfg, tag + "b", out_dir, failures, with_core)
        return a + b
    if len(ids) > 1 and (any(out_dir.glob(f"{tag}a*_unit.csv")) or any(out_dir.glob(f"{tag}b*_unit.csv"))):
        LOG.info(f"{tag} 上次已拆分计算，沿用拆分续跑")
        return split()
    g = cfg["gee"]
    tries = g["max_retries"] if len(ids) > 1 else g["max_retries"] + 1
    try:
        rows, core = retry(lambda: compute(ids), tries=tries,
                           base_delay=g["retry_base_delay_s"], logger=LOG, what=tag)
        if with_core:
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
        LOG.warning(f"{tag} 失败，拆分为 {mid} + {len(ids) - mid} 个单元重试")
        return split()


def run_jobs(jobs: list, cfg: dict, chunk_dir: Path, label: str, with_core=True) -> tuple[list, bool]:
    """jobs 为 [(批次名, 单元列表, compute, 数据组名或 None, 分批方案中的单元数)]。返回 (新失败清单, 是否因连续失败而停止)。"""
    prog = ChunkProgress(len(jobs), LOG, label)
    failures = []
    zero_streak, stopped = 0, False
    for i, (tag, ids, compute, group, n_listed) in enumerate(jobs):
        if (chunk_dir / f"{tag}_unit.csv").exists():
            prog.skip(i)
            continue
        if not ids:
            prog.skip(i, "本批单元已不在当前单元表中，跳过")
            continue
        if len(ids) < n_listed and any(chunk_dir.glob(f"{tag}[ab]*_unit.csv")):
            LOG.warning(f"{tag} 的单元比分批方案少（可能重新运行过 00），旧的拆分文件可能与新的两半对不上，"
                        f"个别单元会被漏算。建议删除 chunks/ 与分批方案后重跑。")
        prog.start(i, f"{len(ids)} 个单元（{ids[0]} … {ids[-1]}）")
        new = []
        n = run_with_split(ids, compute, cfg, tag, chunk_dir, new, with_core)
        failures += [dict(f, group=group) for f in new] if group else new
        prog.finish(i, n)
        # 连续 3 批全部失败，多半是系统性问题（数据集 ID、代码、网络或 GEE 配额），继续跑只会把全国单元都记为失败
        zero_streak = zero_streak + 1 if n == 0 else 0
        if zero_streak >= 3:
            LOG.error("连续 3 批全部失败，已停止。请查看日志与 failures.csv 中的报错（或先运行 --preflight），"
                      "排除问题后重新运行即可从断点续跑。")
            stopped = True
            break
    prog.summary()
    return failures, stopped


def _tag_of(p: Path) -> str:
    return p.name[: -len("_unit.csv")]


def update_failures(fpath: Path, new: list, chunk_dir: Path, prefix: str, annual=False):
    """并入本次新失败的单元，并删去之后已成功补算的单元（只看本次同一批次前缀与批处理导出的结果文件）。"""
    keys = ["unit_id", "group"] if annual else ["unit_id"]
    if not (new or fpath.exists()):
        return
    old = read_table(fpath) if fpath.exists() else pd.DataFrame(columns=keys + ["error"])
    allf = pd.concat([old, pd.DataFrame(new, columns=keys + ["error"])]).drop_duplicates(keys, keep="last")
    files = list(chunk_dir.glob(f"{prefix}_*_unit.csv"))
    if annual:
        done = set()
        for p in files:   # 批次名 = <前缀>_<数据组>_<序号>[a/b…]，数据组名不含下划线
            group = _tag_of(p).split("_")[-2]
            done |= {(u, group) for u in read_table(p)["unit_id"].astype(str)}
        hit = pd.Series([(str(u), str(gr)) in done for u, gr in zip(allf["unit_id"], allf["group"])],
                        index=allf.index, dtype=bool)
    else:
        done = set()
        for p in files + list(chunk_dir.glob("export_*_unit.csv")):
            done |= set(read_table(p)["unit_id"].astype(str))
        hit = allf["unit_id"].astype(str).isin(done)
    allf = allf[~hit]
    atomic_write_csv(allf, fpath)
    if len(allf):
        LOG.warning(f"{len(allf)} 个{'单元年度数据组' if annual else '单元'}仍失败，见 {fpath.name}。可在 config 中增大 tile_scale 后重跑"
                    f"（会自动只补算失败单元）{'' if annual else '，或运行 --export-failed 改用批处理导出'}。")


# ===========================================================================
# 代码块 9：分批方案
# 目的：首次运行把单元按 chunk_size 分批并写入分批方案（manifest），续跑时沿用同一分批，保证“已完成批次”的判断有效。
#       isolate_large_units 为 true 时，面积超过 large_unit_km2 的单元（面积读 00 输出的 units_table.csv
#       或 units_did_table.csv）各自单独成批，排在普通批次之后，避免一个特大单元拖垮整批。
#       已有分批方案时不改动已有批次；只有不在方案中的单元（例如重新运行 00 后新增的）追加为新批次，同样区分大单元。
# 结果：返回 manifest 字典 {"chunk_size", "chunks"}，并写入 <前缀>_manifest.json。
# ===========================================================================
def large_units(g: dict, table_path: Path) -> set:
    if not g.get("isolate_large_units", False):
        return set()
    thr = float(g.get("large_unit_km2", 20000))
    if not table_path.exists():
        LOG.warning(f"找不到 {table_path.name}，无法按面积识别大单元，本次不单独成批")
        return set()
    t = read_table(table_path)
    if "area_km2" not in t.columns or "unit_id" not in t.columns:
        LOG.warning(f"{table_path.name} 中没有 unit_id 或 area_km2 列，无法按面积识别大单元，本次不单独成批")
        return set()
    area = pd.to_numeric(t["area_km2"], errors="coerce")
    return set(t.loc[area > thr, "unit_id"].astype(str))


def plan_chunks(path: Path, ids: list, size: int, big: set, thr_km2=None) -> dict:
    def pack(us):
        normal = [u for u in us if u not in big]
        large = [u for u in us if u in big]
        return [normal[i:i + size] for i in range(0, len(normal), size)] + [[u] for u in large]
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("chunk_size") != size:
            LOG.warning(f"config 中 chunk_size = {size}，但已有分批方案 {path.name} 用的是 {manifest.get('chunk_size')}；"
                        f"为保证续跑判断有效，继续沿用已有分批（失败批次仍会自动拆半）。若还没有任何批次完成，"
                        f"可删除 {path.name} 后重跑以启用新的 chunk_size。")
    else:
        manifest = {"chunk_size": size, "chunks": pack(ids)}
        n_big = len(big & set(ids))
        if n_big:
            manifest["isolated_large_units"] = [u for u in ids if u in big]
            LOG.info(f"{n_big} 个面积超过 {thr_km2} km² 的大单元单独成批，排在普通批次之后")
        atomic_write_json(manifest, path)
        return manifest
    listed = {u for ch in manifest["chunks"] for u in ch}
    extra = [u for u in ids if u not in listed]
    if extra:
        LOG.warning(f"{len(extra)} 个单元不在已有分批方案中（可能重新运行过 00），追加为新批次：{extra[:5]} …")
        manifest["chunks"] += pack(extra)
        if big & set(extra):
            manifest["isolated_large_units"] = manifest.get("isolated_large_units", []) + [u for u in extra if u in big]
        atomic_write_json(manifest, path)
    return manifest


# ===========================================================================
# 代码块 10：合并全部批次
# 目的：把 chunks/ 下所有 *_unit.csv 与 *_core.geojson 合并为总表与总图层。
#       同一单元出现在多个文件中时，优先级为：全国正式运行 chunk_* > 批处理导出 export_* > 试跑 test_*；
#       试跑结果只补充尚未正式计算的单元；中心建成区多边形同样去重。
#       年度模式把各批宽表转成长表（unit_id、year 与各变量），同一单元年份变量按同样的优先级去重。
# 结果：gee_unit_metrics.csv、core_polygons_2020.geojson；年度模式 annual_long.csv。
# ===========================================================================
def _merge_rank(p: Path) -> int:
    if p.name.startswith("chunk_"):
        return 2
    if p.name.startswith("export_"):
        return 1
    return 0


def _merge_order(p: Path):
    """排序键：试跑文件在前、导出文件居中、正式文件在后，配合 keep='last' 让正式结果优先。"""
    return (_merge_rank(p), p.name)


def merge_all(out_dir: Path):
    ch = out_dir / "chunks"
    csvs = sorted(ch.glob("*_unit.csv"), key=_merge_order)
    if not csvs:
        LOG.warning("还没有任何已完成的批次。")
        return
    parts = []
    for p in csvs:
        d = read_table(p)
        parts.append(d.assign(_from_test=_merge_rank(p) == 0))
    df = pd.concat(parts, ignore_index=True)
    df = df.drop_duplicates("unit_id", keep="last").sort_values("unit_id")
    n_test = int(df["_from_test"].sum())
    df = df.drop(columns="_from_test")
    atomic_write_csv(df, out_dir / "gee_unit_metrics.csv")
    feats = {}
    for p in sorted(ch.glob("*_core.geojson"), key=_merge_order):
        for f in json.loads(p.read_text(encoding="utf-8"))["features"]:
            feats[str(f.get("properties", {}).get("unit_id"))] = f
    atomic_write_text(out_dir / "core_polygons_2020.geojson",
                      json.dumps({"type": "FeatureCollection", "features": list(feats.values())}, ensure_ascii=False))
    LOG.info(f"已合并 {len(csvs)} 个批次文件，共 {len(df)} 个单元 → gee_unit_metrics.csv")
    if n_test:
        LOG.warning(f"其中 {n_test} 个单元只有试跑（test_*）结果；若试跑后改过参数，请在全国运行完成后再使用这些行。")


def merge_annual(adir: Path):
    csvs = sorted((adir / "chunks").glob("*_unit.csv"), key=_merge_order)
    parts = []
    for rank, p in enumerate(csvs):
        d = read_table(p)
        cols = [c for c in d.columns if re.match(ANNUAL_RE, str(c))]
        if not cols:
            continue
        m = d.melt(id_vars="unit_id", value_vars=cols, var_name="col", value_name="value")
        ext = m["col"].astype(str).str.extract(ANNUAL_RE)
        parts.append(pd.DataFrame({"unit_id": m["unit_id"].astype(str), "year": ext[1].astype(int),
                                   "var": ext[0], "value": pd.to_numeric(m["value"], errors="coerce"),
                                   "_rank": rank}))
    if not parts:
        LOG.warning("年度模式还没有任何已完成的批次。")
        return
    df = (pd.concat(parts, ignore_index=True).sort_values("_rank", kind="stable")
          .drop_duplicates(["unit_id", "year", "var"], keep="last"))
    wide = df.pivot(index=["unit_id", "year"], columns="var", values="value").reset_index()
    wide.columns.name = None
    wide = wide[["unit_id", "year"] + [v for v in ANNUAL_VARS if v in wide.columns]].sort_values(["unit_id", "year"])
    atomic_write_csv(wide, adir / "annual_long.csv")
    LOG.info(f"已合并 {len(csvs)} 个年度批次文件：{wide['unit_id'].nunique()} 个单元、{len(wide)} 个单元年份 → annual_long.csv")


# ===========================================================================
# 代码块 11：批处理导出（--export-failed）与导出结果合并（--merge-exports）
# 目的：交互请求（getInfo）约 5 分钟超时，特大单元拆到单个仍可能失败。批处理任务没有这一限制：
#       对 failures.csv 中的每个单元，构建与正式运行相同的计算图，把 u_、c_、r_ 属性并到中心建成区要素上，
#       以 GeoJSON 导出到 Google Drive 的 export_folder 文件夹。提交后打印任务 ID，并每隔 1 分钟汇报一次状态。
#       已提交的任务记在 export_tasks.json：重新运行只继续查询，排队、运行中或已完成的任务不会重复提交，
#       失败或被取消的任务会重新提交。
#       研究者从 Drive 下载全部 GeoJSON 到本地文件夹后运行 --merge-exports，逐个文件转成 chunks/export_<单元>_unit.csv
#       与 _core.geojson（按文件汇报进度，可重复运行），从 failures.csv 中删去这些单元，再重新合并总表。
# 结果：Drive 中的 export_<单元>.geojson（准实验单元层为 did_export_<单元>.geojson）；本地 chunks/export_* 与更新后的总表。
# ===========================================================================
_ACTIVE = ("READY", "RUNNING", "CANCEL_REQUESTED")


def refresh_tasks(tasks: dict, uids: list):
    ids = [tasks[u]["id"] for u in uids]
    if not ids:
        return
    st = retry(lambda: ee.data.getTaskStatus(ids), tries=3, base_delay=10, logger=LOG, what="查询导出任务状态")
    for u, s in zip(uids, st):
        tasks[u]["state"] = s.get("state", "UNKNOWN")
        if s.get("error_message"):
            tasks[u]["error"] = s["error_message"]


def poll_tasks(tasks: dict, uids: list, tpath: Path):
    if not uids:
        return
    last = {u: tasks[u].get("state") for u in uids}
    try:
        while True:
            refresh_tasks(tasks, uids)
            atomic_write_json(tasks, tpath)
            for u in uids:
                s = tasks[u]["state"]
                if s != last[u] and s in ("COMPLETED", "FAILED", "CANCELLED"):
                    (LOG.info if s == "COMPLETED" else LOG.warning)(
                        f"单元 {u} 导出{'完成' if s == 'COMPLETED' else '失败：' + tasks[u].get('error', s)[:200]}")
                last[u] = s
            st = [tasks[u]["state"] for u in uids]
            n_act = sum(s in _ACTIVE for s in st)
            LOG.info(f"[导出任务] 完成 {st.count('COMPLETED')}/{len(uids)} | 运行中 {st.count('RUNNING')} | "
                     f"排队 {st.count('READY')} | 失败或取消 {len(uids) - n_act - st.count('COMPLETED')}")
            if n_act == 0:
                break
            time.sleep(EXPORT_POLL_S)
    except KeyboardInterrupt:
        LOG.info("已停止查询。任务仍在 GEE 服务器上运行；重新运行 --export-failed 会继续查询，已提交的任务不会重复提交。")


def export_failed(out_dir: Path, did: bool, cfg: dict, by_id: dict, make_fc, seats_for):
    g = cfg["gee"]
    fpath = out_dir / "failures.csv"
    if not fpath.exists():
        LOG.info("没有 failures.csv，无需导出。")
        return
    fl = read_table(fpath)
    uids = list(dict.fromkeys(fl["unit_id"].dropna().astype(str)))
    gone = [u for u in uids if u not in by_id]
    if gone:
        LOG.warning(f"{len(gone)} 个失败单元已不在当前单元表中，跳过：{gone[:5]}")
    chunk_dir = out_dir / "chunks"
    todo = [u for u in uids if u in by_id and not (chunk_dir / f"export_{u}_unit.csv").exists()]
    if not todo:
        LOG.info("failures.csv 中的单元都已有导出结果，无需导出。")
        return
    tpath = out_dir / "export_tasks.json"
    tasks = json.loads(tpath.read_text(encoding="utf-8")) if tpath.exists() else {}
    refresh_tasks(tasks, [u for u in todo if u in tasks])
    folder = g.get("export_folder") or "fdt_gee_exports"
    pre = "did_" if did else ""
    prog = ChunkProgress(len(todo), LOG, "导出提交")
    for i, uid in enumerate(todo):
        t = tasks.get(uid)
        if t and t.get("state") in _ACTIVE + ("COMPLETED",):
            prog.skip(i, f"{uid} 已提交过（任务 {t['id']}，状态 {t['state']}），不重复提交")
            continue
        prog.start(i, uid)
        try:
            fc = export_collection(build_chunk(make_fc([uid]), cfg, seats_for([uid])))
            task = ee.batch.Export.table.toDrive(collection=fc, description=f"fdt_{pre}{uid}", folder=folder,
                                                 fileNamePrefix=f"{pre}export_{uid}", fileFormat="GeoJSON")
            retry(task.start, tries=g["max_retries"] + 1, base_delay=g["retry_base_delay_s"], logger=LOG,
                  what=f"提交 {uid}")
        except KeyboardInterrupt:
            raise
        except Exception as e:  # noqa: BLE001
            LOG.error(f"单元 {uid} 的导出任务提交失败：{str(e)[:200]}")
            prog.finish(i, 0)
            continue
        tasks[uid] = {"id": task.id, "state": "READY", "file": f"{pre}export_{uid}.geojson",
                      "submitted": time.strftime("%Y-%m-%d %H:%M:%S")}
        atomic_write_json(tasks, tpath)
        LOG.info(f"已提交单元 {uid}：任务 ID {task.id}")
        prog.finish(i, 1)
    prog.summary()
    poll_tasks(tasks, [u for u in todo if u in tasks], tpath)
    n_ok = sum(tasks[u]["state"] == "COMPLETED" for u in todo if u in tasks)
    LOG.info(f"{n_ok} 个单元已导出到 Google Drive 的 {folder} 文件夹。请把其中的 {pre}export_*.geojson 全部下载到同一个本地文件夹，"
             f"再运行：python 01_gee_extract_rs.py{' --units did' if did else ''} --merge-exports <本地文件夹>")


def _polygons_of(geom: dict) -> list:
    """把 GeoJSON 几何拆成多边形坐标列表（Polygon、MultiPolygon、GeometryCollection）；其他类型忽略。"""
    if not geom:
        return []
    t = geom.get("type")
    if t == "Polygon":
        return [geom["coordinates"]]
    if t == "MultiPolygon":
        return list(geom["coordinates"])
    if t == "GeometryCollection":
        return [p for gg in geom.get("geometries", []) for p in _polygons_of(gg)]
    return []


def export_to_chunk(gj: dict, uid: str) -> tuple[dict, dict]:
    """一个导出文件 → (总表的一行, 中心建成区 FeatureCollection)。导出时若几何被切成多块，合并为一个多部件多边形。"""
    feats = gj.get("features") or ([gj] if gj.get("type") == "Feature" else [])
    if not feats:
        raise ValueError("文件中没有要素")
    props, polys = {}, []
    for f in feats:
        for k, v in (f.get("properties") or {}).items():
            if not str(k).startswith("system:"):
                props.setdefault(k, v)
        polys += _polygons_of(f.get("geometry"))
    got = str(props.get("unit_id", uid))
    if got != uid:
        LOG.warning(f"文件名中的单元 {uid} 与文件内的 unit_id {got} 不一致，以文件内为准")
    props["unit_id"] = got
    geom = (None if not polys else {"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
            else {"type": "MultiPolygon", "coordinates": polys})
    cprops = {k: v for k, v in props.items() if k == "unit_id" or str(k).startswith(("c_", "core"))}
    return props, {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": geom, "properties": cprops}]}


def merge_exports(folder: str, out_dir: Path, did: bool) -> int:
    folder = Path(folder).expanduser()
    if not folder.is_dir():
        LOG.error(f"找不到文件夹 {folder}。请先从 Google Drive 下载导出的 GeoJSON 文件。")
        sys.exit(1)
    pat = re.compile(r"^(did_)?export_([A-Za-z0-9]+)")
    found = {}
    for p in sorted(folder.iterdir()):
        m = pat.match(p.name)
        if p.suffix.lower() not in (".geojson", ".json") or not m or bool(m.group(1)) != did:
            continue
        uid = m.group(2)
        if uid not in found or p.stat().st_mtime > found[uid].stat().st_mtime:   # Drive 重名文件取最新的一个
            found[uid] = p
    if not found:
        LOG.warning(f"{folder} 中没有 {'did_' if did else ''}export_*.geojson 文件。")
        return 0
    chunk_dir = out_dir / "chunks"
    prog = ChunkProgress(len(found), LOG, "导出合并")
    ok = []
    for i, (uid, p) in enumerate(sorted(found.items())):
        prog.start(i, p.name)
        try:
            row, core = export_to_chunk(json.loads(p.read_text(encoding="utf-8")), uid)
        except Exception as e:  # noqa: BLE001
            LOG.error(f"{p.name} 无法读取：{str(e)[:200]}")
            prog.finish(i, 0)
            continue
        uid = row["unit_id"]
        atomic_write_text(chunk_dir / f"export_{uid}_core.geojson", json.dumps(core, ensure_ascii=False))
        atomic_write_csv(pd.DataFrame([row]), chunk_dir / f"export_{uid}_unit.csv")
        ok.append(uid)
        prog.finish(i, 1)
    prog.summary()
    fpath = out_dir / "failures.csv"
    if ok and fpath.exists():
        f = read_table(fpath)
        atomic_write_csv(f[~f["unit_id"].astype(str).isin(ok)], fpath)
    LOG.info(f"已转换 {len(ok)} 个导出文件 → chunks/export_*")
    return len(ok)


# ===========================================================================
# 代码块 12：主流程
# 目的：选定单元层（--units main / did）→ 读取分析单元 → 按模式分派：
#       合并（--merge-only、--merge-exports）、预检、批处理导出、年度模式或正式提取；
#       正式提取与年度模式都生成或读取分批方案 → 逐批计算（跳过已完成）→ 汇报进度 → 合并。
# 结果：见文件开头“输出”说明。
# ===========================================================================
def unit_set(cfg: dict, name: str) -> dict:
    ud = resolve(cfg["units"]["out_dir"])
    base = resolve(cfg["gee"]["out_dir"])
    if name == "did":
        return {"units": ud / "units_did_for_gee.geojson", "seats": ud / "seats_did.geojson",
                "table": ud / "units_did_table.csv", "out_dir": base / "did", "did": True}
    return {"units": ud / "units_for_gee.geojson", "seats": ud / "seats.geojson",
            "table": ud / "units_table.csv", "out_dir": base, "did": False}


def main():
    ap = argparse.ArgumentParser(description="用 Google Earth Engine 批量提取分析单元的遥感指标")
    ap.add_argument("--preflight", action="store_true", help="只检查 GEE 登录与数据集")
    ap.add_argument("--province", default=None, help="只跑某省（两位代码，如 44）")
    ap.add_argument("--limit", type=int, default=None, help="只跑前 N 个单元（试跑用）")
    ap.add_argument("--merge-only", action="store_true", help="只合并已有批次（与 --annual 同用时合并年度批次）")
    ap.add_argument("--units", choices=["main", "did"], default="main",
                    help="main = 分析单元（默认）；did = 每个 2020 年县级行政区一个单元（准实验用）")
    ap.add_argument("--annual", action="store_true", help="年度模式：固定 2020 年中心建成区，逐年提取 GAIA、VIIRS、Dynamic World")
    ap.add_argument("--export-failed", action="store_true", help="把 failures.csv 中的单元提交为批处理导出任务（Google Drive）")
    ap.add_argument("--merge-exports", metavar="本地文件夹", default=None,
                    help="把从 Drive 下载的导出 GeoJSON 转成批次文件并重新合并总表")
    args = ap.parse_args()

    cfg = load_config()
    g = cfg["gee"]
    uset = unit_set(cfg, args.units)
    out_dir = uset["out_dir"]
    did = uset["did"]
    (out_dir / "chunks").mkdir(parents=True, exist_ok=True)
    adir = out_dir / ((g.get("annual") or {}).get("out_subdir") or "annual")
    if args.merge_exports:
        merge_exports(args.merge_exports, out_dir, did)
        merge_all(out_dir)
        return
    if args.merge_only:
        if args.annual:
            (adir / "chunks").mkdir(parents=True, exist_ok=True)
            merge_annual(adir)
        else:
            merge_all(out_dir)
        return
    init_ee(g["project"], float(g.get("request_timeout_s", 600)))
    if args.preflight:
        preflight(cfg)
        return

    if not uset["units"].exists():
        LOG.error(f"找不到 {uset['units'].name}，请先运行 00_prepare_units.py"
                  + ("（config 中 units.write_did_units 须为 true）" if did else ""))
        sys.exit(1)
    gj = json.loads(uset["units"].read_text(encoding="utf-8"))
    feats = sorted(gj["features"], key=lambda f: str(f["properties"]["unit_id"]))
    for f in feats:
        f["properties"]["unit_id"] = str(f["properties"]["unit_id"])
    if args.province:
        feats = [f for f in feats
                 if str(f["properties"].get("prov_code") or f["properties"]["unit_id"][:2]).startswith(args.province)]
    if args.limit:
        feats = feats[: args.limit]
    by_id = {f["properties"]["unit_id"]: f for f in feats}

    # 单元几何来源：local = 每批从本地 GeoJSON 发送（默认，免上传）；asset = 读取已上传的 GEE 表格资产（更稳，推荐全国运行）
    asset_id = None
    if g.get("units_source", "local") == "asset":
        asset_id = g.get("units_did_asset") if did else g["units_asset"]
        if not asset_id:
            LOG.warning("--units did 没有对应的 GEE 表格资产（可在 config 的 gee 段加 units_did_asset），本次从本地 GeoJSON 发送几何")
    if asset_id:
        units_asset = ee.FeatureCollection(asset_id)

        def make_fc(ids):
            return units_asset.filter(ee.Filter.inList("unit_id", ids))
    else:
        def make_fc(ids):
            return ee.FeatureCollection([ee.Feature(by_id[u]) for u in ids if u in by_id])

    # 驻地点：每批只发送本批单元的驻地点（全国约 2 800 个点不必随每个请求发送）
    seat_by_id = {}
    if uset["seats"].exists():
        for f in json.loads(uset["seats"].read_text(encoding="utf-8")).get("features", []):
            seat_by_id.setdefault(str(f.get("properties", {}).get("unit_id")), []).append(f)

    def seats_for(ids):
        fs = [f for u in ids for f in seat_by_id.get(u, [])]
        return ee.FeatureCollection({"type": "FeatureCollection", "features": fs}) if fs else None

    if args.export_failed:
        if args.annual:
            LOG.error("--export-failed 只处理主模式的 failures.csv，不能与 --annual 同用；年度模式失败的单元请调小 "
                      "annual.dw_years_per_request 或 chunk_size 后重新运行 --annual。")
            sys.exit(1)
        export_failed(out_dir, did, cfg, by_id, make_fc, seats_for)
        return

    prefix = "chunk" if not (args.province or args.limit) else f"test_{args.province or 'all'}_{args.limit or 'all'}"
    size = int(g["chunk_size"])
    big = large_units(g, uset["table"])
    thr = g.get("large_unit_km2")
    ids_all = list(by_id)

    if args.annual:
        stopped = run_annual(cfg, adir, out_dir, prefix, ids_all, size, big, thr, make_fc, seats_for)
    else:
        manifest = plan_chunks(out_dir / f"{prefix}_manifest.json", ids_all, size, big, thr)
        jobs = [(f"{prefix}_{i:04d}", [u for u in ch if u in by_id],
                 lambda ids: run_chunk(make_fc(ids), cfg, seats_for(ids)), None, len(ch))
                for i, ch in enumerate(manifest["chunks"])]
        failures, stopped = run_jobs(jobs, cfg, out_dir / "chunks", "chunk")
        update_failures(out_dir / "failures.csv", failures, out_dir / "chunks", prefix)
        merge_all(out_dir)
    if stopped:
        sys.exit(1)


def run_annual(cfg, adir, out_dir, prefix, ids_all, size, big, thr, make_fc, seats_for) -> bool:
    """年度模式：读取固定的 2020 年中心建成区，按数据组 × 批次逐一计算，最后合并为长表。返回是否因连续失败而停止。"""
    g = cfg["gee"]
    cdir = adir / "chunks"
    cdir.mkdir(parents=True, exist_ok=True)
    groups = annual_groups(g)
    if not groups:
        LOG.error("config 的 gee.annual 中没有可用的年份（gaia_years、viirs_years、dw_years），年度模式无事可做。")
        return False
    core_path = out_dir / "core_polygons_2020.geojson"
    core_feats = {}
    if core_path.exists():
        for f in json.loads(core_path.read_text(encoding="utf-8")).get("features", []):
            uid = str((f.get("properties") or {}).get("unit_id"))
            if f.get("geometry"):
                core_feats[uid] = {"type": "Feature", "geometry": f["geometry"], "properties": {"unit_id": uid}}
    else:
        LOG.warning(f"找不到 {core_path.name}（请先完成正式运行并合并）。年度模式将在服务器端按同一规则重新识别中心建成区，"
                    "结果与主运行的中心建成区应一致，但每个请求更慢。")
    missing = [u for u in ids_all if u not in core_feats]
    if core_path.exists() and missing:
        LOG.warning(f"{len(missing)} 个单元不在 {core_path.name} 中（主运行失败或尚未运行），"
                    f"年度模式在服务器端重新识别其中心建成区：{missing[:5]} …")
    ds = DS(cfg)

    def make_cores(ids):
        have = [ee.Feature(core_feats[u]) for u in ids if u in core_feats]
        miss = [u for u in ids if u not in core_feats]
        fc = ee.FeatureCollection(have) if have else None
        if miss:
            built_ref, seats = ds.ghsl_s(g["green_year"]), seats_for(miss)
            re_fc = make_fc(miss).map(lambda u: ee.Feature(
                core_feature(u, built_ref, g["core"], seats).geometry(), {"unit_id": u.get("unit_id")}))
            fc = fc.merge(re_fc) if fc is not None else re_fc
        return fc

    manifest = plan_chunks(adir / f"{prefix}_manifest.json", ids_all, size, big, thr)
    idset = set(ids_all)
    jobs = []
    for gname, kind, years in groups:
        for i, ch in enumerate(manifest["chunks"]):
            jobs.append((f"{prefix}_{gname}_{i:04d}", [u for u in ch if u in idset],
                         lambda ids, kind=kind, years=years: fetch_annual(
                             build_annual(make_fc(ids), make_cores(ids), cfg, kind, years)),
                         gname, len(ch)))
    LOG.info("年度模式数据组：" + "；".join(f"{n}（{ys[0]}–{ys[-1]}）" for n, _, ys in groups)
             + f"；共 {len(manifest['chunks'])} 批 × {len(groups)} 组")
    failures, stopped = run_jobs(jobs, cfg, cdir, "annual", with_core=False)
    update_failures(adir / "failures.csv", failures, cdir, prefix, annual=True)
    merge_annual(adir)
    return stopped


if __name__ == "__main__":
    main()
