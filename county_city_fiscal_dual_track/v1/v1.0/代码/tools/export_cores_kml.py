# -*- coding: utf-8 -*-
"""
tools/export_cores_kml.py  把中心建成区导出为 KML，在 Google Earth 中目视核对，并生成核对表

为什么需要：01 用 GHSL 建成栅格自动识别县城和中心城区。河流会把城区切成两块，闭运算会把相邻村庄或工业园连进来，
驻地点有误时会选中别的斑块。这些问题要靠熟悉当地的人对照影像判断，广东试点先核对约 20 个熟悉的县城
和广州、深圳、珠海的中心城区。

在哪里运行：Mac 终端 (Terminal)
    conda activate fiscal
    cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
    python tools/export_cores_kml.py --province 44                    # 广东全部单元
    python tools/export_cores_kml.py --units CP440100,CP440300,440183 # 指定单元（市辖区单元写 CP 加地级代码）
    python tools/export_cores_kml.py --province 44 --out ~/Desktop/广东中心建成区.kml
    python tools/export_cores_kml.py --did --province 44              # 准实验县级单元层（01 --units did 的结果）

输入：数据/中间/gee/core_polygons_2020.geojson（01 的输出；--did 时为 数据/中间/gee/did/ 下的同名文件）
      数据/中间/units/units_table.csv（成员名称；--did 时为 units_did_table.csv）
      数据/中间/units/seats.geojson（驻地点，有则一并画出；--did 时为 seats_did.geojson）
输出：KML 文件，默认 数据/中间/qa/cores_kml/cores_<范围>.kml。每个中心建成区一个地标 (placemark)，
      属性含 unit_id、成员名称、识别方法 core_method、面积 core_area_km2、闭运算半径。
      同名核对表 cores_<范围>_核对表.csv，列为 unit_id、name、core_ok、problem_type、note，后附参考列。
      再次运行不会覆盖核对表中已经填写的内容，只补充新单元、更新参考列。

在 Google Earth 中核对：
  1. 打开 Google Earth Pro 桌面版（免费），在文件菜单中打开 KML。网页版 earth.google.com 也可以在项目中导入 KML。
  2. 左侧列表按省展开，双击单元即飞到该处。红色边线为中心建成区，橙色边线表示没有找到建成斑块、退化为几何中心
     1 km 缓冲的单元，黄色图钉为驻地点。
  3. 对照影像判断边界是否合理。常见问题有四类。河流切分，指河对岸的城区没有被包括进来。连带村庄，指边界连进了
     周边村庄、工业园或邻县城区。驻地错误，指选中的斑块不含县城，通常是驻地点坐标有误。其他问题写在 note 中。
  4. 在核对表中每行填 core_ok（Y 或 N）。填 N 时，problem_type 从 河流切分、连带村庄、驻地错误、其他 中选一个，
     note 写具体情况。再次运行本脚本会统计已核对的单元和各类问题的个数。
"""
from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import atomic_write_csv, atomic_write_text, get_logger, load_config, read_table, resolve  # noqa: E402

LOG = get_logger("export_cores_kml")

METHOD_LABEL = {"seat_patch": "含驻地点的斑块", "largest_patch": "单元内最大斑块",
                "fallback_centroid_1km": "未找到建成斑块，几何中心 1 km 缓冲"}
PROBLEM_TYPES = ("河流切分", "连带村庄", "驻地错误", "其他")
CHECK_COLS = ["unit_id", "name", "core_ok", "problem_type", "note"]
REF_COLS = ["unit_type", "core_method", "core_area_km2"]


# ---------------------------------------------------------------------------
# 代码块 1：读取中心建成区、名称与驻地点
# 目的：按 --province 或 --units 选出要导出的单元；名称取自 00 的单元属性表。
# 结果：features（GeoJSON 要素列表）、names（unit_id → 名称）、types、seats（unit_id → [经度, 纬度]）。
# ---------------------------------------------------------------------------
def code_of(uid: str) -> str:
    return uid[2:] if uid.startswith("CP") else uid


def load_inputs(cfg: dict, did: bool, cores_path: str | None):
    gee_dir = resolve(cfg["gee"]["out_dir"]) / ("did" if did else "")
    units_dir = resolve(cfg["units"]["out_dir"])
    cp = Path(cores_path).expanduser().resolve() if cores_path else gee_dir / "core_polygons_2020.geojson"
    if not cp.exists():
        raise SystemExit(f"找不到 {cp}。请先运行 01_gee_extract_rs.py{' --units did' if did else ''}"
                         "（或 --merge-only 合并已完成的批次）。")
    features = json.loads(cp.read_text(encoding="utf-8")).get("features", [])
    names, types = {}, {}
    tpath = units_dir / ("units_did_table.csv" if did else "units_table.csv")
    if tpath.exists():
        t = read_table(tpath, code_cols=("unit_id", "adcode", "prov_code", "pref_code"))
        col = "name" if "name" in t else "member_names"
        for uid, nm in zip(t["unit_id"], t[col] if col in t else [""] * len(t)):
            nm = nm if isinstance(nm, str) else ""
            parts = [x for x in nm.split("、") if x]
            if len(parts) > 3:        # 市辖区单元成员多，地标名称只列前三个
                nm = "、".join(parts[:3]) + f"等 {len(parts)} 个区县"
            names[str(uid)] = nm
        if "unit_type" in t:
            types = dict(zip(t["unit_id"].astype(str), t["unit_type"].astype(str)))
    else:
        LOG.warning(f"找不到 {tpath.name}，地标只显示 unit_id。请先运行 00_prepare_units.py。")
    seats = {}
    spath = units_dir / ("seats_did.geojson" if did else "seats.geojson")
    if spath.exists():
        for f in json.loads(spath.read_text(encoding="utf-8")).get("features", []):
            g = f.get("geometry") or {}
            if g.get("type") == "Point":
                seats.setdefault(str(f["properties"].get("unit_id")), g["coordinates"][:2])
    return cp, features, names, types, seats


def select(features: list, provinces: set | None, units: set | None) -> list:
    out = []
    for f in features:
        uid = str((f.get("properties") or {}).get("unit_id"))
        if provinces and code_of(uid)[:2] not in provinces:
            continue
        if units and uid not in units and code_of(uid) not in units:
            continue
        out.append(f)
    return sorted(out, key=lambda f: str(f["properties"]["unit_id"]))


# ---------------------------------------------------------------------------
# 代码块 2：生成 KML 文本
# 目的：直接写 KML（不依赖其他软件包）。面、多面与几何集合中的面都写出，内环写成 innerBoundaryIs；
#       坐标保留 6 位小数（约 0.1 m）。属性同时写进弹出说明框和 ExtendedData，Google Earth 中点击地标即可看到。
# 结果：KML 字符串。
# ---------------------------------------------------------------------------
STYLES = """  <Style id="core"><LineStyle><color>ff0000ff</color><width>2.5</width></LineStyle>
    <PolyStyle><color>330000ff</color></PolyStyle></Style>
  <Style id="fallback"><LineStyle><color>ff0080ff</color><width>2.5</width></LineStyle>
    <PolyStyle><color>330080ff</color></PolyStyle></Style>
  <Style id="seat"><IconStyle><color>ff00ffff</color><scale>1.1</scale>
    <Icon><href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href></Icon></IconStyle></Style>
"""


def _ring(coords) -> str:
    pts = " ".join(f"{c[0]:.6f},{c[1]:.6f},0" for c in coords)
    return f"<LinearRing><coordinates>{pts}</coordinates></LinearRing>"


def _polygon(rings) -> str:
    if not rings:
        return ""
    inner = "".join(f"<innerBoundaryIs>{_ring(r)}</innerBoundaryIs>" for r in rings[1:])
    return f"<Polygon><tessellate>1</tessellate><outerBoundaryIs>{_ring(rings[0])}</outerBoundaryIs>{inner}</Polygon>"


def polygons_of(geom: dict) -> list:
    """GeoJSON 几何中的全部面（每个面是环的列表）。线和点不写进中心建成区图层。"""
    if not geom:
        return []
    t = geom.get("type")
    if t == "Polygon":
        return [geom["coordinates"]]
    if t == "MultiPolygon":
        return list(geom["coordinates"])
    if t == "GeometryCollection":
        return [p for g in geom.get("geometries", []) for p in polygons_of(g)]
    return []


def geom_kml(geom: dict) -> str:
    polys = [p for p in polygons_of(geom) if p]
    if not polys:
        return ""
    body = "".join(_polygon(p) for p in polys)
    return body if len(polys) == 1 else f"<MultiGeometry>{body}</MultiGeometry>"


def _num(x, nd=3):
    try:
        return round(float(x), nd)
    except (TypeError, ValueError):
        return None


def placemark(f: dict, names: dict, types: dict) -> tuple[str, dict]:
    p = f.get("properties") or {}
    uid = str(p.get("unit_id"))
    method = str(p.get("core_method", ""))
    a = _num(p.get("core_area_m2"), 1)
    area = round(a / 1e6, 3) if a is not None else None
    info = {"unit_id": uid, "成员": names.get(uid, ""), "单元类型": types.get(uid, ""),
            "core_method": f"{method}（{METHOD_LABEL.get(method, '未知')}）", "core_area_km2": area,
            "core_closing_m": p.get("core_closing_m", "")}
    rows = "".join(f"<tr><td>{escape(str(k))}</td><td>{escape('' if v is None else str(v))}</td></tr>"
                   for k, v in info.items())
    ext = "".join(f'<Data name="{escape(str(k))}"><value>{escape("" if v is None else str(v))}</value></Data>'
                  for k, v in info.items())
    style = "#fallback" if method == "fallback_centroid_1km" else "#core"
    title = escape(f"{uid} {names.get(uid, '')}".strip())
    kml = (f"<Placemark><name>{title}</name><styleUrl>{style}</styleUrl>"
           f"<description><![CDATA[<table border=\"1\" cellpadding=\"3\">{rows}</table>]]></description>"
           f"<ExtendedData>{ext}</ExtendedData>{geom_kml(f.get('geometry'))}</Placemark>")
    ref = {"unit_type": types.get(uid, ""), "core_method": method, "core_area_km2": area}
    return kml, ref


def build_kml(features: list, names: dict, types: dict, seats: dict, title: str) -> tuple[str, list, int]:
    by_prov: dict = {}
    refs, n_empty = [], 0
    for f in features:
        uid = str(f["properties"]["unit_id"])
        pm, ref = placemark(f, names, types)
        if "<Polygon>" not in pm:
            n_empty += 1
        parts = [pm]
        if uid in seats:
            lon, lat = seats[uid]
            parts.append(f"<Placemark><name>{escape(uid)} 驻地</name><styleUrl>#seat</styleUrl>"
                         f"<Point><coordinates>{lon:.6f},{lat:.6f},0</coordinates></Point></Placemark>")
        by_prov.setdefault(code_of(uid)[:2], []).append("\n".join(parts))
        refs.append({"unit_id": uid, "name": names.get(uid, ""), **ref})
    folders = "".join(f"<Folder><name>省代码 {pv}（{len(pms)} 个单元）</name>\n" + "\n".join(pms) + "\n</Folder>\n"
                      for pv, pms in sorted(by_prov.items()))
    kml = ('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n'
           f"<name>{escape(title)}</name>\n{STYLES}{folders}</Document>\n</kml>\n")
    return kml, refs, n_empty


# ---------------------------------------------------------------------------
# 代码块 3：核对表（保留已填写内容）
# 目的：新建或更新核对表。已有核对表时，研究者填写的 core_ok、problem_type、note 保留不动，
#       只更新名称与参考列，并补上新导出的单元；同时检查填写是否规范，统计核对进度。
# 结果：<KML 同名>_核对表.csv。
# ---------------------------------------------------------------------------
def update_checklist(path: Path, refs: list) -> None:
    new = pd.DataFrame(refs, columns=["unit_id", "name"] + REF_COLS)
    if path.exists():
        old = read_table(path, code_cols=("unit_id",))
        for c in CHECK_COLS:
            if c not in old:
                old[c] = ""
        old = old.astype({c: "string" for c in CHECK_COLS}).fillna("")
        keep = old[CHECK_COLS[2:] + ["unit_id"]]
        merged = new.merge(keep, on="unit_id", how="left")
        extra = old[~old["unit_id"].isin(new["unit_id"])]        # 这次没有导出、但以前核对过的单元也保留
        out = pd.concat([merged, extra.reindex(columns=merged.columns)], ignore_index=True) if len(extra) else merged
    else:
        out = new.assign(core_ok="", problem_type="", note="")
    out = out.reindex(columns=CHECK_COLS + REF_COLS)
    for c in ("core_ok", "problem_type", "note"):
        out[c] = out[c].astype("string").fillna("")
    atomic_write_csv(out, path)

    ok = out["core_ok"].str.strip().str.upper()
    bad_ok = out[~ok.isin(["", "Y", "N"])]
    bad_type = out[ok.eq("N") & ~out["problem_type"].str.strip().isin(PROBLEM_TYPES)]
    done = int(ok.isin(["Y", "N"]).sum())
    if done:
        LOG.info(f"核对进度：已核对 {done} / {len(out)} 个单元，合理 {int(ok.eq('Y').sum())} 个，有问题 {int(ok.eq('N').sum())} 个")
        counts = out.loc[ok.eq("N"), "problem_type"].str.strip().value_counts()
        if len(counts):
            LOG.info("问题类型：" + "，".join(f"{k or '未填'} {v} 个" for k, v in counts.items()))
    if len(bad_ok):
        LOG.warning(f"core_ok 只能填 Y 或 N，以下单元填写不规范：{bad_ok['unit_id'].tolist()[:20]}")
    if len(bad_type):
        LOG.warning(f"core_ok 为 N 的单元，problem_type 应为 {'、'.join(PROBLEM_TYPES)} 之一，"
                    f"以下单元需要补填：{bad_type['unit_id'].tolist()[:20]}")


# ---------------------------------------------------------------------------
# 代码块 4：命令行入口
# 目的：解析参数，导出 KML 与核对表。
# 结果：终端打印导出的单元数与文件位置。
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="中心建成区导出为 KML，并生成核对表")
    ap.add_argument("--province", help="省级代码前两位，逗号分隔，如 44 或 44,45")
    ap.add_argument("--units", help="unit_id，逗号分隔，如 CP440100,440183")
    ap.add_argument("--out", help="输出 KML 路径（默认 数据/中间/qa/cores_kml/cores_<范围>.kml）")
    ap.add_argument("--did", action="store_true", help="导出准实验县级单元层（01 --units did 的结果）")
    ap.add_argument("--cores", help="直接指定中心建成区 GeoJSON 文件")
    args = ap.parse_args()

    cfg = load_config()
    provinces = {p.strip()[:2] for p in args.province.split(",") if p.strip()} if args.province else None
    units = {u.strip() for u in args.units.split(",") if u.strip()} if args.units else None
    src, features, names, types, seats = load_inputs(cfg, args.did, args.cores)
    sel = select(features, provinces, units)
    if not sel:
        raise SystemExit(f"{src.name} 中没有符合条件的单元（共 {len(features)} 个）。请检查 --province 或 --units。")
    if units:
        found = {str(f["properties"]["unit_id"]) for f in sel}
        miss = [u for u in units if u not in found and u not in {code_of(x) for x in found}]
        if miss:
            LOG.warning(f"以下单元不在中心建成区文件中：{miss}")
    scope = ("prov" + "_".join(sorted(provinces))) if provinces else ("units" if units else "all")
    stem = f"cores_{'did_' if args.did else ''}{scope}"
    out = Path(args.out).expanduser().resolve() if args.out else resolve("数据/中间/qa/cores_kml") / f"{stem}.kml"
    if out.suffix.lower() != ".kml":
        out = out.with_suffix(".kml")
    kml, refs, n_empty = build_kml(sel, names, types, seats, f"中心建成区核对 {stem}")
    atomic_write_text(out, kml)
    if n_empty:
        LOG.warning(f"{n_empty} 个单元的几何为空或不是面，KML 中只有名称")
    n_seat = sum(1 for r in refs if r["unit_id"] in seats)
    LOG.info(f"已导出 {len(sel)} 个中心建成区（其中 {n_seat} 个带驻地点）→ {out}")
    update_checklist(out.with_name(out.stem + "_核对表.csv"), refs)
    LOG.info(f"核对表 → {out.with_name(out.stem + '_核对表.csv')}")


if __name__ == "__main__":
    main()
