# -*- coding: utf-8 -*-
"""
tools/build_osm_parks_greenways.py  下载 OpenStreetMap 中国数据，提取公园、绿道与河道，按省打包供 GEE 上传

为什么需要：遥感只能识别植被，不能识别公园这种管理属性。报告中公园和绿道两个词只用于矢量数据，
01_gee_extract_rs.py 的 park_asset（公园面）、greenway_asset（绿道线）、river_asset（河道面）都需要先上传矢量资产。
本脚本把 OSM 全国数据整理成这三类要素，并按省打成 GEE 可以直接上传的 Shapefile 压缩包。
OSM 坐标就是 WGS-84，不需要做坐标转换（高德、百度数据才需要 tools/coord_gcj02_to_wgs84.py）。

在哪里运行：Mac 终端 (Terminal)
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python tools/build_osm_parks_greenways.py                   # 全流程：下载、提取、按省打包；可随时 Ctrl+C，重新运行会续跑
    python tools/build_osm_parks_greenways.py --download-only   # 只下载（约 1 GB 以上，断点续传）
    python tools/build_osm_parks_greenways.py --province 44     # 只打包广东（试点用），可写多个：--province 44,45
    python tools/build_osm_parks_greenways.py --national        # 另外打一个全国压缩包（全国运行时上传这个）
    python tools/build_osm_parks_greenways.py --pbf ~/Downloads/china-latest.osm.pbf   # 用已下载的文件，跳过下载
    python tools/build_osm_parks_greenways.py --refresh         # 重新下载最新数据并重新提取（Geofabrik 每天更新）

下载：默认地址 https://download.geofabrik.de/asia/china-latest.osm.pbf。先写到 .part 文件，每 20 MB 打印一次进度；
      断网或中断后重新运行，从 .part 的末尾继续（HTTP Range）。若服务器上的文件在中断期间已更新，自动从头下载，
      避免把新旧两个版本拼在一起。下载完成后用网站发布的 .md5 校验，不一致会重新下载。
      请不要在一天内反复下载同一文件，Geofabrik 对频繁下载会限速。

提取工具（二选一，脚本自动选择，也可用 --engine cli 或 --engine pyosmium 指定）：
  A. osmium-tool 命令行（推荐，快）。Mac 安装方法：先装 Homebrew（brew.sh），再运行 brew install osmium-tool。
     脚本先用 osmium tags-filter 从全国文件中筛出相关要素（一次读完整个文件），再用 osmium export 导出为
     GeoJSONSeq（每行一个要素），最后逐行读入并按下面的规则分类。
  B. pyosmium（Python 包，安装方法 pip install osmium）。没有 osmium-tool 时使用。节点坐标索引写在磁盘文件上
     （sparse_file_array），内存占用小，全国数据需要数 GB 硬盘空间。比 A 慢，全国数据未实测耗时。

提取规则：
  公园 parks（面）     leisure=park；以及 leisure=garden 且名称含公园二字
  绿道 greenways（线） 名称含绿道或碧道（rule=name）；highway=cycleway（rule=cycleway）；
                       route=bicycle 或名称含绿道、碧道的路线关系中直接列出的 way 成员（rule=route，嵌套关系不展开）
  河道 rivers（面）    waterway=riverbank；natural=water 且 water=river 或 canal
  每个要素保留 osm_id、name、rule、leisure、highway、waterway、natural、water、access、route_nm（所属路线名称），
  另计算 area_m2（面）或 length_m（线），在中国 Albers 等积投影下计算。access=private 的公园多为小区内部绿地，
  需要区分公共与俱乐部绿地时可按 access 列筛选。没有 highway 标签的面状地物轮廓（如名称含绿道的公园边界）不算绿道线。
  边界自相交、缺节点的面，osmium 无法组装成面，会被跳过（两种提取工具相同），数量通常很少。

输出（数据/中间/osm/）：
  download/china-latest.osm.pbf         下载的原始数据（.part 为未完成部分）
  work/                                 中间文件（筛选后的 pbf、GeoJSONSeq、节点索引、省界），可删除
  osm_parks_greenways.gpkg              图层 parks、greenways、rivers（全国，WGS-84）
  osm_province_summary.csv              各省公园个数与面积、绿道条数与长度、河道面积，用于判断 OSM 完整度
  gee_upload/44_parks.zip 等            各省 Shapefile 压缩包；每个要素按代表点（面）或中点（线）只归入一个省，
                                        各省合并后不会重复计数。--national 时另有 all_parks.zip 等全国包
  省的范围取自 数据/中间/units/units_full.gpkg 的 prov_code（先运行 00_prepare_units.py）；没有该文件时只输出全国包。

上传 GEE：Code Editor 左侧 Assets，NEW，Shape files，选中压缩包上传。完成后把资产路径填入 外部参数/config.yaml 的
  gee.park_asset、gee.greenway_asset、gee.river_asset（试点用广东的包，全国运行用 --national 的全国包）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (ChunkProgress, atomic_write_csv, atomic_write_json, atomic_write_text,  # noqa: E402
                    get_logger, load_config, resolve)

LOG = get_logger("build_osm_parks_greenways")

DEFAULT_URL = "https://download.geofabrik.de/asia/china-latest.osm.pbf"
CHINA_ALBERS = "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
GREEN_NAMES = ("绿道", "碧道")
LAYERS = {"parks": "MultiPolygon", "greenways": "LineString", "rivers": "MultiPolygon"}
FIELDS = ["osm_id", "name", "rule", "leisure", "highway", "waterway", "natural", "water", "access", "route_nm"]
TAG_FIELDS = ["leisure", "highway", "waterway", "natural", "water", "access"]
# osmium tags-filter 表达式：一次读完全国文件，筛出三类要素的候选（含所引用的节点与成员）
FILTER_EXPRS = ["wr/leisure=park,garden", "wr/waterway=riverbank", "wr/natural=water",
                "w/highway=cycleway", "w/name=*绿道*", "w/name=*碧道*",
                "r/route=bicycle", "r/name=*绿道*", "r/name=*碧道*"]


# ===========================================================================
# 代码块 1：断点续传下载
# 目的：把大文件先写到 .part，每下载 chunk_mb 打印一次进度；网络中断时按指数退避重试，并从 .part 末尾续传。
#       续传请求带 If-Range（ETag 或 Last-Modified），服务器上的文件变了会整份重发，脚本随之从头下载，
#       不会把两个版本拼在一起。下载完成后与网站发布的 .md5 比对。
# 结果：dest 位置出现完整且校验通过的文件；dest.md5 记录校验值。
# ===========================================================================
def _requests():
    try:
        import requests
        return requests
    except ImportError:
        raise SystemExit("下载需要 requests 包，请先运行：pip install requests")


def fetch_md5(session, url: str, timeout: int = 60) -> str | None:
    try:
        r = session.get(url, timeout=timeout)
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001  md5 取不到时照常下载，只是不能校验
        LOG.warning(f"没有取到校验文件 {url}（{str(e)[:120]}），下载后不做 MD5 校验")
        return None
    m = re.search(r"\b([0-9a-fA-F]{32})\b", r.text)
    return m.group(1).lower() if m else None


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def _validator(headers) -> str | None:
    """If-Range 只能用强 ETag；弱 ETag（W/ 开头）时改用 Last-Modified。"""
    etag = headers.get("ETag")
    if etag and not etag.startswith("W/"):
        return etag
    return headers.get("Last-Modified")


def download(url: str, dest: Path, chunk_mb: float = 20, tries: int = 8, base_delay: float = 10,
             verify_md5: bool = True, max_rounds: int = 2) -> Path:
    requests = _requests()
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    meta_path = dest.with_name(dest.name + ".part.json")
    session = requests.Session()
    session.headers["User-Agent"] = "county_city_fiscal_dual_track/1.0 (research; resumable download)"
    chunk_bytes = int(chunk_mb * 1024 * 1024)

    for _ in range(max_rounds):
        # 1a. 远端文件信息（大小与版本标识）。只采用成功的响应：出错页面（如 503）的大小与版本标识
        #     和已下载部分对不上，若拿来比较会误判“服务器文件已更新”而删掉 .part
        head = None
        for k in range(tries):
            try:
                resp = session.head(url, allow_redirects=True, timeout=60)
                if resp.status_code in (405, 501):      # 服务器不支持 HEAD：用 GET 只取响应头
                    resp = session.get(url, stream=True, timeout=60)
                    resp.close()
                resp.raise_for_status()
                head = resp
                break
            except requests.RequestException as e:
                last = k == tries - 1
                wait = min(base_delay * 2 ** k, 300)
                LOG.warning(f"查询远端文件第 {k + 1}/{tries} 次失败：{str(e)[:150]}" + ("" if last else f"；{wait:.0f}s 后重试"))
                if not last:
                    time.sleep(wait)
        if head is None:
            raise SystemExit("多次重试仍无法连接下载服务器。请检查网络或代理后重新运行，已下载部分会保留。")
        total = int(head.headers.get("Content-Length") or 0) or None
        validator = _validator(head.headers)
        md5_expected = fetch_md5(session, url + ".md5") if verify_md5 else None

        # 1b. 已有 .part 但远端文件已变化：从头下载
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except ValueError:
                meta = {}
        if part.exists() and (meta.get("url") != url or (validator and meta.get("validator") != validator)
                              or (total and meta.get("total") and meta.get("total") != total)):
            LOG.info("服务器上的文件在上次下载后已更新，已下载部分作废，从头开始下载")
            part.unlink()
        atomic_write_json({"url": url, "validator": validator, "total": total, "md5": md5_expected}, meta_path)

        # 1c. 分段下载，失败重试并续传
        have = part.stat().st_size if part.exists() else 0
        if have:
            LOG.info(f"发现未完成的下载，已有 {have / 2**20:.0f} MB，从断点继续")
        fails, t0, last_report = 0, time.time(), have
        t_last = time.time()
        while True:
            have = part.stat().st_size if part.exists() else 0
            if total and have > total:                   # .part 比远端文件还大，说明已损坏
                LOG.warning("已下载部分比服务器上的文件还大，从头下载")
                part.unlink()
                continue
            if total and have == total:
                break
            headers = {}
            if have:
                headers["Range"] = f"bytes={have}-"
                if validator:
                    headers["If-Range"] = validator
            start_have = have
            try:
                with session.get(url, headers=headers, stream=True, timeout=(30, 120)) as r:
                    if r.status_code == 416:            # 请求的起点超出文件末尾：.part 已完整或比远端还长
                        if total and have == total:
                            break
                        LOG.warning("断点位置与服务器文件大小不符，从头下载")
                        part.unlink()
                        continue
                    r.raise_for_status()
                    if have and r.status_code == 200:
                        LOG.info("服务器返回了完整文件（不支持续传或文件已更新），从头下载")
                        have = 0
                        last_report = 0
                    if r.status_code == 200:
                        total = int(r.headers.get("Content-Length") or 0) or total
                        # 文件已更新时，后续续传的 If-Range 要用新版本的标识，否则每次中断后都会从头再来
                        validator = _validator(r.headers) or validator
                        atomic_write_json({"url": url, "validator": validator, "total": total, "md5": md5_expected},
                                          meta_path)
                    mode = "ab" if r.status_code == 206 else "wb"
                    with open(part, mode) as f:
                        for block in r.iter_content(chunk_size=1 << 20):
                            if not block:
                                continue
                            f.write(block)
                            have += len(block)
                            if have - last_report >= chunk_bytes:
                                f.flush()
                                now = time.time()
                                speed = (have - last_report) / max(now - t_last, 1e-6) / 2**20
                                pct = f"{100 * have / total:.1f}%" if total else "总大小未知"
                                eta = f" | 预计剩余 {(total - have) / 2**20 / max(speed, 1e-6) / 60:.1f} min" if total else ""
                                LOG.info(f"[下载] {have / 2**20:.0f} / {(total or 0) / 2**20:.0f} MB（{pct}）"
                                         f" | 本段 {speed:.1f} MB/s{eta}")
                                last_report, t_last = have, now
                if not total:
                    break                                # 服务器不告诉大小时，一次读完即结束
                if have <= start_have:
                    raise OSError("服务器没有返回任何数据")
            except (requests.RequestException, OSError) as e:
                have = part.stat().st_size if part.exists() else 0
                fails = 1 if have > start_have else fails + 1   # 本次有进展则重新计数
                if fails > tries:
                    raise SystemExit(f"连续 {tries} 次下载失败，已保存 {have / 2**20:.0f} MB。"
                                     "请检查网络后重新运行本脚本，会从断点继续。")
                wait = min(base_delay * 2 ** (fails - 1), 300)
                LOG.warning(f"下载中断（{str(e)[:150]}），已有 {have / 2**20:.0f} MB；{wait:.0f}s 后第 {fails}/{tries} 次重试")
                time.sleep(wait)
        LOG.info(f"下载完成：{part.stat().st_size / 2**20:.0f} MB，用时 {(time.time() - t0) / 60:.1f} min")

        # 1d. MD5 校验。校验值不符时再取一次 .md5（下载期间网站可能已更新），仍不符则删除重下
        if md5_expected:
            LOG.info("正在计算 MD5 校验值")
            got = file_md5(part)
            if got != md5_expected:
                again = fetch_md5(session, url + ".md5")
                if again and got == again:
                    md5_expected = again
                else:
                    LOG.warning(f"MD5 不一致（本地 {got}，网站 {again or md5_expected}），删除后重新下载")
                    part.unlink()
                    meta_path.unlink(missing_ok=True)
                    continue
            LOG.info("MD5 校验通过")
        os.replace(part, dest)
        meta_path.unlink(missing_ok=True)
        atomic_write_text(dest.with_name(dest.name + ".md5"), f"{md5_expected or '未校验'}  {dest.name}\n")
        return dest
    raise SystemExit(f"下载 {max_rounds} 轮仍未通过 MD5 校验，请稍后重试或手动下载后用 --pbf 指定文件。")


# ===========================================================================
# 代码块 2：分类规则与写出（两种提取工具共用）
# 目的：同一套规则判断一个 OSM 要素属于公园、绿道、河道中的哪一类；分批写入 GeoPackage，
#       每批计算面积或长度。写到临时文件，全部完成后改名，中断不会留下半截的正式文件。
# 结果：osm_parks_greenways.gpkg 的 parks、greenways、rivers 三个图层。
# ===========================================================================
def feature_name(tags: dict) -> str:
    return tags.get("name") or tags.get("name:zh") or tags.get("name:zh-Hans") or ""


def classify_polygon(tags: dict) -> str | None:
    le = tags.get("leisure")
    if le == "park" or (le == "garden" and "公园" in feature_name(tags)):
        return "parks"
    if tags.get("waterway") == "riverbank" or (tags.get("natural") == "water" and tags.get("water") in ("river", "canal")):
        return "rivers"
    return None


AREA_KEYS = ("leisure", "landuse", "natural", "building", "amenity", "place", "waterway")


def is_area_like(tags: dict) -> bool:
    """没有 highway 标签、却带有面状地物标签的 way（如名称含绿道的公园轮廓）不当作绿道线。"""
    return "highway" not in tags and (tags.get("area") == "yes" or any(k in tags for k in AREA_KEYS))


def classify_line(tags: dict, way_id: int, route_ways: dict) -> str | None:
    """返回绿道规则（name、cycleway、route），不是绿道时返回 None。"""
    if tags.get("highway") == "cycleway":
        return "cycleway"
    if is_area_like(tags):
        return None
    if any(k in feature_name(tags) for k in GREEN_NAMES):
        return "name"
    if way_id in route_ways:
        return "route"
    return None


def is_green_route(tags: dict) -> bool:
    name = feature_name(tags)
    return tags.get("route") == "bicycle" or (tags.get("type") == "route" and any(k in name for k in GREEN_NAMES))


def record(osm_id: str, tags: dict, rule: str = "", route_nm: str = "") -> dict:
    rec = {"osm_id": osm_id, "name": feature_name(tags), "rule": rule, "route_nm": route_nm}
    for k in TAG_FIELDS:
        rec[k] = tags.get(k, "")
    return rec


class LayerWriter:
    def __init__(self, path: Path, flush_n: int = 20000):
        self.final = path
        self.tmp = path.with_name(path.stem + ".partial.gpkg")
        if self.tmp.exists():
            self.tmp.unlink()
        self.flush_n = flush_n
        self.buf = {k: [] for k in LAYERS}
        self.count = {k: 0 for k in LAYERS}
        self.started: set = set()

    def add(self, layer: str, rec: dict, geom):
        self.buf[layer].append((rec, geom))
        if len(self.buf[layer]) >= self.flush_n:
            self.flush(layer)

    def flush(self, layer: str):
        import geopandas as gpd
        import pyogrio
        import shapely
        items = self.buf[layer]
        if not items and layer in self.started:
            return
        geoms = [g for _, g in items]
        df = pd.DataFrame([r for r, _ in items], columns=FIELDS)
        gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries(geoms, crs=4326))
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
        if LAYERS[layer] == "MultiPolygon" and len(gdf):
            bad = ~gdf.geometry.is_valid
            if bad.any():                    # 自相交等无效面先修复，只保留面状部分（GEE 上传时无效面会报错）
                fixed = []
                for g in shapely.make_valid(gdf.geometry[bad].to_numpy()):
                    parts = [p for p in shapely.get_parts(g) if p.geom_type in ("Polygon", "MultiPolygon")]
                    fixed.append(shapely.union_all(parts) if parts else None)
                gdf.loc[bad, "geometry"] = fixed
                gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
        proj = gdf.geometry.to_crs(CHINA_ALBERS)
        if LAYERS[layer] == "MultiPolygon":
            gdf["area_m2"] = proj.area.round(1)
        else:
            gdf["length_m"] = proj.length.round(1)
        pyogrio.write_dataframe(gdf, self.tmp, layer=layer, driver="GPKG", append=layer in self.started,
                                geometry_type=LAYERS[layer], promote_to_multi=LAYERS[layer] == "MultiPolygon")
        self.started.add(layer)
        self.count[layer] += len(gdf)
        self.buf[layer] = []

    def close(self):
        for layer in LAYERS:
            self.flush(layer)
        os.replace(self.tmp, self.final)
        LOG.info("已写出 " + str(self.final) + "：" + "，".join(f"{k} {v} 个" for k, v in self.count.items()))


# ===========================================================================
# 代码块 3A：用 osmium-tool 命令行提取
# 目的：tags-filter 一次读完全国文件，筛出候选要素；cat 导出路线关系（OPL 文本），得到路线成员 way；
#       export 把候选要素导出为 GeoJSONSeq，逐行读入并分类。每一步的产物先写临时名再改名，已完成的步骤续跑时跳过。
# 结果：写入 LayerWriter；终端每读入 20 万个候选要素打印一次进度。
# ===========================================================================
def _run(cmd: list, what: str):
    LOG.info(f"{what}：{' '.join(map(str, cmd))}")
    t0 = time.time()
    r = subprocess.run([str(c) for c in cmd])
    if r.returncode != 0:
        raise SystemExit(f"{what} 失败（退出码 {r.returncode}），请检查上面 osmium 的报错信息")
    LOG.info(f"{what} 完成，用时 {(time.time() - t0) / 60:.1f} min")


def _step(out: Path, src: Path, cmd_builder, what: str):
    """out 比 src 新时视为已完成（断点续跑）；否则写到临时文件再改名。"""
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        LOG.info(f"{what}：已有结果 {out.name}，跳过（断点续跑）")
        return
    tmp = out.with_name(out.name.replace(".", ".tmp.", 1))
    _run(cmd_builder(tmp), what)
    os.replace(tmp, out)


_OPL_ESC = re.compile(r"%([0-9a-fA-F]+)%")


def _opl_unescape(s: str) -> str:
    return _OPL_ESC.sub(lambda m: chr(int(m.group(1), 16)), s)


def parse_route_ways(opl_path: Path) -> dict:
    """从 OPL 文本读出路线关系（route=bicycle 或名称含绿道、碧道）的 way 成员：way_id → 路线名称。"""
    ways: dict = {}
    with open(opl_path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("r"):
                continue
            tags, members = {}, []
            for field in line.rstrip("\n").split(" "):
                if field.startswith("T") and len(field) > 1:
                    for kv in field[1:].split(","):
                        if "=" in kv:
                            k, v = kv.split("=", 1)
                            tags[_opl_unescape(k)] = _opl_unescape(v)
                elif field.startswith("M") and len(field) > 1:
                    members = field[1:].split(",")
            if not is_green_route(tags):
                continue
            rname = feature_name(tags) or tags.get("ref", "")
            for m in members:
                if m.startswith("w"):
                    ref = m[1:].split("@", 1)[0]
                    if ref.isdigit():
                        ways.setdefault(int(ref), rname)
    return ways


def _area_osm_id(fid: str) -> str:
    """osmium export 的面要素 id 为 a+数字：偶数来自 way（数字/2），奇数来自关系（(数字-1)/2）。"""
    if fid.startswith("a") and fid[1:].isdigit():
        n = int(fid[1:])
        return f"w{n // 2}" if n % 2 == 0 else f"r{(n - 1) // 2}"
    return fid


def extract_cli(pbf: Path, work: Path, writer: LayerWriter, report_every: int = 200_000):
    from shapely.geometry import shape
    osmium = shutil.which("osmium")
    filt = work / "candidates.osm.pbf"
    _step(filt, pbf, lambda o: [osmium, "tags-filter", pbf, *FILTER_EXPRS, "-o", o, "-O"], "osmium tags-filter 筛选候选要素")
    opl = work / "relations.opl"
    _step(opl, filt, lambda o: [osmium, "cat", filt, "-t", "relation", "-f", "opl", "-o", o, "-O"], "osmium cat 导出关系")
    seq = work / "candidates.geojsonseq"
    _step(seq, filt, lambda o: [osmium, "export", filt, "-f", "geojsonseq", "-u", "type_id",
                                "--geometry-types", "linestring,polygon", "-x", "print_record_separator=false",
                                "-o", o, "-O"], "osmium export 导出几何")
    route_ways = parse_route_ways(opl)
    LOG.info(f"路线关系成员 way：{len(route_ways)} 条")
    n, t0 = 0, time.time()
    with open(seq, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lstrip("\x1e")
            if not line:
                continue
            feat = json.loads(line)
            tags = feat.get("properties") or {}
            fid = str(feat.get("id", ""))
            gtype = (feat.get("geometry") or {}).get("type", "")
            n += 1
            if gtype in ("Polygon", "MultiPolygon"):
                layer = classify_polygon(tags)
                if layer:
                    writer.add(layer, record(_area_osm_id(fid), tags), shape(feat["geometry"]))
            elif gtype == "LineString" and fid.startswith("w"):
                wid = int(fid[1:]) if fid[1:].isdigit() else -1
                rule = classify_line(tags, wid, route_ways)
                if rule:
                    writer.add("greenways", record(fid, tags, rule, route_ways.get(wid, "")), shape(feat["geometry"]))
            if n % report_every == 0:
                LOG.info(f"[提取] 已读入 {n} 个候选要素 | 公园 {writer.count['parks'] + len(writer.buf['parks'])}"
                         f" | 绿道 {writer.count['greenways'] + len(writer.buf['greenways'])}"
                         f" | 河道 {writer.count['rivers'] + len(writer.buf['rivers'])} | 用时 {(time.time() - t0) / 60:.1f} min")
    LOG.info(f"[提取] 候选要素共 {n} 个，逐行分类完成")


# ===========================================================================
# 代码块 3B：用 pyosmium 提取
# 目的：第一遍只读关系，记下路线成员 way；第二遍读取节点、way 与面（pyosmium 自动把闭合 way 与多面关系组装成面），
#       节点坐标索引写在磁盘文件（sparse_file_array）上，内存占用小。每读 200 万条 way 打印一次进度。
# 结果：写入 LayerWriter。
# ===========================================================================
def extract_pyosmium(pbf: Path, work: Path, writer: LayerWriter, report_every: int = 2_000_000):
    import osmium
    import shapely

    class Routes(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.ways: dict = {}

        def relation(self, r):
            tags = {t.k: t.v for t in r.tags}
            if not is_green_route(tags):
                return
            rname = feature_name(tags) or tags.get("ref", "")
            for m in r.members:
                if m.type == "w":
                    self.ways.setdefault(m.ref, rname)

    class Extract(osmium.SimpleHandler):
        def __init__(self, route_ways):
            super().__init__()
            self.route_ways = route_ways
            self.wkb = osmium.geom.WKBFactory()
            self.n_ways = 0
            self.n_bad = 0
            self.t0 = time.time()

        def way(self, w):
            self.n_ways += 1
            if self.n_ways % report_every == 0:
                LOG.info(f"[提取] 已读取 {self.n_ways} 条 way | 公园 {writer.count['parks'] + len(writer.buf['parks'])}"
                         f" | 绿道 {writer.count['greenways'] + len(writer.buf['greenways'])}"
                         f" | 河道 {writer.count['rivers'] + len(writer.buf['rivers'])} | 用时 {(time.time() - self.t0) / 60:.1f} min")
            t = w.tags
            if not ("highway" in t or "name" in t or w.id in self.route_ways):
                return
            tags = {x.k: x.v for x in t}
            rule = classify_line(tags, w.id, self.route_ways)
            if not rule:
                return
            try:
                geom = shapely.from_wkb(self.wkb.create_linestring(w))
            except Exception:  # noqa: BLE001  缺节点或退化的 way 跳过并计数
                self.n_bad += 1
                return
            writer.add("greenways", record(f"w{w.id}", tags, rule, self.route_ways.get(w.id, "")), geom)

        def area(self, a):
            t = a.tags
            if not ("leisure" in t or "waterway" in t or "natural" in t):
                return
            tags = {x.k: x.v for x in t}
            layer = classify_polygon(tags)
            if not layer:
                return
            try:
                geom = shapely.from_wkb(self.wkb.create_multipolygon(a))
            except Exception:  # noqa: BLE001
                self.n_bad += 1
                return
            writer.add(layer, record(("w" if a.from_way() else "r") + str(a.orig_id()), tags), geom)

    LOG.info("pyosmium 第一遍：读取路线关系")
    rt = Routes()
    rt.apply_file(str(pbf))
    LOG.info(f"路线关系成员 way：{len(rt.ways)} 条")
    idx_file = work / "node_locations.idx"
    idx_file.unlink(missing_ok=True)
    LOG.info(f"pyosmium 第二遍：读取几何（节点坐标索引写在 {idx_file}）")
    ex = Extract(rt.ways)
    ex.apply_file(str(pbf), locations=True, idx=f"sparse_file_array,{idx_file}")
    idx_file.unlink(missing_ok=True)
    if ex.n_bad:
        LOG.warning(f"{ex.n_bad} 个要素缺少节点或几何无效，已跳过")
    LOG.info(f"[提取] 共读取 {ex.n_ways} 条 way，完成")


def pick_engine(choice: str) -> str:
    if choice in ("auto", "cli") and shutil.which("osmium"):
        return "cli"
    if choice == "cli":
        raise SystemExit("找不到 osmium 命令。请运行 brew install osmium-tool，或改用 --engine pyosmium。")
    try:
        import osmium  # noqa: F401
        return "pyosmium"
    except ImportError:
        raise SystemExit("没有可用的 OSM 提取工具。二选一安装：\n"
                         "  A. brew install osmium-tool（推荐，需先安装 Homebrew）\n"
                         "  B. pip install osmium")


# ===========================================================================
# 代码块 4：按省打包
# 目的：用 00 输出的 units_full.gpkg 合并出省界；每个要素取代表点（面）或中点（线），落在哪个省就归入哪个省，
#       海岸线附近落在省界外 5 km 内的归入最近的省，其余不进入分省包（多为港澳台、境外或海上）。
#       各省三类要素分别写成 Shapefile 并压缩，已存在的压缩包跳过（断点续跑），每完成一个省打印一次进度。
# 结果：gee_upload/<省代码两位>_<图层>.zip；osm_province_summary.csv。
# ===========================================================================
def province_polygons(units_path: Path, cache: Path):
    import geopandas as gpd
    if cache.exists() and cache.stat().st_mtime >= units_path.stat().st_mtime:
        return gpd.read_file(cache)
    LOG.info("由分析单元合并省界（只做一次，结果缓存在 work/provinces.gpkg）")
    u = gpd.read_file(units_path, columns=["prov_code", "geometry"]).to_crs(4326)
    u["prov"] = u["prov_code"].astype(str).str[:2]
    prov = u.dissolve(by="prov", as_index=False)[["prov", "geometry"]]
    tmp = cache.with_name(cache.stem + ".tmp.gpkg")
    prov.to_file(tmp, driver="GPKG")
    os.replace(tmp, cache)
    return prov


def assign_province(gdf, prov):
    import geopandas as gpd
    if gdf.empty:
        return pd.Series([], dtype=object, index=gdf.index)
    g = gdf.geometry.to_crs(CHINA_ALBERS)
    pts = g.representative_point() if gdf.geom_type.str.contains("Polygon").any() else g.interpolate(0.5, normalized=True)
    pts = gpd.GeoDataFrame(geometry=pts, crs=CHINA_ALBERS)
    pa = prov.to_crs(CHINA_ALBERS)
    j = gpd.sjoin(pts, pa, predicate="within", how="left")
    j = j[~j.index.duplicated()]
    out = j["prov"].reindex(gdf.index)
    miss = out.isna()
    if miss.any():
        near = gpd.sjoin_nearest(pts[miss], pa, max_distance=5000, how="left")
        near = near[~near.index.duplicated()]
        out.loc[miss] = near["prov"].reindex(out.index[miss]).to_numpy()
    return out


def write_zip(gdf, zpath: Path, layer: str):
    tmpdir = zpath.parent / f".{zpath.stem}.tmpdir"
    shutil.rmtree(tmpdir, ignore_errors=True)
    tmpdir.mkdir(parents=True)
    shp = tmpdir / f"{zpath.stem}.shp"
    import pyogrio
    pyogrio.write_dataframe(gdf, shp, driver="ESRI Shapefile", encoding="UTF-8", geometry_type=LAYERS[layer],
                            promote_to_multi=LAYERS[layer] == "MultiPolygon")
    tmpzip = zpath.with_name(zpath.name + ".tmp")
    with zipfile.ZipFile(tmpzip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(tmpdir.iterdir()):
            z.write(f, f.name)
    os.replace(tmpzip, zpath)
    shutil.rmtree(tmpdir, ignore_errors=True)


def split_provinces(gpkg: Path, units_path: Path, work: Path, out_dir: Path, only: set | None, national: bool,
                    refresh: bool):
    import geopandas as gpd
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {layer: gpd.read_file(gpkg, layer=layer) for layer in LAYERS}
    stale = refresh or any(p.stat().st_mtime < gpkg.stat().st_mtime for p in out_dir.glob("*.zip"))
    if stale:
        for p in out_dir.glob("*.zip"):          # GPKG 比压缩包新（重新提取过），旧压缩包作废
            p.unlink()
    if units_path.exists():
        prov = province_polygons(units_path, work / "provinces.gpkg")
        for layer, gdf in data.items():
            gdf["prov_code"] = assign_province(gdf, prov)
            n_out = int(gdf["prov_code"].isna().sum())
            if n_out:
                LOG.info(f"{layer}：{n_out} 个要素不在任何省界内（多为港澳台、境外或海上），不进入分省包")
        provs = sorted(prov["prov"].unique())
    else:
        LOG.warning(f"找不到 {units_path}，无法按省拆分，只输出全国包。先运行 00_prepare_units.py 可得到分省包。")
        for gdf in data.values():
            gdf["prov_code"] = None
        provs, national = [], True

    # 各省统计（全部省份，用于判断 OSM 完整度）
    rows = []
    for p in provs:
        r = {"prov_code": p + "0000"}
        for layer, gdf in data.items():
            sub = gdf[gdf["prov_code"] == p]
            r[f"n_{layer}"] = len(sub)
            if "area_m2" in sub:
                r[f"{layer}_area_km2"] = round(float(sub["area_m2"].sum()) / 1e6, 3)
            if "length_m" in sub:
                r[f"{layer}_length_km"] = round(float(sub["length_m"].sum()) / 1e3, 3)
        rows.append(r)
    if rows:
        atomic_write_csv(pd.DataFrame(rows), gpkg.parent / "osm_province_summary.csv")

    todo = [p for p in provs if not only or p in only]
    prog = ChunkProgress(len(todo) + (1 if national else 0), LOG, label="省")
    for i, p in enumerate(todo):
        zips = {layer: out_dir / f"{p}_{layer}.zip" for layer in LAYERS}
        if all(z.exists() for z in zips.values()):
            prog.skip(i, f"{p} 已打包，跳过（断点续跑）")
            continue
        prog.start(i, f"省代码 {p}")
        counts = []
        for layer, z in zips.items():
            if not z.exists():
                sub = data[layer][data[layer]["prov_code"] == p]
                write_zip(sub, z, layer)
                counts.append(f"{layer} {len(sub)} 个")
        LOG.info(f"省代码 {p} 已打包：{'，'.join(counts)}")
        prog.finish(i)
    if national:
        i = len(todo)
        zips = {layer: out_dir / f"all_{layer}.zip" for layer in LAYERS}
        if all(z.exists() for z in zips.values()):
            prog.skip(i, "全国包已存在，跳过（断点续跑）")
        else:
            prog.start(i, "全国包")
            for layer, z in zips.items():
                if not z.exists():
                    write_zip(data[layer], z, layer)
            LOG.info("全国包已打包：" + "，".join(f"{k} {len(g)} 个" for k, g in data.items()))
            prog.finish(i)
    prog.summary()
    LOG.info(f"上传用压缩包在 {out_dir}。在 GEE Code Editor 的 Assets 中选 NEW、Shape files 上传，"
             "再把资产路径填入 config.yaml 的 gee.park_asset、gee.greenway_asset、gee.river_asset。")


# ===========================================================================
# 代码块 5：主流程
# 目的：下载 → 提取（GPKG 已存在则跳过）→ 按省打包（已有压缩包跳过）。
# 结果：数据/中间/osm/ 下的全部输出。
# ===========================================================================
def main():
    ap = argparse.ArgumentParser(description="下载 OSM 中国数据，提取公园、绿道、河道并按省打包")
    ap.add_argument("--url", default=DEFAULT_URL, help="pbf 下载地址")
    ap.add_argument("--pbf", help="使用已下载的 pbf 文件，跳过下载")
    ap.add_argument("--download-only", action="store_true", help="只下载")
    ap.add_argument("--engine", choices=("auto", "cli", "pyosmium"), default="auto", help="提取工具")
    ap.add_argument("--province", help="只打包这些省（两位代码，逗号分隔，如 44 或 44,45）")
    ap.add_argument("--national", action="store_true", help="另外输出全国压缩包 all_*.zip")
    ap.add_argument("--refresh", action="store_true", help="重新下载最新数据并重新提取、打包")
    ap.add_argument("--redo-extract", action="store_true", help="不重新下载，但重新提取与打包")
    ap.add_argument("--chunk-mb", type=float, default=20, help="下载时每多少 MB 打印一次进度（默认 20）")
    ap.add_argument("--retries", type=int, default=8, help="下载连续失败的最多重试次数（默认 8）")
    ap.add_argument("--retry-delay", type=float, default=10, help="首次重试等待秒数，之后每次加倍（默认 10）")
    ap.add_argument("--no-md5", action="store_true", help="不做 MD5 校验（服务器没有 .md5 文件时用）")
    ap.add_argument("--out-dir", help="输出文件夹（默认 数据/中间/osm）")
    args = ap.parse_args()

    out = Path(args.out_dir).expanduser().resolve() if args.out_dir else resolve("数据/中间/osm")
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    gpkg = out / "osm_parks_greenways.gpkg"

    # 5a. 下载
    if args.pbf:
        pbf = Path(args.pbf).expanduser().resolve()
        if not pbf.exists():
            raise SystemExit(f"找不到 {pbf}")
    else:
        pbf = out / "download" / Path(args.url).name
        if pbf.exists() and not args.refresh:
            LOG.info(f"已有下载文件 {pbf.name}（{time.strftime('%Y-%m-%d', time.localtime(pbf.stat().st_mtime))}），"
                     "跳过下载。需要最新数据时加 --refresh。")
        else:
            download(args.url, pbf, args.chunk_mb, args.retries, args.retry_delay, verify_md5=not args.no_md5)
    if args.download_only:
        return

    # 5b. 提取
    if gpkg.exists() and (args.refresh or args.redo_extract or gpkg.stat().st_mtime < pbf.stat().st_mtime):
        gpkg.unlink()
    if gpkg.exists():
        LOG.info(f"已有 {gpkg.name}，跳过提取（断点续跑）。需要重新提取时加 --redo-extract。")
    else:
        engine = pick_engine(args.engine)
        LOG.info(f"提取工具：{'osmium-tool 命令行' if engine == 'cli' else 'pyosmium'}；输入 {pbf}")
        writer = LayerWriter(gpkg)
        if engine == "cli":
            extract_cli(pbf, work, writer)
        else:
            extract_pyosmium(pbf, work, writer)
        writer.close()

    # 5c. 按省打包
    cfg = load_config()
    units_path = resolve(cfg["units"]["out_dir"]) / "units_full.gpkg"
    only = {p.strip()[:2] for p in args.province.split(",")} if args.province else None
    split_provinces(gpkg, units_path, work, out / "gee_upload", only, args.national,
                    args.refresh or args.redo_extract)


if __name__ == "__main__":
    main()
