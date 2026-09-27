# -*- coding: utf-8 -*-
"""
tools/coord_gcj02_to_wgs84.py  把高德坐标 (GCJ-02) 或百度坐标 (BD-09) 转换为 WGS-84

为什么需要：高德、腾讯地图使用国测局加密坐标 GCJ-02，百度地图使用 BD-09。它们与 GEE 影像、OSM 和本项目边界使用的
WGS-84 相差约 300 至 700 m，足以把公园挪到街区之外。高德、百度的公园 AOI、学校医院 POI、政府驻地点
都要先用本工具转换，再填入 数据/原始 或上传 GEE。OSM 数据本身就是 WGS-84，不需要转换。

在哪里运行：Mac 终端 (Terminal)
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
  CSV 点表（默认自动识别 lon、lng、经度 与 lat、纬度 列，也可用 --lon-col、--lat-col 指定）：
    python tools/coord_gcj02_to_wgs84.py --from gcj02 输入.csv 输出.csv
    python tools/coord_gcj02_to_wgs84.py --from bd09 输入.csv 输出.csv --lon-col 经度 --lat-col 纬度
  高德接口返回的 location 列（经度和纬度写在同一格，用英文逗号隔开）：
    python tools/coord_gcj02_to_wgs84.py --from gcj02 poi.csv poi_wgs84.csv --xy-col location
  矢量文件（GeoJSON、GPKG、SHP；点、线、面及其多部件的全部顶点都会转换，GPKG 的每个图层都会转换）：
    python tools/coord_gcj02_to_wgs84.py --from gcj02 公园AOI.geojson 公园AOI_wgs84.gpkg
  自检（随机点往返转换，打印最大误差，单位为米）：
    python tools/coord_gcj02_to_wgs84.py --selftest

输出：
  CSV 输入得到 CSV（UTF-8，Excel 可直接打开）。原坐标列改写为 WGS-84，原值另存为 <列名>_gcj02 或 <列名>_bd09。
  矢量输入得到 GeoJSON、GPKG 或 SHP（按输出文件扩展名决定），坐标系标为 EPSG:4326，属性原样保留。
  终端打印每个 chunk 的进度，以及中国境内点数、平均移动距离、境外未转换点数。

方法：
  正变换用公开的标准公式（WGS-84 到 GCJ-02 的克拉索夫斯基椭球偏移公式，GCJ-02 到 BD-09 的百度偏移公式）。
  反变换没有解析解，用不动点迭代：猜测 w，计算正变换 f(w) 与目标坐标的差 d，令 w 减去 d，直到 d 小于 1e-7 度（约 1 cm）。
  只有落在中国范围矩形（经度 72.004 至 137.8347，纬度 0.8293 至 55.8271）内的点才转换，范围外的点原样保留。
  该矩形也覆盖蒙古、朝鲜半岛等邻国的一部分，本研究的数据都在国内，不受影响。
  港澳台的高德坐标是否加偏各数据源不一，本研究不使用这三地的单元。

大文件：CSV 按 --chunk-size 行一批读写，矢量按同样数目的要素一批读写，每批打印一行进度。
        结果先写到临时文件，全部完成后才改名为正式文件，中途中断不会留下半截文件；重新运行即可。
"""
from __future__ import annotations

import argparse
import codecs
import math
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ChunkProgress, get_logger, read_table  # noqa: E402

LOG = get_logger("coord_gcj02_to_wgs84")

# ---------------------------------------------------------------------------
# 代码块 1：正变换公式与常数
# 目的：实现 WGS-84 到 GCJ-02、GCJ-02 到 BD-09 的标准正变换（numpy 向量化，一次处理整批点）。
# 结果：wgs84_to_gcj02、gcj02_to_bd09、forward 三个函数，输入输出都是经度、纬度数组（单位为度）。
# ---------------------------------------------------------------------------
A_KRASOVSKY = 6378245.0                 # 克拉索夫斯基椭球长半轴 (m)
EE_KRASOVSKY = 0.00669342162296594323   # 克拉索夫斯基椭球第一偏心率平方
X_PI = math.pi * 3000.0 / 180.0         # 百度偏移公式中的常数
CHINA_BOX = (72.004, 137.8347, 0.8293, 55.8271)   # 经度下限、上限，纬度下限、上限
TOL_DEG = 1e-7                          # 反变换收敛阈值（度）
MAX_ITER = 30                           # 反变换最多迭代次数（通常 3 至 5 次即收敛）
EARTH_R = 6371008.8                     # 计算误差距离用的地球平均半径 (m)
SOURCES = ("gcj02", "bd09")


def _offset_lat(x, y):
    r = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * np.sqrt(np.abs(x))
    r += (20.0 * np.sin(6.0 * x * np.pi) + 20.0 * np.sin(2.0 * x * np.pi)) * 2.0 / 3.0
    r += (20.0 * np.sin(y * np.pi) + 40.0 * np.sin(y / 3.0 * np.pi)) * 2.0 / 3.0
    r += (160.0 * np.sin(y / 12.0 * np.pi) + 320.0 * np.sin(y * np.pi / 30.0)) * 2.0 / 3.0
    return r


def _offset_lon(x, y):
    r = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * np.sqrt(np.abs(x))
    r += (20.0 * np.sin(6.0 * x * np.pi) + 20.0 * np.sin(2.0 * x * np.pi)) * 2.0 / 3.0
    r += (20.0 * np.sin(x * np.pi) + 40.0 * np.sin(x / 3.0 * np.pi)) * 2.0 / 3.0
    r += (150.0 * np.sin(x / 12.0 * np.pi) + 300.0 * np.sin(x / 30.0 * np.pi)) * 2.0 / 3.0
    return r


def wgs84_to_gcj02(lon, lat):
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    dlat = _offset_lat(lon - 105.0, lat - 35.0)
    dlon = _offset_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * np.pi
    magic = 1.0 - EE_KRASOVSKY * np.sin(radlat) ** 2
    sqrtmagic = np.sqrt(magic)
    dlat = (dlat * 180.0) / ((A_KRASOVSKY * (1.0 - EE_KRASOVSKY)) / (magic * sqrtmagic) * np.pi)
    dlon = (dlon * 180.0) / (A_KRASOVSKY / sqrtmagic * np.cos(radlat) * np.pi)
    return lon + dlon, lat + dlat


def gcj02_to_bd09(lon, lat):
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    z = np.sqrt(lon * lon + lat * lat) + 0.00002 * np.sin(lat * X_PI)
    theta = np.arctan2(lat, lon) + 0.000003 * np.cos(lon * X_PI)
    return z * np.cos(theta) + 0.0065, z * np.sin(theta) + 0.006


def forward(lon, lat, src: str):
    """WGS-84 到 src（gcj02 或 bd09）的正变换。"""
    gx, gy = wgs84_to_gcj02(lon, lat)
    return (gx, gy) if src == "gcj02" else gcj02_to_bd09(gx, gy)


def in_china(lon, lat):
    lo0, lo1, la0, la1 = CHINA_BOX
    return np.isfinite(lon) & np.isfinite(lat) & (lon >= lo0) & (lon <= lo1) & (lat >= la0) & (lat <= la1)


# ---------------------------------------------------------------------------
# 代码块 2：迭代反变换
# 目的：给定 GCJ-02 或 BD-09 坐标 t，求 WGS-84 坐标 w，使 forward(w) 与 t 之差小于 1e-7 度。
#       中国范围外的点、缺失值原样返回。
# 结果：返回 (经度数组, 纬度数组, 统计字典)。统计字典含境内点数、境外点数、未收敛点数与平均移动距离（米）。
# ---------------------------------------------------------------------------
def haversine_m(lon1, lat1, lon2, lat2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * EARTH_R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def to_wgs84(lon, lat, src: str):
    lon = np.asarray(lon, dtype=float).copy()
    lat = np.asarray(lat, dtype=float).copy()
    finite = np.isfinite(lon) & np.isfinite(lat)
    m = in_china(lon, lat)
    stats = {"n_in": int(m.sum()), "n_out": int((finite & ~m).sum()), "n_nan": int((~finite).sum()),
             "n_bad": 0, "shift_sum_m": 0.0}
    if not m.any():
        return lon, lat, stats
    tx, ty = lon[m], lat[m]
    wx, wy = tx.copy(), ty.copy()
    for _ in range(MAX_ITER):
        fx, fy = forward(wx, wy, src)
        dx, dy = fx - tx, fy - ty
        if max(np.abs(dx).max(), np.abs(dy).max()) < TOL_DEG:
            break
        wx -= dx
        wy -= dy
    fx, fy = forward(wx, wy, src)
    stats["n_bad"] = int((np.maximum(np.abs(fx - tx), np.abs(fy - ty)) >= TOL_DEG).sum())
    stats["shift_sum_m"] = float(haversine_m(tx, ty, wx, wy).sum())
    lon[m], lat[m] = wx, wy
    return lon, lat, stats


def add_stats(total: dict, part: dict) -> None:
    for k, v in part.items():
        total[k] = total.get(k, 0) + v


def report_stats(total: dict, src: str) -> None:
    n_in = total.get("n_in", 0)
    mean = total.get("shift_sum_m", 0.0) / n_in if n_in else float("nan")
    LOG.info(f"坐标统计：中国境内 {n_in} 个点已从 {src} 转为 WGS-84，平均移动 {mean:.0f} m。"
             f"境外 {total.get('n_out', 0)} 个点原样保留，缺失 {total.get('n_nan', 0)} 个。")
    if total.get("n_bad"):
        LOG.warning(f"{total['n_bad']} 个点迭代 {MAX_ITER} 次仍未收敛到 {TOL_DEG} 度，请检查这些坐标是否有误。")
    if n_in and mean < 50:
        LOG.warning("平均移动不到 50 m，与 GCJ-02、BD-09 的典型偏移（300 至 700 m）不符。请确认输入确实是加密坐标，"
                    "已是 WGS-84 的数据再转一次反而会产生偏移。")


# ---------------------------------------------------------------------------
# 代码块 3：CSV 表格（分批读写）
# 目的：逐批读取 CSV，改写经纬度列，原值另存一列，其余列按原文本写出（不改动代码前导零、电话号码等）。
#       编码识别与 common.read_table 相同（先 UTF-8，失败再 GB18030）。这里不直接调用 read_table，
#       因为它一次读入整个文件，并会把非代码列转成数字；大文件需要分批，其他列需要原样保留。
#       xlsx 输入较小，直接用 read_table 读入后同样分批处理。
# 结果：输出 CSV（UTF-8 带 BOM），先写临时文件，全部完成后改名。
# ---------------------------------------------------------------------------
LON_CANDIDATES = ("lon", "lng", "longitude", "long", "x", "经度", "wgs_lon")
LAT_CANDIDATES = ("lat", "latitude", "y", "纬度", "wgs_lat")


def detect_encoding(path: Path) -> str:
    dec = codecs.getincrementaldecoder("utf-8-sig")()
    try:
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                dec.decode(block)
        dec.decode(b"", final=True)
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "gb18030"


def count_lines(path: Path) -> int:
    n = 0
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            n += block.count(b"\n")
    return n


def pick_col(cols, given, cands, what):
    if given:
        if given not in cols:
            raise SystemExit(f"找不到{what}列 {given}，现有列为 {list(cols)}")
        return given
    low = {str(c).strip().lower(): c for c in cols}
    for c in cands:
        if c in low:
            return low[c]
    raise SystemExit(f"没有自动识别到{what}列，请用 --lon-col、--lat-col 或 --xy-col 指定。现有列为 {list(cols)}")


def iter_table_chunks(path: Path, chunk: int):
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = read_table(path).astype("string")   # 读入后转为文本，与 CSV 分支一致
        for i in range(0, max(len(df), 1), chunk):
            yield df.iloc[i:i + chunk].copy()
        return
    enc = detect_encoding(path)
    LOG.info(f"{path.name} 的编码识别为 {'UTF-8' if enc == 'utf-8-sig' else 'GB18030（GBK）'}")
    yield from pd.read_csv(path, encoding=enc, dtype=str, keep_default_na=False, chunksize=chunk)


def convert_table(src: Path, dst: Path, frm: str, chunk: int, lon_col=None, lat_col=None, xy_col=None):
    if dst.suffix.lower() != ".csv":
        raise SystemExit("表格只输出 CSV，请把输出文件名改为 .csv")
    n_rows = count_lines(src) - 1 if src.suffix.lower() == ".csv" else None
    n_chunks = max(1, math.ceil(n_rows / chunk)) if n_rows else 1
    prog = ChunkProgress(n_chunks, LOG, label="chunk")
    tmp = dst.with_name(dst.name + ".tmp")
    dst.parent.mkdir(parents=True, exist_ok=True)
    total: dict = {}
    first = True
    for i, df in enumerate(iter_table_chunks(src, chunk)):
        prog.total = max(prog.total, i + 1)
        prog.start(i, f"读取 {len(df)} 行")
        if xy_col:
            if xy_col not in df.columns:
                raise SystemExit(f"找不到 {xy_col} 列，现有列为 {list(df.columns)}")
            parts = df[xy_col].astype("string").str.split(",", n=1, expand=True).reindex(columns=[0, 1])
            lon = pd.to_numeric(parts[0], errors="coerce").to_numpy(dtype=float)
            lat = pd.to_numeric(parts[1], errors="coerce").to_numpy(dtype=float)
            wx, wy, st = to_wgs84(lon, lat, frm)
            df[f"{xy_col}_{frm}"] = df[xy_col]
            ok = np.isfinite(wx) & np.isfinite(wy)
            df[xy_col] = np.where(ok, [f"{a:.7f},{b:.7f}" for a, b in zip(wx, wy)], df[xy_col].astype(object))
            # 另加数值型 lon、lat 两列（已有同名列时不覆盖），便于直接作为驻地点表或上传 GEE
            for name, arr in (("lon", wx), ("lat", wy)):
                if name not in df.columns:
                    df[name] = np.round(arr, 7)
        else:
            lc = pick_col(df.columns, lon_col, LON_CANDIDATES, "经度")
            ac = pick_col(df.columns, lat_col, LAT_CANDIDATES, "纬度")
            lon = pd.to_numeric(df[lc], errors="coerce").to_numpy(dtype=float)
            lat = pd.to_numeric(df[ac], errors="coerce").to_numpy(dtype=float)
            wx, wy, st = to_wgs84(lon, lat, frm)
            df[f"{lc}_{frm}"] = df[lc]
            df[f"{ac}_{frm}"] = df[ac]
            ok = np.isfinite(wx) & np.isfinite(wy)
            df[lc] = np.where(ok, np.round(wx, 7).astype(object), df[lc].astype(object))
            df[ac] = np.where(ok, np.round(wy, 7).astype(object), df[ac].astype(object))
        add_stats(total, st)
        df.to_csv(tmp, index=False, mode="w" if first else "a", header=first,
                  encoding="utf-8-sig" if first else "utf-8")
        first = False
        prog.finish(i, None)
    os.replace(tmp, dst)
    report_stats(total, frm)
    LOG.info(f"已写出 {dst}")


# ---------------------------------------------------------------------------
# 代码块 4：矢量文件（分批读写，全部顶点转换）
# 目的：用 pyogrio 按要素分批读取，shapely.transform 对每个几何的全部顶点（外环、内环、多部件、几何集合）做反变换，
#       再追加写入输出文件。GPKG 输入的每个图层都会转换；输出为 GeoJSON 或 SHP 时只能有一个图层。
# 结果：输出矢量文件，坐标系 EPSG:4326。先写到临时文件夹，全部完成后移到正式位置。
# ---------------------------------------------------------------------------
VECTOR_DRIVERS = {".gpkg": "GPKG", ".geojson": "GeoJSON", ".json": "GeoJSON", ".shp": "ESRI Shapefile"}


def transform_geoms(geoms, frm: str, total: dict):
    import shapely

    def fn(coords):
        x, y, st = to_wgs84(coords[:, 0], coords[:, 1], frm)
        add_stats(total, st)
        out = coords.copy()
        out[:, 0], out[:, 1] = x, y
        return out

    arr = np.asarray(geoms, dtype=object)
    out = np.empty(len(arr), dtype=object)
    has_z = shapely.has_z(arr)
    if (~has_z).any():
        out[~has_z] = shapely.transform(arr[~has_z], fn, include_z=False)
    if has_z.any():
        out[has_z] = shapely.transform(arr[has_z], fn, include_z=True)
    return out


def convert_vector(src: Path, dst: Path, frm: str, chunk: int, encoding: str | None):
    try:
        import geopandas as gpd
        import pyogrio
    except ImportError:
        raise SystemExit("矢量转换需要 geopandas 与 pyogrio，请先运行 pip install -r requirements.txt")
    driver = VECTOR_DRIVERS.get(dst.suffix.lower())
    if driver is None:
        raise SystemExit(f"不支持的输出格式 {dst.suffix}，请用 .gpkg、.geojson 或 .shp")
    layers = [str(x[0]) for x in pyogrio.list_layers(src)]
    if len(layers) > 1 and driver != "GPKG":
        raise SystemExit(f"{src.name} 有 {len(layers)} 个图层，输出只能用 .gpkg 才能保留全部图层")
    read_kw = {"encoding": encoding} if encoding else {}
    infos = []
    for lyr in layers:
        info = pyogrio.read_info(src, layer=lyr, **read_kw)
        crs = info.get("crs")
        if crs:
            from pyproj import CRS
            if not CRS.from_user_input(crs).is_geographic:
                raise SystemExit(f"图层 {lyr} 是投影坐标（{crs}），GCJ-02、BD-09 只有经纬度形式，请确认数据来源")
        infos.append((lyr, int(info.get("features") or 0)))
    n_chunks = sum(max(1, math.ceil(n / chunk)) for _, n in infos)
    prog = ChunkProgress(n_chunks, LOG, label="chunk")
    tmpdir = dst.parent / f".{dst.name}.tmpdir"
    shutil.rmtree(tmpdir, ignore_errors=True)
    tmpdir.mkdir(parents=True)
    tmp = tmpdir / dst.name
    total: dict = {}
    k = 0
    for li, (lyr, n) in enumerate(infos):
        for j, start in enumerate(range(0, max(n, 1), chunk)):
            prog.start(k, f"图层 {lyr} 第 {start + 1} 至 {min(start + chunk, n)} 个要素")
            gdf = pyogrio.read_dataframe(src, layer=lyr, skip_features=start, max_features=chunk, **read_kw)
            if len(gdf):
                gdf = gpd.GeoDataFrame(gdf.drop(columns="geometry"),
                                       geometry=transform_geoms(gdf.geometry.values, frm, total), crs=4326)
            else:
                gdf = gdf.set_crs(4326, allow_override=True)
            kw = {"encoding": "UTF-8"} if driver == "ESRI Shapefile" else {}
            # 每个图层的第一批新建图层（GPKG 的后续图层加到同一文件中），之后各批追加
            pyogrio.write_dataframe(gdf, tmp, layer=lyr if driver == "GPKG" else None, driver=driver,
                                    append=j > 0, **kw)
            prog.finish(k, None)
            k += 1
    for f in tmpdir.iterdir():
        os.replace(f, dst.parent / f.name)
    shutil.rmtree(tmpdir, ignore_errors=True)
    report_stats(total, frm)
    LOG.info(f"已写出 {dst}（{len(infos)} 个图层，{sum(n for _, n in infos)} 个要素）")


# ---------------------------------------------------------------------------
# 代码块 5：自检
# 目的：确认正变换与公开参考值一致，反变换往返误差小于 0.5 m，中国范围外的点不被改动，几何的全部顶点都被转换。
# 结果：终端逐项打印结果；全部通过时退出码为 0，否则为 1。
# ---------------------------------------------------------------------------
def selftest(n: int = 200000) -> bool:
    ok = True
    # 5a. 参考值：GCJ-02 与 BD-09 正变换的常用参考结果（北京天安门附近 116.404, 39.915）
    gx, gy = wgs84_to_gcj02(116.404, 39.915)
    bx, by = gcj02_to_bd09(116.404, 39.915)
    ref = [("WGS-84 到 GCJ-02", (gx, gy), (116.41024449916938, 39.91640428150164)),
           ("GCJ-02 到 BD-09", (bx, by), (116.41036949371029, 39.92133699351021))]
    for name, got, exp in ref:
        d = float(haversine_m(got[0], got[1], exp[0], exp[1]))
        passed = d < 0.01
        ok &= passed
        print(f"[{'通过' if passed else '失败'}] {name} 参考值偏差 {d:.4f} m")
    # 5b. 随机点往返：WGS-84 → 正变换 → 本工具反变换 → 与原点比较
    rng = np.random.default_rng(20260926)
    lon = rng.uniform(73.5, 135.0, n)
    lat = rng.uniform(18.0, 53.5, n)
    for src in SOURCES:
        fx, fy = forward(lon, lat, src)
        wx, wy, st = to_wgs84(fx, fy, src)
        err = haversine_m(lon, lat, wx, wy)
        shift = haversine_m(lon, lat, fx, fy)
        passed = float(err.max()) < 0.5 and st["n_bad"] == 0
        ok &= passed
        print(f"[{'通过' if passed else '失败'}] {src} 往返 {n} 个随机点：最大误差 {err.max():.2e} m，"
              f"平均误差 {err.mean():.2e} m，未收敛 {st['n_bad']} 个（原始偏移 {shift.min():.0f} 至 {shift.max():.0f} m）")
    # 5c. 中国范围外的点保持不变（东京、柏林、悉尼），缺失值保持缺失
    ox = np.array([139.69, 13.40, 151.21, np.nan])
    oy = np.array([35.69, 52.52, -33.87, 30.0])
    wx, wy, _ = to_wgs84(ox, oy, "gcj02")
    passed = np.allclose(wx[:3], ox[:3]) and np.allclose(wy[:3], oy[:3]) and np.isnan(wx[3])
    ok &= passed
    print(f"[{'通过' if passed else '失败'}] 中国范围外的点与缺失值原样保留")
    # 5d. 几何：带内环的面与多线，全部顶点都被转换，顶点数不变
    try:
        import shapely
        from shapely.geometry import MultiLineString, Polygon
        poly = Polygon([(113.2, 23.1), (113.3, 23.1), (113.3, 23.2), (113.2, 23.2)],
                       [[(113.24, 23.14), (113.26, 23.14), (113.26, 23.16)]])
        mls = MultiLineString([[(113.2, 23.1), (113.25, 23.15)], [(116.3, 39.9), (116.4, 39.95), (116.5, 39.9)]])
        tot: dict = {}
        out = transform_geoms([poly, mls, None], "gcj02", tot)
        c_in = np.vstack([shapely.get_coordinates(g) for g in (poly, mls)])
        c_out = np.vstack([shapely.get_coordinates(g) for g in out[:2]])
        wx, wy, _ = to_wgs84(c_in[:, 0], c_in[:, 1], "gcj02")
        passed = (c_in.shape == c_out.shape and np.allclose(c_out[:, 0], wx) and np.allclose(c_out[:, 1], wy)
                  and out[2] is None and len(out[0].interiors) == 1)
        ok &= passed
        print(f"[{'通过' if passed else '失败'}] 几何顶点转换：{len(c_in)} 个顶点（含内环与多部件）全部转换，空几何保留")
    except ImportError:
        print("[跳过] 没有安装 shapely，未检查几何顶点转换")
    print("自检全部通过。" if ok else "自检有失败项，请把以上输出发给合作者。")
    return ok


# ---------------------------------------------------------------------------
# 代码块 6：命令行入口
# 目的：按输入文件扩展名选择表格或矢量分支。
# 结果：写出转换后的文件；--selftest 只做自检。
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="GCJ-02 / BD-09 坐标转 WGS-84")
    ap.add_argument("--from", dest="frm", choices=SOURCES, help="输入坐标系：gcj02（高德、腾讯）或 bd09（百度）")
    ap.add_argument("input", nargs="?", help="输入文件：.csv、.xlsx、.geojson、.gpkg 或 .shp")
    ap.add_argument("output", nargs="?", help="输出文件：表格输入用 .csv；矢量输入用 .gpkg、.geojson 或 .shp")
    ap.add_argument("--lon-col", help="经度列名（CSV）")
    ap.add_argument("--lat-col", help="纬度列名（CSV）")
    ap.add_argument("--xy-col", help="经纬度写在同一格的列名，如高德的 location（经度,纬度）")
    ap.add_argument("--chunk-size", type=int, default=100000, help="每批行数或要素数（默认 100000）")
    ap.add_argument("--encoding", help="SHP 输入没有 .cpg 文件且中文乱码时指定，如 GBK")
    ap.add_argument("--selftest", action="store_true", help="只运行自检")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if not (args.frm and args.input and args.output):
        ap.error("需要 --from、输入文件与输出文件三项（或只用 --selftest）")
    src, dst = Path(args.input).expanduser().resolve(), Path(args.output).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"找不到输入文件：{src}")
    if src == dst:
        raise SystemExit("输出文件不能与输入文件相同，请另起文件名（例如加 _wgs84 后缀）")
    LOG.info(f"开始转换 {src.name}（{args.frm} → WGS-84），每批 {args.chunk_size}")
    if src.suffix.lower() in (".csv", ".txt", ".xlsx", ".xls"):
        convert_table(src, dst, args.frm, args.chunk_size, args.lon_col, args.lat_col, args.xy_col)
    else:
        convert_vector(src, dst, args.frm, args.chunk_size, args.encoding)


if __name__ == "__main__":
    main()
